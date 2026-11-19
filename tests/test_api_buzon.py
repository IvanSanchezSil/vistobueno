"""Tests del buzón de trámite (comunicación app ↔ userscript, v1.14.0).

Cubre tres niveles:

- Unitario: la clase Buzon (dos ventanas TTL, revisión, conciliación,
  inconsistencia, confirmación explícita y copia defensiva).
- Contrato: los endpoints HTTP del buzón sobre la app real (publicación,
  autorelleno, trámite retenido, confirmación, conciliación, papeleo) y
  los 409/422 que impiden que un cliente viejo habilite el papeleo.
- Seguridad: el buzón NUNCA emite cabeceras CORS y solo se sirve por
  loopback (o token compartido).

Uso:
    pytest tests/test_api_buzon.py -v
"""

from datetime import UTC, datetime, timedelta

import pytest
from conftest import CLIENTE
from fastapi.testclient import TestClient

import validator.api
from validator.api import app
from validator.buzon import (
    AutoresNoCoinciden,
    Buzon,
    ConfirmacionInvalida,
    HandleInvalido,
    HandleNoCoincide,
    RevisionNoCoincide,
    SinFichaVigente,
    TituloNoCoincide,
    TramiteNoCoincide,
)

# Cliente con un peer que NO es loopback: simula una petición que llega
# desde otro equipo de la red (auditoría 2026-10-26, AUD-09). El Host es
# el loopback para aislar el control del peer (AUD-28).
CLIENTE_FUERA = TestClient(app, client=("10.0.0.5", 40000), base_url="http://127.0.0.1")

TITULO = "Tesis de prueba"
AUTOR = "Ana María Pérez García"
# Mismo nombre sin tilde: la comparación normalizada lo acepta.
AUTOR_SIN_TILDE = "Ana María Pérez Garcia"
# Nombre realmente distinto: la comparación debe rechazarlo.
AUTOR_DISTINTO = "Otra Persona"
FICHA = {
    "extraidos": [
        {"campo": "dc.title", "valor": TITULO, "pagina": 1, "detectado": True},
        {"campo": "dc.contributor.author", "valor": [AUTOR], "pagina": 1, "detectado": True},
        {"campo": "dc.date.issued", "valor": "2026", "pagina": 1, "detectado": True},
        {"campo": "escuela", "valor": "Educación Inicial", "pagina": 1, "detectado": True},
    ],
    "manuales": [
        {"campo": "matricula", "valor": "10584011-18"},
        {"campo": "renati.author.dni", "valor": "12345678"},
    ],
}

FICHA_SIN_AUTORES = {
    "extraidos": [
        {"campo": "dc.title", "valor": TITULO, "pagina": 1, "detectado": True},
        {"campo": "dc.date.issued", "valor": "2026", "pagina": 1, "detectado": True},
        {"campo": "escuela", "valor": "Educación Inicial", "pagina": 1, "detectado": True},
    ],
    "manuales": [
        {"campo": "matricula", "valor": "10584011-18"},
        {"campo": "renati.author.dni", "valor": None},
    ],
}

FICHA_REEMPLAZO = {
    "extraidos": [
        {"campo": "dc.title", "valor": "Otra tesis", "pagina": 1, "detectado": True},
    ],
    "manuales": [],
}

HANDLE = "https://hdl.handle.net/20.500.14414/99999"
OTRO_HANDLE = "https://hdl.handle.net/20.500.14414/88888"
TIMESTAMP = "2026-10-19T18:10:00"
TITULO_OBSERVADO = TITULO


class RelojFalso:
    """Reloj controlable para probar las dos ventanas sin dormir."""

    def __init__(self, inicio: datetime | None = None) -> None:
        self.ahora = inicio or datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, segundos: float) -> None:
        self.ahora += timedelta(seconds=segundos)


def _cuerpo_deposito(
    tramite_id: str,
    *,
    revision: int = 0,
    handle: str = HANDLE,
    titulo: str = TITULO_OBSERVADO,
    autores: list[str] | None = None,
    timestamp: str = TIMESTAMP,
    atestacion: str = "operador",
) -> dict:
    cuerpo = {
        "tramite_id": tramite_id,
        "handle": handle,
        "titulo_observado": titulo,
        "timestamp": timestamp,
        "revision_esperada": revision,
    }
    if autores is not None:
        cuerpo["autores_observados"] = autores
    if atestacion:
        cuerpo["atestacion"] = atestacion
    return cuerpo


def _publicar_ficha(cliente: TestClient = CLIENTE, ficha: dict = FICHA):
    return cliente.post("/ficha-pendiente", json=ficha)


def _publicar_deposito(
    tramite_id: str,
    *,
    revision: int = 0,
    autores: list[str] | None = None,
    titulo: str = TITULO_OBSERVADO,
    cliente: TestClient = CLIENTE,
):
    return cliente.post(
        "/deposito",
        json=_cuerpo_deposito(tramite_id, revision=revision, autores=autores, titulo=titulo),
    )


def _solicitud_papeleo(tramite_id: str, ficha: dict = FICHA) -> dict:
    return {
        "ficha": ficha,
        "tramite_id": tramite_id,
        "handle": HANDLE,
        "timestamp": TIMESTAMP,
    }


@pytest.fixture(autouse=True)
def _buzon_limpio(monkeypatch):
    """Aísla los tests: el buzón es un singleton del proceso."""
    monkeypatch.setattr(validator.api, "_BUZON", Buzon())
    yield


# ---------------------------------------------------------------------------
# Unitario: la clase Buzon
# ---------------------------------------------------------------------------


class TestBuzonUnitario:
    """Dos ventanas, revisión, confirmación explícita y conciliación."""

    def test_ranura_vacia_devuelve_none(self):
        buzon = Buzon()
        assert buzon.leer_ficha() is None
        assert buzon.leer_tramite() is None
        assert buzon.leer_deposito() is None

    def test_publicar_y_leer_ficha(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        assert publicacion.revision == 0
        assert publicacion.autofill_hasta < publicacion.retenido_hasta
        leida = buzon.leer_ficha()
        assert leida is not None
        assert leida.ficha == FICHA
        assert leida.tramite_id == publicacion.tramite_id
        assert leida.revision == 0

    def test_ultima_gana_con_tramite_nuevo(self):
        buzon = Buzon()
        primero = buzon.publicar_ficha({"a": 1})
        segundo = buzon.publicar_ficha({"b": 2})
        assert primero.tramite_id != segundo.tramite_id
        leida = buzon.leer_ficha()
        assert leida is not None
        assert leida.ficha == {"b": 2}
        assert leida.tramite_id == segundo.tramite_id
        assert leida.revision == 0

    def test_vencer_autorelleno_no_borra_el_tramite(self):
        """La ventana corta solo bloquea el relleno; la evidencia sigue."""
        reloj = RelojFalso()
        buzon = Buzon(reloj=reloj)
        publicacion = buzon.publicar_ficha(FICHA)
        reloj.avanzar(3601)

        assert buzon.leer_ficha() is None
        estado = buzon.leer_tramite()
        assert estado is not None
        assert estado.autofill_habil is False
        assert estado.ficha == FICHA
        assert estado.tramite_id == publicacion.tramite_id

        buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id))
        assert buzon.leer_deposito() is not None

    def test_retencion_expirada_limpia_todo(self):
        reloj = RelojFalso()
        buzon = Buzon(reloj=reloj)
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id))
        reloj.avanzar(86401)

        assert buzon.leer_ficha() is None
        assert buzon.leer_tramite() is None
        assert buzon.leer_deposito() is None
        with pytest.raises(SinFichaVigente):
            buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id))

    def test_retencion_menor_se_ajusta_al_autorelleno(self):
        reloj = RelojFalso()
        buzon = Buzon(
            ttl_autorelleno_segundos=3600,
            ttl_tramite_segundos=60,
            reloj=reloj,
        )
        publicacion = buzon.publicar_ficha(FICHA)
        reloj.avanzar(3599)
        estado = buzon.leer_tramite()
        assert estado is not None
        assert estado.retenido_hasta == publicacion.autofill_hasta

    def test_confirmacion_exige_atestacion(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        with pytest.raises(ConfirmacionInvalida):
            buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id, atestacion=""))
        assert buzon.leer_deposito() is None

    def test_confirmacion_exige_revision(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        cuerpo = _cuerpo_deposito(publicacion.tramite_id)
        cuerpo.pop("revision_esperada")
        with pytest.raises(ConfirmacionInvalida):
            buzon.reportar_deposito(cuerpo)
        assert buzon.leer_deposito() is None

    def test_revision_obsoleta_no_cambia_nada(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        with pytest.raises(RevisionNoCoincide):
            buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id, revision=99))
        assert buzon.leer_deposito() is None
        estado = buzon.leer_tramite()
        assert estado is not None
        assert estado.revision == 0

    def test_tramite_ajeno_no_confirma(self):
        buzon = Buzon()
        buzon.publicar_ficha(FICHA)
        with pytest.raises(TramiteNoCoincide):
            buzon.reportar_deposito(_cuerpo_deposito("tramite-anterior"))

    def test_titulo_distinto_bloquea_la_confirmacion(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        with pytest.raises(TituloNoCoincide):
            buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id, titulo="Otra tesis"))
        assert buzon.leer_deposito() is None

    def test_handle_de_otro_repositorio_no_confirma(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        with pytest.raises(HandleInvalido):
            buzon.reportar_deposito(
                _cuerpo_deposito(
                    publicacion.tramite_id,
                    handle="https://hdl.handle.net/1234/99999",
                )
            )
        assert buzon.leer_deposito() is None

    def test_autores_distintos_bloquean_la_confirmacion(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        with pytest.raises(AutoresNoCoinciden):
            buzon.reportar_deposito(
                _cuerpo_deposito(publicacion.tramite_id, autores=["Otra Persona"])
            )
        assert buzon.leer_deposito() is None

    def test_autores_iguales_se_verifican(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id, autores=[AUTOR]))
        deposito = buzon.leer_deposito()
        assert deposito is not None
        assert deposito["autores_verificados"] is True

    def test_autores_ausentes_se_registran_como_no_verificados(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id))
        deposito = buzon.leer_deposito()
        assert deposito is not None
        assert deposito["autores_observados"] is None
        assert deposito["autores_verificados"] is False

    def test_confirmado_en_lo_genera_el_servidor(self):
        reloj = RelojFalso()
        buzon = Buzon(reloj=reloj)
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(
            _cuerpo_deposito(publicacion.tramite_id, timestamp="2026-10-19T18:10:00")
        )
        deposito = buzon.leer_deposito()
        assert deposito is not None
        assert deposito["timestamp"] == "2026-10-19T18:10:00"
        assert deposito["confirmado_en"] == reloj.ahora.isoformat()
        assert deposito["confirmado_por"] == "operador"
        assert deposito["revision_confirmada"] == 0
        assert deposito["estado"] == "confirmado_por_operador"

    def test_conciliar_sin_deposito_no_crea_evidencia(self):
        buzon = Buzon()
        buzon.publicar_ficha(FICHA)
        estado = buzon.reconciliar(
            ficha={**FICHA, "extraidos": [{**FICHA["extraidos"][0], "valor": "Corregido"}]},
            revision_esperada=0,
            handle=HANDLE,
            motivo="Corrección del título",
        )
        assert estado.revision == 1
        assert estado.deposito is None
        assert estado.confirmacion_vigente is False
        assert buzon.leer_deposito() is None

    def test_conciliar_con_revision_obsoleta_falla(self):
        buzon = Buzon()
        buzon.publicar_ficha(FICHA)
        with pytest.raises(RevisionNoCoincide):
            buzon.reconciliar(
                ficha=FICHA_REEMPLAZO,
                revision_esperada=99,
                handle=HANDLE,
                motivo="Corrección",
            )
        estado = buzon.leer_tramite()
        assert estado is not None
        assert estado.ficha == FICHA
        assert estado.revision == 0

    def test_conciliar_post_confirmacion_invalida_confirmacion(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id))
        corregida = {
            **FICHA,
            "extraidos": [
                {**FICHA["extraidos"][0], "valor": "Título corregido"},
                *FICHA["extraidos"][1:],
            ],
        }
        estado = buzon.reconciliar(
            ficha=corregida,
            revision_esperada=0,
            handle=HANDLE,
            motivo="Título corregido",
        )
        assert estado.revision == 1
        assert estado.deposito is not None
        assert estado.deposito["handle"] == HANDLE
        assert estado.deposito["revision_confirmada"] == 0
        assert estado.confirmacion_vigente is False

    def test_conciliar_con_handle_ajeno_y_deposito_falla(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id))
        with pytest.raises(HandleNoCoincide):
            buzon.reconciliar(
                ficha=FICHA_REEMPLAZO,
                revision_esperada=0,
                handle=OTRO_HANDLE,
                motivo="Otra tesis",
            )
        estado = buzon.leer_tramite()
        assert estado is not None
        assert estado.revision == 0
        assert estado.ficha == FICHA

    def test_inconsistencia_bloquea_y_se_limpia_al_conciliar(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.marcar_inconsistencia(
            tramite_id=publicacion.tramite_id,
            handle=HANDLE,
            revision_esperada=0,
            motivos=["El título del ítem no coincide"],
        )
        estado = buzon.leer_tramite()
        assert estado is not None
        assert estado.inconsistencia is not None
        assert estado.inconsistencia["motivos"] == ["El título del ítem no coincide"]

        estado = buzon.reconciliar(
            ficha=FICHA,
            revision_esperada=0,
            handle=HANDLE,
            motivo="Título revisado",
        )
        assert estado.inconsistencia is None

    def test_inconsistencia_con_revision_obsoleta_falla(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        with pytest.raises(RevisionNoCoincide):
            buzon.marcar_inconsistencia(
                tramite_id=publicacion.tramite_id,
                handle=HANDLE,
                revision_esperada=99,
                motivos=["motivo"],
            )
        estado = buzon.leer_tramite()
        assert estado is not None
        assert estado.inconsistencia is None

    def test_lectura_devuelve_copia(self):
        buzon = Buzon()
        buzon.publicar_ficha({"a": 1, "lista": [1]})
        leido = buzon.leer_ficha()
        assert leido is not None
        leido.ficha["a"] = 999
        leido.ficha["lista"][0] = 999
        otra = buzon.leer_ficha()
        assert otra is not None
        assert otra.ficha == {"a": 1, "lista": [1]}

    def test_nueva_ficha_borra_deposito_anterior(self):
        buzon = Buzon()
        primero = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(_cuerpo_deposito(primero.tramite_id))
        segundo = buzon.publicar_ficha(FICHA)
        assert primero.tramite_id != segundo.tramite_id
        assert buzon.leer_deposito() is None
        with pytest.raises(TramiteNoCoincide):
            buzon.reportar_deposito(_cuerpo_deposito(primero.tramite_id))

    def test_limpiar_vacia_todo(self):
        buzon = Buzon()
        publicacion = buzon.publicar_ficha(FICHA)
        buzon.reportar_deposito(_cuerpo_deposito(publicacion.tramite_id))
        buzon.limpiar()
        assert buzon.leer_ficha() is None
        assert buzon.leer_tramite() is None
        assert buzon.leer_deposito() is None


# ---------------------------------------------------------------------------
# Contrato: endpoints HTTP del buzón
# ---------------------------------------------------------------------------


class TestBuzonEndpoints:
    """Flujo POST → GET sobre la app FastAPI real."""

    @pytest.fixture(autouse=True)
    def _firma(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_FIRMA", "Responsable de prueba")

    def test_publicar_y_leer_ficha(self):
        respuesta = _publicar_ficha()
        assert respuesta.status_code == 201
        publicada = respuesta.json()
        assert publicada["tramite_id"]
        assert publicada["revision"] == 0
        assert publicada["autofill_hasta"] < publicada["retenido_hasta"]
        assert publicada["vence_en"] == publicada["autofill_hasta"]

        leida = CLIENTE.get("/ficha-pendiente")
        assert leida.status_code == 200
        sobre = leida.json()
        assert sobre["ficha"] == FICHA
        assert sobre["tramite_id"] == publicada["tramite_id"]
        assert sobre["revision"] == 0
        assert sobre["autofill_hasta"] == publicada["autofill_hasta"]

    def test_ficha_vacia_da_404(self):
        respuesta = CLIENTE.get("/ficha-pendiente")
        assert respuesta.status_code == 404
        assert "ficha" in respuesta.json()["detail"]

    def test_ficha_ultima_gana_por_http(self):
        primera = _publicar_ficha().json()
        segunda = _publicar_ficha(ficha=FICHA_REEMPLAZO).json()
        assert primera["tramite_id"] != segunda["tramite_id"]
        leida = CLIENTE.get("/ficha-pendiente")
        assert leida.status_code == 200
        assert leida.json()["ficha"] == FICHA_REEMPLAZO
        assert leida.json()["tramite_id"] == segunda["tramite_id"]

    def test_ficha_payload_invalido_da_422(self):
        respuesta = CLIENTE.post("/ficha-pendiente", json={"cualquier": "cosa"})
        assert respuesta.status_code == 422

    def test_publicar_y_leer_deposito(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = _publicar_deposito(tramite_id, autores=[AUTOR])
        assert respuesta.status_code == 204

        leido = CLIENTE.get("/deposito")
        assert leido.status_code == 200
        deposito = leido.json()
        assert deposito["tramite_id"] == tramite_id
        assert deposito["handle"] == HANDLE
        assert deposito["titulo_observado"] == TITULO_OBSERVADO
        assert deposito["titulo"] == TITULO_OBSERVADO
        assert deposito["timestamp"] == TIMESTAMP
        assert deposito["revision_confirmada"] == 0
        assert deposito["confirmacion_vigente"] is True
        assert deposito["autores_verificados"] is True
        assert deposito["confirmado_por"] == "operador"
        assert deposito["confirmado_en"]

    def test_deposito_vacio_da_404(self):
        respuesta = CLIENTE.get("/deposito")
        assert respuesta.status_code == 404
        assert "depósito" in respuesta.json()["detail"]

    def test_deposito_sin_ficha_da_404(self):
        respuesta = _publicar_deposito("tramite-sin-ficha")
        assert respuesta.status_code == 404
        assert "ficha" in respuesta.json()["detail"]

    def test_deposito_con_tramite_ajeno_da_409(self):
        _publicar_ficha()
        respuesta = _publicar_deposito("tramite-anterior")
        assert respuesta.status_code == 409
        assert "trámite" in respuesta.json()["detail"]

    def test_deposito_payload_invalido_da_422(self):
        respuesta = CLIENTE.post("/deposito", json={"handle": ""})
        assert respuesta.status_code == 422

    def test_payload_automatico_viejo_da_422_y_no_habilita_papeleo(self):
        """El contrato exige atestación y revisión; el reporte viejo no entra."""
        tramite_id = _publicar_ficha().json()["tramite_id"]
        viejo = {
            "tramite_id": tramite_id,
            "handle": HANDLE,
            "titulo_observado": TITULO_OBSERVADO,
            "timestamp": TIMESTAMP,
        }
        respuesta = CLIENTE.post("/deposito", json=viejo)
        assert respuesta.status_code == 422
        assert CLIENTE.get("/deposito").status_code == 404
        assert (
            CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id)).status_code == 409
        )

    def test_payload_con_titulo_viejo_da_422(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = CLIENTE.post(
            "/deposito",
            json={
                **_cuerpo_deposito(tramite_id),
                "titulo": TITULO_OBSERVADO,
            },
        )
        assert respuesta.status_code == 422

    def test_confirmacion_con_revision_obsoleta_da_409(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(tramite_id, revision=99).status_code == 409
        assert CLIENTE.get("/deposito").status_code == 404
        # La revisión correcta sí confirma.
        assert _publicar_deposito(tramite_id, revision=0).status_code == 204

    def test_handle_de_otro_repositorio_da_422(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = CLIENTE.post(
            "/deposito",
            json=_cuerpo_deposito(tramite_id, handle="https://hdl.handle.net/1234/99999"),
        )
        assert respuesta.status_code == 422

    def test_titulo_distinto_da_409(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = CLIENTE.post(
            "/deposito",
            json=_cuerpo_deposito(tramite_id, titulo="Otra tesis"),
        )
        assert respuesta.status_code == 409
        assert "título" in respuesta.json()["detail"].lower()

    def test_autores_distintos_dan_409(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = _publicar_deposito(tramite_id, autores=["Otra Persona"])
        assert respuesta.status_code == 409
        assert "autores" in respuesta.json()["detail"].lower()

    def test_autores_ausentes_se_registran_como_no_verificados(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(tramite_id).status_code == 204
        deposito = CLIENTE.get("/deposito").json()
        assert deposito["autores_observados"] is None
        assert deposito["autores_verificados"] is False

    def test_nueva_ficha_invalida_deposito_y_reporte_viejo(self):
        primero = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(primero).status_code == 204

        segundo = _publicar_ficha().json()["tramite_id"]
        assert primero != segundo
        assert CLIENTE.get("/deposito").status_code == 404
        assert _publicar_deposito(primero).status_code == 409

    def test_reintento_del_mismo_tramite_se_acepta(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(tramite_id).status_code == 204
        segundo = CLIENTE.post(
            "/deposito",
            json=_cuerpo_deposito(
                tramite_id,
                handle=OTRO_HANDLE,
                timestamp="2026-10-19T18:11:00",
            ),
        )
        assert segundo.status_code == 204
        leido = CLIENTE.get("/deposito").json()
        assert leido["tramite_id"] == tramite_id
        assert leido["handle"] == OTRO_HANDLE
        assert leido["timestamp"] == "2026-10-19T18:11:00"


class TestVentanasTemporales:
    """Autorelleno y retención son ventanas distintas sobre el mismo trámite."""

    def test_confirmacion_tardia_tras_expirar_autorelleno(self, monkeypatch):
        """La secuencia completa: ficha vencida para rellenar, depósito tardío."""
        monkeypatch.setenv("VISTOBUENO_FIRMA", "Responsable de prueba")
        reloj = RelojFalso()
        monkeypatch.setattr(validator.api, "_BUZON", Buzon(reloj=reloj))
        tramite_id = _publicar_ficha().json()["tramite_id"]

        reloj.avanzar(3601)
        assert CLIENTE.get("/ficha-pendiente").status_code == 404

        tramite = CLIENTE.get("/tramite")
        assert tramite.status_code == 200
        assert tramite.json()["autofill_habil"] is False
        assert tramite.json()["revision"] == 0

        assert _publicar_deposito(tramite_id, revision=0).status_code == 204
        assert CLIENTE.get("/deposito").status_code == 200
        fila = CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id))
        assert fila.status_code == 200
        assert TITULO in fila.json()["filas"][0]

    def test_retencion_expirada_bloquea_confirmacion_y_papeleo(self, monkeypatch):
        reloj = RelojFalso()
        monkeypatch.setattr(validator.api, "_BUZON", Buzon(reloj=reloj))
        tramite_id = _publicar_ficha().json()["tramite_id"]

        reloj.avanzar(86401)
        assert CLIENTE.get("/tramite").status_code == 404
        assert _publicar_deposito(tramite_id).status_code == 404
        assert (
            CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id)).status_code == 409
        )

    def test_reinicio_vacia_el_buzon(self, monkeypatch):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(tramite_id).status_code == 204
        monkeypatch.setattr(validator.api, "_BUZON", Buzon())
        assert CLIENTE.get("/tramite").status_code == 404
        assert CLIENTE.get("/deposito").status_code == 404
        assert (
            CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id)).status_code == 409
        )

    def test_tramite_legible_sin_autorelleno(self, monkeypatch):
        reloj = RelojFalso()
        monkeypatch.setattr(validator.api, "_BUZON", Buzon(reloj=reloj))
        _publicar_ficha()
        reloj.avanzar(3601)
        tramite = CLIENTE.get("/tramite").json()
        assert tramite["ficha"] == FICHA
        assert tramite["autofill_habil"] is False
        assert tramite["deposito"] is None


class TestConciliacion:
    """Corrección revisada: sin ciclo, con revisión y sin aprobar por handle."""

    def test_correccion_previa_a_confirmacion(self, monkeypatch):
        """Autor canónico incorrecto → ítem corregido → conciliar → confirmar."""
        monkeypatch.setenv("VISTOBUENO_FIRMA", "Responsable de prueba")
        tramite_id = _publicar_ficha().json()["tramite_id"]

        # El ítem observado contradice la ficha: no se puede confirmar.
        rechazo = _publicar_deposito(tramite_id, revision=0, autores=[AUTOR_DISTINTO])
        assert rechazo.status_code == 409
        assert CLIENTE.get("/deposito").status_code == 404

        ficha_corregida = {
            **FICHA,
            "extraidos": [
                {**FICHA["extraidos"][0]},
                {**FICHA["extraidos"][1], "valor": [AUTOR_SIN_TILDE]},
                *FICHA["extraidos"][2:],
            ],
        }
        conciliacion = CLIENTE.post(
            "/ficha-pendiente/reconciliar",
            json={
                "tramite_id": tramite_id,
                "handle": HANDLE,
                "ficha": ficha_corregida,
                "motivo": "El autor del ítem es el correcto",
                "revision_esperada": 0,
            },
        )
        assert conciliacion.status_code == 200
        assert conciliacion.json()["revision"] == 1
        assert conciliacion.json()["confirmacion_vigente"] is False
        assert conciliacion.json()["deposito"] is None

        # Conciliar no creó evidencia de depósito.
        assert CLIENTE.get("/deposito").status_code == 404
        assert (
            CLIENTE.post(
                "/fila-registro",
                json=_solicitud_papeleo(tramite_id, ficha_corregida),
            ).status_code
            == 409
        )

        # El cliente relee la revisión y confirma por separado.
        tramite = CLIENTE.get("/tramite").json()
        assert tramite["revision"] == 1
        assert tramite["ficha"] == ficha_corregida
        confirmacion = _publicar_deposito(tramite_id, revision=1, autores=[AUTOR_SIN_TILDE])
        assert confirmacion.status_code == 204

        fila = CLIENTE.post(
            "/fila-registro",
            json=_solicitud_papeleo(tramite_id, ficha_corregida),
        )
        assert fila.status_code == 200
        assert AUTOR_SIN_TILDE in fila.json()["filas"][0]

    def test_panel_viejo_no_confirma_la_revision_nueva(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        ficha_corregida = {
            **FICHA,
            "extraidos": [
                {**FICHA["extraidos"][0], "valor": "Corregido"},
                *FICHA["extraidos"][1:],
            ],
        }
        assert (
            CLIENTE.post(
                "/ficha-pendiente/reconciliar",
                json={
                    "tramite_id": tramite_id,
                    "handle": HANDLE,
                    "ficha": ficha_corregida,
                    "motivo": "Título corregido",
                    "revision_esperada": 0,
                },
            ).status_code
            == 200
        )
        # El panel abierto en revisión 0 intenta confirmar después.
        assert _publicar_deposito(tramite_id, revision=0).status_code == 409
        assert CLIENTE.get("/deposito").status_code == 404
        # La revisión vigente sí confirma, con el título canónico nuevo.
        assert _publicar_deposito(tramite_id, revision=1, titulo="Corregido").status_code == 204

    def test_reconciliacion_post_confirmacion_exige_reconfirmar(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_FIRMA", "Responsable de prueba")
        tramite_id = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(tramite_id, revision=0, autores=[AUTOR]).status_code == 204
        assert (
            CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id)).status_code == 200
        )

        ficha_corregida = {
            **FICHA,
            "extraidos": [
                {**FICHA["extraidos"][0], "valor": "Título corregido"},
                *FICHA["extraidos"][1:],
            ],
        }
        conciliacion = CLIENTE.post(
            "/ficha-pendiente/reconciliar",
            json={
                "tramite_id": tramite_id,
                "handle": HANDLE,
                "ficha": ficha_corregida,
                "motivo": "Título corregido",
                "revision_esperada": 0,
            },
        )
        assert conciliacion.status_code == 200
        assert conciliacion.json()["revision"] == 1
        assert conciliacion.json()["confirmacion_vigente"] is False
        assert conciliacion.json()["deposito"]["handle"] == HANDLE
        assert conciliacion.json()["deposito"]["revision_confirmada"] == 0

        # La evidencia se conserva, pero el papeleo exige reconfirmar.
        assert (
            CLIENTE.post(
                "/fila-registro",
                json=_solicitud_papeleo(tramite_id, ficha_corregida),
            ).status_code
            == 409
        )
        assert (
            _publicar_deposito(
                tramite_id, revision=1, autores=[AUTOR], titulo="Título corregido"
            ).status_code
            == 204
        )
        fila = CLIENTE.post(
            "/fila-registro",
            json=_solicitud_papeleo(tramite_id, ficha_corregida),
        )
        assert fila.status_code == 200
        assert "Título corregido" in fila.json()["filas"][0]

    def test_conciliar_con_handle_ajeno_da_409(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(tramite_id).status_code == 204
        respuesta = CLIENTE.post(
            "/ficha-pendiente/reconciliar",
            json={
                "tramite_id": tramite_id,
                "handle": OTRO_HANDLE,
                "ficha": FICHA_REEMPLAZO,
                "motivo": "Otra tesis",
                "revision_esperada": 0,
            },
        )
        assert respuesta.status_code == 409
        assert "handle" in respuesta.json()["detail"].lower()
        assert CLIENTE.get("/deposito").json()["handle"] == HANDLE

    def test_reconciliar_sin_deposito_no_crea_evidencia(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = CLIENTE.post(
            "/ficha-pendiente/reconciliar",
            json={
                "tramite_id": tramite_id,
                "handle": HANDLE,
                "ficha": FICHA,
                "motivo": "Revisión sin cambios",
                "revision_esperada": 0,
            },
        )
        assert respuesta.status_code == 200
        assert respuesta.json()["revision"] == 1
        assert CLIENTE.get("/deposito").status_code == 404
        assert (
            CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id)).status_code == 409
        )

    def test_inconsistencia_bloquea_papeleo_y_se_limpia_al_conciliar(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_FIRMA", "Responsable de prueba")
        tramite_id = _publicar_ficha().json()["tramite_id"]
        assert _publicar_deposito(tramite_id).status_code == 204

        marca = CLIENTE.post(
            "/ficha-pendiente/inconsistencia",
            json={
                "tramite_id": tramite_id,
                "handle": HANDLE,
                "motivos": ["El título del ítem no coincide"],
                "revision_esperada": 0,
            },
        )
        assert marca.status_code == 204
        assert (
            CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id)).status_code == 409
        )
        assert (
            "inconsistencia"
            in CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id))
            .json()["detail"]
            .lower()
        )

        assert (
            CLIENTE.post(
                "/ficha-pendiente/reconciliar",
                json={
                    "tramite_id": tramite_id,
                    "handle": HANDLE,
                    "ficha": FICHA,
                    "motivo": "Título revisado",
                    "revision_esperada": 0,
                },
            ).status_code
            == 200
        )
        assert _publicar_deposito(tramite_id, revision=1).status_code == 204
        assert (
            CLIENTE.post("/fila-registro", json=_solicitud_papeleo(tramite_id)).status_code == 200
        )

    def test_inconsistencia_con_revision_obsoleta_da_409(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = CLIENTE.post(
            "/ficha-pendiente/inconsistencia",
            json={
                "tramite_id": tramite_id,
                "handle": HANDLE,
                "motivos": ["motivo"],
                "revision_esperada": 99,
            },
        )
        assert respuesta.status_code == 409
        assert CLIENTE.get("/tramite").json()["inconsistencia"] is None

    def test_inconsistencia_sin_motivos_da_422(self):
        tramite_id = _publicar_ficha().json()["tramite_id"]
        respuesta = CLIENTE.post(
            "/ficha-pendiente/inconsistencia",
            json={
                "tramite_id": tramite_id,
                "handle": HANDLE,
                "motivos": ["   "],
                "revision_esperada": 0,
            },
        )
        assert respuesta.status_code == 422


class TestAccesoBuzon:
    """El buzón solo se sirve desde la máquina donde corre la app (AUD-09).

    La ficha viaja con datos personales del estudiante (DNI, ORCID,
    resumen) y su ranura es de "última gana": sin este control, cualquiera
    de la red podría leerlos o pisar la ficha en vuelo.
    """

    def test_peticion_desde_otro_equipo_da_403(self):
        _publicar_ficha()
        respuesta = CLIENTE_FUERA.get("/ficha-pendiente")
        assert respuesta.status_code == 403
        assert "loopback" in respuesta.json()["detail"]

    def test_peticion_desde_otro_equipo_no_pisa_la_ficha(self):
        _publicar_ficha()
        respuesta = _publicar_ficha(cliente=CLIENTE_FUERA, ficha=FICHA_REEMPLAZO)
        assert respuesta.status_code == 403
        assert CLIENTE.get("/ficha-pendiente").json()["ficha"] == FICHA

    def test_peticion_desde_otro_equipo_no_confirma_depositos(self):
        respuesta = _publicar_deposito("cualquier-tramite", cliente=CLIENTE_FUERA)
        assert respuesta.status_code == 403
        assert CLIENTE.get("/deposito").status_code == 404

    def test_loopback_sigue_funcionando(self):
        assert _publicar_ficha().status_code == 201
        assert CLIENTE.get("/ficha-pendiente").status_code == 200

    def test_loopback_no_necesita_token(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_API_TOKEN", "secreto-de-prueba")
        assert _publicar_ficha().status_code == 201
        assert CLIENTE.get("/ficha-pendiente").status_code == 200

    def test_token_ausente_da_403(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_API_TOKEN", "secreto-de-prueba")
        respuesta = CLIENTE_FUERA.get("/ficha-pendiente")
        assert respuesta.status_code == 403
        assert "token" in respuesta.json()["detail"].lower()

    def test_token_incorrecto_da_403(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_API_TOKEN", "secreto-de-prueba")
        respuesta = CLIENTE_FUERA.get(
            "/ficha-pendiente",
            headers={"X-VistoBueno-Token": "otro-token"},
        )
        assert respuesta.status_code == 403

    def test_token_correcto_permite_el_buzon(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_API_TOKEN", "secreto-de-prueba")
        cabeceras = {"X-VistoBueno-Token": "secreto-de-prueba"}
        respuesta = CLIENTE.post("/ficha-pendiente", json=FICHA, headers=cabeceras)
        assert respuesta.status_code == 201
        leida = CLIENTE.get("/ficha-pendiente", headers=cabeceras)
        assert leida.status_code == 200
        assert leida.json()["ficha"] == FICHA

    def test_token_correcto_habilita_a_otro_equipo(self, monkeypatch):
        monkeypatch.setenv("VISTOBUENO_API_TOKEN", "secreto-de-prueba")
        cabeceras = {"X-VistoBueno-Token": "secreto-de-prueba"}
        respuesta = CLIENTE_FUERA.post("/ficha-pendiente", json=FICHA, headers=cabeceras)
        assert respuesta.status_code == 201
        leida = CLIENTE_FUERA.get("/ficha-pendiente", headers=cabeceras)
        assert leida.status_code == 200
        assert leida.json()["ficha"] == FICHA

    def test_sin_token_configurado_el_remoto_sigue_cerrado(self):
        respuesta = CLIENTE_FUERA.get("/ficha-pendiente")
        assert respuesta.status_code == 403
        assert "loopback" in respuesta.json()["detail"]


class TestBuzonInvarianteSinCors:
    """El buzón jamás emite cabeceras CORS.

    Invariante de seguridad del plan (PLAN_FICHA §6): la ficha contiene
    datos personales del estudiante; sin CORS, una página web maliciosa
    en el navegador del operador no puede leer las respuestas (el
    navegador bloquea la lectura cruzada). El userscript no se ve
    afectado: GM_xmlhttpRequest corre en el contexto de la extensión.
    Si alguien agrega CORSMiddleware sin querer, este test lo detecta.
    """

    def test_get_ficha_sin_cors(self):
        respuesta = CLIENTE.get("/ficha-pendiente")
        assert "access-control-allow-origin" not in respuesta.headers
        assert "access-control-allow-methods" not in respuesta.headers

    def test_post_ficha_sin_cors(self):
        respuesta = _publicar_ficha()
        assert "access-control-allow-origin" not in respuesta.headers

    def test_endpoints_deposito_sin_cors(self):
        respuesta = CLIENTE.get("/deposito")
        assert "access-control-allow-origin" not in respuesta.headers
        respuesta = CLIENTE.post("/deposito", json=_cuerpo_deposito("cualquiera"))
        assert "access-control-allow-origin" not in respuesta.headers

    def test_tramite_y_conciliacion_sin_cors(self):
        respuesta = CLIENTE.get("/tramite")
        assert "access-control-allow-origin" not in respuesta.headers
        respuesta = CLIENTE.post(
            "/ficha-pendiente/reconciliar",
            json={
                "tramite_id": "x",
                "handle": HANDLE,
                "ficha": FICHA,
                "motivo": "x",
                "revision_esperada": 0,
            },
        )
        assert "access-control-allow-origin" not in respuesta.headers
