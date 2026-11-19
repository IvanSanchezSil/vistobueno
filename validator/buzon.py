"""Buzón de una ranura para la comunicación con el userscript de depósito.

Mecanismo de intercambio entre la SPA (que publica la ficha completada
por el operador) y el userscript que corre en el navegador del operador
sobre las páginas de DSpace (que lee la ficha y confirma el depósito).

Diseño (ver docs/CONTRATO_API.md y docs/PLAN_FICHA_DEPOSITO.md §6):

- **Una sola ranura** por dirección: "última gana". Supuesto documentado:
  un operador, una tesis en vuelo a la vez.
- **Dos ventanas sobre un solo trámite**:
  - *autorelleno* (1 hora por defecto): una ficha olvidada no puede
    rellenar un formulario horas después. Al vencer, la ficha deja de
    servirse para rellenar, pero NO se borra.
  - *retención del trámite* (24 horas por defecto): la ficha canónica,
    su revisión y el estado del depósito siguen disponibles para una
    confirmación tardía (por ejemplo, un flujo de aprobación que tarda).
  La retención nunca es menor que el autorelleno.
- **Estado en memoria del proceso**: sin base de datos, sin sesiones. Un
  reinicio vacía el buzón. Las ventanas son una política inicial, no una
  garantía para todos los flujos de DSpace.
- **Thread-safe**: los endpoints síncronos de FastAPI corren en el
  threadpool, por lo que el acceso concurrente es posible.

Seguridad (docs/CONTRATO_API.md): la API no agrega cabeceras CORS, así
que una página web cualquiera en el navegador del operador no puede LEER
el contenido del buzón (contiene datos personales del estudiante). El
userscript lo lee por GM_xmlhttpRequest, que corre en el contexto de la
extensión y no está sujeto a CORS.

Contrato de confirmación: el depósito NO se infiere de una página de
ítem, de un handle ni de un reporte automático. Se registra solo cuando
el operador confirma explícitamente (`atestacion="operador"`) una
revisión concreta. El servidor genera `confirmado_en`; el `timestamp`
del clic en Depositar se conserva como fuente de la HORA del papeleo.
"""

import logging
import re
import threading
import unicodedata
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

_log = logging.getLogger(__name__)

TTL_AUTORRELLENO_POR_DEFECTO = 3600.0  # 1 hora
TTL_TRAMITE_POR_DEFECTO = 86400.0  # 24 horas

# Handle institucional del Repositorio UNT. Se exige la forma completa:
# un enlace a otro repositorio no identifica un ítem de esta institución.
HANDLE_RE = re.compile(r"^https://hdl\.handle\.net/20\.500\.14414/\d+/?$")


@dataclass(frozen=True)
class Publicacion:
    """Identidad y ventanas del trámite recién publicado."""

    tramite_id: str
    revision: int
    autofill_hasta: datetime
    retenido_hasta: datetime


@dataclass(frozen=True)
class LecturaFicha:
    """Ficha elegible para autorelleno, con la revisión que la identifica."""

    ficha: dict
    tramite_id: str
    revision: int
    autofill_hasta: datetime
    retenido_hasta: datetime


@dataclass(frozen=True)
class EstadoTramite:
    """Estado canónico completo de un trámite retenido.

    Los diccionarios son copias: el llamador no puede mutar el estado del
    buzón. `deposito` es None mientras no exista una confirmación
    explícita del operador; una revisión posterior invalida esa
    confirmación sin borrar la evidencia.
    """

    ficha: dict
    tramite_id: str
    revision: int
    inconsistencia: dict | None
    deposito: dict | None
    publicada_en: datetime
    autofill_hasta: datetime
    retenido_hasta: datetime
    autofill_habil: bool
    confirmacion_vigente: bool


class SinFichaVigente(Exception):
    """No hay un trámite retenido para aceptar la operación."""


class TramiteNoCoincide(Exception):
    """La operación pertenece a un trámite anterior."""


class RevisionNoCoincide(Exception):
    """La operación se preparó sobre una revisión que ya cambió."""


class TituloNoCoincide(Exception):
    """El título observado no identifica la ficha canónica."""


class AutoresNoCoinciden(Exception):
    """Los autores observados contradicen la ficha canónica."""


class HandleNoCoincide(Exception):
    """La conciliación intenta cambiar el ítem depositado."""


class HandleInvalido(Exception):
    """El handle no tiene la forma institucional esperada."""


class ConfirmacionInvalida(Exception):
    """La escritura no declara una confirmación explícita del operador."""


def _normalizar(texto: str) -> str:
    """Minúsculas, sin acentos y con espacios colapsados."""
    if not isinstance(texto, str):
        return ""
    sin_acentos = "".join(
        c for c in unicodedata.normalize("NFD", texto) if not unicodedata.combining(c)
    )
    return " ".join(sin_acentos.lower().split())


def _titulo_de_ficha(ficha: dict) -> str:
    """Devuelve `dc.title` de la ficha, o cadena vacía."""
    for campo in ficha.get("extraidos", []):
        if campo.get("campo") == "dc.title":
            valor = campo.get("valor")
            if isinstance(valor, str):
                return valor.strip()
            return ""
    return ""


def _autores_de_ficha(ficha: dict) -> list[str]:
    """Devuelve la lista de autores de la ficha, sin entradas vacías."""
    for campo in ficha.get("extraidos", []):
        if campo.get("campo") == "dc.contributor.author":
            valor = campo.get("valor")
            if isinstance(valor, list):
                return [v.strip() for v in valor if isinstance(v, str) and v.strip()]
            if isinstance(valor, str) and valor.strip():
                return [valor.strip()]
    return []


def _autores_equivalentes(a: list[str], b: list[str]) -> bool:
    """Compara autores por conjunto normalizado (el orden no identifica)."""
    return sorted(_normalizar(x) for x in a) == sorted(_normalizar(x) for x in b)


class Buzon:
    """Buzón de una ranura por dirección, con dos ventanas y "última gana".

    Atributos:
        ttl_autorelleno_segundos: Ventana en que la ficha se sirve para
            rellenar el formulario.
        ttl_tramite_segundos: Ventana en que el trámite completo (ficha,
            revisión, inconsistencia y depósito) se conserva.
    """

    def __init__(
        self,
        ttl_autorelleno_segundos: float = TTL_AUTORRELLENO_POR_DEFECTO,
        ttl_tramite_segundos: float = TTL_TRAMITE_POR_DEFECTO,
        reloj=None,
    ) -> None:
        self._ttl_autorelleno = max(float(ttl_autorelleno_segundos), 0.0)
        retencion = max(float(ttl_tramite_segundos), 0.0)
        if retencion < self._ttl_autorelleno:
            _log.warning(
                "VISTOBUENO_TTL_TRAMITE_SEG (%s) es menor que "
                "VISTOBUENO_TTL_AUTORRELLENO_SEG (%s): se usa el de autorelleno.",
                retencion,
                self._ttl_autorelleno,
            )
            retencion = self._ttl_autorelleno
        self._ttl_tramite = retencion
        self._reloj = reloj or (lambda: datetime.now(UTC))
        self._lock = threading.Lock()

        self._ficha: dict | None = None
        self._tramite_id: str | None = None
        self._revision = 0
        self._publicada_en: datetime | None = None
        self._autofill_hasta: datetime | None = None
        self._retenido_hasta: datetime | None = None
        self._inconsistencia: dict | None = None
        self._deposito: dict | None = None

    # --- Higiene interna ---

    def _ahora(self) -> datetime:
        momento = self._reloj()
        if momento.tzinfo is None:
            return momento.replace(tzinfo=UTC)
        return momento

    def _limpiar_ranuras(self) -> None:
        """Vacía el estado; el llamador ya tiene el lock."""
        self._ficha = None
        self._tramite_id = None
        self._revision = 0
        self._publicada_en = None
        self._autofill_hasta = None
        self._retenido_hasta = None
        self._inconsistencia = None
        self._deposito = None

    def _retenido(self) -> bool:
        """True si el trámite sigue dentro de la ventana de retención."""
        if self._ficha is None or self._tramite_id is None or self._retenido_hasta is None:
            return False
        if self._ahora() > self._retenido_hasta:
            self._limpiar_ranuras()
            return False
        return True

    def _autofill_habil(self) -> bool:
        """True si la ficha se puede servir para rellenar el formulario."""
        if not self._retenido() or self._autofill_hasta is None:
            return False
        return self._ahora() <= self._autofill_hasta

    def _estado(self) -> EstadoTramite | None:
        """Arma la instantánea canónica; requiere lock."""
        if not self._retenido():
            return None
        assert self._ficha is not None
        assert self._tramite_id is not None
        assert self._publicada_en is not None
        assert self._autofill_hasta is not None
        assert self._retenido_hasta is not None
        deposito = deepcopy(self._deposito)
        vigente = bool(
            deposito is not None and deposito.get("revision_confirmada") == self._revision
        )
        return EstadoTramite(
            ficha=deepcopy(self._ficha),
            tramite_id=self._tramite_id,
            revision=self._revision,
            inconsistencia=deepcopy(self._inconsistencia),
            deposito=deposito,
            publicada_en=self._publicada_en,
            autofill_hasta=self._autofill_hasta,
            retenido_hasta=self._retenido_hasta,
            autofill_habil=self._autofill_habil(),
            confirmacion_vigente=vigente,
        )

    # --- Ranura de la ficha (SPA → userscript) ---

    def publicar_ficha(self, ficha: dict) -> Publicacion:
        """Publica la ficha y devuelve trámite, revisión y ventanas.

        Cada publicación crea un trámite nuevo y descarta el depósito y la
        inconsistencia anteriores: un título igual no significa que sea la
        misma tesis.
        """
        with self._lock:
            ahora = self._ahora()
            self._ficha = deepcopy(ficha)
            self._tramite_id = uuid4().hex
            self._revision = 0
            self._publicada_en = ahora
            self._autofill_hasta = ahora + timedelta(seconds=self._ttl_autorelleno)
            self._retenido_hasta = ahora + timedelta(seconds=self._ttl_tramite)
            self._inconsistencia = None
            self._deposito = None
            return Publicacion(
                tramite_id=self._tramite_id,
                revision=self._revision,
                autofill_hasta=self._autofill_hasta,
                retenido_hasta=self._retenido_hasta,
            )

    def leer_ficha(self) -> LecturaFicha | None:
        """Devuelve la ficha si es elegible para autorelleno; si no, None.

        Una ficha retenida pero fuera de la ventana de autorelleno NO se
        sirve aquí: se consulta por `leer_tramite()`.
        """
        with self._lock:
            if not self._autofill_habil():
                return None
            assert self._ficha is not None
            assert self._tramite_id is not None
            assert self._autofill_hasta is not None
            assert self._retenido_hasta is not None
            return LecturaFicha(
                ficha=deepcopy(self._ficha),
                tramite_id=self._tramite_id,
                revision=self._revision,
                autofill_hasta=self._autofill_hasta,
                retenido_hasta=self._retenido_hasta,
            )

    def leer_tramite(self) -> EstadoTramite | None:
        """Devuelve el trámite retenido completo, aunque el autorelleno venció."""
        with self._lock:
            return self._estado()

    # --- Confirmación del depósito (userscript → SPA) ---

    def reportar_deposito(self, datos: dict) -> None:
        """Registra una confirmación explícita del operador.

        Requisitos (fallan sin cambiar el estado):

        - `atestacion == "operador"`: un reporte automático no confirma nada.
        - `revision_esperada` igual a la revisión vigente: un panel viejo no
          confirma datos nuevos.
        - trámite vigente y título observado igual al canónico. Si la ficha
          canónica no trae título, no hay nada que comparar: la
          confirmación queda registrada como `titulo_verificado=false`.
        - autores observados, si vienen, iguales a los canónicos.

        El servidor genera `confirmado_en`; `timestamp` sigue siendo el
        momento del clic en Depositar y la fuente de la HORA del papeleo.
        """
        with self._lock:
            if datos.get("atestacion") != "operador":
                raise ConfirmacionInvalida(
                    "El depósito solo se registra con confirmación explícita "
                    'del operador (`atestacion="operador"`).'
                )
            revision = datos.get("revision_esperada")
            if not isinstance(revision, int):
                raise ConfirmacionInvalida(
                    "Falta la revisión revisada por el operador (`revision_esperada`)."
                )
            if not self._retenido():
                raise SinFichaVigente(
                    "No hay una ficha vigente: expiró o no se preparó el depósito."
                )
            assert self._tramite_id is not None
            if datos.get("tramite_id") != self._tramite_id:
                raise TramiteNoCoincide(
                    "El depósito pertenece a un trámite anterior; vuelve a preparar la ficha."
                )
            if revision != self._revision:
                raise RevisionNoCoincide(
                    "La ficha cambió después de abrir el panel de confirmación. "
                    "Vuelve a leer el trámite y confirma la revisión vigente."
                )

            handle = datos.get("handle")
            if not isinstance(handle, str) or not HANDLE_RE.match(handle):
                raise HandleInvalido("El handle no tiene la forma institucional esperada.")
            timestamp = datos.get("timestamp")
            if not isinstance(timestamp, str) or not timestamp.strip():
                raise ConfirmacionInvalida(
                    "Falta el momento del clic en Depositar; no se inventa una hora."
                )

            assert self._ficha is not None
            titulo_canonico = _titulo_de_ficha(self._ficha)
            titulo_observado = datos.get("titulo_observado")
            if not isinstance(titulo_observado, str) or not titulo_observado.strip():
                raise TituloNoCoincide(
                    "La página del ítem no expone un título; no se puede confirmar."
                )
            titulo_verificado = False
            if titulo_canonico:
                if _normalizar(titulo_canonico) != _normalizar(titulo_observado):
                    raise TituloNoCoincide(
                        "El título observado del ítem no coincide con la ficha. "
                        "Concilia la ficha corregida antes de confirmar."
                    )
                titulo_verificado = True

            autores_canonicos = _autores_de_ficha(self._ficha)
            autores_observados = datos.get("autores_observados")
            autores_verificados = False
            if autores_observados is not None:
                if not isinstance(autores_observados, list) or not all(
                    isinstance(a, str) for a in autores_observados
                ):
                    raise ConfirmacionInvalida(
                        "`autores_observados` debe ser una lista de textos o null."
                    )
                observados = [a.strip() for a in autores_observados if a.strip()]
                if observados:
                    if not autores_canonicos:
                        raise AutoresNoCoinciden(
                            "El ítem declara autores que la ficha canónica no tiene. "
                            "Revisa y concilia la ficha."
                        )
                    if not _autores_equivalentes(observados, autores_canonicos):
                        raise AutoresNoCoinciden(
                            "Los autores observados del ítem no coinciden con la ficha. "
                            "Concilia la ficha corregida antes de confirmar."
                        )
                    autores_verificados = True

            self._deposito = {
                "tramite_id": self._tramite_id,
                "handle": handle,
                "titulo_observado": titulo_observado.strip(),
                "titulo_verificado": titulo_verificado,
                "autores_observados": deepcopy(autores_observados),
                "autores_verificados": autores_verificados,
                "timestamp": timestamp.strip(),
                "revision_confirmada": revision,
                "confirmado_en": self._ahora().isoformat(),
                "confirmado_por": "operador",
                "estado": "confirmado_por_operador",
            }

    def leer_deposito(self) -> dict | None:
        """Devuelve la confirmación vigente; None si no hay depósito retenido."""
        with self._lock:
            if not self._retenido() or self._deposito is None:
                return None
            return deepcopy(self._deposito)

    # --- Conciliación e inconsistencia ---

    def reconciliar(
        self,
        *,
        ficha: dict,
        revision_esperada: int,
        handle: str,
        motivo: str,
    ) -> EstadoTramite:
        """Reemplaza la ficha canónica con una corrección revisada.

        Funciona antes y después de la confirmación:

        - Sin depósito: no crea evidencia de depósito. El handle es solo
          contexto del ítem que el operador está mirando.
        - Con depósito: exige el mismo handle y conserva la evidencia, pero
          la confirmación queda atada a la revisión anterior. El papeleo
          exige una reconfirmación de la revisión nueva.

        Nunca aprueba datos nuevos por el solo hecho de conservar el handle.
        """
        with self._lock:
            if not self._retenido():
                raise SinFichaVigente(
                    "No hay un trámite retenido: expiró o no se publicó la ficha."
                )
            assert self._tramite_id is not None
            if revision_esperada != self._revision:
                raise RevisionNoCoincide(
                    "La revisión esperada no es la vigente: otra corrección cambió "
                    "la ficha mientras tanto. Vuelve a leer el trámite."
                )
            if not isinstance(handle, str) or not HANDLE_RE.match(handle):
                raise HandleInvalido("El handle no tiene la forma institucional esperada.")
            if not isinstance(motivo, str) or not motivo.strip():
                raise ConfirmacionInvalida(
                    "La conciliación exige un motivo revisado por el operador."
                )
            if self._deposito is not None:
                if self._deposito.get("handle") != handle:
                    raise HandleNoCoincide(
                        "La corrección apunta a otro handle: no se puede conciliar "
                        "sobre el depósito confirmado. Prepara un trámite nuevo."
                    )
            self._ficha = deepcopy(ficha)
            self._revision += 1
            self._inconsistencia = None
            estado = self._estado()
            assert estado is not None
            return estado

    def marcar_inconsistencia(
        self,
        *,
        tramite_id: str,
        handle: str,
        revision_esperada: int,
        motivos: list[str],
    ) -> None:
        """Marca el trámite como inconsistente hasta una conciliación.

        La marca comparte la retención del trámite y bloquea el papeleo.
        El handle identifica el ítem observado; si ya hay un depósito
        confirmado, debe ser el mismo ítem.
        """
        with self._lock:
            if not self._retenido():
                raise SinFichaVigente(
                    "No hay un trámite retenido: expiró o no se publicó la ficha."
                )
            assert self._tramite_id is not None
            if tramite_id != self._tramite_id:
                raise TramiteNoCoincide(
                    "La inconsistencia pertenece a un trámite anterior; vuelve a leer el trámite."
                )
            if revision_esperada != self._revision:
                raise RevisionNoCoincide(
                    "La revisión esperada no es la vigente: vuelve a leer el trámite."
                )
            if not isinstance(handle, str) or not HANDLE_RE.match(handle):
                raise HandleInvalido("El handle no tiene la forma institucional esperada.")
            if self._deposito is not None and self._deposito.get("handle") != handle:
                raise HandleNoCoincide(
                    "La inconsistencia apunta a otro handle que el depósito confirmado."
                )
            limpios = [m.strip() for m in motivos if isinstance(m, str) and m.strip()]
            if not limpios:
                raise ConfirmacionInvalida("La inconsistencia exige al menos un motivo.")
            self._inconsistencia = {
                "motivos": limpios,
                "revision": self._revision,
                "reportada_en": self._ahora().isoformat(),
            }

    # --- Higiene ---

    def limpiar(self) -> None:
        """Vacía el trámite completo (uso en tests y para reiniciar el flujo)."""
        with self._lock:
            self._limpiar_ranuras()
