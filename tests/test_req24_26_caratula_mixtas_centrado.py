"""REQ-24/REQ-26: mixtas y centrado de línea y ciudad en la carátula.

Antes, `caratula_ciudad_pais_negrita` medía la UNIVERSIDAD (el primer
«Trujillo» del documento) y su patrón aceptaba solo mayúsculas; la regla de
alineación no incluía «línea de investigación». Con esos selectores, un texto
todo en mayúsculas o una línea/ciudad desalineada pasaban en verde.

Los textos del factory son placeholders: no entra PII al repo.
"""

from pathlib import Path

import pytest
from _docx_builder import compilar_docx
from docx_factory import aplicar_mutacion, configuracion_base

from validator.engine import load_rules, validate_docx

RAIZ = Path(__file__).resolve().parent.parent
REGLAS = load_rules(str(RAIZ / "reglas_unt.yaml"))
ALINEACION = "alineacion_caratula_todos_elementos"
CIUDAD = "caratula_ciudad_pais_negrita"
LINEA = "caratula_linea_investigacion"


def _resultados(config: dict) -> dict:
    ruta = Path(compilar_docx(config))
    try:
        return {r.rule_id: r for r in validate_docx(str(ruta), REGLAS)}
    finally:
        ruta.unlink(missing_ok=True)


def test_documento_bueno_cumple_las_tres_reglas():
    resultados = _resultados(configuracion_base())
    for regla in (ALINEACION, CIUDAD, LINEA):
        assert resultados[regla].passed, f"{regla}: {resultados[regla].found}"


@pytest.mark.parametrize("bloque", ["linea", "ciudad"])
def test_solo_mayusculas_falla_segun_el_bloque(bloque: str):
    config = configuracion_base()
    texto = config["portada"][bloque]["texto"]
    config["portada"][bloque]["texto"] = texto.upper()
    resultados = _resultados(config)
    regla = LINEA if bloque == "linea" else CIUDAD
    assert not resultados[regla].passed
    assert "incumplen" in resultados[regla].found


@pytest.mark.parametrize("bloque", ["linea", "ciudad"])
def test_linea_y_ciudad_desalineadas_fallan(bloque: str):
    config = configuracion_base()
    config["portada"][bloque]["jc"] = "right"
    resultados = _resultados(config)
    assert not resultados[ALINEACION].passed
    assert "center" in resultados[ALINEACION].found


def test_la_negrita_se_mide_en_la_ciudad_no_en_la_universidad():
    sin_negrita_universidad = aplicar_mutacion(
        "caratula_universidad_negrita_mayusculas", configuracion_base()
    )
    assert _resultados(sin_negrita_universidad)[CIUDAD].passed

    sin_negrita_ciudad = aplicar_mutacion("caratula_ciudad_pais_negrita", configuracion_base())
    assert not _resultados(sin_negrita_ciudad)[CIUDAD].passed
