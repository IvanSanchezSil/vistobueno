"""Tests de la Fase F2: tokenizer, PDA (automata_pila) y flujo tokenizado.

Cubre:
- Tokenizer: orden y tipos de tokens (TITULO, PARRAFO, TABLA, IMAGEN,
  SALTO_SECCION) y las proyecciones solo()/textos().
- PDA puro: aceptación con estado final Y pila vacía; rechazo por pila
  no vacía en estado final; rechazo por tope inesperado; transiciones
  epsilon.
- Compilador DSL `automata_pila` end-to-end (balanceado / no balanceado).
- Gramática de estructura consumiendo el flujo tokenizado (tipo_flujo).

Uso:
    pytest tests/test_f2_automatas.py -v
"""
import tempfile
import zipfile
from pathlib import Path

from validator.automata import PDA, TransicionPDA
from validator.compilador import CompilerDSL
from validator.engine import validate_docx
from validator.extractor import extract
from validator.tokenizer import (
    IMAGEN,
    PARRAFO,
    SALTO_SECCION,
    TABLA,
    TITULO,
    solo,
    textos,
    tokenizar,
)

# ---------------------------------------------------------------------------
# Helpers: construir un DOCX mínimo en memoria
# ---------------------------------------------------------------------------

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ANS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PIC_NS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

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


def _para(texto: str, estilo: str = "", con_blip: bool = False) -> str:
    pPr = ""
    if estilo:
        pPr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>'
    dibujo = ""
    if con_blip:
        dibujo = (
            '<w:drawing><w:inline xmlns:a="' + ANS + '"><a:graphic><a:graphicData '
            'xmlns:pic="' + PIC_NS + '"><pic:pic><pic:blipFill>'
            '<a:blip r:embed="rId20" xmlns:r="' + REL_NS + '"/>'
            '</pic:blipFill></pic:pic></a:graphicData></a:graphic></w:inline></w:drawing>'
        )
    return (
        f"<w:p>{pPr}<w:r>{dibujo}"
        f'<w:t xml:space="preserve">{texto}</w:t></w:r></w:p>'
    )


def _tabla() -> str:
    """Una tabla de una celda cuyo interior es otro párrafo (anidado)."""
    celda = (
        "<w:tc>"
        '<w:p><w:r><w:t xml:space="preserve">CELDA_1</w:t></w:r></w:p>'
        "</w:tc>"
    )
    return f"<w:tbl><w:tblPr/><w:tr>{celda}</w:tr></w:tbl>"


def _docxml(paras: list) -> str:
    body = "".join(paras)
    body += '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{body}</w:body></w:document>'
    )


def _make_docx(paras: list) -> str:
    """Escribe un DOCX mínimo en un archivo temporal y devuelve su ruta."""
    doc = _docxml(paras)
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


# ---------------------------------------------------------------------------
# Tests: Tokenizer (análisis léxico)
# ---------------------------------------------------------------------------


class TestTokenizer:
    def _tokens(self, paras: list):
        path = _make_docx(paras)
        try:
            return tokenizar(extract(path))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_flujo_tipos_y_orden(self):
        tokens = self._tokens([
            _para("CAPÍTULO I", "Ttulo1"),
            _para("texto de párrafo"),
            _tabla(),
            _para("imagen aquí", con_blip=True),
            _para("Subsección", "Heading2"),
        ])
        assert [t.tipo for t in tokens] == [
            TITULO, PARRAFO, TABLA, PARRAFO, PARRAFO, IMAGEN, TITULO,
            SALTO_SECCION,
        ]

    def test_heading_nivel_y_texto(self):
        tokens = self._tokens([
            _para("CAPÍTULO I", "Ttulo1"),
            _para("Subsección", "Heading2"),
        ])
        tits = [t for t in tokens if t.tipo == TITULO]
        assert [(t.texto, t.nivel) for t in tits] == [
            ("CAPÍTULO I", 1),
            ("Subsección", 2),
        ]

    def test_parrafo_anidado_en_tabla(self):
        """El tokenizer incluye párrafos dentro de celdas (paridad legacy)."""
        tokens = self._tokens([_tabla()])
        textos_parrafo = [t.texto for t in tokens if t.tipo == PARRAFO]
        assert "CELDA_1" in textos_parrafo

    def test_solo_y_textos(self):
        tokens = self._tokens([
            _para("CAPÍTULO I", "Ttulo1"),
            _para("cuerpo"),
        ])
        assert [t.texto for t in solo(tokens, [TITULO])] == ["CAPÍTULO I"]
        assert textos(solo(tokens, [PARRAFO])) == ["cuerpo"]


# ---------------------------------------------------------------------------
# Tests: PDA puro
# ---------------------------------------------------------------------------


class TestPDA:
    def _pda(self) -> PDA:
        return PDA(
            estados=["__inicio__", "cap", "fin"],
            transiciones=[
                TransicionPDA("__inicio__", "cap", "CAPÍTULO", push="cap"),
                TransicionPDA("cap", "cap", "SECCIÓN"),
                TransicionPDA("cap", "__inicio__", "FIN DE CAPÍTULO", pop="cap"),
                TransicionPDA("__inicio__", "fin", "EPÍLOGO"),
            ],
            inicial="__inicio__",
            aceptacion=["fin"],
        )

    def test_acepta_balanceado(self):
        ok, falt = self._pda().reconocer([
            "CAPÍTULO I", "SECCIÓN 1.1", "FIN DE CAPÍTULO", "EPÍLOGO",
        ])
        assert ok
        assert falt == []

    def test_acepta_multinivel_y_multicap(self):
        ok, falt = self._pda().reconocer([
            "CAPÍTULO I", "SECCIÓN 1.1", "SECCIÓN 1.2", "FIN DE CAPÍTULO",
            "CAPÍTULO II", "FIN DE CAPÍTULO", "EPÍLOGO",
        ])
        assert ok
        assert falt == []

    def test_rechaza_seccion_sin_cierre(self):
        ok, falt = self._pda().reconocer(
            ["CAPÍTULO I", "SECCIÓN 1.1", "EPÍLOGO"]
        )
        assert not ok
        assert falt  # reporta lo que falta desde el estado 'cap'

    def test_rechaza_estado_final_con_pila_llena(self):
        pda = PDA(
            estados=["__inicio__", "fin"],
            transiciones=[
                TransicionPDA("__inicio__", "__inicio__", "ABRIR", push="A"),
                TransicionPDA("__inicio__", "fin", "CERRAR"),
            ],
            inicial="__inicio__",
            aceptacion=["fin"],
        )
        ok, falt = pda.reconocer(["ABRIR", "CERRAR"])
        assert not ok
        assert "sin cerrar" in falt[0]

    def test_rechaza_tope_de_pila_inesperado(self):
        pda = PDA(
            estados=["__inicio__", "cap"],
            transiciones=[
                TransicionPDA("__inicio__", "cap", "CAPÍTULO", push="cap"),
                TransicionPDA("cap", "__inicio__", "FIN", pop="seccion"),
            ],
            inicial="__inicio__",
            aceptacion=["__inicio__"],
        )
        ok, falt = pda.reconocer(["CAPÍTULO", "FIN"])
        assert not ok
        assert "tope de pila inesperado" in falt[0]

    def test_transicion_epsilon_no_consume(self):
        pda = PDA(
            estados=["__inicio__", "lanz", "fin"],
            transiciones=[
                TransicionPDA("__inicio__", "lanz", "LANZAMIENTO"),
                TransicionPDA("lanz", "fin", "", consumir=False),
            ],
            inicial="__inicio__",
            aceptacion=["fin"],
        )
        ok, falt = pda.reconocer(["LANZAMIENTO"])
        assert ok
        assert falt == []


# ---------------------------------------------------------------------------
# Tests: Compilador DSL automata_pila (end-to-end)
# ---------------------------------------------------------------------------


class TestAutomataPilaDSL:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "estructura_capitulos",
                "tipo": "estructura",
                "severidad": "error",
                "descripcion": "Capítulos balanceados con pila",
                "automata_pila": {
                    "tipo_flujo": "titulos",
                    "normalizacion": ["mayusculas", "ignorar_indent"],
                    "inicial": "inicio",
                    "aceptacion": ["fin"],
                    "transiciones": [
                        {"desde": "inicio", "hacia": "cap", "patron": "CAPÍTULO",
                         "consumir": True, "push": "cap"},
                        {"desde": "cap", "hacia": "cap", "patron": "SECCIÓN",
                         "consumir": True},
                        {"desde": "cap", "hacia": "inicio", "patron": "FIN DE CAPÍTULO",
                         "consumir": True, "pop": "cap"},
                        {"desde": "inicio", "hacia": "fin", "patron": "EPÍLOGO",
                         "consumir": True},
                    ],
                },
            }
        ],
    }

    def test_compila_automata_pila(self):
        compilado = CompilerDSL().compilar(self.RULES)
        assert len(compilado) == 1
        assert compilado[0].rule["id"] == "estructura_capitulos"
        assert compilado[0].analizadores[0].tipo_flujo == "titulos"

    def test_cumple_balanceado(self):
        path = _make_docx([
            _para("Capítulo I", "Ttulo1"),
            _para("Sección 1.1", "Heading2"),
            _para("Fin de capítulo", "Ttulo1"),
            _para("Epílogo", "Ttulo1"),
        ])
        try:
            resultados = validate_docx(path, self.RULES)
            assert len(resultados) == 1
            assert resultados[0].passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_capitulo_sin_cerrar(self):
        path = _make_docx([
            _para("Capítulo I", "Ttulo1"),
            _para("Epílogo", "Ttulo1"),
        ])
        try:
            resultados = validate_docx(path, self.RULES)
            assert resultados[0].passed is False
            assert "faltantes" in resultados[0].found
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_sin_epilogo(self):
        path = _make_docx([
            _para("Capítulo I", "Ttulo1"),
            _para("Fin de capítulo", "Ttulo1"),
        ])
        try:
            resultados = validate_docx(path, self.RULES)
            assert resultados[0].passed is False
            assert "faltantes" in resultados[0].found
        finally:
            Path(path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Tests: Gramática consumiendo el flujo tokenizado
# ---------------------------------------------------------------------------


class TestGramaticaConTokens:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "estructura_tokenizada",
                "tipo": "estructura",
                "severidad": "error",
                "descripcion": "Estructura sobre el flujo tokenizado",
                "gramatica_estructura": {
                    "tipo_flujo": "documento",
                    "tipos": ["TITULO", "PARRAFO"],
                    "reglas_sintacticas": ["TESIS → INTRODUCCIÓN RESULTADOS"],
                    "terminales": ["INTRODUCCIÓN", "RESULTADOS"],
                    "no_terminales": ["TESIS"],
                    "inicio": "TESIS",
                },
            }
        ],
    }

    def test_cumple_con_parrafos_intermedios(self):
        path = _make_docx([
            _para("Introducción", "Ttulo1"),
            _para("cuerpo del capítulo de introducción"),
            _para("Resultados", "Heading2"),
        ])
        try:
            resultados = validate_docx(path, self.RULES)
            assert resultados[0].passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple(self):
        path = _make_docx([
            _para("Introducción", "Ttulo1"),
            _para("párrafo suelto"),
        ])
        try:
            resultados = validate_docx(path, self.RULES)
            assert resultados[0].passed is False
            assert "faltantes" in resultados[0].found
        finally:
            Path(path).unlink(missing_ok=True)