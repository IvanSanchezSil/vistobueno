"""RI-07: acotar los XPath de carátula al bloque de carátula.

Retblast midó 40,74 s de 44,29 s en dos reglas (`caratula_autores_tamano`
y `ficha_autores`) porque `ExtractedDocx.xpath()` evaluaba el XPath en TODO
el árbol y filtraba por carátula recién después. Acá se fija que:

1. el XPath reducido devuelve los mismos nodos que el filtro anterior para
   todas las expresiones de carátula del catálogo;
2. el reporte completo (semáforo, resumen, resultados y ficha) es idéntico
   con la implementación nueva y con la anterior, incluso con un cuerpo
   largo y párrafos engañosos (`ASESOR:`, `Línea de Investigación:`);
3. el árbol reducido tiene solo los párrafos de carátula, no el cuerpo.

Los nombres son placeholders: no entra PII al repo.
"""

from pathlib import Path

import pytest
import yaml
from _caratula_real import PORTADA
from docx import Document
from docx.enum.section import WD_SECTION
from lxml import etree

from validator.engine import build_report, load_ficha_rules, load_rules, validate_docx
from validator.extractor import NS, ExtractedDocx, extract

RAIZ = Path(__file__).resolve().parent.parent
YAMLS = ("reglas_unt.yaml", "reglas_ficha.yaml")
CONTEXTOS = ("caratula", "caratula_ficha")


def _expresiones_caratula():
    """Todo XPath declarado con contexto de carátula en los YAML de reglas."""
    salida = []

    def caminar(objeto):
        if isinstance(objeto, dict):
            contexto = objeto.get("contexto")
            if contexto in CONTEXTOS:
                for clave in ("xpath", "parrafo_xpath"):
                    expresion = objeto.get(clave)
                    if isinstance(expresion, str):
                        salida.append(
                            (
                                objeto.get("parte", "document"),
                                contexto,
                                expresion,
                            )
                        )
            for valor in objeto.values():
                caminar(valor)
        elif isinstance(objeto, list):
            for valor in objeto:
                caminar(valor)

    for nombre in YAMLS:
        data = yaml.safe_load((RAIZ / nombre).read_text(encoding="utf-8"))
        caminar(data)
    return salida


EXPRESIONES = _expresiones_caratula()


@pytest.fixture(scope="module")
def docx_cuerpo_largo(tmp_path_factory) -> Path:
    """Carátula real + cuerpo largo con párrafos que imitan la portada."""
    documento = Document()
    for linea in PORTADA:
        documento.add_paragraph(linea)
    # Salto de sección real: la carátula queda delimitada por `w:pPr/w:sectPr`.
    documento.add_section(WD_SECTION.NEW_PAGE)
    for i in range(200):
        documento.add_paragraph(f"Párrafo {i:04d}: texto de cuerpo sin datos de portada.")
        if i % 40 == 0:
            documento.add_paragraph("ASESOR: dato engañoso del cuerpo")
            documento.add_paragraph("Línea de Investigación: dato engañoso del cuerpo")
    destino = tmp_path_factory.mktemp("ri07") / "cuerpo_largo.docx"
    documento.save(destino)
    return destino


def _firma(nodo):
    """Identifica un nodo por su ruta y texto, sin depender de copias."""
    if isinstance(nodo, etree._Element):
        return ("elem", nodo.getroottree().getpath(nodo), "".join(nodo.itertext()))
    return (type(nodo).__name__, str(nodo))


def _xpath_original(self, parte, xpath_expr, contexto="todos"):
    """La implementación previa a RI-07, para comparar comportamiento."""
    clave = (parte, contexto, xpath_expr)
    if clave in self._cache:
        return self._cache[clave]
    arboles = self._arboles(parte)
    if not arboles:
        raise ValueError(f"parte '{parte}' no disponible en este archivo")
    nodos = []
    for tree in arboles:
        nodos.extend(tree.xpath(xpath_expr, namespaces=NS))
    if contexto == "cuerpo":
        nodos = [n for n in nodos if self.is_cuerpo(n)]
    if contexto == "cuerpo_prosa":
        nodos = [n for n in nodos if self.is_cuerpo_prosa(n)]
    if contexto == "seccion_cuerpo":
        nodos = [n for n in nodos if self.es_seccion_cuerpo(n)]
    if contexto == "caratula":
        nodos = [n for n in nodos if self.is_caratula(n)]
    if contexto == "caratula_ficha":
        nodos = [n for n in nodos if self.is_caratula_ficha(n)]
    self._cache[clave] = nodos
    return nodos


@pytest.mark.parametrize(("parte", "contexto", "expresion"), EXPRESIONES)
def test_el_xpath_reducido_devuelve_los_mismos_nodos(docx_cuerpo_largo, parte, contexto, expresion):
    """Ninguna expresión del catálogo cambia de resultado al acotar el árbol."""
    extraido = extract(str(docx_cuerpo_largo))
    reducido = [_firma(n) for n in extraido.xpath(parte, expresion, contexto)]
    completo = [_firma(n) for n in _xpath_original(extraido, parte, expresion, contexto)]
    assert reducido == completo


def test_el_arbol_reducido_excluye_el_cuerpo(docx_cuerpo_largo):
    """La copia de carátula no arrastra los 200 párrafos del cuerpo."""
    extraido = extract(str(docx_cuerpo_largo))
    arbol, mapa = extraido._arbol_caratula("caratula")
    copias = arbol.xpath("//w:body/w:p", namespaces=NS)
    assert len(copias) == len(extraido._caratula)
    assert len(copias) < 30
    assert all(copia in mapa for copia in copias)
    # Los nodos devueltos son los originales: la paginación sigue funcionando.
    parrafo = extraido.xpath("document", "//w:body/w:p[1]", "caratula")[0]
    assert parrafo in extraido._caratula
    assert extraido.pagina_de(parrafo) is not None


def _reporte(ruta: Path) -> dict:
    resultados = validate_docx(
        str(ruta),
        load_rules(str(RAIZ / "reglas_unt.yaml")),
        load_ficha_rules(str(RAIZ / "reglas_ficha.yaml")),
    )
    informe = build_report(resultados)
    return {
        "semaforo": informe["semaforo"],
        "resumen": informe["resumen"],
        "resultados": [(r.rule_id, r.passed, r.severity.value, r.found) for r in resultados],
        "ficha": informe.get("ficha", {}),
    }


def test_reporte_igual_con_cuerpo_largo(docx_cuerpo_largo, monkeypatch):
    """Semáforo, advertencias y capturas no cambian respecto del motor anterior."""
    nuevo = _reporte(docx_cuerpo_largo)
    with monkeypatch.context() as parche:
        parche.setattr(ExtractedDocx, "xpath", _xpath_original)
        anterior = _reporte(docx_cuerpo_largo)
    assert nuevo == anterior


def test_capturas_con_cuerpo_largo(docx_cuerpo_largo):
    """Los dos autores, el asesor y su ORCID siguen separados y en orden."""
    informe = _reporte(docx_cuerpo_largo)
    ficha = informe["ficha"]
    assert ficha["dc.contributor.author"]["valor"] == [
        "Br. Apellido, Nombre",
        "Br. Apellido2, Nombre2",
    ]
    assert ficha["dc.contributor.advisor"]["valor"] == "Dra. Apellido, Nombre"
    assert ficha["renati.advisor.orcid"]["valor"] == "0000-0000-0000-0002"
