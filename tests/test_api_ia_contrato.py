"""Tests de contrato para los endpoints del módulo de IA (Funcionalidad 2).

Verifica GET /asistente/estado y POST /asistente/explicar con StubLLM
inyectado, sin red ni GPU. La IA es advisory: estos tests también fijan
que no altera POST /validar ni el semáforo.

Uso:
    pytest tests/test_api_ia_contrato.py -v
"""

import asyncio
import json
import threading
import time
from pathlib import Path

import pytest
from docx_factory import aplicar_mutacion, compilar_docx, configuracion_base
from fastapi.testclient import TestClient

import validator.api as api_module
import validator.llm as llm_module
from validator import api as validator_api
from validator.api import app
from validator.llm import LLMError, StubLLM

MIME_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


# ---------------------------------------------------------------------------
# Fixtures y helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def cliente_ia():
    """Cliente de prueba para los endpoints de IA.

    Conserva y restaura los overrides de dependencia: otros tests de la API
    no inyectan cliente LLM.
    """
    overrides_originales = dict(app.dependency_overrides)
    try:
        yield TestClient(app, client=("127.0.0.1", 50001), base_url="http://127.0.0.1")
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(overrides_originales)


def _docx_bytes(config=None) -> bytes:
    """Construye un DOCX válido del factory para pruebas de la API."""
    ruta = compilar_docx(config if config is not None else configuracion_base())
    return Path(ruta).read_bytes()


def _docx_rojo_bytes() -> bytes:
    """DOCX con un fallo real: el cuerpo queda a 15 pt en vez de 12 pt."""
    return _docx_bytes(aplicar_mutacion("tamano_cuerpo", configuracion_base()))


def _archivo_docx(contenido: bytes | None = None, nombre: str = "tesis.docx"):
    """Devuelve un tuple (nombre, bytes, content-type) para multipart."""
    return (nombre, contenido if contenido is not None else _docx_bytes(), MIME_DOCX)


def _inyectar_cliente(cliente: StubLLM) -> None:
    """Sustituye la dependencia del cliente IA por el stub dado."""
    app.dependency_overrides[api_module.obtener_cliente_ia] = lambda: cliente


class _StubCaido(StubLLM):
    """Stub que simula un servicio de IA caído."""

    async def disponible(self) -> bool:
        raise LLMError("servicio caído")


class _StubLento(StubLLM):
    """Stub que se queda esperando: simula un LLM lento.

    La petición queda en la espera al LLM, que es justo el estado que
    retiene el hueco de validación si el endpoint lo toma al principio.
    """

    def __init__(self, evento: threading.Event) -> None:
        super().__init__(
            respuestas=json.dumps(
                {
                    "explicaciones": [
                        {"rule_id": "tamano_cuerpo", "explicacion": "El cuerpo debe ir a 12 pt"}
                    ],
                    "prioridades": [
                        {
                            "orden": 1,
                            "rule_id": "tamano_cuerpo",
                            "razon": "Es un requisito de formato del cuerpo.",
                            "esfuerzo": "bajo",
                        }
                    ],
                }
            ),
            modelo="stub",
        )
        self._evento = evento
        self.entradas = 0

    async def chat(self, system, user, json_schema=None):
        self.entradas += 1
        while not self._evento.is_set():
            await asyncio.sleep(0.01)
        return await super().chat(system, user, json_schema)


# ---------------------------------------------------------------------------
# Tests: GET /asistente/estado
# ---------------------------------------------------------------------------


class TestEstadoIA:
    """Estado del módulo de IA: siempre 200, disponible=false si no hay OLLAMA_URL."""

    def test_estado_sin_ollama_url_devuelve_disponible_false(self, cliente_ia, monkeypatch):
        """Sin OLLAMA_URL → 200 con disponible=false."""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        respuesta = cliente_ia.get("/asistente/estado")
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["disponible"] is False
        assert cuerpo["modelo"] == ""

    def test_estado_con_stub_devuelve_disponible_true(self, cliente_ia, monkeypatch):
        """Con StubLLM → 200 con disponible=true y el modelo del stub."""
        monkeypatch.setattr(
            llm_module,
            "get_llm_client",
            lambda *_args, **_kwargs: StubLLM(respuestas="{}", modelo="stub"),
        )
        respuesta = cliente_ia.get("/asistente/estado")
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["disponible"] is True
        assert cuerpo["modelo"] == "stub"

    def test_estado_con_servicio_caido_no_devuelve_503(self, cliente_ia, monkeypatch):
        """Un LLM caído se expresa como disponible=false, no como 503."""
        monkeypatch.setattr(llm_module, "get_llm_client", lambda *_args, **_kwargs: _StubCaido())
        respuesta = cliente_ia.get("/asistente/estado")
        assert respuesta.status_code == 200
        assert respuesta.json() == {"disponible": False, "modelo": ""}

    def test_estado_no_se_cuelga_con_un_servicio_mudo(self, cliente_ia, monkeypatch):
        """Un servicio que acepta la conexión pero no responde no cuelga la SPA."""

        async def _colgado():
            await asyncio.sleep(30)
            return {"disponible": True, "modelo": "stub"}

        monkeypatch.setattr(api_module, "estado_ia", _colgado)
        monkeypatch.setattr(api_module, "TIEMPO_MAX_ESTADO_IA_S", 0.05)

        respuesta = cliente_ia.get("/asistente/estado")

        assert respuesta.status_code == 200
        assert respuesta.json() == {"disponible": False, "modelo": ""}

    def test_estado_con_url_malformada_no_devuelve_500(self, cliente_ia, monkeypatch):
        """Una `OLLAMA_URL` inválida se informa como no disponible, no como 500."""
        monkeypatch.setenv("OLLAMA_URL", "http://[::1")

        respuesta = cliente_ia.get("/asistente/estado")

        assert respuesta.status_code == 200
        assert respuesta.json() == {"disponible": False, "modelo": ""}


# ---------------------------------------------------------------------------
# Tests: POST /asistente/explicar
# ---------------------------------------------------------------------------


class TestExplicarIA:
    """Explicación y priorización de fallos (Funcionalidad 2)."""

    def test_explicar_sin_ollama_url_devuelve_503(self, cliente_ia, monkeypatch):
        """Sin OLLAMA_URL → 503."""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        respuesta = cliente_ia.post("/asistente/explicar", files={"archivo": _archivo_docx()})
        assert respuesta.status_code == 503

    def test_explicar_con_stub_devuelve_200(self, cliente_ia):
        """Con un fallo real, el stub produce explicación y prioridad."""
        stub = StubLLM(
            respuestas=json.dumps(
                {
                    "explicaciones": [
                        {
                            "rule_id": "tamano_cuerpo",
                            "explicacion": "El cuerpo debe ir a 12 pt",
                        }
                    ],
                    "prioridades": [
                        {
                            "orden": 1,
                            "rule_id": "tamano_cuerpo",
                            "razon": "Es un requisito de formato del cuerpo.",
                            "esfuerzo": "bajo",
                        }
                    ],
                }
            ),
            modelo="stub",
        )
        _inyectar_cliente(stub)

        respuesta = cliente_ia.post(
            "/asistente/explicar", files={"archivo": _archivo_docx(_docx_rojo_bytes())}
        )

        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["modelo"] == "stub"
        assert [e["rule_id"] for e in cuerpo["explicaciones"]] == ["tamano_cuerpo"]
        assert [p["rule_id"] for p in cuerpo["prioridades"]] == ["tamano_cuerpo"]
        # Una sola llamada: la respuesta del stub es válida a la primera.
        assert len(stub.llamadas) == 1

    def test_explicar_pasa_el_tipo_documental_al_prompt(self, cliente_ia):
        """El prompt recibe el tipo inferido por el motor determinista."""
        stub = StubLLM(
            respuestas=json.dumps({"explicaciones": [], "prioridades": []}),
            modelo="stub",
        )
        _inyectar_cliente(stub)

        respuesta = cliente_ia.post(
            "/asistente/explicar", files={"archivo": _archivo_docx(_docx_rojo_bytes())}
        )

        assert respuesta.status_code == 200
        prompt = stub.llamadas[0][1]
        assert '"tipo_documento": "tinv_cuantitativo"' in prompt

    def test_explicar_sin_fallos_no_llama_a_la_ia(self, cliente_ia):
        """Un documento conforme devuelve listas vacías sin gastar LLM."""
        stub = StubLLM(respuestas="{}", modelo="stub")
        _inyectar_cliente(stub)

        respuesta = cliente_ia.post("/asistente/explicar", files={"archivo": _archivo_docx()})

        assert respuesta.status_code == 200
        assert respuesta.json() == {"explicaciones": [], "prioridades": [], "modelo": "stub"}
        assert stub.llamadas == []

    def test_explicar_con_respuesta_invalida_devuelve_422(self, cliente_ia):
        """JSON no interpretable tras el reintento → 422."""
        stub = StubLLM(respuestas="esto no es JSON", modelo="stub")
        _inyectar_cliente(stub)

        respuesta = cliente_ia.post(
            "/asistente/explicar", files={"archivo": _archivo_docx(_docx_rojo_bytes())}
        )

        assert respuesta.status_code == 422
        assert "no devolvió un formato interpretable" in respuesta.json()["detail"]
        assert len(stub.llamadas) == 2  # MAX_INTENTOS

    def test_explicar_con_servicio_caido_devuelve_503(self, cliente_ia):
        """LLMError del servicio → 503."""
        _inyectar_cliente(StubLLM(respuestas=[], modelo="stub"))

        respuesta = cliente_ia.post(
            "/asistente/explicar", files={"archivo": _archivo_docx(_docx_rojo_bytes())}
        )

        assert respuesta.status_code == 503
        assert "Servicio de IA no disponible" in respuesta.json()["detail"]

    def test_explicar_respeta_el_cupo_de_cpu(self, cliente_ia, monkeypatch):
        """La ruta de IA no puede saltarse el cupo de validación (RI-01)."""
        cupo = validator_api.LimitadorCPU(presupuesto_segundos=0.001)
        cupo.registrar_coste(1.0)
        monkeypatch.setattr(validator_api, "_LIMITADOR_CPU_VALIDACION", cupo)
        _inyectar_cliente(StubLLM(respuestas="{}", modelo="stub"))

        respuesta = cliente_ia.post(
            "/asistente/explicar", files={"archivo": _archivo_docx(_docx_rojo_bytes())}
        )

        assert respuesta.status_code == 429
        assert respuesta.headers.get("Retry-After")

    def test_explicar_sin_archivo_devuelve_422(self, cliente_ia):
        """Sin el campo `archivo`, FastAPI responde 422."""
        _inyectar_cliente(StubLLM(respuestas="{}", modelo="stub"))
        respuesta = cliente_ia.post("/asistente/explicar", files={})
        assert respuesta.status_code == 422

    def test_explicar_nombre_vacio_se_rechaza(self, cliente_ia):
        """Nombre vacío: se rechaza igual que en POST /validar."""
        _inyectar_cliente(StubLLM(respuestas="{}", modelo="stub"))
        respuesta = cliente_ia.post(
            "/asistente/explicar",
            files={"archivo": ("", b"", MIME_DOCX)},
        )
        assert respuesta.status_code in (400, 422)

    def test_explicar_no_altera_validar(self, cliente_ia):
        """La ruta advisory no cambia el semáforo de POST /validar."""
        stub = StubLLM(
            respuestas=json.dumps({"explicaciones": [], "prioridades": []}),
            modelo="stub",
        )
        _inyectar_cliente(stub)
        doc = _docx_rojo_bytes()

        explicar = cliente_ia.post("/asistente/explicar", files={"archivo": _archivo_docx(doc)})
        validar = cliente_ia.post("/validar", files={"archivo": _archivo_docx(doc)})

        assert explicar.status_code == 200
        assert validar.status_code == 200
        assert validar.json()["semaforo"] == "rojo"

    def test_explicar_archivo_no_docx_devuelve_415(self, cliente_ia):
        """Content-type no soportado → 415."""
        _inyectar_cliente(StubLLM(respuestas="{}", modelo="stub"))
        respuesta = cliente_ia.post(
            "/asistente/explicar",
            files={"archivo": ("foto.docx", b"no es un docx", "image/jpeg")},
        )
        assert respuesta.status_code == 415

    def test_explicar_extension_no_docx_devuelve_415(self, cliente_ia):
        """Extensión no soportada → 415."""
        _inyectar_cliente(StubLLM(respuestas="{}", modelo="stub"))
        respuesta = cliente_ia.post(
            "/asistente/explicar",
            files={"archivo": ("tesis.txt", b"texto", "text/plain")},
        )
        assert respuesta.status_code == 415

    def test_explicar_archivo_corrupto_devuelve_422(self, cliente_ia):
        """Firma ZIP inválida con nombre y MIME correctos → 422."""
        _inyectar_cliente(StubLLM(respuestas="{}", modelo="stub"))
        respuesta = cliente_ia.post(
            "/asistente/explicar",
            files={"archivo": _archivo_docx(contenido=b"no empieza con PK")},
        )
        assert respuesta.status_code == 422


# ---------------------------------------------------------------------------
# Tests: la espera al LLM no retiene los huecos de validación
# ---------------------------------------------------------------------------


class TestLaEsperaAlLLMNoBloqueaLaValidacion:
    """La cota de validaciones cubre el trabajo de CPU, no la espera.

    `POST /asistente/explicar` valida el DOCX (trabajo pesado) y después
    espera al LLM local, que puede tardar hasta 180 s sin consumir CPU de
    la API. Si esa espera retuviera un hueco de validación, dos
    explicaciones en curso dejarían `/validar` sin servicio aunque la
    máquina estuviera ociosa (revisión adversarial de RI-01).
    """

    @staticmethod
    def _lanzar_explicaciones(cliente_ia, stub, doc, cuantas):
        """Lanza explicaciones en segundo plano y espera a que lleguen al LLM."""
        resultados: list = []

        def _explicar() -> None:
            resultados.append(
                cliente_ia.post("/asistente/explicar", files={"archivo": _archivo_docx(doc)})
            )

        hilos = [threading.Thread(target=_explicar) for _ in range(cuantas)]
        for hilo in hilos:
            hilo.start()
        limite = time.monotonic() + 30
        while stub.entradas < cuantas and time.monotonic() < limite:
            time.sleep(0.02)
        return hilos, resultados

    def test_dos_ia_en_curso_no_bloquean_validar(self, cliente_ia):
        """Con dos explicaciones esperando al LLM, /validar sigue entrando."""
        evento = threading.Event()
        stub = _StubLento(evento)
        _inyectar_cliente(stub)
        doc = _docx_rojo_bytes()

        hilos, resultados = self._lanzar_explicaciones(cliente_ia, stub, doc, 2)
        try:
            assert stub.entradas == 2, "las explicaciones no llegaron al LLM"

            # Las dos explicaciones están esperando: el hueco de
            # validación debe estar libre (la validación ya terminó).
            validar = cliente_ia.post("/validar", files={"archivo": _archivo_docx(doc)})

            assert validar.status_code == 200, validar.text
        finally:
            evento.set()
            for hilo in hilos:
                hilo.join(timeout=30)

        assert [r.status_code for r in resultados] == [200, 200]

    def test_la_tercera_explicacion_simultanea_recibe_429(self, cliente_ia):
        """La cota de IA limita las explicaciones concurrentes."""
        evento = threading.Event()
        stub = _StubLento(evento)
        _inyectar_cliente(stub)
        doc = _docx_rojo_bytes()

        hilos, _ = self._lanzar_explicaciones(cliente_ia, stub, doc, api_module.MAX_IA_CONCURRENTES)
        try:
            assert stub.entradas == api_module.MAX_IA_CONCURRENTES

            rebotada = cliente_ia.post("/asistente/explicar", files={"archivo": _archivo_docx(doc)})

            assert rebotada.status_code == 429
            detalle = rebotada.json()["detail"].lower()
            assert "ia" in detalle
            # El mensaje y el header dicen la misma espera.
            espera = int(rebotada.headers["Retry-After"])
            unidad = "segundo" if espera == 1 else "segundos"
            assert f"{espera} {unidad}" in detalle
        finally:
            evento.set()
            for hilo in hilos:
                hilo.join(timeout=30)
