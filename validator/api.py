"""API FastAPI para VistoBueno — endpoint POST /validar.

Expone el motor de validación de formato de tesis como servicio HTTP.
Recibe un archivo DOCX, lo procesa contra las reglas de formato de la
UNT, y devuelve un reporte estructurado en JSON.

Uso:
    python -m validator.api
    # o con uvicorn directamente:
    uvicorn validator.api:app --reload
"""

import asyncio
import logging
import math
import os
import re
import secrets
import tempfile
import threading
import time
import zipfile
from collections.abc import Callable
from datetime import datetime
from functools import cache
from ipaddress import ip_address
from pathlib import Path
from typing import Any, Literal, cast
from zoneinfo import ZoneInfo

from email_validator import EmailNotValidError, validate_email
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from .api_models import (
    CampoExtraidoFicha,
    CampoManualFicha,
    ConstanciaRequest,
    DepositoAPI,
    DepositoRecibido,
    DepositoReportado,
    EstadoAsistenteAPI,
    EstadoDepositoAPI,
    EstadoNotificacionAPI,
    ExplicacionItemAPI,
    ExplicacionYPrioridadAPI,
    FichaDeposito,
    FichaPendienteLeida,
    FichaPendientePublicada,
    FilaRegistroRequest,
    FilasRegistroResponse,
    InconsistenciaAPI,
    InconsistenciaRequest,
    MetadatosValidacion,
    NotificacionAPI,
    PrioridadItemAPI,
    PromptIA,
    ReconciliacionResponse,
    ReconciliarRequest,
    ResultadoReglaAPI,
    ResumenValidacion,
    SeveridadAPI,
    TramiteLeido,
    ValidarResponse,
)
from .asistente import RespuestaIAInvalida, explicar_y_priorizar
from .buzon import (
    AutoresNoCoinciden,
    Buzon,
    ConfirmacionInvalida,
    EstadoTramite,
    HandleInvalido,
    HandleNoCoincide,
    RevisionNoCoincide,
    SinFichaVigente,
    TituloNoCoincide,
    TramiteNoCoincide,
)
from .constancia import (
    MIME_DOCX as MIME_DOCX_CONSTANCIA,
)
from .constancia import (
    DatosConstancia,
    ErrorConfiguracionConstancia,
    ErrorDatosConstancia,
    _nombre_seguro,
    constancia_en_zip,
    constancias_por_autor,
    filas_a_csv,
    filas_a_tsv,
    filas_a_xlsx,
    llenar_constancia,
)
from .dsl_check import DSLValidationError
from .engine import build_report, load_ficha_rules, load_rules, validate_docx
from .extractor import InvalidDocumentError
from .llm import (
    LLMClient,
    LLMError,
    LLMNoDisponible,
    estado_ia,
    get_llm_client,
)
from .models import RuleResult
from .notificacion import ConfigSMTP, enviar_notificacion
from .prompts import build_ai_help_section

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# F5: la API consume el motor DSL (reglas_unt.yaml, 47 reglas) en lugar del
# YAML legacy (unt_format_rules_schema.yaml, 32 mecánicas). Esto activa las
# 9 reglas F3 (resumen_longitud, referencias_minimo_*, anexos_minimos_*,
# caratula_orcid, proyecto_caratula_texto) y las de la F2 (paginación,
# encabezados/pies) dentro de POST /validar.
REGLAS_YAML_PATH = str(Path(__file__).resolve().parent.parent / "reglas_unt.yaml")

TAMANO_MAXIMO_BYTES = 10 * 1024 * 1024  # 10 MB

# Zona horaria del registro oficial y de la constancia. El userscript
# reporta la hora de pared del Perú; un timestamp ISO 8601 con offset se
# convierte a esta zona para que el documento no dependa del navegador.
ZONA_LIMA = ZoneInfo("America/Lima")

# Tipos de content-type admitidos. La puerta real NO es esta lista: un DOCX
# es un paquete OPC (ZIP) y algunos clientes lo envían con tipos genéricos.
# El control efectivo es la extensión `.docx` + la firma "PK" del archivo;
# los tres chequeos están en `validar()` (extensión, content-type y firma).
# AUD-13: un .docx legítimo con `application/zip`
# recibía 415 y el frontend lo aceptaba (acepta por MIME o extensión).
TIPOS_ACEPTADOS = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/zip",  # un DOCX es un ZIP: algunos clientes lo envían así
    "application/octet-stream",  # algunos navegadores envían esto para .docx
}

EXTENSION_ACEPTADA = ".docx"

# Claves acordadas de la ficha de depósito (v1.7.0, PLAN_FICHA §4).
# Los extraídos los publica el motor en reporte["ficha"] (handover
# HANDOVER_MOTOR_FICHA_DEPOSITO §4); los manuales los teclea el operador.
CAMPOS_EXTRAIDOS_FICHA = (
    "dc.title",
    "dc.contributor.author",
    "dc.contributor.advisor",
    "dc.description.abstract",
    "dc.subject",
    "dc.date.issued",
    "escuela",
    "renati.juror",
)
CAMPOS_MANUALES_FICHA = (
    "matricula",
    "renati.author.dni",
    "renati.advisor.dni",
    "renati.advisor.orcid",
)


# ---------------------------------------------------------------------------
# Control de acceso al buzón (auditoría 2026-10-26, AUD-09)
# ---------------------------------------------------------------------------
# El buzón travela datos personales del estudiante (DNI, ORCID, resumen) y
# su ranura es de "última gana": alguien que llegue desde la red puede
# leerlos o pisar la ficha en vuelo.
#
# El despliegue real es LOCAL: la app corre en la PC del encargado y
# `uvicorn` hace bind a 127.0.0.1. Por eso el control de acceso por
# defecto es el **loopback**: solo los peticiones que llegan desde la
# propia máquina pueden tocar el buzón.
#
# Si alguien expone la API fuera de la máquina (bind a 0.0.0.0 o un
# reverse proxy en otro host), puede exigir además un token compartido
# por header. La comparación es en tiempo constante.

CABECERA_TOKEN_BUZON = "X-VistoBueno-Token"
HOSTS_LOOPBACK = frozenset({"127.0.0.1", "::1", "localhost"})

# Hosts admitidos en el header `Host` de cualquier petición. Además del
# loopback se puede sumar un dominio propio con VISTOBUENO_HOSTS (lista
# separada por comas), por ejemplo si la API vive detrás de un reverse
# proxy en la misma máquina. `*` desactiva el chequeo (no recomendado).
HOSTS_CONFIABLES_DEFAULT = ("127.0.0.1", "localhost", "::1")


def _host_sin_puerto(valor: str) -> str:
    """Normaliza un host: minúsculas, sin puerto y sin corchetes IPv6.

    Un IPv6 literal tiene dos o más `:`: no tiene puerto que quitar, así
    que se devuelve completo (`::1` se queda `::1`, no `""`). Sin este
    caso, el host vacío entraba en la lista de admitidos y una petición
    sin header `Host` pasaba el control (revisión PR #71, N1).
    """
    host = valor.strip().lower()
    if host.startswith("["):
        cierre = host.find("]")
        return host[1:cierre] if cierre != -1 else host
    if host.count(":") > 1:
        # IPv6 literal sin corchetes: "::1", "fe80::1".
        return host
    return host.split(":", 1)[0]


def _hosts_confiables() -> frozenset[str]:
    """Hosts admitidos, leídos del entorno en cada petición.

    Cada entrada se normaliza como el header `Host`: minúsculas, sin
    puerto y sin corchetes IPv6. Así, `VISTOBUENO_HOSTS=10.0.0.5:8000`
    sirve para el peer que se anuncia como `10.0.0.5:8000` y también
    para el que se anuncia como `10.0.0.5` (revisión PR #71, B3).

    Las entradas que quedan vacías se descartan: un host vacío admitiría
    peticiones sin header `Host` (revisión PR #71, N1).
    """
    extra = os.environ.get("VISTOBUENO_HOSTS", "")
    candidatos = [h for h in HOSTS_CONFIABLES_DEFAULT if h.strip()]
    candidatos += [h for h in extra.split(",") if h.strip()]
    return frozenset(h for h in (_host_sin_puerto(h) for h in candidatos) if h)


def _es_loopback(host: str | None) -> bool:
    """True si el host del par es la propia máquina.

    Acepta el nombre "localhost" y cualquier dirección del rango
    loopback: 127.0.0.0/8 completo (no solo 127.0.0.1) y ::1.
    """
    valor = (host or "").strip().lower()
    if valor in HOSTS_LOOPBACK:
        return True
    try:
        return ip_address(valor).is_loopback
    except ValueError:
        return False


class MiddlewareHostConfiable:
    """Rechaza peticiones con un header `Host` ajeno (400).

    Cierra el *DNS rebinding*: la página del atacante se sirve desde su
    dominio (Host: atacante.example) aunque su DNS resuelva a 127.0.0.1.
    El navegador conserva el Host del dominio en la petición, así que el
    chequeo corta el ataque en todos los navegadores; no depende de
    Private Network Access (mitigación solo de Chrome).

    El puerto se ignora y se admite IPv6 literal ("[::1]:8000").

    Todo el rango loopback (127.0.0.0/8) se acepta, igual que el control
    de acceso por peer: los dos chequeos cuentan la misma frontera.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return
        hosts = _hosts_confiables()
        if "*" in hosts:
            await self.app(scope, receive, send)
            return
        host = _host_sin_puerto(Headers(scope=scope).get("host", ""))
        if host in hosts or _es_loopback(host):
            await self.app(scope, receive, send)
            return
        respuesta = PlainTextResponse("Host no permitido", status_code=400)
        await respuesta(scope, receive, send)


def _token_api() -> str:
    """Token compartido de la API; vacío significa "no se exige token"."""
    return (os.environ.get("VISTOBUENO_API_TOKEN") or "").strip()


async def verificar_acceso_local(request: Request) -> None:
    """Dependency de todos los endpoints: loopback o token compartido.

    La API se despliega en la PC del operador y `uvicorn` hace bind a
    127.0.0.1: el loopback es la frontera de confianza del MVP
    (auditoría 2026-10-26, AUD-09). El control cubre **toda** la API
    porque el buzón y el papeleo manejan datos personales (DNI, ORCID,
    resumen) y documentos oficiales: un `curl` desde otro equipo no
    puede validar, leer la ficha ni generar constancias.

    Reglas:

    - **Peer del loopback**: siempre permitido. La SPA y el userscript
      hablan con `127.0.0.1` y no envían token.
    - **Peer de otra máquina**: permitido solo si hay un token
      configurado (`VISTOBUENO_API_TOKEN`) y el header coincide.

    El token se comprueba **antes** de rechazar al peer remoto: sin ese
    orden, el token no serviría para el único caso que documenta (API
    expuesta fuera de la máquina).
    """
    host = request.client.host if request.client else None
    if _es_loopback(host):
        return
    token = _token_api()
    recibido = request.headers.get(CABECERA_TOKEN_BUZON, "")
    if token and secrets.compare_digest(recibido.encode(), token.encode()):
        return
    if not token:
        raise HTTPException(
            status_code=403,
            detail=(
                "La API de VistoBueno solo se sirve desde la máquina donde "
                "corre la app (loopback). Si la API se expone a otros "
                "equipos, define VISTOBUENO_API_TOKEN y envía el header "
                f"'{CABECERA_TOKEN_BUZON}'."
            ),
        )
    raise HTTPException(
        status_code=403,
        detail=(
            "Falta o no coincide el token de la API. Envía el header "
            f"'{CABECERA_TOKEN_BUZON}' con el valor de "
            "VISTOBUENO_API_TOKEN."
        ),
    )


# ---------------------------------------------------------------------------
# Limitador de peticiones (auditoría 2026-10-26, AUD-12)
# ---------------------------------------------------------------------------
# POST /validar recompila el DSL en cada request: el recurso a proteger es
# el CPU del proceso. El límite vive en memoria (sin base de datos, como el
# buzón): se reinicia con el servidor y no se comparte entre workers (el
# despliegue documentado es de UN worker).
#
# Es una mitigación mínima: si algún día la API se expone fuera de la
# máquina, el límite real va en el reverse proxy (ver README).

MAXIMO_PETICIONES_DEFAULT = 60
VENTANA_PETICIONES_DEFAULT = 60.0

# Cupo adaptativo por CPU (AUD-12, segunda iteración). El límite por
# número de peticiones asume que todas cuestan lo mismo, y no es cierto:
# la misma validación tarda ~60 ms en un equipo y ~250 ms en otro. El
# cupo acumula los segundos de trabajo MEDIDOS y se fuga a
# `presupuesto_segundos` por ventana, así que se ajusta solo al hardware
# sin constantes por modelo de PC.
#
# RI-01: el presupuesto debe dejar entrar dos tesis normales seguidas.
# La comprobación es `deuda < presupuesto`: la segunda entra mientras la
# primera no haya agotado el cupo. Con 5 s hay margen para una tesis real
# (la revisión integral midió ~3.5 s de trabajo restante tras RI-07) y la
# ráfaga de documentos patológicos sigue cortada.
PRESUPUESTO_CPU_DEFAULT = 5.0  # segundos de trabajo por ventana
PRESUPUESTO_CPU_PAPELES_DEFAULT = 1.0  # el papeleo (DOCX/XLSX) pesa más
COSTE_CPU_MINIMO = 0.01
COSTE_CPU_MAXIMO = 10.0  # un documento patológico no bloquea media hora


class LimitadorPeticiones:
    """Ventana fija por IP: cuenta las peticiones de un intervalo.

    Attributes:
        _peticiones: IP → (cantidad, inicio de la ventana).
        _lock: el acceso puede ser concurrente (endpoints en threadpool).
    """

    def __init__(self) -> None:
        self._peticiones: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def registrar(self, ip: str, maximo: int, ventana: float) -> tuple[bool, float]:
        """Registra una petición.

        Returns:
            (permitido, segundos para reintentar). Si no está permitida,
            los segundos son el tiempo que falta para que venza la ventana.
        """
        ahora = time.monotonic()
        with self._lock:
            cantidad, inicio = self._peticiones.get(ip, (0, ahora))
            if ahora - inicio >= ventana:
                cantidad, inicio = 0, ahora
            cantidad += 1
            self._peticiones[ip] = (cantidad, inicio)
            if cantidad > maximo:
                return False, max(ventana - (ahora - inicio), 0.0)
            self._purgar(ahora, ventana)
            return True, 0.0

    def _purgar(self, ahora: float, ventana: float) -> None:
        """Descarta las entradas vencidas (evita que el dict crezca sin fin)."""
        if len(self._peticiones) <= 1000:
            return
        self._peticiones = {
            ip: datos for ip, datos in self._peticiones.items() if ahora - datos[1] < ventana
        }

    def limpiar(self) -> None:
        """Vacía el estado (tests y reinicio del flujo)."""
        with self._lock:
            self._peticiones.clear()


class LimitadorCPU:
    """Cupo adaptativo por presupuesto de CPU (cubo con fugas).

    `_deuda` acumula los segundos de trabajo medidos y se fuga a
    `presupuesto_segundos / ventana_segundos` por segundo. Una petición
    entra si la deuda está por debajo del presupuesto. El presupuesto es
    el mismo en cualquier equipo; lo que cambia es cuántas peticiones
    caben en él:

    - equipo rápido (~60 ms por validación): ~83 seguidas con 5 s;
    - equipo lento (~250 ms por validación): ~20 seguidas;
    - tesis real (~3.5 s tras RI-07): dos seguidas.

    La segunda petición entra mientras la primera no agote el cupo; por
    eso el presupuesto se fija por encima del coste de una tesis normal
    (RI-01). La tasa sostenida es de 5 s de CPU por minuto en cualquier
    caso, así que una ráfaga sigue cortada.

    El coste se mide en el endpoint (`registrar_coste`) después de la
    operación pesada, así que no hay números mágicos por hardware.

    Attributes:
        _deuda: segundos de trabajo acumulados; se recorta al consultar.
        _lock: el cupo se consulta desde endpoints concurrentes.
    """

    def __init__(
        self,
        *,
        presupuesto_segundos: float = PRESUPUESTO_CPU_DEFAULT,
        ventana_segundos: float = VENTANA_PETICIONES_DEFAULT,
    ) -> None:
        # Los valores base son los del constructor: `ajustar()` vuelve a
        # ellos cuando la variable de entorno desaparece, para que quitar
        # la salida de emergencia no deje el cupo pegado (revisión PR
        # #71, N2).
        self._presupuesto_base = max(presupuesto_segundos, 0.0)
        self._ventana_base = max(ventana_segundos, 0.1)
        self._presupuesto = self._presupuesto_base
        self._ventana = self._ventana_base
        self._tasa = self._presupuesto / self._ventana
        self._deuda = 0.0
        self._ultimo = time.monotonic()
        self._lock = threading.Lock()

    def _fugar_deuda(self, ahora: float) -> None:
        """Descuenta la deuda por el tiempo transcurrido (llamar con el lock)."""
        if ahora <= self._ultimo:
            return
        self._deuda = max(0.0, self._deuda - (ahora - self._ultimo) * self._tasa)
        self._ultimo = ahora

    def fugar(self) -> None:
        """Deja correr el tiempo: la deuda se descuenta aunque nadie pregunte.

        Se usa en el modo legacy, donde el cupo de CPU no se cobra: la
        deuda anterior debe seguir decayendo para no bloquear al
        operador al volver al modo adaptativo (revisión PR #71, M1).
        """
        with self._lock:
            self._fugar_deuda(time.monotonic())

    def ajustar(
        self,
        *,
        presupuesto_segundos: float | None = None,
        ventana_segundos: float | None = None,
    ) -> None:
        """Aplica la configuración leída del entorno (presupuesto y ventana).

        `None` significa "vuelve al valor base del limitador": cuando la
        variable de entorno deja de estar definida, el cupo regresa a su
        valor por defecto. Si no, la salida de emergencia (presupuesto 0)
        quedaría pegada hasta reiniciar el proceso (revisión PR #71, N2).

        La tasa de fuga depende de la ventana, así que cambiarla recalcula
        la tasa. La deuda ya acumulada no se toca: se sigue cobrando.
        """
        with self._lock:
            self._presupuesto = (
                self._presupuesto_base
                if presupuesto_segundos is None
                else max(presupuesto_segundos, 0.0)
            )
            self._ventana = (
                self._ventana_base if ventana_segundos is None else max(ventana_segundos, 0.1)
            )
            self._tasa = self._presupuesto / self._ventana

    def adquirir(self) -> tuple[bool, float]:
        """Consulta si entra una petición más.

        Returns:
            (permitido, segundos para reintentar). La deuda se cobra al
            terminar, con el coste real (`registrar_coste`).
        """
        with self._lock:
            self._fugar_deuda(time.monotonic())
            if self._presupuesto <= 0:
                return True, 0.0  # cupo desactivado
            if self._deuda < self._presupuesto:
                return True, 0.0
            falta = (
                (self._deuda - self._presupuesto) / self._tasa if self._tasa > 0 else self._ventana
            )
            return False, max(falta, 1.0)

    def registrar_coste(self, segundos: float) -> None:
        """Suma a la deuda el coste real de la operación pesada."""
        with self._lock:
            if self._presupuesto <= 0:
                return  # cupo desactivado: no hay nada que cobrar
            self._deuda += min(max(segundos, COSTE_CPU_MINIMO), COSTE_CPU_MAXIMO)

    @property
    def deuda(self) -> float:
        """Deuda acumulada en segundos de CPU (diagnóstico y tests)."""
        with self._lock:
            return self._deuda

    @property
    def presupuesto(self) -> float:
        """Presupuesto vigente, en segundos de CPU por ventana."""
        with self._lock:
            return self._presupuesto

    @property
    def ventana(self) -> float:
        """Ventana vigente del cupo, en segundos."""
        with self._lock:
            return self._ventana

    def limpiar(self) -> None:
        """Vacía el estado (tests y reinicio del flujo)."""
        with self._lock:
            self._deuda = 0.0
            self._ultimo = time.monotonic()


_LIMITADOR_PETICIONES = LimitadorPeticiones()
_LIMITADOR_CPU_VALIDACION = LimitadorCPU()
# El papeleo (DOCX/XLSX) pesa más que una validación: menos presupuesto.
_LIMITADOR_CPU_PAPELES = LimitadorCPU(presupuesto_segundos=PRESUPUESTO_CPU_PAPELES_DEFAULT)


# ---------------------------------------------------------------------------
# Medición del coste real (revisión PR #71, B1)
# ---------------------------------------------------------------------------


class _MedidorCPU:
    """Mide los segundos de CPU del hilo que ejecuta el trabajo pesado.

    `time.thread_time()` cuenta el tiempo de CPU del hilo que llama, no
    la latencia. Con peticiones concurrentes, la espera del GIL no se
    cuenta: es exactamente la parte que no es trabajo real. Medir la
    latencia hacía que el cupo dependiera del equipo y de la carga, no
    del trabajo (revisión PR #71, B1).
    """

    def __init__(self) -> None:
        self.segundos: float = 0.0

    def medir(self, fn: Callable[..., Any], *args: Any) -> Any:
        """Ejecuta `fn` en este hilo y guarda el coste medido.

        El coste se guarda también si `fn` lanza: un documento corrupto
        consume CPU igual que uno válido.
        """
        inicio = time.thread_time()
        try:
            return fn(*args)
        finally:
            self.segundos += time.thread_time() - inicio


# ---------------------------------------------------------------------------
# Configuración de los cupos (leída del entorno en cada petición)
# ---------------------------------------------------------------------------


def _modo_adaptativo() -> bool:
    """True si el cupo vigente es el adaptativo por CPU.

    El modo legacy (`VISTOBUENO_RATE_LIMIT_MAX` definido) usa su propia
    ventana fija por IP. En ese modo el cupo de CPU no se cobra: su
    fuga vive dentro de `adquirir()` y nadie lo llama (revisión PR #71,
    M1).
    """
    return "VISTOBUENO_RATE_LIMIT_MAX" not in os.environ


def _ventana_peticiones() -> float | None:
    """Ventana de los cupos en segundos, leída del entorno en cada request.

    Devuelve None si la variable no está definida: manda el valor por
    defecto del limitador. Rige en los dos modos: el legacy por IP y el
    adaptativo por CPU (revisión PR #71, M2).
    """
    bruto = os.environ.get("VISTOBUENO_RATE_LIMIT_VENTANA_SEG")
    if bruto is None:
        return None
    try:
        return max(float(bruto), 0.1)
    except ValueError:
        return VENTANA_PETICIONES_DEFAULT


def _presupuesto_cpu(nombre_var: str, defecto: float) -> float | None:
    """Presupuesto de CPU por ventana, leído del entorno.

    Devuelve None si la variable no está definida: manda el valor por
    defecto del limitador. `0` desactiva el cupo: es la salida de
    emergencia para el operador que necesita papelar sin cortes
    (revisión PR #71, M3).
    """
    bruto = os.environ.get(nombre_var)
    if bruto is None:
        return None
    try:
        return max(float(bruto), 0.0)
    except ValueError:
        return defecto


def _config_limite_peticiones() -> tuple[int, float]:
    """Límite por IP y ventana, leídos del entorno en cada request.

    Returns:
        (máximo de peticiones, ventana en segundos). Un máximo de 0
        desactiva el límite.
    """
    try:
        maximo = int(os.environ.get("VISTOBUENO_RATE_LIMIT_MAX", MAXIMO_PETICIONES_DEFAULT))
    except ValueError:
        maximo = MAXIMO_PETICIONES_DEFAULT
    ventana = _ventana_peticiones()
    return max(0, maximo), VENTANA_PETICIONES_DEFAULT if ventana is None else ventana


def _rechazar_por_limite(reintentar: float, recurso: str) -> None:
    """Respuesta 429 uniforme de los cupos.

    `Retry-After` sigue el estándar HTTP: segundos, redondeados hacia
    arriba para no reintentar antes de que el cupo libere espacio. El
    mensaje usa la misma espera que el header; cambia a minutos cuando
    la espera llega a 60 s.
    """
    espera = max(1, math.ceil(reintentar))
    if espera < 60:
        unidad = "segundo" if espera == 1 else "segundos"
        wait_msg = f"Espera {espera} {unidad} antes de reintentar."
    else:
        minutos = math.ceil(espera / 60)
        unidad = "minuto" if minutos == 1 else "minutos"
        wait_msg = f"Espera {minutos} {unidad} antes de reintentar."
    raise HTTPException(
        status_code=429,
        headers={"Retry-After": str(espera)},
        detail=(f"Demasiadas peticiones de {recurso} seguidas. {wait_msg}"),
    )


async def limitar_validaciones(request: Request) -> None:
    """Dependency de POST /validar: corta los abusos de CPU con 429.

    Si `VISTOBUENO_RATE_LIMIT_MAX` está definido se usa la ventana fija
    por IP (comportamiento previo; `0` la desactiva). Si no, se usa el
    cupo adaptativo por CPU, que se ajusta a la velocidad del equipo.
    """
    if not _modo_adaptativo():
        maximo, ventana = _config_limite_peticiones()
        if maximo <= 0:
            return
        ip = request.client.host if request.client else "desconocido"
        permitido, reintentar = _LIMITADOR_PETICIONES.registrar(ip, maximo, ventana)
        if not permitido:
            _rechazar_por_limite(reintentar, "validación")
        return
    _LIMITADOR_CPU_VALIDACION.ajustar(
        presupuesto_segundos=_presupuesto_cpu(
            "VISTOBUENO_RATE_LIMIT_CPU_SEG", PRESUPUESTO_CPU_DEFAULT
        ),
        ventana_segundos=_ventana_peticiones(),
    )
    permitido, reintentar = _LIMITADOR_CPU_VALIDACION.adquirir()
    if not permitido:
        _rechazar_por_limite(reintentar, "validación")


async def limitar_papeleo() -> None:
    """Dependency de /constancia y /fila-registro: cupo adaptativo por CPU.

    El presupuesto se lee del entorno en cada petición:
    `VISTOBUENO_RATE_LIMIT_PAPELES_CPU_SEG` lo sube y `0` lo desactiva.
    Es la salida de emergencia para el operador que necesita papelar
    sin cortes (revisión PR #71, M3).
    """
    _LIMITADOR_CPU_PAPELES.ajustar(
        presupuesto_segundos=_presupuesto_cpu(
            "VISTOBUENO_RATE_LIMIT_PAPELES_CPU_SEG", PRESUPUESTO_CPU_PAPELES_DEFAULT
        ),
        ventana_segundos=_ventana_peticiones(),
    )
    permitido, reintentar = _LIMITADOR_CPU_PAPELES.adquirir()
    if not permitido:
        _rechazar_por_limite(reintentar, "documentos")


def _cobrar_coste_validacion(segundos: float) -> None:
    """Cobra el coste medido al cupo de validación, si ese cupo rige.

    En el modo legacy (`VISTOBUENO_RATE_LIMIT_MAX`) el cupo de CPU no se
    consulta: cobrar la deuda sin que nadie la fugue dejaría al
    operador bloqueado al volver al modo adaptativo. En ese modo solo se
    deja correr el tiempo, para que la deuda anterior se desangre
    (revisión PR #71, M1).
    """
    if _modo_adaptativo():
        _LIMITADOR_CPU_VALIDACION.registrar_coste(segundos)
    else:
        _LIMITADOR_CPU_VALIDACION.fugar()


@cache
def _get_rules() -> dict:
    """Carga el YAML de reglas una sola vez (cacheado en memoria)."""
    return load_rules(REGLAS_YAML_PATH)


@cache
def _get_ficha_rules() -> dict:
    """Carga el ruleset de captura de la ficha (diseño 17), una sola vez.

    Devuelve ``{}`` si el archivo no existe (despliegue sin ficha): la
    respuesta sigue trayendo los campos acordados con ``detectado=false``.
    """
    return load_ficha_rules()


# ---------------------------------------------------------------------------
# Mapeo motor interno → DTO API
# ---------------------------------------------------------------------------


def _rule_result_a_dto(r: RuleResult) -> ResultadoReglaAPI:
    """Convierte un RuleResult del motor a un ResultadoReglaAPI (DTO)."""
    return ResultadoReglaAPI(
        rule_id=r.rule_id,
        paso=r.passed,
        severidad=SeveridadAPI(r.severity.value),
        mensaje=r.message,
        esperado=r.expected,
        encontrado=r.found,
        ubicacion=r.location,
        fuente=r.fuente,
        cita=r.cita,
        aplicable=r.aplicable,
    )


def _extraer_metadata_tipo_documento(
    resultados_motor: list[RuleResult],
) -> dict:
    """Extrae los campos opcionales de tipo de documento de la detección.

    La regla `deteccion_tipo_documento` siempre se ejecuta; su `encontrado`
    contiene la decisión como texto. Se parsea para publicar:

    - `tipo_documento_declarado`: lo que dice el Anexo 10 (None si no declaró).
    - `tipo_documento_inferido`: lo que se dedujo de las firmas (None si no se
      pudo inferir).
    - `tipo_documento_estado`: "vigente" si se determinó un tipo,
      "sin_determinar" si no se pudo, "contradictorio" si el Anexo 10 y las
      firmas no coinciden.

    El parseo es determinista sobre el texto que genera el motor mismo, por
    lo que no hay riesgo de desalineación.
    """
    detector = next((r for r in resultados_motor if r.rule_id == "deteccion_tipo_documento"), None)
    if detector is None or not detector.found:
        return {
            "tipo_documento_declarado": None,
            "tipo_documento_inferido": None,
            "tipo_documento_estado": "sin_determinar",
        }

    encontrado = detector.found
    declarado = re.search(r"declarado=([a-z_]+)", encontrado)
    inferido = re.search(r"inferido=([a-z_]+)", encontrado)
    contradice = "contradictorio:" in encontrado
    sin_determinar = encontrado.startswith("sin_determinado")

    if contradice:
        estado = "contradictorio"
    elif sin_determinar:
        estado = "sin_determinar"
    else:
        estado = "vigente"

    # declarado e inferido son Optional[Match[str]]; en contradice ambos existen
    declarado_val = declarado.group(1) if declarado else None
    inferido_val = inferido.group(1) if inferido else None

    return {
        "tipo_documento_declarado": declarado_val,
        "tipo_documento_inferido": inferido_val,
        "tipo_documento_estado": estado,
    }


def _valor_utilizable(valor: object) -> bool:
    """True si el valor capturado sirve para el formulario de DSpace.

    Contrato de la ficha (auditoría 2026-10-26, AUD-25 y AUD-26): un
    campo con `detectado=true` debe traer un valor **utilizable**. El
    motor puede publicar capturas vacías o con la forma equivocada (por
    ejemplo, el asesor vacío o la línea de ciudad en vez del año), y
    ese dato viaja al formulario oficial, a la constancia y al
    registro. La API no lo publica como detectado: lo deja para que el
    operador lo teclee.
    """
    if valor is None:
        return False
    if isinstance(valor, str):
        return bool(valor.strip())
    if isinstance(valor, list):
        # Una lista sirve si tiene al menos un elemento con texto.
        return any(isinstance(item, str) and item.strip() for item in valor)
    return True


def _forma_valida(campo: str, valor: object) -> bool:
    """True si el valor además tiene la forma que espera el campo.

    Solo `dc.date.issued` tiene forma estricta: el formulario pide un
    año. El chequeo es de **valor completo**, no de "contiene": la
    captura real de AUD-26 es el párrafo del título, que termina en
    ", Trujillo 2024". Un `contains` dejaría pasar ese texto y el
    ítem se publicaría con la fecha equivocada.
    """
    if campo != "dc.date.issued":
        return True
    if isinstance(valor, list):
        valor = valor[0] if valor else ""
    if not isinstance(valor, str):
        return False
    return bool(re.fullmatch(r"(?:19|20)\d{2}", valor.strip()))


def _ficha_desde_reporte(reporte: dict) -> FichaDeposito:
    """Construye la ficha de depósito a partir del reporte del motor.

    El motor publica las extracciones en `reporte["ficha"]` como un
    dict campo→dato, cada dato con la forma acordada del handover §4:
    `{"valor": …, "pagina": …, "detectado": …}`. Si un campo no fue
    capturado (p. ej. `renati.juror`, viabilidad negativa del diseño
    17), viaja con `detectado=false` y `valor=null`: el contrato es
    estable y el frontend puede construirse ya.

    Un campo solo viaja con `detectado=true` si su valor es **utilizable**
    y tiene la **forma** que espera el campo (ver `_valor_utilizable` y
    `_forma_valida`). Si no, viaja con `detectado=false` y `valor=null`:
    el operador lo teclea en la pantalla de ficha.

    Los manuales siempre viajan vacíos desde el servidor: los llena el
    operador en la pantalla.
    """
    datos_motor = reporte.get("ficha") or {}
    extraidos = []
    for campo in CAMPOS_EXTRAIDOS_FICHA:
        dato = datos_motor.get(campo) or {}
        valor = dato.get("valor")
        detectado = (
            bool(dato.get("detectado")) and _valor_utilizable(valor) and _forma_valida(campo, valor)
        )
        extraidos.append(
            CampoExtraidoFicha(
                campo=campo,
                valor=valor if detectado else None,
                pagina=dato.get("pagina") if detectado else None,
                detectado=detectado,
            )
        )
    manuales = [CampoManualFicha(campo=c, valor=None) for c in CAMPOS_MANUALES_FICHA]
    return FichaDeposito(extraidos=extraidos, manuales=manuales)


def _construir_respuesta(
    resultados_motor: list,
    reporte: dict,
    prompts_data: list,
    archivo_nombre: str,
    archivo_tamano: int,
    rules_data: dict,
) -> ValidarResponse:
    """Ensambla la respuesta completa de la API a partir de la salida del motor."""
    resultados_dto = [
        _rule_result_a_dto(r)
        for r in resultados_motor
        # Las reglas de CAPTURA (diseño 17) no son reglas de validación:
        # no viajan en `resultados`; sus datos van en `ficha_deposito`.
        if not r.captura
    ]
    resumen_motor = reporte["resumen"]

    # La ficha solo materializa con semáforo verde (invariante del
    # contrato v1.7.0): un documento con errores bloqueantes no se
    # deposita, y no hay nada que pre-llenar.
    ficha = _ficha_desde_reporte(reporte) if reporte["semaforo"] == "verde" else None

    return ValidarResponse(
        semaforo=reporte["semaforo"],
        resumen=ResumenValidacion(
            total=resumen_motor["total"],
            total_evaluadas=resumen_motor["total_evaluadas"],
            reglas_no_aplicables=resumen_motor["reglas_no_aplicables"],
            fallidos_error=resumen_motor["fallidos_error"],
            fallidos_warning=resumen_motor["fallidos_warning"],
        ),
        resultados=resultados_dto,
        como_preguntar_a_una_ia=[
            PromptIA(rule_id=p["rule_id"], prompt=p["prompt"]) for p in prompts_data
        ],
        metadatos=MetadatosValidacion(
            archivo_nombre=archivo_nombre,
            archivo_tamano_bytes=archivo_tamano,
            reglas_evaluadas=resumen_motor["total_evaluadas"],
            reglas_totales=resumen_motor["total"],
            version_esquema=rules_data.get("version", "desconocido"),
            **_extraer_metadata_tipo_documento(resultados_motor),
        ),
        ficha_deposito=ficha,
    )


def _validar_correo(correo: str | None) -> str | None:
    """Valida el correo electrónico del estudiante (campo opcional).

    - `None` o cadena vacía → `None` (el frontend puede omitirlo o enviar "").
    - Si se envía, debe tener formato de correo válido; si no, lanza 422
      con mensaje descriptivo en español.

    El valor normalizado retornado es el destinatario de la notificación de
    observaciones (Actividad 6): se envía un correo cuando el semáforo es
    "rojo", la notificación está habilitada y el servidor SMTP acepta el envío.
    """
    if correo is None:
        return None
    correo_limpio = correo.strip()
    if not correo_limpio:
        return None

    try:
        resultado = validate_email(correo_limpio, check_deliverability=False)
        return resultado.normalized
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Correo electrónico inválido: '{correo_limpio}'. "
                f"Formato esperado: usuario@dominio."
            ),
        ) from e


# ---------------------------------------------------------------------------
# Aplicación FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(
    title="VistoBueno API",
    description="API de validación automática de formato de tesis — UNT FECyC",
    version="1.15.0",
)
# DNS rebinding: se valida el header Host antes de cualquier endpoint.
app.add_middleware(MiddlewareHostConfiable)


@app.exception_handler(LLMNoDisponible)
async def _llm_no_disponible_handler(request: Request, exc: LLMNoDisponible):
    """Convierte `LLMNoDisponible` en 503 para los endpoints de IA."""
    return JSONResponse(status_code=503, content={"detail": str(exc)})


async def _guardar_docx_temporal(archivo: UploadFile) -> tuple[str, int]:
    """Valida el DOCX subido y lo guarda en un archivo temporal.

    Aplica la misma validación de entrada que `POST /validar`: nombre,
    extensión, content-type, tamaño, archivo vacío, firma ZIP y presencia
    de `word/document.xml`. Devuelve la ruta del temporal y el tamaño en
    bytes; el llamador debe borrar la ruta.

    La usan `/validar` y `/asistente/explicar` para que las dos rutas
    rechacen los archivos con los mismos códigos y mensajes.
    """
    if archivo.filename is None or archivo.filename == "":
        raise HTTPException(
            status_code=400,
            detail="Campo 'archivo' requerido. Envíe un archivo .docx en el campo 'archivo' del formulario multipart.",
        )

    if not archivo.filename.lower().endswith(EXTENSION_ACEPTADA):
        raise HTTPException(
            status_code=415,
            detail=(
                f"Tipo de archivo no soportado: '{archivo.filename}'. "
                f"Solo se aceptan archivos .docx "
                f"({EXTENSION_ACEPTADA})."
            ),
        )

    content_type = archivo.content_type or ""
    if content_type and content_type not in TIPOS_ACEPTADOS:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Content-Type no soportado: '{content_type}'. Solo se aceptan archivos .docx."
            ),
        )

    # Leer a lo sumo TAMANO_MAXIMO_BYTES + 1: evita cargar en memoria un
    # upload arbitrariamente grande antes de validar el tamaño.
    try:
        contenido = await archivo.read(TAMANO_MAXIMO_BYTES + 1)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail="No se pudo leer el archivo enviado.",
        ) from e

    tamano = len(contenido)
    if tamano > TAMANO_MAXIMO_BYTES:
        raise HTTPException(
            status_code=413,
            detail=("El archivo excede el tamaño máximo permitido (10 MB)."),
        )

    if tamano == 0:
        raise HTTPException(
            status_code=422,
            detail="El archivo está vacío.",
        )

    # Un DOCX es un paquete OPC (ZIP). La firma local permite rechazar
    # rápido un archivo renombrado a .docx sin abrirlo.
    if not contenido.startswith(b"PK\x03\x04"):
        raise HTTPException(
            status_code=422,
            detail=(
                "El archivo no es un ZIP/DOCX válido: cabecera incorrecta "
                "(se esperaba la firma 'PK')."
            ),
        )

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=EXTENSION_ACEPTADA) as tmp:
            tmp.write(contenido)
            tmp_path = tmp.name

        # La parte OPC obligatoria se comprueba antes de validar: si falta,
        # la respuesta es 422; un KeyError posterior de las reglas es un
        # fallo interno de configuración y sigue la ruta del 500.
        with zipfile.ZipFile(tmp_path) as paquete:
            if "word/document.xml" not in paquete.namelist():
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "El archivo no contiene un documento Word válido: "
                        "archivo interno faltante ('word/document.xml')."
                    ),
                )
    except zipfile.BadZipFile as e:
        if tmp_path is not None:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
        raise HTTPException(
            status_code=422,
            detail=(
                "No se pudo procesar el archivo DOCX: archivo corrupto o no es un DOCX válido."
            ),
        ) from e
    except BaseException:
        if tmp_path is not None:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass
        raise

    if tmp_path is None:  # pragma: no cover - NamedTemporaryFile lanza o asigna
        raise HTTPException(
            status_code=500,
            detail="No se pudo preparar el archivo temporal.",
        )
    return tmp_path, tamano


@app.post(
    "/validar",
    response_model=ValidarResponse,
    summary="Validar formato de tesis",
    description=(
        "Recibe un archivo DOCX de tesis y devuelve un reporte de validación "
        "contra las reglas de formato de la Universidad Nacional de Trujillo."
    ),
    responses={
        400: {"description": "Sin archivo en la solicitud"},
        403: {"description": "Petición desde otro equipo o sin token válido"},
        413: {"description": "Archivo excede el tamaño máximo (10 MB)"},
        415: {"description": "Tipo de archivo no soportado"},
        422: {"description": "Archivo corrupto, no es DOCX válido o correo inválido"},
        429: {"description": "Demasiadas peticiones de validación seguidas"},
        500: {"description": "Error interno del validador"},
    },
    dependencies=[Depends(verificar_acceso_local), Depends(limitar_validaciones)],
)
async def validar(
    archivo: UploadFile = File(..., description="Archivo .docx a validar"),
    incluir_prompts_ia: bool = Query(
        default=True,
        description="Incluir la sección 'Cómo preguntar a una IA' en la respuesta",
    ),
    correo: str | None = Form(
        default=None,
        description=(
            "Correo electrónico del estudiante (opcional). "
            "Destinatario de las observaciones cuando se solicita el envío "
            "(campo `notificar`)."
        ),
        # Swagger prellenaba "string" y un Execute sin editar enviaba
        # basura; con ejemplo vacío el campo se deja en blanco solo
        # (revisión del PR #55, hallazgo 2).
        examples=[""],
    ),
    notificar: bool = Form(
        default=False,
        description=(
            "Solicitar el envío del correo de observaciones al estudiante "
            "(opt-in del operador). Solo aplica con semáforo rojo y un "
            "`correo` válido."
        ),
    ),
    depositar: bool = Form(
        default=False,
        description=(
            "DEPRECADO (decisión 2026-10-28): el depósito automático en DSpace "
            "queda fuera del flujo. El flujo oficial es la ficha (SPA) → buzón → "
            "userscript, y el archivo lo adjunta el encargado en el formulario "
            "oficial de DSpace. El campo se conserva para no romper el "
            "contrato, pero ya no dispara ninguna llamada."
        ),
    ),
    titulo: str | None = Form(
        default=None,
        description=(
            "DEPRECADO: metadato dc.title que usaba el depósito automático. "
            "El título de la ficha de depósito lo captura el motor del DOCX."
        ),
        examples=[""],
    ),
    autores: str | None = Form(
        default=None,
        description=(
            "DEPRECADO: metadato dc.contributor.author que usaba el depósito "
            "automático. Los autores los captura el motor del DOCX y el "
            "operador los corrige en la pantalla de ficha."
        ),
        examples=[""],
    ),
    asesor: str | None = Form(
        default=None,
        description=(
            "DEPRECADO: metadato dc.contributor.advisor que usaba el depósito "
            "automático. El asesor lo captura el motor del DOCX."
        ),
        examples=[""],
    ),
    resumen: str | None = Form(
        default=None,
        description=(
            "DEPRECADO: metadato dc.description.abstract que usaba el depósito "
            "automático. El resumen lo captura el motor del DOCX."
        ),
        examples=[""],
    ),
    palabras_clave: str | None = Form(
        default=None,
        description=(
            "DEPRECADO: metadato dc.subject que usaba el depósito automático. "
            "Las palabras clave las captura el motor del DOCX."
        ),
        examples=[""],
    ),
):
    # --- Validación: correo electrónico (opcional) ---
    correo_normalizado = _validar_correo(correo)

    # --- Validación del DOCX y guardado en archivo temporal ---
    # La misma validación de entrada la usa /asistente/explicar.
    tmp_path = None
    try:
        tmp_path, tamano = await _guardar_docx_temporal(archivo)

        rules_data = _get_rules()

        # El 422 se acota a excepciones explícitas del archivo. Un ValueError
        # o KeyError de las reglas es un fallo interno de configuración y debe
        # llegar al 500 exterior. Los errores del mapeo a DTO también quedan
        # fuera de este bloque y siguen la misma ruta de 500.
        # El motor es síncrono y CPU-intenso (recompila el DSL en cada
        # request): se despacha al threadpool para no congelar el event
        # loop mientras dura la validación. Se pasa el ruleset de captura
        # de la ficha (diseño 17) en la MISMA pasada: sus capturas viajan
        # en reporte["ficha"] y no afectan semáforo ni resumen.
        medidor = _MedidorCPU()
        try:
            resultados_motor = await run_in_threadpool(
                medidor.medir, validate_docx, tmp_path, rules_data, _get_ficha_rules()
            )
        except DSLValidationError as e:
            # Reglas rotas = error de configuración del servidor, no del
            # documento del estudiante.
            raise HTTPException(
                status_code=500,
                detail=f"Error interno del validador: configuración de reglas inválida: {e}",
            ) from e
        except InvalidDocumentError as e:
            # El paquete es un ZIP, pero su XML no representa un documento
            # Word procesable. Esta excepción es explícita: otros ValueError
            # pueden venir de una configuración defectuosa y deben quedar en
            # el 500 exterior, no culpar al archivo del estudiante.
            raise HTTPException(
                status_code=422,
                detail=f"El archivo no contiene un documento Word válido: {e}.",
            ) from e
        except zipfile.BadZipFile as e:
            # Archivo no es un ZIP válido (truncado, corrupto, etc.)
            raise HTTPException(
                status_code=422,
                detail=(
                    "No se pudo procesar el archivo DOCX: archivo corrupto o no es un DOCX válido."
                ),
            ) from e
        finally:
            # El cupo adaptativo descuenta el TRABAJO real (CPU del hilo
            # que validó), no la latencia: con peticiones concurrentes, la
            # espera del GIL no es trabajo (revisión PR #71, B1).
            _cobrar_coste_validacion(medidor.segundos)

        reporte = build_report(resultados_motor)

        # Prompts de IA (solo si se solicitan)
        prompts_data = []
        if incluir_prompts_ia:
            fallidos = [r for r in resultados_motor if not r.passed]
            prompts_data = build_ai_help_section(fallidos)

        respuesta = _construir_respuesta(
            resultados_motor=resultados_motor,
            reporte=reporte,
            prompts_data=prompts_data,
            # El helper ya validó que el nombre existe y no está vacío.
            archivo_nombre=archivo.filename or "",
            archivo_tamano=tamano,
            rules_data=rules_data,
        )

        # --- Notificación de observaciones (Actividad 6, best-effort) ---
        # El estado se expone al personal del repositorio (herramienta de
        # uso interno): "enviado" permite informar "enviamos las observaciones
        # al correo del estudiante"; "fallo" incluye el motivo técnico.
        # El envío es opt-in por solicitud (`notificar`): el operador decide
        # cuándo el reporte está listo para llegarle al estudiante. Se exige
        # además semáforo "rojo" y un `correo` válido, y el servidor debe
        # tener la notificación habilitada. enviar_notificacion() NUNCA
        # lanza: un fallo de SMTP no debe romper la respuesta HTTP.
        estado = EstadoNotificacionAPI.SIN_CORREO
        detalle: str | None = None
        if correo_normalizado:
            if not notificar:
                estado = EstadoNotificacionAPI.NO_SOLICITADO
            elif respuesta.semaforo != "rojo":
                estado = EstadoNotificacionAPI.SIN_OBSERVACIONES
            else:
                config_smtp = ConfigSMTP.desde_entorno()
                if not config_smtp.enabled:
                    estado = EstadoNotificacionAPI.DESHABILITADO
                    # Nota de configuración para el personal del repositorio
                    # (hallazgo B3): sin esto, "casilla marcada → 200 OK →
                    # nada" era indistinguible de un envío silencioso. El
                    # detalle indica cómo habilitar el servidor.
                    detalle = (
                        "El servidor no tiene la notificación habilitada: "
                        "configure VISTOBUENO_NOTIFICACIONES=1 y VISTOBUENO_SMTP_HOST."
                    )
                else:
                    # smtplib es bloqueante (timeout de hasta 10 s): fuera
                    # del event loop, o un SMTP caído congela toda la API.
                    resultado_envio = await run_in_threadpool(
                        enviar_notificacion,
                        respuesta,
                        correo_normalizado,
                        config=config_smtp,
                    )
                    if resultado_envio.enviado:
                        estado = EstadoNotificacionAPI.ENVIADO
                    else:
                        estado = EstadoNotificacionAPI.FALLO
                        detalle = resultado_envio.detalle
        respuesta.notificacion = NotificacionAPI(estado=estado, detalle=detalle)

        # --- Depósito en DSpace (Actividad 10) — DEPRECADO ---
        # Decisión del equipo (2026-10-28, auditoría de comportamiento): la
        # app NO escribe en la API de DSpace. El flujo oficial es la ficha
        # (SPA) → buzón → userscript, que rellena el formulario oficial; el
        # archivo lo adjunta el encargado en ese formulario.
        # Por eso `depositar=true` ya NO dispara ninguna llamada: responde
        # "deshabilitado" con la nota que explica el flujo vigente. El campo
        # y el DTO `deposito` se conservan para no romper el contrato.
        estado_dep = EstadoDepositoAPI.SIN_SOLICITUD
        detalle_dep: str | None = None
        if depositar:
            estado_dep = EstadoDepositoAPI.DESHABILITADO
            detalle_dep = (
                "El depósito automático está deshabilitado: el flujo oficial es "
                "el formulario de DSpace + el userscript de VistoBueno; el "
                "archivo lo adjunta el encargado en el formulario oficial."
            )
        respuesta.deposito = DepositoAPI(estado=estado_dep, detalle=detalle_dep)

        return respuesta

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error interno del validador: {type(e).__name__}: {e}",
        ) from e
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Buzón de una ranura: comunicación con el userscript de depósito
# ---------------------------------------------------------------------------


# Instancia única del buzón (una ranura de trámite con dos ventanas).
# Es la única pieza de estado del servidor: ver docs/CONTRATO_API.md.
def _ttl_desde_entorno(nombre: str, defecto: float) -> float:
    """Lee un TTL positivo del entorno; un valor inválido no tumba la API."""
    bruto = (os.environ.get(nombre) or "").strip()
    if not bruto:
        return defecto
    try:
        valor = float(bruto)
    except ValueError:
        logging.getLogger(__name__).warning(
            "%s='%s' no es un número; se usa %.0f segundos.", nombre, bruto, defecto
        )
        return defecto
    if valor <= 0:
        logging.getLogger(__name__).warning(
            "%s=%.0f no es positivo; se usa %.0f segundos.", nombre, valor, defecto
        )
        return defecto
    return valor


TTL_AUTORRELLENO_SEG = _ttl_desde_entorno("VISTOBUENO_TTL_AUTORRELLENO_SEG", 3600.0)
TTL_TRAMITE_SEG = _ttl_desde_entorno("VISTOBUENO_TTL_TRAMITE_SEG", 86400.0)
_BUZON = Buzon(
    ttl_autorelleno_segundos=TTL_AUTORRELLENO_SEG,
    ttl_tramite_segundos=TTL_TRAMITE_SEG,
)


def _deposito_recibido(datos: dict, revision: int) -> DepositoRecibido:
    """Convierte el depósito almacenado al DTO de lectura."""
    return DepositoRecibido(
        tramite_id=datos["tramite_id"],
        handle=datos["handle"],
        titulo_observado=datos["titulo_observado"],
        titulo_verificado=bool(datos.get("titulo_verificado")),
        autores_observados=datos.get("autores_observados"),
        autores_verificados=bool(datos.get("autores_verificados")),
        timestamp=datos["timestamp"],
        revision_confirmada=datos["revision_confirmada"],
        confirmado_en=datos["confirmado_en"],
        confirmado_por=datos.get("confirmado_por", "operador"),
        confirmacion_vigente=datos["revision_confirmada"] == revision,
        titulo=datos["titulo_observado"],
    )


@app.post(
    "/ficha-pendiente",
    status_code=201,
    response_model=FichaPendientePublicada,
    summary="Publicar la ficha completada en el buzón",
    description=(
        "La SPA publica la ficha (extraídos + manuales) para que el "
        "userscript de depósito la lea desde el navegador del operador. "
        "Cada publicación crea un `tramite_id` y una `revision` nuevos, y "
        "descarta el depósito anterior, aunque el título sea el mismo. "
        "El buzón tiene UNA ranura ('última gana'). La ficha es elegible "
        "para autorelleno durante `autofill_hasta` (1 hora por defecto); "
        "el trámite completo se retiene hasta `retenido_hasta` (24 horas "
        "por defecto) para confirmaciones tardías y papeleo. "
        "Solo se sirve desde la máquina donde corre la app (loopback); "
        "si hay token configurado, exige el header "
        f"'{CABECERA_TOKEN_BUZON}'."
    ),
    responses={403: {"description": "Petición desde otro equipo o sin token válido"}},
    dependencies=[Depends(verificar_acceso_local)],
)
async def publicar_ficha_pendiente(ficha: FichaDeposito) -> FichaPendientePublicada:
    publicacion = _BUZON.publicar_ficha(ficha.model_dump())
    return FichaPendientePublicada(
        tramite_id=publicacion.tramite_id,
        revision=publicacion.revision,
        autofill_hasta=publicacion.autofill_hasta,
        retenido_hasta=publicacion.retenido_hasta,
        vence_en=publicacion.autofill_hasta,
    )


@app.get(
    "/ficha-pendiente",
    response_model=FichaPendienteLeida,
    summary="Leer la ficha elegible para autorelleno",
    description=(
        "El userscript lee aquí la ficha a rellenar, su `tramite_id` y la "
        "`revision` vigente. El 404 significa que no es elegible para "
        "autorelleno: la ranura está vacía o venció la ventana de 1 hora. "
        "Una ficha retenida fuera de esa ventana se consulta por "
        "`GET /tramite`. Solo se sirve desde la máquina donde corre la app "
        "(loopback); si hay token configurado, exige el header "
        f"'{CABECERA_TOKEN_BUZON}'."
    ),
    responses={
        403: {"description": "Petición desde otro equipo o sin token válido"},
        404: {"description": "Sin ficha elegible para autorelleno"},
    },
    dependencies=[Depends(verificar_acceso_local)],
)
async def leer_ficha_pendiente() -> FichaPendienteLeida:
    estado = _BUZON.leer_tramite()
    if estado is None:
        raise HTTPException(
            status_code=404,
            detail="Sin ficha pendiente: la ranura está vacía o venció la retención.",
        )
    if not estado.autofill_habil:
        raise HTTPException(
            status_code=404,
            detail=(
                "La ficha está retenida pero ya no es elegible para autorelleno "
                "(venció la ventana de 1 hora). Consúltala con GET /tramite."
            ),
        )
    return FichaPendienteLeida(
        ficha=FichaDeposito(**estado.ficha),
        tramite_id=estado.tramite_id,
        revision=estado.revision,
        autofill_hasta=estado.autofill_hasta,
        retenido_hasta=estado.retenido_hasta,
        vence_en=estado.autofill_hasta,
    )


@app.get(
    "/tramite",
    response_model=TramiteLeido,
    summary="Leer el trámite retenido (ficha canónica, revisión y depósito)",
    description=(
        "Devuelve la ficha canónica vigente, su `revision`, la "
        "`inconsistencia` pendiente y el `deposito` confirmado, si existe. "
        "Sigue disponible después de vencer el autorelleno (hasta la "
        "retención del trámite, 24 horas por defecto). La SPA lo usa para "
        "refrescar antes del papeleo y el userscript para construir el "
        "panel de confirmación con la revisión vigente. "
        "Solo se sirve desde la máquina donde corre la app (loopback); si "
        f"hay token configurado, exige el header '{CABECERA_TOKEN_BUZON}'."
    ),
    responses={
        403: {"description": "Petición desde otro equipo o sin token válido"},
        404: {"description": "Sin trámite retenido"},
    },
    dependencies=[Depends(verificar_acceso_local)],
)
async def leer_tramite() -> TramiteLeido:
    estado = _BUZON.leer_tramite()
    if estado is None:
        raise HTTPException(
            status_code=404,
            detail="Sin trámite retenido: la ranura está vacía o venció la retención.",
        )
    inconsistencia = (
        InconsistenciaAPI(**estado.inconsistencia) if estado.inconsistencia is not None else None
    )
    deposito = (
        _deposito_recibido(estado.deposito, estado.revision)
        if estado.deposito is not None
        else None
    )
    return TramiteLeido(
        ficha=FichaDeposito(**estado.ficha),
        tramite_id=estado.tramite_id,
        revision=estado.revision,
        inconsistencia=inconsistencia,
        deposito=deposito,
        publicada_en=estado.publicada_en,
        autofill_hasta=estado.autofill_hasta,
        retenido_hasta=estado.retenido_hasta,
        autofill_habil=estado.autofill_habil,
        confirmacion_vigente=estado.confirmacion_vigente,
    )


@app.post(
    "/deposito",
    status_code=204,
    summary="Confirmar el depósito archivado (escritura explícita)",
    description=(
        "El userscript envía la confirmación explícita del operador desde "
        "la página del ítem: `tramite_id`, handle, título observado, "
        "autores observados (opcional), el `timestamp` del clic en "
        "Depositar, la `revision_esperada` revisada y "
        '`atestacion="operador"`. Un payload automático de la versión '
        "anterior no incluye la atestación ni la revisión y recibe 422: no "
        "crea evidencia ni habilita papeleo. El servidor genera "
        "`confirmado_en` (solo auditoría); `timestamp` sigue alimentando la "
        "HORA del registro y de la constancia. 404 si no hay trámite "
        "retenido; 409 si el trámite, la revisión, el título o los autores "
        "no coinciden. Solo se sirve desde la máquina donde corre la app "
        "(loopback); si hay token configurado, exige el header "
        f"'{CABECERA_TOKEN_BUZON}'."
    ),
    responses={
        403: {"description": "Petición desde otro equipo o sin token válido"},
        404: {"description": "Sin trámite retenido para aceptar la confirmación"},
        409: {"description": "Trámite, revisión, título o autores no coinciden"},
        422: {"description": "Falta la atestación explícita o la revisión esperada"},
    },
    dependencies=[Depends(verificar_acceso_local)],
)
async def reportar_deposito(datos: DepositoReportado) -> None:
    try:
        _BUZON.reportar_deposito(datos.model_dump())
    except SinFichaVigente as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (TramiteNoCoincide, RevisionNoCoincide) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (TituloNoCoincide, AutoresNoCoinciden) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ConfirmacionInvalida, HandleInvalido) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.get(
    "/deposito",
    response_model=DepositoRecibido,
    summary="Leer la confirmación del depósito",
    description=(
        "La SPA sondea aquí mientras espera la confirmación del operador. "
        "404 cuando no hay confirmación o venció la retención del trámite. "
        "`confirmacion_vigente=false` significa que una conciliación "
        "posterior cambió la ficha: hace falta reconfirmar. `titulo` se "
        "conserva como alias deprecado de `titulo_observado`. Solo se "
        "sirve desde la máquina donde corre la app (loopback); si hay "
        f"token configurado, exige el header '{CABECERA_TOKEN_BUZON}'."
    ),
    responses={
        403: {"description": "Petición desde otro equipo o sin token válido"},
        404: {"description": "Sin confirmación de depósito o trámite vencido"},
    },
    dependencies=[Depends(verificar_acceso_local)],
)
async def leer_deposito_reportado() -> DepositoRecibido:
    estado = _BUZON.leer_tramite()
    if estado is None or estado.deposito is None:
        raise HTTPException(
            status_code=404,
            detail="Sin depósito confirmado: vacío, no confirmado o trámite vencido.",
        )
    return _deposito_recibido(estado.deposito, estado.revision)


@app.post(
    "/ficha-pendiente/inconsistencia",
    status_code=204,
    summary="Marcar una inconsistencia entre el ítem y la ficha",
    description=(
        "El userscript lo llama cuando la página del ítem contradice la "
        "ficha canónica (título o autores distintos). La marca bloquea el "
        "papeleo hasta una conciliación. Exige el `tramite_id`, el handle, "
        "la `revision_esperada` y al menos un motivo. Una revisión obsoleta "
        "devuelve 409 y no cambia nada. Solo se sirve desde la máquina "
        "donde corre la app (loopback); si hay token configurado, exige el "
        f"header '{CABECERA_TOKEN_BUZON}'."
    ),
    responses={
        403: {"description": "Petición desde otro equipo o sin token válido"},
        404: {"description": "Sin trámite retenido"},
        409: {"description": "Trámite, revisión o handle no coinciden"},
        422: {"description": "Sin motivos válidos"},
    },
    dependencies=[Depends(verificar_acceso_local)],
)
async def marcar_inconsistencia(datos: InconsistenciaRequest) -> None:
    try:
        _BUZON.marcar_inconsistencia(
            tramite_id=datos.tramite_id,
            handle=datos.handle,
            revision_esperada=datos.revision_esperada,
            motivos=datos.motivos,
        )
    except SinFichaVigente as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (TramiteNoCoincide, RevisionNoCoincide, HandleNoCoincide) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ConfirmacionInvalida, HandleInvalido) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


@app.post(
    "/ficha-pendiente/reconciliar",
    response_model=ReconciliacionResponse,
    summary="Conciliar una corrección con el ítem depositado",
    description=(
        "Reemplaza la ficha canónica con una corrección revisada por el "
        "operador. Exige `revision_esperada`; una revisión obsoleta "
        "devuelve 409 y no escribe nada. Funciona SIN depósito (no crea "
        "evidencia de depósito ni habilita papeleo) y CON depósito "
        "confirmado (exige el mismo handle, conserva la evidencia y "
        "invalida la confirmación: el papeleo exige reconfirmar la "
        "revisión nueva). El handle nunca aprueba datos por sí solo. Solo "
        "se sirve desde la máquina donde corre la app (loopback); si hay "
        f"token configurado, exige el header '{CABECERA_TOKEN_BUZON}'."
    ),
    responses={
        403: {"description": "Petición desde otro equipo o sin token válido"},
        404: {"description": "Sin trámite retenido"},
        409: {"description": "Revisión obsoleta o handle distinto del depositado"},
        422: {"description": "Handle o ficha mal formados, o motivo vacío"},
    },
    dependencies=[Depends(verificar_acceso_local)],
)
async def reconciliar_ficha(datos: ReconciliarRequest) -> ReconciliacionResponse:
    try:
        estado = _BUZON.reconciliar(
            ficha=datos.ficha.model_dump(),
            revision_esperada=datos.revision_esperada,
            handle=datos.handle,
            motivo=datos.motivo,
        )
    except SinFichaVigente as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (RevisionNoCoincide, HandleNoCoincide) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except (ConfirmacionInvalida, HandleInvalido) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    deposito = (
        _deposito_recibido(estado.deposito, estado.revision)
        if estado.deposito is not None
        else None
    )
    return ReconciliacionResponse(
        tramite_id=estado.tramite_id,
        revision=estado.revision,
        handle=datos.handle,
        confirmacion_vigente=estado.confirmacion_vigente,
        deposito=deposito,
    )


# ---------------------------------------------------------------------------
# Constancia de depósito (Modelo B) y fila de registro
# ---------------------------------------------------------------------------

# Plantilla oficial de la constancia. Vive en recursos/ (no versionada:
# es un artefacto institucional). Ruta sobreescribible por entorno.
PLANTILLA_CONSTANCIA_POR_DEFECTO = (
    Path(__file__).resolve().parent.parent / "recursos" / "TESIS DIGITAL MODELO B-2026.docx"
)


def _ruta_plantilla_constancia() -> Path:
    """Ruta de la plantilla del Modelo B (configurable por entorno)."""
    return Path(
        os.environ.get("VISTOBUENO_PLANTILLA_CONSTANCIA", str(PLANTILLA_CONSTANCIA_POR_DEFECTO))
    )


def _firma_operador() -> str:
    """Firma del responsable (columna FIRMA del registro), por entorno."""
    return os.environ.get("VISTOBUENO_FIRMA", "").strip()


def _verificar_tramite_depositado(solicitud: FilaRegistroRequest) -> EstadoTramite:
    """Ata el papeleo al estado canónico de la misma ficha.

    La solicitud solo confirma la identidad del trámite. El papeleo usa la
    ficha canónica y la confirmación guardada por el servidor. Si falta el
    estado, la confirmación no es la vigente, hay una inconsistencia sin
    conciliar o cualquier campo no coincide, la respuesta es 409: la SPA
    debe refrescar `GET /tramite` y volver a preparar o confirmar.

    La HORA del papeleo sale del `timestamp` del clic en Depositar;
    `confirmado_en` es solo auditoría y nunca se sustituye aquí.
    """
    estado = _BUZON.leer_tramite()
    if estado is None or estado.deposito is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "No hay un depósito confirmado vigente para este papeleo: "
                "expiró el trámite, no se publicó o no se confirmó el ítem. "
                "Vuelve a preparar la ficha."
            ),
        )
    deposito = estado.deposito
    if deposito.get("tramite_id") != solicitud.tramite_id:
        raise HTTPException(
            status_code=409,
            detail=(
                "El trámite de la solicitud no coincide con el depósito vigente. "
                "Vuelve a preparar la ficha."
            ),
        )
    if deposito.get("handle") != solicitud.handle:
        raise HTTPException(
            status_code=409,
            detail=(
                "El handle de la solicitud no coincide con el depósito vigente. "
                "Usa el handle confirmado por el userscript."
            ),
        )
    if deposito.get("timestamp") != solicitud.timestamp:
        raise HTTPException(
            status_code=409,
            detail=(
                "El timestamp de la solicitud no coincide con el depósito vigente. "
                "Vuelve a preparar la ficha."
            ),
        )
    if deposito.get("revision_confirmada") != estado.revision:
        raise HTTPException(
            status_code=409,
            detail=(
                "La ficha cambió después de la confirmación del depósito. "
                "Reconfirma la revisión vigente antes de generar papeleo."
            ),
        )
    if estado.inconsistencia is not None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Hay una inconsistencia entre el ítem y la ficha sin conciliar. "
                "Concilia la corrección antes de generar papeleo."
            ),
        )
    if solicitud.ficha.model_dump() != estado.ficha:
        raise HTTPException(
            status_code=409,
            detail=(
                "La ficha de la solicitud no coincide con la ficha canónica. "
                "Refresca el trámite antes de generar papeleo."
            ),
        )
    return estado


def _constancias_de_solicitud(snapshot: EstadoTramite) -> list[DatosConstancia]:
    """Arma los datos canónicos: una constancia por autor.

    La ficha, el handle y el timestamp salen del snapshot del servidor.
    El cliente no puede sustituirlos.

    Errores:

    - 422: timestamp canónico que no es ISO 8601, o falta un dato de la
      ficha (título, autores, matrículas alineadas).
    - 500: configuración del servidor (firma o plantilla).
    """
    deposito = snapshot.deposito
    if deposito is None:
        # `_verificar_tramite_depositado` ya lo garantiza; el chequeo
        # explícito mantiene el tipo del snapshot verificable.
        raise HTTPException(
            status_code=409,
            detail=(
                "No hay un depósito confirmado vigente para este papeleo: "
                "vuelve a preparar la ficha."
            ),
        )
    timestamp = deposito["timestamp"]
    try:
        momento = _parsear_timestamp(timestamp)
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Timestamp inválido: '{timestamp}'. Use ISO 8601 (p. ej. 2026-10-19T18:10:00).",
        ) from e

    firma = _firma_operador()
    if not firma:
        raise HTTPException(
            status_code=500,
            detail=(
                "El servidor no tiene la firma del responsable configurada: "
                "defina VISTOBUENO_FIRMA (nombre que va en la columna FIRMA del registro)."
            ),
        )

    ficha = FichaDeposito(**snapshot.ficha)
    try:
        return constancias_por_autor(ficha.model_dump(), deposito["handle"], momento, firma)
    except ErrorDatosConstancia as e:
        raise HTTPException(status_code=422, detail=str(e)) from e


def _filas_de_registro(datos: list[DatosConstancia]) -> list[str]:
    """Calcula una fila TSV por autor (trabajo CPU, se ejecuta en el threadpool)."""
    return [d.fila_registro() for d in datos]


def _parsear_timestamp(texto: str) -> datetime:
    """Parsea el timestamp ISO 8601 y lo normaliza a la hora del Perú.

    El userscript envía hora de pared (sin offset), porque el registro
    oficial y la constancia usan la hora peruana. Un timestamp sin
    offset se interpreta como `America/Lima`; uno con offset se convierte
    a esa zona. Así el documento no depende de la zona del navegador ni
    del servidor.
    """
    momento = datetime.fromisoformat(texto)
    if momento.tzinfo is None:
        return momento.replace(tzinfo=ZONA_LIMA)
    return momento.astimezone(ZONA_LIMA)


def _nombre_archivo_constancia(datos: DatosConstancia) -> str:
    """Nombre de descarga: 'constancia - {autor sanitizado}.docx'.

    Delega a _nombre_seguro en constancia.py para que el nombre del
    zip y el del docx sean consistentes entre sí.
    """
    return f"constancia - {_nombre_seguro(datos.autor)}.docx"


@app.post(
    "/constancia",
    summary="Descargar la constancia de UN autor (Modelo B lleno, o paquete zip)",
    description=(
        "Genera la constancia de depósito del Modelo B con los MERGEFIELD "
        "reemplazados por los valores canónicos de la ficha publicada. Una "
        "constancia POR AUTOR: la SPA descarga una por cada estudiante "
        "iterando `indice_autor`. Devuelve el .docx como descarga binaria. "
        "Con `formato=zip` devuelve en su lugar un paquete con la constancia "
        ".docx y la fila del registro del autor como .csv (hallazgo 11: "
        '"POST /constancia podría incluirlo").'
    ),
    responses={
        200: {"description": "Constancia .docx (o paquete .zip con formato=zip)"},
        403: {"description": "Petición desde otro equipo o sin token válido"},
        409: {
            "description": "El trámite, la ficha, el handle o el timestamp no coinciden con el depósito vigente"
        },
        422: {
            "description": "Timestamp canónico inválido, falta un dato de la ficha o índice fuera de rango"
        },
        429: {"description": "Demasiadas generaciones de documentos seguidas"},
        500: {"description": "Firma o plantilla sin configurar en el servidor"},
    },
    dependencies=[Depends(verificar_acceso_local), Depends(limitar_papeleo)],
)
async def descargar_constancia(
    solicitud: ConstanciaRequest,
    formato: Literal["docx", "zip"] = Query(
        default="docx",
        description=(
            "docx: la constancia (retrocompatible). zip: constancia + "
            "registro.csv del autor en un solo paquete (hallazgo 11: "
            "'la constancia podría incluirlo')"
        ),
    ),
) -> Response:
    snapshot = _verificar_tramite_depositado(solicitud)
    datos = _constancias_de_solicitud(snapshot)
    if solicitud.indice_autor >= len(datos):
        raise HTTPException(
            status_code=422,
            detail=(
                f"indice_autor={solicitud.indice_autor} fuera de rango: "
                f"la ficha trae {len(datos)} autor(es)."
            ),
        )
    objetivo = datos[solicitud.indice_autor]
    medidor = _MedidorCPU()
    try:
        if formato == "zip":
            contenido = await run_in_threadpool(
                medidor.medir, constancia_en_zip, _ruta_plantilla_constancia(), objetivo
            )
            return Response(
                content=contenido,
                media_type="application/zip",
                headers={
                    "Content-Disposition": (
                        f'attachment; filename="{_nombre_archivo_constancia(objetivo)}.zip"'
                    )
                },
            )
        contenido = await run_in_threadpool(
            medidor.medir, llenar_constancia, _ruta_plantilla_constancia(), objetivo
        )
    except ErrorConfiguracionConstancia as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        # CPU real del hilo que generó el documento, no la latencia
        # (revisión PR #71, B1).
        _LIMITADOR_CPU_PAPELES.registrar_coste(medidor.segundos)
    return Response(
        content=contenido,
        media_type=MIME_DOCX_CONSTANCIA,
        headers={
            "Content-Disposition": f'attachment; filename="{_nombre_archivo_constancia(objetivo)}"'
        },
    )


@app.post(
    "/fila-registro",
    response_model=FilasRegistroResponse,
    summary="Generar las filas del registro (TSV, una por autor)",
    description=(
        "Devuelve las filas listas para pegar en el registro oficial de la "
        "biblioteca (XLSX): una por autor, en el orden exacto de columnas. "
        "Usa la ficha publicada y el depósito vigente del servidor. La app "
        "JAMÁS escribe el registro oficial: el operador pega la fila. Con "
        "`formato` en `tsv`, `csv` o `xlsx` devuelve en su lugar un ARCHIVO "
        "descargable listo para abrir en Excel/LibreOffice (hallazgo 11 de "
        "la revisión del PR #55): elimina los errores de pegado (encoding, "
        "tabs perdidos, columnas desalineadas)."
    ),
    responses={
        200: {"description": "Lista de filas TSV (json) o archivo descargable (tsv/csv/xlsx)"},
        403: {"description": "Petición desde otro equipo o sin token válido"},
        409: {
            "description": "El trámite, la ficha, el handle o el timestamp no coinciden con el depósito vigente"
        },
        422: {
            "description": "Timestamp canónico inválido, falta un dato de la ficha o formato desconocido"
        },
        429: {"description": "Demasiadas generaciones de documentos seguidas"},
        500: {"description": "Firma sin configurar en el servidor"},
    },
    dependencies=[Depends(verificar_acceso_local), Depends(limitar_papeleo)],
)
async def generar_fila_registro(
    solicitud: FilaRegistroRequest,
    formato: Literal["json", "tsv", "csv", "xlsx"] = Query(
        default="json",
        description="json: la lista TSV (retrocompatible). tsv/csv/xlsx: archivo descargable",
    ),
):
    snapshot = _verificar_tramite_depositado(solicitud)
    datos = _constancias_de_solicitud(snapshot)
    medidor = _MedidorCPU()
    try:
        filas = await run_in_threadpool(medidor.medir, _filas_de_registro, datos)

        if formato == "json":
            return FilasRegistroResponse(filas=filas)

        if formato == "tsv":
            texto = await run_in_threadpool(medidor.medir, filas_a_tsv, filas)
            return Response(
                content=texto.encode("utf-8"),
                media_type="text/tab-separated-values; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="registro_vistobueno.tsv"'},
            )
        if formato == "csv":
            texto = await run_in_threadpool(medidor.medir, filas_a_csv, filas)
            return Response(
                content=texto.encode("utf-8"),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="registro_vistobueno.csv"'},
            )
        # formato == "xlsx"
        contenido = await run_in_threadpool(medidor.medir, filas_a_xlsx, filas)
        return Response(
            content=contenido,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="registro_vistobueno.xlsx"'},
        )
    finally:
        # CPU real del hilo que armó las filas, no la latencia
        # (revisión PR #71, B1).
        _LIMITADOR_CPU_PAPELES.registrar_coste(medidor.segundos)


# ---------------------------------------------------------------------------
# Asistente del encargado — módulo de IA (diseño 16, Funcionalidad 2)
# ---------------------------------------------------------------------------
# Módulo advisory: nunca toca el semáforo ni produce `RuleResult`.
# Es opt-in con `OLLAMA_URL`; sin ella, `estado` responde `disponible=false`
# y `explicar` responde 503.

# La sonda de disponibilidad no debe colgar la SPA: si el servicio acepta
# la conexión pero no responde, se corta la espera y se informa como no
# disponible. El plazo del cliente LLM (`OLLAMA_TIMEOUT`, 180 s por
# defecto) es demasiado largo para un botón que consulta el estado.
TIEMPO_MAX_ESTADO_IA_S = 5.0


def obtener_cliente_ia() -> LLMClient:
    """Devuelve el cliente LLM para los endpoints de IA.

    Inyectable en tests con
    `app.dependency_overrides[obtener_cliente_ia] = lambda: StubLLM(...)`.

    Solo lo usa `POST /asistente/explicar`: `GET /asistente/estado` llama
    a `estado_ia()`, que ya sabe devolver `disponible=false` cuando el
    módulo no está configurado.
    """
    return get_llm_client()


@app.get(
    "/asistente/estado",
    response_model=EstadoAsistenteAPI,
    summary="Estado del módulo de IA",
    description=(
        "Devuelve si el módulo de IA está disponible y el modelo en uso. "
        "Nunca devuelve 503: si no hay `OLLAMA_URL` o el servicio no responde, "
        "responde con `disponible=false` para que el frontend desactive el botón."
    ),
    responses={
        200: {"description": "Estado del módulo de IA (siempre devuelve 200)"},
        403: {"description": "Petición desde otro equipo o sin token válido"},
    },
    dependencies=[Depends(verificar_acceso_local)],
)
async def estado_asistente() -> EstadoAsistenteAPI:
    """GET /asistente/estado — estado del módulo de IA (nunca 503)."""
    try:
        estado = await asyncio.wait_for(estado_ia(), timeout=TIEMPO_MAX_ESTADO_IA_S)
    except TimeoutError:
        # Un servicio que acepta la conexión pero no responde no puede
        # colgar la SPA: se informa como no disponible.
        return EstadoAsistenteAPI(disponible=False, modelo="")
    return EstadoAsistenteAPI(
        disponible=bool(estado["disponible"]),
        modelo=str(estado["modelo"]),
    )


@app.post(
    "/asistente/explicar",
    response_model=ExplicacionYPrioridadAPI,
    summary="Explicación y priorización de fallos (Funcionalidad 2)",
    description=(
        "Valida un DOCX con el motor determinista y le pide al LLM que "
        "explique las reglas fallidas y las priorice por orden de corrección. "
        "Es advisory: nunca toca el semáforo ni produce un `RuleResult`. "
        "Reutiliza la validación de entrada de POST /validar (extensión, "
        "content-type, tamaño y firma ZIP)."
    ),
    responses={
        400: {"description": "Sin archivo en la solicitud"},
        403: {"description": "Petición desde otro equipo o sin token válido"},
        413: {"description": "Archivo excede el tamaño máximo (10 MB)"},
        415: {"description": "Tipo de archivo no soportado"},
        422: {
            "description": "Archivo corrupto, no es DOCX válido o respuesta de IA no interpretable"
        },
        429: {"description": "Demasiadas peticiones de validación seguidas"},
        503: {"description": "Módulo de IA no disponible (falta OLLAMA_URL o servicio caído)"},
    },
    dependencies=[Depends(verificar_acceso_local), Depends(limitar_validaciones)],
)
async def explicar_asistente(
    archivo: UploadFile = File(...),  # noqa: B008
    client: LLMClient = Depends(obtener_cliente_ia),  # noqa: B008
) -> ExplicacionYPrioridadAPI:
    """POST /asistente/explicar — explica y prioriza los fallos de un DOCX."""
    # --- Validación del DOCX y guardado en archivo temporal ---
    tmp_path = None
    try:
        tmp_path, _ = await _guardar_docx_temporal(archivo)

        medidor = _MedidorCPU()
        try:
            resultados_motor = await run_in_threadpool(
                medidor.medir, validate_docx, tmp_path, _get_rules(), _get_ficha_rules()
            )
        except DSLValidationError as e:
            raise HTTPException(
                status_code=500,
                detail=f"Error interno del validador: configuración de reglas inválida: {e}",
            ) from e
        except InvalidDocumentError as e:
            raise HTTPException(
                status_code=422,
                detail=f"El archivo no contiene un documento Word válido: {e}.",
            ) from e
        except zipfile.BadZipFile as e:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No se pudo procesar el archivo DOCX: archivo corrupto o no es un DOCX válido."
                ),
            ) from e
        finally:
            _cobrar_coste_validacion(medidor.segundos)

        # Tipo documental efectivo: el inferido manda; si no hubo inferencia,
        # se usa el declarado. La IA lo recibe como contexto, nunca lo cambia.
        metadatos_tipo = _extraer_metadata_tipo_documento(resultados_motor)
        tipo_documento: str | None = (
            metadatos_tipo["tipo_documento_inferido"] or metadatos_tipo["tipo_documento_declarado"]
        )

        # Funcionalidad 2: explicar y priorizar los fallos.
        try:
            resultado = await explicar_y_priorizar(
                resultados_motor, client=client, tipo_documento=tipo_documento
            )
        except LLMError as e:
            raise HTTPException(
                status_code=503,
                detail=f"Servicio de IA no disponible: {e}",
            ) from e
        except RespuestaIAInvalida as e:
            raise HTTPException(
                status_code=422,
                detail=f"La IA no devolvió un formato interpretable: {e}",
            ) from e

        return ExplicacionYPrioridadAPI(
            explicaciones=[
                ExplicacionItemAPI(rule_id=e.rule_id, explicacion=e.explicacion)
                for e in resultado.explicaciones
            ],
            prioridades=[
                PrioridadItemAPI(
                    orden=p.orden,
                    rule_id=p.rule_id,
                    razon=p.razon,
                    esfuerzo=cast(Literal["bajo", "medio", "alto"], p.esfuerzo),
                )
                for p in resultado.prioridades
            ],
            modelo=resultado.modelo,
        )
    finally:
        if tmp_path is not None:
            try:
                Path(tmp_path).unlink(missing_ok=True)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# SPA del frontend (opcional)
# ---------------------------------------------------------------------------

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def _montar_spa(app: FastAPI, dist_dir: Path = FRONTEND_DIST) -> bool:
    """Sirve la SPA construida si existe frontend/dist/index.html.

    El montaje va después de todas las rutas para no tapar /validar,
    /docs ni el resto de la API. Sin build, la API sigue funcionando sola.

    La SPA cambia de vista con estado de React, no con la URL; por eso no
    hace falta un fallback de index.html para rutas profundas.
    """
    if not (dist_dir / "index.html").is_file():
        return False
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="spa")
    return True


_montar_spa(app)


# ---------------------------------------------------------------------------
# Punto de entrada para ejecución directa
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    # Bind local por defecto: la API maneja datos personales y documentos
    # oficiales. Para exponerla en la red hay que pedirlo explícitamente
    # (VISTOBUENO_HOST) y definir el token.
    # `proxy_headers=False`: un X-Forwarded-For no puede falsificar el
    # peer y saltar el control de loopback (ver README).
    host = (os.environ.get("VISTOBUENO_HOST") or "127.0.0.1").strip()
    if not _es_loopback(host) and not _token_api():
        raise SystemExit(
            "VISTOBUENO_HOST expone la API fuera de la máquina local: "
            "define VISTOBUENO_API_TOKEN antes de arrancar."
        )
    uvicorn.run(app, host=host, port=8000, proxy_headers=False)
