"""Fixtures compartidas para la suite de tests de VistoBueno.

Proporciona el cliente de prueba,constantes de validación de contrato
y la ruta a la plantilla de prueba.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from validator.api import app

# ---------------------------------------------------------------------------
# Cliente de prueba global
# ---------------------------------------------------------------------------

CLIENTE = TestClient(app)

# ---------------------------------------------------------------------------
# Rutas a recursos de prueba
# ---------------------------------------------------------------------------

RECURSOS_DIR = Path(__file__).resolve().parent.parent / "recursos"
PLANTILLA = RECURSOS_DIR / "EDUCACION INICIAL-PLANTILLA INVESTIGACIÓN CUANTITATIVA.docx"


# ---------------------------------------------------------------------------
# constantes de validación de contrato (campos esperados en la respuesta API)
# ---------------------------------------------------------------------------

# Campos que debe tener cada elemento en 'resultados'
CAMPOS_RESULTADO = {
    "rule_id",
    "paso",
    "severidad",
    "mensaje",
    "esperado",
    "encontrado",
    "ubicacion",
    "fuente",
    "cita",
}

# Campos del objeto 'resumen'
CAMPOS_RESUMEN = {"total", "fallidos_error", "fallidos_warning"}

# Campos del objeto 'metadatos'
CAMPOS_METADATOS = {
    "archivo_nombre",
    "archivo_tamano_bytes",
    "reglas_evaluadas",
    "version_esquema",
}


# ---------------------------------------------------------------------------
# Fixture para enviar la plantilla
# ---------------------------------------------------------------------------


@pytest.fixture
def plantilla_bytes():
    """Devuelve el contenido binario de la plantilla oficial de prueba."""
    if not PLANTILLA.exists():
        pytest.skip("Plantilla de prueba no disponible")
    return PLANTILLA.read_bytes()


@pytest.fixture
def plantilla_cliente():
    """Envía la plantilla oficial y devuelve la respuesta de la API."""
    if not PLANTILLA.exists():
        pytest.skip("Plantilla de prueba no disponible")
    with open(PLANTILLA, "rb") as f:
        respuesta = CLIENTE.post(
            "/validar",
            files={
                "archivo": (
                    "tesis.docx",
                    f,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
        )
    return respuesta
