"""Regresiones de NM-01 (M12a): numeración de páginas y pie activo.

Los cuatro contraejemplos de la auditoría normativa se reproducen mutando
el DOCX del factory. Cada caso parte del documento base y cambia solo el
nodo indicado, como en `docs/AUDITORIA_NORMATIVA_2026-11-12.md`:

- decimal explícito en el cuerpo (antes rojo por existir);
- reinicio romano en 99 (antes verde);
- `w:titlePg w:val="0"` (antes verde);
- PAGE en un párrafo alineado a la izquierda, con otro párrafo derecho
  sin PAGE (antes verde).

Además se cubren los bordes del arreglo: `titlePg` verdadero explícito,
formato arábigo incorrecto, reinicio del cuerpo en 1, inicio 1 de los
preliminares, pie con PAGE sin alineación y PAGEREF que no es PAGE.

Uso:
    pytest tests/test_m12a_numeracion.py -v
"""

from __future__ import annotations

import copy
import zipfile
from pathlib import Path

import pytest
from docx_factory import compilar_docx, configuracion_base
from lxml import etree

from validator.engine import build_report, load_rules, validate_docx

RAIZ = Path(__file__).resolve().parent.parent
RULES = load_rules(str(RAIZ / "reglas_unt.yaml"))

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
NS = {"w": W}


@pytest.fixture(scope="module")
def docx_base() -> str:
    path = compilar_docx(configuracion_base())
    yield path
    Path(path).unlink(missing_ok=True)


def _mutar(base: str, destino: Path, mutadores: dict) -> None:
    """Copia el DOCX y aplica un mutador a cada parte indicada."""
    with zipfile.ZipFile(base) as zin, zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            mutador = mutadores.get(item.filename)
            if mutador is not None:
                root = etree.fromstring(
                    data,
                    etree.XMLParser(resolve_entities=False, no_network=True),
                )
                mutador(root)
                data = etree.tostring(
                    root,
                    xml_declaration=True,
                    encoding="UTF-8",
                    standalone=True,
                )
            zout.writestr(item, data)


def _por_regla(path: str) -> tuple[dict, dict[str, dict]]:
    reporte = build_report(validate_docx(path, RULES))
    return reporte, {r["rule_id"]: r for r in reporte["resultados"]}


def _sectprs(doc) -> list:
    return doc.xpath("//w:sectPr", namespaces=NS)


def _pg_num(sect) -> etree._Element:
    pg = sect.find(f"{{{W}}}pgNumType")
    if pg is None:
        pg = etree.SubElement(sect, f"{{{W}}}pgNumType")
    return pg


def _decimal_explicito(doc) -> None:
    _pg_num(_sectprs(doc)[-1]).set(f"{{{W}}}fmt", "decimal")


def _roman_restart_99(doc) -> None:
    for sect in doc.xpath("(//w:sectPr)[position() < last()]", namespaces=NS):
        _pg_num(sect).set(f"{{{W}}}start", "99")


def _titlepg_false(doc) -> None:
    doc.xpath("//w:sectPr[1]/w:titlePg", namespaces=NS)[0].set(f"{{{W}}}val", "0")


def _titlepg_true(doc) -> None:
    doc.xpath("//w:sectPr[1]/w:titlePg", namespaces=NS)[0].set(f"{{{W}}}val", "true")


def _titlepg_vivo_en_otra_seccion(doc) -> None:
    """Apaga `titlePg` en la carátula y lo deja vivo en el cuerpo."""
    _titlepg_false(doc)
    sect = _sectprs(doc)[-1]
    titlepg = sect.find(f"{{{W}}}titlePg")
    if titlepg is None:
        titlepg = etree.SubElement(sect, f"{{{W}}}titlePg")
    titlepg.set(f"{{{W}}}val", "true")


def _titlepg_solo_en_seccion_posterior(doc) -> None:
    """Estructura de la tesis real: el primer sectPr no declara `titlePg`."""
    sectprs = _sectprs(doc)
    titlepg = sectprs[0].find(f"{{{W}}}titlePg")
    if titlepg is not None:
        sectprs[0].remove(titlepg)
    destino = sectprs[1]
    vivo = destino.find(f"{{{W}}}titlePg")
    if vivo is None:
        vivo = etree.SubElement(destino, f"{{{W}}}titlePg")
    vivo.attrib.pop(f"{{{W}}}val", None)


def _formato_cuerpo_incorrecto(doc) -> None:
    _pg_num(_sectprs(doc)[-1]).set(f"{{{W}}}fmt", "lowerRoman")


def _cuerpo_reinicia_en_1(doc) -> None:
    _pg_num(_sectprs(doc)[-1]).set(f"{{{W}}}start", "1")


def _preliminares_inicio_1(doc) -> None:
    _pg_num(_sectprs(doc)[0]).set(f"{{{W}}}start", "1")


def _preliminares_reinicia_despues(doc, inicio: str = "1") -> None:
    """Duplica el salto de sección y declara `start` en el segundo."""
    marcador = doc.xpath("//w:p[w:pPr/w:sectPr]", namespaces=NS)[0]
    copia = copy.deepcopy(marcador)
    marcador.addnext(copia)
    pg = copia.find(f"{{{W}}}pPr/{{{W}}}sectPr/{{{W}}}pgNumType")
    pg.set(f"{{{W}}}start", inicio)


def _parrafos_pie(footer) -> list:
    return footer.xpath("//w:p", namespaces=NS)


def _agregar_campo_page(p) -> None:
    begin = etree.SubElement(p, f"{{{W}}}r")
    etree.SubElement(begin, f"{{{W}}}fldChar").set(f"{{{W}}}fldCharType", "begin")
    instr = etree.SubElement(p, f"{{{W}}}r")
    texto = etree.SubElement(instr, f"{{{W}}}instrText")
    texto.set(XML_SPACE, "preserve")
    texto.text = " PAGE \\* MERGEFORMAT "
    end = etree.SubElement(p, f"{{{W}}}r")
    etree.SubElement(end, f"{{{W}}}fldChar").set(f"{{{W}}}fldCharType", "end")


def _page_number_left(footer) -> None:
    derecho = _parrafos_pie(footer)[0]
    for run in list(derecho):
        if run.tag == f"{{{W}}}r":
            derecho.remove(run)
    texto = etree.SubElement(derecho, f"{{{W}}}r")
    etree.SubElement(texto, f"{{{W}}}t").text = "UNIVERSIDAD"

    izquierdo = etree.SubElement(footer, f"{{{W}}}p")
    ppr = etree.SubElement(izquierdo, f"{{{W}}}pPr")
    etree.SubElement(ppr, f"{{{W}}}jc").set(f"{{{W}}}val", "left")
    _agregar_campo_page(izquierdo)


def _pie_sin_alineacion(footer) -> None:
    ppr = _parrafos_pie(footer)[0].find(f"{{{W}}}pPr")
    if ppr is not None:
        jc = ppr.find(f"{{{W}}}jc")
        if jc is not None:
            ppr.remove(jc)


def _pageref(footer) -> None:
    for instr in footer.xpath("//w:instrText", namespaces=NS):
        if instr.text and "PAGE" in instr.text:
            instr.text = " PAGEREF _Toc123 \\h "


def test_baseline_sigue_verde(docx_base):
    reporte, _ = _por_regla(docx_base)
    assert reporte["semaforo"] == "verde"


def test_decimal_explicito_en_el_cuerpo_no_falla_por_existir(docx_base, tmp_path):
    destino = tmp_path / "decimal.docx"
    _mutar(docx_base, destino, {"word/document.xml": _decimal_explicito})
    reporte, res = _por_regla(str(destino))
    assert res["numeracion_cuerpo_arabigo"]["passed"], res["numeracion_cuerpo_arabigo"]["found"]
    assert reporte["semaforo"] == "verde"


def test_reinicio_romano_99_falla(docx_base, tmp_path):
    destino = tmp_path / "romano.docx"
    _mutar(docx_base, destino, {"word/document.xml": _roman_restart_99})
    reporte, res = _por_regla(str(destino))
    assert not res["numeracion_preliminares_romano"]["passed"]
    assert reporte["semaforo"] == "rojo"


def test_titlepg_apagado_falla(docx_base, tmp_path):
    destino = tmp_path / "titlepg.docx"
    _mutar(docx_base, destino, {"word/document.xml": _titlepg_false})
    reporte, res = _por_regla(str(destino))
    assert not res["caratula_no_se_enumera"]["passed"]
    assert reporte["semaforo"] == "rojo"


def test_titlepg_verdadero_explicito_pasa(docx_base, tmp_path):
    destino = tmp_path / "titlepg-true.docx"
    _mutar(docx_base, destino, {"word/document.xml": _titlepg_true})
    _, res = _por_regla(str(destino))
    assert res["caratula_no_se_enumera"]["passed"]


def test_page_a_la_izquierda_falla_aunque_otro_parrafo_sea_derecho(docx_base, tmp_path):
    destino = tmp_path / "page-left.docx"
    _mutar(docx_base, destino, {"word/footer1.xml": _page_number_left})
    reporte, res = _por_regla(str(destino))
    assert not res["numeracion_posicion"]["passed"]
    assert reporte["semaforo"] == "rojo"


def test_pie_con_page_sin_alineacion_falla(docx_base, tmp_path):
    destino = tmp_path / "page-sin-jc.docx"
    _mutar(docx_base, destino, {"word/footer1.xml": _pie_sin_alineacion})
    _, res = _por_regla(str(destino))
    assert not res["numeracion_posicion"]["passed"]


def test_pageref_no_cuenta_como_numero_de_pagina(docx_base, tmp_path):
    destino = tmp_path / "pageref.docx"
    _mutar(docx_base, destino, {"word/footer1.xml": _pageref})
    _, res = _por_regla(str(destino))
    assert not res["numeracion_posicion"]["passed"]


def test_formato_arabigo_incorrecto_en_el_cuerpo_falla(docx_base, tmp_path):
    destino = tmp_path / "cuerpo-romano.docx"
    _mutar(docx_base, destino, {"word/document.xml": _formato_cuerpo_incorrecto})
    _, res = _por_regla(str(destino))
    assert not res["numeracion_cuerpo_arabigo"]["passed"]


def test_cuerpo_no_reinicia_en_1_si_hay_preliminares(docx_base, tmp_path):
    destino = tmp_path / "cuerpo-1.docx"
    _mutar(docx_base, destino, {"word/document.xml": _cuerpo_reinicia_en_1})
    _, res = _por_regla(str(destino))
    assert not res["numeracion_cuerpo_arabigo"]["passed"]


def test_preliminares_pueden_declarar_inicio_1(docx_base, tmp_path):
    destino = tmp_path / "preliminar-1.docx"
    _mutar(docx_base, destino, {"word/document.xml": _preliminares_inicio_1})
    _, res = _por_regla(str(destino))
    assert res["numeracion_preliminares_romano"]["passed"]


def test_reinicio_explicito_en_una_seccion_posterior_falla(docx_base, tmp_path):
    destino = tmp_path / "preliminar-reinicio.docx"
    _mutar(docx_base, destino, {"word/document.xml": _preliminares_reinicia_despues})
    _, res = _por_regla(str(destino))
    assert not res["numeracion_preliminares_romano"]["passed"]


def test_inicio_2_en_seccion_posterior_no_es_reinicio(docx_base, tmp_path):
    """Carátula en su sección (i) y dedicatoria declarada en ii es válido."""
    destino = tmp_path / "preliminar-inicio-2.docx"
    _mutar(
        docx_base,
        destino,
        {"word/document.xml": lambda doc: _preliminares_reinicia_despues(doc, "2")},
    )
    _, res = _por_regla(str(destino))
    assert res["numeracion_preliminares_romano"]["passed"]


def test_titlepg_apagado_en_caratula_no_salva_el_de_otra_seccion(docx_base, tmp_path):
    """Un `titlePg` vivo en otra sección no salva una carátula apagada."""
    destino = tmp_path / "titlepg-otra-seccion.docx"
    _mutar(docx_base, destino, {"word/document.xml": _titlepg_vivo_en_otra_seccion})
    _, res = _por_regla(str(destino))
    assert not res["caratula_no_se_enumera"]["passed"]


def test_titlepg_en_seccion_posterior_no_falla(docx_base, tmp_path):
    """La tesis real declara `titlePg` en el segundo sectPr, no en el primero."""
    destino = tmp_path / "titlepg-seccion-posterior.docx"
    _mutar(docx_base, destino, {"word/document.xml": _titlepg_solo_en_seccion_posterior})
    _, res = _por_regla(str(destino))
    assert res["caratula_no_se_enumera"]["passed"]
