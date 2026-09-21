"""Tests de la paginación física real (F2 ítem 1).

Cubre:
- `_paginacion_para`: mapa párrafo -> página a partir de
  `w:lastRenderedPageBreak` y `w:br w:type="page"`.
- `ExtractedDocx.pagina_de`: página de un párrafo (None si no es párrafo).
- `AnalizadorPaginacion` (`paginacion` / `paginas_distintas`): pasa solo si
  los objetivos caen en páginas físicas distintas; falla con
  `paginas_repetidas` o `no_encontrado` (xpath sin coincidencias).
- Regla `indice_paginas_separadas` end-to-end contra `reglas_unt.yaml`
  (documento base separado / mutación agrupada / índice renombrado).
- Linter y compilador DSL aceptan la sección `paginacion`.

Uso:
    pytest tests/test_f2_paginacion.py -v
"""

import tempfile
import zipfile
from pathlib import Path

from docx_factory import (
    aplicar_mutacion,
    compilar_docx,
    configuracion_base,
)

from validator.compilador import SECCIONES_ANALIZADOR, CompilerDSL
from validator.dsl_check import linter
from validator.engine import load_rules, validate_docx
from validator.extractor import NS, extract

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

RAIZ = Path(__file__).resolve().parent.parent
YAML_PATH = RAIZ / "reglas_unt.yaml"

_MAYUS = "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑÜ"
_MINUS = "abcdefghijklmnopqrstuvwxyzáéíóúñü"


def _xpath_que_contiene(termino: str) -> str:
    return (
        '//w:body//w:p[contains(translate(normalize-space(.), '
        f'"{_MAYUS}", "{_MINUS}"), "{termino}")]'
    )


_XPATHS_INDICES = [_xpath_que_contiene(t) for t in ("contenidos", "tablas", "figuras")]


def _para(texto: str) -> str:
    return f'<w:p><w:r><w:t xml:space="preserve">{texto}</w:t></w:r></w:p>'


def _p_break() -> str:
    """Párrafo con salto renderizado por Word (w:lastRenderedPageBreak)."""
    return "<w:p><w:r><w:lastRenderedPageBreak/></w:r></w:p>"


def _p_br_page() -> str:
    """Párrafo con salto de página explícito (w:br w:type=\"page\")."""
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def _make_docx(paras: list) -> str:
    """Escribe un DOCX mínimo en un archivo temporal y devuelve su ruta."""
    body = "".join(paras)
    body += '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{body}</w:body></w:document>'
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def _regla_paginacion(xpaths: list) -> dict:
    """Regla DSL `paginacion` autocontenida (para un DOCX mínimo)."""
    return {
        "id": "paginacion_test",
        "tipo": "paginacion",
        "descripcion": "Los índices deben presentarse en páginas separadas",
        "valor_esperado": "cada índice en una página distinta",
        "severidad": "warning",
        "ubicacion": "Sección Índice",
        "fuente": "MANUAL.docx",
        "cita": '"cada índice debe presentarse en páginas separadas"',
        "paginacion": {"comparacion": "paginas_distintas", "xpaths": xpaths},
    }


# ---------------------------------------------------------------------------
# Mapa de paginación física (_paginacion_para / ExtractedDocx)
# ---------------------------------------------------------------------------


def _extraer_factory(cfg):
    path = compilar_docx(cfg)
    try:
        return extract(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_paginacion_es_monotona_y_pagina_inicial():
    ext = _extraer_factory(configuracion_base())
    paras = ext.document.xpath("//w:body//w:p", namespaces=NS)
    pags = [ext.pagina_de(p) for p in paras]
    assert pags[0] == 1
    assert all(isinstance(p, int) for p in pags)
    assert all(a <= b for a, b in zip(pags, pags[1:], strict=False))


def test_mapa_de_saltos_renderizados_y_explicitos():
    # Word: lastRenderedPageBreak (párrafo que cierra la página N) y
    # w:br w:type="page" (salto explícito). El párrafo con salto SÍ queda en
    # la página actual; el contenido siguiente pasa a la siguiente.
    path = _make_docx([_para("A"), _p_break(), _para("B"), _p_br_page(), _para("C")])
    try:
        ext = extract(path)
    finally:
        Path(path).unlink(missing_ok=True)
    paras = ext.document.xpath("//w:body//w:p", namespaces=NS)
    assert [ext.pagina_de(p) for p in paras] == [1, 1, 2, 2, 3]


def test_pagina_de_no_para_es_none():
    ext = _extraer_factory(configuracion_base())
    assert ext.pagina_de(None) is None
    assert ext.pagina_de(ext.document) is None


# ---------------------------------------------------------------------------
# AnalizadorPaginacion: paginas_distintas
# ---------------------------------------------------------------------------


def _analizador_paginas(paras: list):
    """Compila una regla `paginacion` y devuelve su AnalizadorPaginacion."""
    regla = _regla_paginacion(_XPATHS_INDICES)
    compilada = CompilerDSL().compilar({"reglas": [regla]})[0]
    path = _make_docx(paras)
    try:
        extracted = extract(path)
    finally:
        Path(path).unlink(missing_ok=True)
    return compilada.analizadores[0], extracted


def _validar_una(paras: list, xpaths: list):
    path = _make_docx(paras)
    try:
        return validate_docx(path, {"reglas": [_regla_paginacion(xpaths)]})[0]
    finally:
        Path(path).unlink(missing_ok=True)


def test_paginas_distintas_pasa():
    an, extracted = _analizador_paginas(
        [_p_break(), _para("INDICE DE CONTENIDOS"), _p_break(), _para("INDICE DE TABLAS"),
         _p_break(), _para("INDICE DE FIGURAS")]
    )
    ok, detalle = an.analizar(extracted)
    assert ok
    assert "paginas_distintas" in detalle
    # End-to-end: la regla pasa (found queda en "cumple", por convención).
    r = _validar_una(
        [_p_break(), _para("INDICE DE CONTENIDOS"), _p_break(), _para("INDICE DE TABLAS"),
         _p_break(), _para("INDICE DE FIGURAS")],
        _XPATHS_INDICES,
    )
    assert r.passed


def test_paginas_repetidas_falla():
    # Sin salto entre CONTENIDOS y TABLAS quedan en la misma página.
    r = _validar_una(
        [_p_break(), _para("INDICE DE CONTENIDOS"), _para("INDICE DE TABLAS"),
         _p_break(), _para("INDICE DE FIGURAS")],
        _XPATHS_INDICES,
    )
    assert not r.passed
    assert "paginas_repetidas" in r.found


def test_no_encontrado_falla():
    # Falta el índice de tablas: el xpath no tiene coincidencias.
    r = _validar_una(
        [_p_break(), _para("INDICE DE CONTENIDOS"), _para("INDICE DE FIGURAS")],
        _XPATHS_INDICES,
    )
    assert not r.passed
    assert "no_encontrado" in r.found


# ---------------------------------------------------------------------------
# Regla indice_paginas_separadas end-to-end (reglas_unt.yaml + factory)
# ---------------------------------------------------------------------------


def _resultado_indice(cfg):
    rules = load_rules(str(YAML_PATH))
    path = compilar_docx(cfg)
    try:
        res = validate_docx(path, rules)
    finally:
        Path(path).unlink(missing_ok=True)
    return next(r for r in res if r.rule_id == "indice_paginas_separadas")


def test_indice_paginas_separadas_base_pasa():
    r = _resultado_indice(configuracion_base())
    assert r.passed
    assert r.found == "cumple"


def test_indice_paginas_separadas_mutacion_falla():
    r = _resultado_indice(aplicar_mutacion("indice_paginas_separadas", configuracion_base()))
    assert not r.passed
    assert "paginas_repetidas" in r.found


def test_indice_paginas_separadas_contenidos_renombrado_falla():
    r = _resultado_indice(aplicar_mutacion("indice_subdivisiones", configuracion_base()))
    assert not r.passed
    assert "no_encontrado" in r.found


# ---------------------------------------------------------------------------
# Sección DSL `paginacion` aceptada por linter y compilador
# ---------------------------------------------------------------------------


def test_paginacion_es_seccion_dsl_valida():
    regla = _regla_paginacion(_XPATHS_INDICES)
    assert "paginacion" in SECCIONES_ANALIZADOR
    assert linter({"reglas": [regla]}) == []
    compiladas = CompilerDSL().compilar({"reglas": [regla]})
    assert len(compiladas) == 1
    assert compiladas[0].rule["id"] == "paginacion_test"
    assert compiladas[0].analizadores[0].__class__.__name__ == "AnalizadorPaginacion"


# ---------------------------------------------------------------------------
# Enriquecimiento de `location` con la página física (ítem 1, bloque A)
# ---------------------------------------------------------------------------


def _resultado_dsl(cfg, rule_id):
    rules = load_rules(str(YAML_PATH))
    path = compilar_docx(cfg)
    try:
        res = validate_docx(path, rules)
    finally:
        Path(path).unlink(missing_ok=True)
    return next(r for r in res if r.rule_id == rule_id)


def test_regla_fallida_enriquece_location_con_pagina():
    # sangria_parrafo falla (firstLine=0); su primera línea del cuerpo cae en
    # la página 4 del DOCX sintético (3 saltos previos: contenido, tablas y
    # figuras). El motor debe anexar "página 4" a `location` (ítem 1).
    cfg = aplicar_mutacion("sangria_parrafo", configuracion_base())
    r = _resultado_dsl(cfg, "sangria_parrafo")
    assert not r.passed
    assert r.location is not None
    assert r.location == 'Sección "Formato general" (párr. 141); página 4'


def test_regla_cumplida_no_altera_location():
    # Regla cumplida: la ubicación queda tal cual (sin sufijo de página).
    r = _resultado_dsl(configuracion_base(), "sangria_parrafo")
    assert r.passed
    assert r.location == 'Sección "Formato general" (párr. 141)'
