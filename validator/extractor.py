"""Extracción y normalización de un DOCX para el motor de reglas.

Encapsula el acceso al paquete OPC (zip) y expone los árboles XML
necesarios (document.xml, footer1.xml, header1.xml) más el contexto
"cuerpo": párrafos de la ÚLTIMA sección (los que están después del
último <w:sectPr> anidado en <w:pPr> — límite real de sección), con
estilo Normal o sin estilo explícito. Ver unt_format_rules_schema.yaml
para la convención completa de mecanismo_verificable.
"""

import zipfile
from dataclasses import dataclass, field

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/officeDocument/relationships",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "pic": "http://schemas.openxmlformats.org/drawingml/2006/picture",
}


def text_of(node) -> str:
    """Concatena el texto de todos los w:t descendientes de un nodo."""
    return "".join(t.text or "" for t in node.iter(W + "t"))


def _para_ancestor(node):
    cur = node
    while cur is not None and cur.tag != W + "p":
        cur = cur.getparent()
    return cur


def _cuerpo_paras(doc) -> set:
    """Párrafos de la última sección del documento (después del último sectPr)."""
    paras = doc.xpath("//w:body/w:p", namespaces=NS)
    boundary = -1
    for idx, p in enumerate(paras):
        if p.find(f"{W}pPr/{W}sectPr") is not None:
            boundary = idx
    result = set()
    for p in paras[boundary + 1 :]:
        pPr = p.find(W + "pPr")
        st = pPr.find(W + "pStyle") if pPr is not None else None
        if st is None or st.get(W + "val") in (None, "", "Normal"):
            result.add(p)
    return result


def _paginacion_para(document) -> dict[int, int]:
    """Calcula el mapa de paginación real (párrafo -> página física).

    Word persiste en el XML dos marcadores fiables de saltos de página:
    ``w:lastRenderedPageBreak`` (insertado al guardar un documento renderizado)
    y ``w:br w:type="page"`` (salto explícito). Recorremos los párrafos en
    orden de documento y correlacionamos cada uno con su número físico de
    página sin necesidad de renderizar el documento.

    La página 1 es la carátula (aunque el manual indique que no se enumera
    visualmente, se cuenta para el correlativo del resto del documento).
    """
    # El mapa usa como clave el ELEMENTO (proxy lxml) y no `id()`: los
    # proxies se liberan y recrean (su `id()` cambia) si no hay una
    # referencia fuerte, lo que rompería las consultas posteriores.
    paginacion: dict = {}
    pagina = 1

    for p in document.xpath("//w:body//w:p", namespaces=NS):
        tiene_salto = (
            p.find(f".//{W}lastRenderedPageBreak", namespaces=NS) is not None
            or p.find(f".//{W}br[@w:type='page']", namespaces=NS) is not None
        )
        paginacion[p] = pagina
        if tiene_salto:
            pagina += 1

    return paginacion


@dataclass
class ExtractedDocx:
    """Árboles XML extraídos + caché XPath + paginación física."""

    document: etree._Element
    footer: etree._Element | None
    header: etree._Element | None
    _cuerpo: set
    # Caché de consultas XPath (F4): clave (parte, contexto, xpath). Evita
    # re-ejecutar la misma consulta por cada analizador de la regla.
    _cache: dict = field(default_factory=dict, repr=False)
    # Paginación real (ítem 1 de la Fase 2): párrafo -> número físico de
    # página, calculada a partir de los saltos que Word persiste en el XML.
    _paginacion: dict = field(default_factory=dict, repr=False)

    def is_cuerpo(self, node) -> bool:
        return _para_ancestor(node) in self._cuerpo

    def pagina_de(self, node) -> int | None:
        """Número físico de página de un párrafo (None si no es un párrafo
        del cuerpo del documento). Es la forma de "devolver también el
        número de página real" pedida en el ítem 1 de la Fase 2."""
        if node is None:
            return None
        p = _para_ancestor(node)
        return self._paginacion.get(p)

    def part(self, name: str) -> etree._Element | None:
        return {
            "document": self.document,
            "footer": self.footer,
            "header": self.header,
        }.get(name)

    def xpath(self, parte: str, xpath_expr: str, contexto: str = "todos") -> list:
        """Consulta XPath con cache por (parte, contexto, xpath).

        Es el punto único por el que los analizadores consultan los árboles:
        dos secciones con el mismo XPath comparten el resultado. Con
        `contexto == "cuerpo"` se filtra por los párrafos de la última
        sección (mismo significado que `_nodos` de los analizadores).
        """
        clave = (parte, contexto, xpath_expr)
        if clave in self._cache:
            return self._cache[clave]
        tree = self.part(parte)
        if tree is None:
            raise ValueError(f"parte '{parte}' no disponible en este archivo")
        nodos = tree.xpath(xpath_expr, namespaces=NS)
        if contexto == "cuerpo":
            nodos = [n for n in nodos if self.is_cuerpo(n)]
        self._cache[clave] = nodos
        return nodos


def extract(docx_path: str) -> ExtractedDocx:
    """Abre un .docx (zip OPC) y devuelve sus partes XML relevantes ya
    parseadas, listas para que checks.run_check las consulte.

    Además de los árboles XML, calcula la paginación física real (párrafo ->
    página) a partir de los saltos de página que Word persiste en el XML,
    para que el motor pueda correlacionar texto con número de página sin
    renderizar el documento.
    """
    with zipfile.ZipFile(docx_path) as z:
        names = z.namelist()
        document = etree.fromstring(z.read("word/document.xml"))
        footer = (
            etree.fromstring(z.read("word/footer1.xml")) if "word/footer1.xml" in names else None
        )
        header = (
            etree.fromstring(z.read("word/header1.xml")) if "word/header1.xml" in names else None
        )

    return ExtractedDocx(
        document=document,
        footer=footer,
        header=header,
        _cuerpo=_cuerpo_paras(document),
        _paginacion=_paginacion_para(document),
    )
