"""Extracción y normalización de un DOCX para el motor de reglas.

Encapsula el acceso al paquete OPC (zip) y expone los árboles XML
necesarios (document.xml, footer1.xml, header1.xml) más el contexto
"cuerpo": párrafos de la ÚLTIMA sección (los que están después del
último <w:sectPr> anidado en <w:pPr> — límite real de sección), con
estilo Normal o sin estilo explícito. Ver unt_format_rules_schema.yaml
para la convención completa de mecanismo_verificable.
"""
import zipfile
from dataclasses import dataclass
from typing import Optional, Set

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
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


def _cuerpo_paras(doc) -> Set:
    paras = doc.xpath("//w:body/w:p", namespaces=NS)
    boundary = -1
    for idx, p in enumerate(paras):
        if p.find(f"{W}pPr/{W}sectPr") is not None:
            boundary = idx
    result = set()
    for p in paras[boundary + 1:]:
        pPr = p.find(W + "pPr")
        st = pPr.find(W + "pStyle") if pPr is not None else None
        if st is None or st.get(W + "val") in (None, "", "Normal"):
            result.add(p)
    return result


@dataclass
class ExtractedDocx:
    document: "etree._Element"
    footer: Optional["etree._Element"]
    header: Optional["etree._Element"]
    _cuerpo: Set

    def is_cuerpo(self, node) -> bool:
        return _para_ancestor(node) in self._cuerpo

    def part(self, name: str) -> Optional["etree._Element"]:
        return {
            "document": self.document,
            "footer": self.footer,
            "header": self.header,
        }.get(name)


def extract(docx_path: str) -> ExtractedDocx:
    """Abre un .docx (zip OPC) y devuelve sus partes XML relevantes ya
    parseadas, listas para que checks.run_check las consulte."""
    with zipfile.ZipFile(docx_path) as z:
        names = z.namelist()
        document = etree.fromstring(z.read("word/document.xml"))
        footer = (
            etree.fromstring(z.read("word/footer1.xml"))
            if "word/footer1.xml" in names
            else None
        )
        header = (
            etree.fromstring(z.read("word/header1.xml"))
            if "word/header1.xml" in names
            else None
        )
    return ExtractedDocx(
        document=document,
        footer=footer,
        header=header,
        _cuerpo=_cuerpo_paras(document),
    )
