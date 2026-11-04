"""Guarda de las respuestas de ejemplo versionadas (`docs/ejemplos/`).

Los dos JSON de `docs/ejemplos/` son la evidencia del resultado esperado del
validador: el par de documentos de demostración y la respuesta que produce
cada uno. Se versionan tal cual, así que cualquier cambio en el motor puede
dejarlos desfasados sin que nada lo note.

Pasó de verdad: el PR #78 (AUD-03) cambió el formato del detalle de las
reglas (`encontrado`) y las respuestas versionadas quedaron con el formato
anterior. Este test lo detecta.

Qué compara:
- el semáforo y el resumen;
- el texto `encontrado` de cada regla (el detalle técnico del motor);
- los prompts de "cómo preguntar a una IA" (incorporan el mismo detalle).

Los DOCX no se comparan byte a byte: se regeneran y se valida la respuesta
que producen. Si el factory cambia, el DOCX cambia y este test falla al
comparar la respuesta.

Si el test falla, la respuesta correcta es regenerar el par:

    python scripts/ejemplo_bueno_malo.py

y revisar el diff antes de commitearlo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "docs" / "ejemplos"

# Mismas mutaciones que aplica `scripts/ejemplo_bueno_malo.py`.
MUTACIONES = [
    "margen_izquierdo",
    "fuente_principal",
    "tamano_cuerpo",
    "interlineado",
    "sangria_parrafo",
]

TIPO_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _respuesta_fresca(nombre: str) -> dict:
    """Regenera el documento de ejemplo y devuelve la respuesta de la API."""
    sys_path = RAIZ / "tests"
    import sys

    if str(sys_path) not in sys.path:
        sys.path.insert(0, str(sys_path))

    from docx_factory import aplicar_mutacion, compilar_docx, configuracion_base

    from fastapi.testclient import TestClient

    from validator.api import app

    cfg = configuracion_base()
    if nombre == "doc_malo":
        for rule_id in MUTACIONES:
            cfg = aplicar_mutacion(rule_id, cfg)

    temporal = Path(compilar_docx(cfg))
    try:
        cliente = TestClient(app, client=("127.0.0.1", 50000), base_url="http://127.0.0.1")
        with temporal.open("rb") as archivo:
            respuesta = cliente.post(
                "/validar",
                files={"archivo": (temporal.name, archivo, TIPO_DOCX)},
            )
        respuesta.raise_for_status()
        return respuesta.json()
    finally:
        temporal.unlink(missing_ok=True)


@pytest.mark.parametrize("nombre", ["doc_bueno", "doc_malo"])
def test_respuesta_versionada_coincide_con_el_motor(nombre: str) -> None:
    """La respuesta versionada debe ser la que produce el motor hoy."""
    versionado = json.loads(
        (EJEMPLOS / f"respuesta_{nombre}.json").read_text(encoding="utf-8")
    )
    fresco = _respuesta_fresca(nombre)

    assert versionado["semaforo"] == fresco["semaforo"], (
        f"el semáforo de {nombre} cambió: regenera el par de ejemplo"
    )
    assert versionado["resumen"] == fresco["resumen"], (
        f"el resumen de {nombre} cambió: regenera el par de ejemplo"
    )

    detalle_por_id = {r["rule_id"]: r["encontrado"] for r in fresco["resultados"]}
    for resultado in versionado["resultados"]:
        rule_id = resultado["rule_id"]
        assert rule_id in detalle_por_id, (
            f"{nombre}: la regla {rule_id} ya no está en la respuesta del motor"
        )
        assert resultado["encontrado"] == detalle_por_id[rule_id], (
            f"{nombre}: el detalle de {rule_id} cambió.\n"
            f"  versionado: {resultado['encontrado']!r}\n"
            f"  actual    : {detalle_por_id[rule_id]!r}\n"
            "Regenera el par: python scripts/ejemplo_bueno_malo.py"
        )

    prompts_por_id = {p["rule_id"]: p["prompt"] for p in fresco.get("como_preguntar_a_una_ia", [])}
    for prompt in versionado.get("como_preguntar_a_una_ia", []):
        rule_id = prompt["rule_id"]
        assert rule_id in prompts_por_id, (
            f"{nombre}: el prompt de {rule_id} ya no está en la respuesta del motor"
        )
        assert prompt["prompt"] == prompts_por_id[rule_id], (
            f"{nombre}: el prompt de {rule_id} cambió.\n"
            "Regenera el par: python scripts/ejemplo_bueno_malo.py"
        )
