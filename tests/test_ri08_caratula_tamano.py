"""RI-08: la regla de 12 pt de carátula cubre los cinco bloques del manual.

Retblast puso `linea.sz` y `ciudad.sz` en 36 pt en el documento bueno y la
regla siguió en verde: la descripción anunciaba línea, ciudad y año, pero los
selectores solo medían autores y asesor. Acá se fija que los cinco bloques
se evalúan con `all_eq` y severidad `error`.

Los nombres del factory son placeholders: no entra PII al repo.
"""

from pathlib import Path

import pytest
from _docx_builder import compilar_docx
from docx_factory import configuracion_base

from validator.engine import load_rules, validate_docx

RAIZ = Path(__file__).resolve().parent.parent
REGLA = "caratula_autores_tamano"


def _resultado(config: dict) -> dict:
    ruta = Path(compilar_docx(config))
    try:
        resultados = validate_docx(str(ruta), load_rules(str(RAIZ / "reglas_unt.yaml")))
    finally:
        ruta.unlink(missing_ok=True)
    return {r.rule_id: r for r in resultados}[REGLA]


def _config_con_anio_separado(sz: int = 24) -> dict:
    """Agrega el año como párrafo propio, como en las tesis reales."""
    config = configuracion_base()
    elementos = list(config["portada"].items())
    indice = [clave for clave, _ in elementos].index("ciudad")
    elementos.insert(indice + 1, ("anio", {"texto": "2026", "sz": sz}))
    config["portada"] = dict(elementos)
    return config


def test_los_cinco_bloques_a_12pt_cumplen():
    regla = _resultado(configuracion_base())
    assert regla.passed, regla.found
    assert regla.severity.value == "error"


@pytest.mark.parametrize("bloque", ["linea", "ciudad"])
def test_36pt_en_linea_o_ciudad_falla(bloque: str):
    config = configuracion_base()
    config["portada"][bloque].update(sz=72)
    regla = _resultado(config)
    assert not regla.passed
    assert "36 pt" in regla.found


def test_anio_separado_a_36pt_falla():
    # `sz` se mide en medios puntos: 72 es 36 pt.
    regla = _resultado(_config_con_anio_separado(sz=72))
    assert not regla.passed
    assert "36 pt" in regla.found


def test_anio_separado_a_12pt_cumple():
    regla = _resultado(_config_con_anio_separado())
    assert regla.passed, regla.found
