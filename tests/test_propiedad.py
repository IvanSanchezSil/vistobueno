"""Tests de propiedad (Fase F6): el motor DSL preserva la correlación
regla ↔ resultado.

El factory `docx_factory` genera un documento "bueno" que cumple TODAS las
reglas mecánicas salvo los esquemas alternativos de estructura
(cualitativo y revisión de literatura), que son mutuamente excluyentes con
el plan cuantitativo. Sobre ese documento se verifican dos propiedades:

1. `test_doc_bueno_pasa_39` — el documento bueno pasa exactamente 39/41
   reglas, y las únicas no pasadas son las documentadas en
   `EXCLUIDAS_BASE`.

2. `test_mutacion_afecta_solo_esa_regla` — para cada una de las 41 reglas,
   aplicar su mutación (desvío MÍNIMO) cambia el resultado SOLO de esa
   regla (comparación punto a punto `(passed, found)` contra el documento
   bueno). Las reglas acopladas por mecanismo IDÉNTICO se declaran en
   `REGLAS_ACOPLADAS` y se validan con su conjunto esperado.

Nota técnica: los autómatas de estructura reportan en `found` un contador
interno `headings=N` que cambia ante cualquier inserción/renombrado de
cabeceras (aunque la semántica no cambie). Por eso, para las reglas
`estructura_tinv_*`, el observable comparado es `passed`; para el resto,
`(passed, found)`.

Uso:
    pytest tests/test_propiedad.py -v
"""
from pathlib import Path

import pytest

from validator.engine import load_rules, validate_docx
from docx_factory import (
    REGLAS,
    REGLAS_ACOPLADAS,
    EXCLUIDAS_BASE,
    configuracion_base,
    aplicar_mutacion,
    compilar_docx,
)

RULES = load_rules("reglas_unt.yaml")

ESTRUCTURA = {
    "estructura_tinv_cuantitativo",
    "estructura_tinv_cualitativo",
    "estructura_tinv_revision_literatura",
}


def _por_regla(resultados):
    return {r.rule_id: r for r in resultados}


def _estado(docx_path: str) -> dict:
    """`(rule_id -> (passed, found))`; para estructura solo `passed`."""
    return {
        r.rule_id: (r.passed, None if r.rule_id in ESTRUCTURA else r.found)
        for r in validate_docx(docx_path, RULES)
    }


def _sin_archivo(path: str):
    Path(path).unlink(missing_ok=True)


def _compare(path_a: str, path_b: str, esperado: set, rule_id: str):
    """Verifica que la única diferencia entre dos documentos es `esperado`."""
    a = _estado(path_a)
    b = _estado(path_b)
    assert set(a) == set(b) == set(REGLAS)
    diffs = {rid for rid in a if a[rid] != b[rid]}
    assert diffs == esperado, (
        f"regla {rule_id}: la mutación cambió {sorted(diffs)}, "
        f"esperado {sorted(esperado)}"
    )


def test_doc_bueno_pasa_39():
    """El documento base cumple 39/41: solo fallan los esquemas alternativos."""
    cfg = configuracion_base()
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)

    assert len(res) == 41
    fallos = {rid for rid, r in res.items() if not r.passed}
    assert fallos == EXCLUIDAS_BASE, f"fallos={sorted(fallos)}"
    for rid, r in res.items():
        if rid not in EXCLUIDAS_BASE:
            assert r.passed, f"{rid}: {r.found!r}"


@pytest.mark.parametrize("rule_id", REGLAS)
def test_mutacion_afecta_solo_esa_regla(rule_id):
    """Cada desvío mínimo invalida únicamente su regla (o su par acoplado)."""
    base_cfg = configuracion_base()
    path_base = compilar_docx(base_cfg)
    try:
        path_mut = compilar_docx(aplicar_mutacion(rule_id, base_cfg))
        try:
            esperado = REGLAS_ACOPLADAS.get(rule_id, set()) | {rule_id}
            _compare(path_base, path_mut, esperado, rule_id)
        finally:
            _sin_archivo(path_mut)
    finally:
        _sin_archivo(path_base)


def test_mutaciones_cubren_las_41_reglas():
    """Cadena de seguridad: toda regla de reglas_unt.yaml tiene mutación."""
    ids_yaml = {r["id"] for r in RULES["reglas"]}
    assert ids_yaml == set(REGLAS)
    assert len(REGLAS) == 41