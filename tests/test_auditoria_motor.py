"""Regresiones de la auditoría de motor de la semana 10 (AUD-01, AUD-02, AUD-20).

Blinda los arreglos con fixtures que reproducen la estructura real de las
plantillas:

- AUD-01: títulos del cuerpo que acaban en letra romana no deben perder su
  última letra al normalizarse (falso positivo de `indice_apunta_secciones`).
- AUD-02: los anexos se buscan hasta el final del documento y los Títulos1
  cuentan como texto (en las plantillas cada "Anexo N." es un Título1).

Uso:
    pytest tests/test_auditoria_motor.py -v
"""

from pathlib import Path

from docx_factory import (
    compilar_docx,
    configuracion_anexos_titulos,
    configuracion_titulo_romano,
)

from validator.analizadores import _norm_indice, _norm_titulo_cuerpo
from validator.engine import load_rules, validate_docx

RULES = load_rules("reglas_unt.yaml")


def _por_regla(resultados):
    return {r.rule_id: r for r in resultados}


def _sin_archivo(path: str):
    Path(path).unlink(missing_ok=True)


def test_norm_indice_no_recorta_sufijo_de_palabra():
    """AUD-01: sin número de página, la última letra se conserva."""
    assert _norm_indice("GENERAL") == "GENERAL"
    assert _norm_titulo_cuerpo("General") == "GENERAL"


def test_norm_indice_si_recorta_pagina_arabiga_y_romana():
    """AUD-01: con número de página, sí se recorta (precedido de espacio)."""
    assert _norm_indice("1.4. OBJETIVOS 9") == "OBJETIVOS"
    assert _norm_indice("OBJETIVOS iv") == "OBJETIVOS"


def test_aud01_titulo_romano_apunta_a_seccion_real():
    """AUD-01/AUD-20: "GENERAL" del cuerpo y "1.4.1. GENERAL 9" del índice."""
    path = compilar_docx(configuracion_titulo_romano())
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["indice_apunta_secciones"].passed


def test_aud02_anexos_como_titulos_satisfacen_minimos():
    """AUD-02/AUD-20: los "Anexo N." como Título1 se detectan igual."""
    path = compilar_docx(configuracion_anexos_titulos())
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["anexos_minimos_cuantitativo"].passed


def test_aud02_reporta_todos_los_faltantes_sin_truncar():
    """AUD-02/AUD-20: `found` lista los 9 anexos faltantes (antes [:8])."""
    cfg = configuracion_anexos_titulos()
    cfg["anexos_items"] = []
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["anexos_minimos_cuantitativo"]
    assert not regla.passed
    # El noveno ítem obligatorio quedaría fuera con el truncado antiguo.
    assert "Carta de autorización de publicación" in regla.found
