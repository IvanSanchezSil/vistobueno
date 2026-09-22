"""Tests de encabezados y pies de página (F2 ítem 2).

Cubre:
- `ExtractedDocx.headers`/`footers`: extracción de TODAS las partes
  `header*.xml`/`footer*.xml` (el motor legacy solo leía `header1`/`footer1`).
- `ExtractedDocx.xpath` con `parte: header`/`footer`: consulta combinada sobre
  todas las partes del tipo.
- Reglas `encabezado_membrete` y `encabezado_formato` end-to-end contra
  `reglas_unt.yaml`: documento base cumple, cada mutación hace fallar SOLO su
  regla, y el encabezado no altera la ubicación (los párrafos de header/footer
  no están en el mapa de paginación).

Uso:
    pytest tests/test_f2_encabezados.py -v
"""

import tempfile
import zipfile
from pathlib import Path

from docx_factory import (
    aplicar_mutacion,
    compilar_docx,
    configuracion_base,
)

from validator.engine import load_rules, validate_docx
from validator.extractor import extract

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

RAIZ = Path(__file__).resolve().parent.parent
YAML_PATH = RAIZ / "reglas_unt.yaml"

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


def _hdr(texto: str) -> str:
    return f'<w:hdr xmlns:w="{WNS}"><w:p><w:r><w:t>{texto}</w:t></w:r></w:p></w:hdr>'


def _documento_con_headers(headers: list) -> str:
    body = "<w:p><w:r><w:t>cuerpo</w:t></w:r></w:p><w:sectPr/>"
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
        for i, h in enumerate(headers, start=1):
            z.writestr(f"word/header{i}.xml", h)
    return path


def _extraer_factory(cfg):
    path = compilar_docx(cfg)
    try:
        return extract(path)
    finally:
        Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Extracción multi-parte de encabezados/pies
# ---------------------------------------------------------------------------


def test_extractor_leer_todas_las_partes_header_footer():
    ext = _extraer_factory(configuracion_base())
    assert len(ext.headers) == 1
    assert len(ext.footers) == 1
    assert ext.header is not None and ext.header.tag == f"{{{WNS}}}hdr"
    assert ext.footer is not None and ext.footer.tag == f"{{{WNS}}}ftr"


def test_xpath_header_combina_todas_las_partes():
    path = _documento_con_headers([_hdr("PIEZAS"), _hdr("SECCION2")])
    try:
        ext = extract(path)
    finally:
        Path(path).unlink(missing_ok=True)
    textos = [t.text for t in ext.xpath("header", "//w:t", "todos")]
    assert textos == ["PIEZAS", "SECCION2"]


def test_xpath_sin_headers_levanta():
    path = _documento_con_headers([])
    try:
        ext = extract(path)
    finally:
        Path(path).unlink(missing_ok=True)
    try:
        ext.xpath("header", "//w:t", "todos")
    except ValueError as e:
        assert "header" in str(e)
    else:
        raise AssertionError("esperaba ValueError por parte header ausente")


# ---------------------------------------------------------------------------
# Reglas end-to-end (reglas_unt.yaml + factory)
# ---------------------------------------------------------------------------


def _resultado_por(cfg, rule_id):
    rules = load_rules(str(YAML_PATH))
    path = compilar_docx(cfg)
    try:
        res = validate_docx(path, rules)
    finally:
        Path(path).unlink(missing_ok=True)
    return next(r for r in res if r.rule_id == rule_id)


def test_encabezados_base_pasan():
    for rid in ("encabezado_membrete", "encabezado_formato"):
        r = _resultado_por(configuracion_base(), rid)
        assert r.passed, f"{rid}: {r.found!r}"


def test_encabezado_membrete_sin_logo_falla():
    r = _resultado_por(
        aplicar_mutacion("encabezado_membrete", configuracion_base()), "encabezado_membrete"
    )
    assert not r.passed
    # El membrete falla, pero el formato del encabezado sigue intacto.
    r2 = _resultado_por(
        aplicar_mutacion("encabezado_membrete", configuracion_base()), "encabezado_formato"
    )
    assert r2.passed


def test_encabezado_formato_fuente_mala_falla():
    r = _resultado_por(
        aplicar_mutacion("encabezado_formato", configuracion_base()), "encabezado_formato"
    )
    assert not r.passed
    r2 = _resultado_por(
        aplicar_mutacion("encabezado_formato", configuracion_base()), "encabezado_membrete"
    )
    assert r2.passed


def test_fallo_de_encabezado_no_altera_ubicacion():
    # Los párrafos de header/footer no están en el mapa de paginación, así que
    # el enriquecimiento con "página N" (ítem 1) no debe aplicarse aquí: la
    # ubicación queda exactamente como viene del YAML.
    r = _resultado_por(
        aplicar_mutacion("encabezado_membrete", configuracion_base()), "encabezado_membrete"
    )
    assert not r.passed
    assert r.location == "Encabezado de página (estándar institucional UNT)"
