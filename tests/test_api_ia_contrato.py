"""Tests de contrato para los endpoints del módulo de IA (Funcionalidad 2).

Verifica GET /asistente/estado y POST /asistente/explicar con StubLLM
inyectado, sin red ni GPU.

Uso:
    pytest tests/test_api_ia_contrato.py -v
"""

from pathlib import Path

import pytest
from docx_factory import compilar_docx, configuracion_base
from fastapi.testclient import TestClient

from validator import api as api_module
from validator.api import app
from validator.llm import StubLLM

MIME_DOCX = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


# ---------------------------------------------------------------------------
# Fixtures y helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def cliente_ia():
    """Cliente de prueba para los endpoints de IA.

    Limpia los overrides de dependencia al terminar para no afectar otros
    tests (en particular los de POST /validar que no inyectan cliente LLM).
    """
    overrides_originales = dict(app.dependency_overrides)
    yield TestClient(app, client=("127.0.0.1", 50001), base_url="http://127.0.0.1")
    app.dependency_overrides.clear()
    app.dependency_overrides.update(overrides_originales)


def _docx_bytes():
    """Construye un DOCX válido del factory para pruebas de la API."""
    ruta = compilar_docx(configuracion_base())
    return Path(ruta).read_bytes()


def _archivo_docx(nombre="tesis.docx"):
    """Devuelve un tuple (nombre, bytes, content-type) para multipart."""
    return (nombre, _docx_bytes(), MIME_DOCX)


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
        """Con StubLLM inyectado → 200 con disponible=true y modelo 'stub'."""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        monkeypatch.setattr(
            api_module,
            "get_llm_client",
            lambda: StubLLM(respuestas="{}", modelo="stub"),
        )
        respuesta = cliente_ia.get("/asistente/estado")
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert cuerpo["disponible"] is True
        assert cuerpo["modelo"] == "stub"


# ---------------------------------------------------------------------------
# Tests: POST /asistente/explicar
# ---------------------------------------------------------------------------


class TestExplicarIA:
    """Explicación y priorización de fallos (Funcionalidad 2)."""

    def test_explicar_sin_ollama_url_devuelve_503(self, cliente_ia, monkeypatch):
        """Sin OLLAMA_URL → 503."""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        respuesta = cliente_ia.post(
            "/asistente/explicar", files={"archivo": _archivo_docx()}
        )
        assert respuesta.status_code == 503

    def test_explicar_con_stub_devuelve_200(self, cliente_ia, monkeypatch):
        """Con StubLLM → 200 con explicaciones y prioridades."""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        app.dependency_overrides[api_module.obtener_cliente_ia] = lambda: StubLLM(
            respuestas={
                "explicaciones": [
                    {"rule_id": "papel_tamano", "explicacion": "El papel debe ser A4"}
                ],
                "prioridades": [
                    {
                        "orden": 1,
                        "rule_id": "papel_tamano",
                        "razon": "Es un requisito fundamental del formato.",
                        "esfuerzo": "bajo",
                    }
                ],
            },
            modelo="stub",
        )
        respuesta = cliente_ia.post(
            "/asistente/explicar", files={"archivo": _archivo_docx()}
        )
        assert respuesta.status_code == 200
        cuerpo = respuesta.json()
        assert "explicaciones" in cuerpo
        assert "prioridades" in cuerpo
        assert cuerpo["modelo"] == "stub"

    def test_explicar_sin_archivo_devuelve_422(self, cliente_ia, monkeypatch):
        """Sin archivo → 422 (campo requerido de FastAPI)."""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        app.dependency_overrides[api_module.obtener_cliente_ia] = lambda: StubLLM(
            respuestas="{}", modelo="stub"
        )
        respuesta = cliente_ia.post("/asistente/explicar", files={})
        assert respuesta.status_code == 422

    def test_explicar_archivo_no_docx_devuelve_415(self, cliente_ia, monkeypatch):
        """Content-type no soportado → 415."""
        monkeypatch.delenv("OLLAMA_URL", raising=False)
        app.dependency_overrides[api_module.obtener_cliente_ia] = lambda: StubLLM(
            respuestas="{}", modelo="stub"
        )
        respuesta = cliente_ia.post(
            "/asistente/explicar",
            files={"archivo": ("foto.docx", b"no es un docx", "image/jpeg")},
        )
        assert respuesta.status_code == 415
