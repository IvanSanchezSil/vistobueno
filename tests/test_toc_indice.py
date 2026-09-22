"""Tests del índice de contenidos (F2 ítems 11 y 12).

Cubre las dos reglas de TOC agregadas en la semana 5:

- `indice_apunta_secciones` (toc_apunta): las entradas del índice apuntan a
  secciones reales del documento.
- `indice_numeracion_jerarquica` (toc_numeracion): capítulos romanos I..VI
  consecutivos y subsecciones decimales en preorder bajo su capítulo.

Uso solo del factory determinista (`docx_factory`): el documento base incluye
un índice con entradas `TDC_ENTRADAS_BASE` que es válido para ambas reglas.

Propiedades que se verifican aquí (aparte de `test_propiedad.py`, que ya
garantiza mutaciones mínimas por regla):
- el documento base pasa ambas reglas;
- un documento SIN región de índice pasa con detalle n/a;
- la mutación de cada regla invalida SOLO esa regla;
- `location` se enriquece con la página física real del primer fallo.
"""

from pathlib import Path

from docx_factory import aplicar_mutacion, compilar_docx, configuracion_base

from validator.engine import load_rules, validate_docx

RULES = load_rules("reglas_unt.yaml")

SUBDIVISIONES = {
    "indice_apunta_secciones",
    "indice_numeracion_jerarquica",
    "indice_subdivisiones",
    "indice_paginas_separadas",
}


def _por_regla(resultados):
    return {r.rule_id: r for r in resultados}


def _sin_archivo(path: str):
    Path(path).unlink(missing_ok=True)


def test_base_pasa_toc():
    """El documento base (con índice válido) pasa ambas reglas de TOC."""
    path = compilar_docx(configuracion_base())
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["indice_apunta_secciones"].passed
    assert res["indice_numeracion_jerarquica"].passed


def test_sin_indice_es_na():
    """Sin región de índice las dos reglas pasan (documentado como n/a)."""
    cfg = configuracion_base()
    cfg["tdc_entradas"] = []
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["indice_apunta_secciones"].passed
    assert res["indice_numeracion_jerarquica"].passed


def test_mutacion_apunta_isola_solo_esa_regla():
    """Ítem 11: una entrada fantasma invalida solo indice_apunta_secciones."""
    path = compilar_docx(aplicar_mutacion("indice_apunta_secciones", configuracion_base()))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert not res["indice_apunta_secciones"].passed
    assert "DELIMITACIÓN" in res["indice_apunta_secciones"].found
    assert res["indice_numeracion_jerarquica"].passed


def test_mutacion_numeracion_isola_solo_esa_regla():
    """Ítem 12: un capítulo descolgado invalida solo la jerarquía."""
    path = compilar_docx(aplicar_mutacion("indice_numeracion_jerarquica", configuracion_base()))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert not res["indice_numeracion_jerarquica"].passed
    assert "descolgado" in res["indice_numeracion_jerarquica"].found
    assert res["indice_apunta_secciones"].passed


def test_location_con_pagina_en_apunta():
    """La ubicación del fallo se enriquece con la página real del índice."""
    path = compilar_docx(aplicar_mutacion("indice_apunta_secciones", configuracion_base()))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert "página" in (res["indice_apunta_secciones"].location or "")


def test_location_con_pagina_en_numeracion():
    """La ubicación del fallo se enriquece con la página real del índice."""
    path = compilar_docx(aplicar_mutacion("indice_numeracion_jerarquica", configuracion_base()))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert "página" in (res["indice_numeracion_jerarquica"].location or "")


def test_amabas_fallan_con_documento_compuesto():
    """Un índice con entrada fantasma Y capítulo descolgado falla ambas."""
    cfg = aplicar_mutacion("indice_apunta_secciones", configuracion_base())
    cfg = aplicar_mutacion("indice_numeracion_jerarquica", cfg)
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert not res["indice_apunta_secciones"].passed
    assert not res["indice_numeracion_jerarquica"].passed
