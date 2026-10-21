"""Tests edgecase del extractor DOCX (R2: defensa zip bomb).

La API limita la subida a 10 MB COMPRIMIDOS, pero un ZIP hostil puede declarar
partes que se expanden a GBs al leerlas. El extractor debe acotar el tamaño
DESCOMPRIMIDO por parte y lanzar BadZipFile (la API lo traduce a 422).

Uso:
    pytest tests/test_extractor_edgecases.py -v
"""

import zipfile

import pytest

from validator.extractor import TAMANO_MAXIMO_PARTE_BYTES, extract


# ---------------------------------------------------------------------------
# DOCXs de prueba minimals (solo lo justo para testear el extractor)
# ---------------------------------------------------------------------------

# Documento XML "mínimo y válido": una etiqueta vacía <w></w>. 6 bytes descomprimidos.
_DOC_MINIMO = b"<w></w>"

# Documento XML "chico": 2 bytes descomprimidos, bien formado: <> (no es XML válido
# standalone, pero como solo testeamos extract() y el document.xml se parsea por
# etree.fromstring, acepta cualquier contenido; usamos <><> para tener 2 bytes XML-ish).
_DOC_CHICO = b"<w></w>"  # 2 bytes


# ---------------------------------------------------------------------------
# Ayuda a construir un DOCX temporal con las partes indicadas.
# ---------------------------------------------------------------------------

def _make_docx(document_xml: bytes, *, headers: dict = None, footers: dict = None,
               footnotes: bytes = b"") -> str:
    """Construye un .docx temporal con las partes indicadas.

    Sólo se escriben las partes solicitadas; las ausentes provocan KeyError
    en el extractor (comportamiento esperado: la API devuelve 422).
    """
    path = "/tmp/mini_docx.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", "")
        z.writestr("word/document.xml", document_xml)
        if headers:
            for nombre, contenido in headers.items():
                z.writestr(nombre, contenido)
        if footers:
            for nombre, contenido in footers.items():
                z.writestr(nombre, contenido)
        if footnotes is not None:
            z.writestr("word/footnotes.xml", footnotes)
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_documento_sobre_tope_lanza_badzipfile(monkeypatch):
    """Documento XML de 5 bytes (b'<w></w>') con tope a 3 bytes → BadZipFile."""
    import pytest
    monkeypatch.setattr("validator.extractor.TAMANO_MAXIMO_PARTE_BYTES", 3)
    path = _make_docx(_DOC_MINIMO)  # 5 bytes descomprimidos
    with pytest.raises(zipfile.BadZipFile):
        extract(path)


def test_documento_abajo_tope_pasa(monkeypatch):
    """Documento XML de 5 bytes (b'<w></w>') con tope a 10 → pasa sin error."""
    import pytest
    import validator.extractor
    monkeypatch.setattr("validator.extractor.TAMANO_MAXIMO_PARTE_BYTES", 10)
    path = _make_docx(_DOC_MINIMO)  # 5 bytes descomprimidos, bajo el tope
    doc = extract(path)
    assert doc.document is not None


def test_header_sobre_tope_lanza_badzipfile(monkeypatch, tmp_path):
    """header1.xml gigante (2000 bytes descomprimidos) con tope a 1000 → BadZipFile."""
    import pytest
    monkeypatch.setattr("validator.extractor.TAMANO_MAXIMO_PARTE_BYTES", 1_000)
    path = "/tmp/mini_header.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", _DOC_MINIMO)  # 5 bytes
        z.writestr("word/header1.xml", b"X" * 2000)  # 2000 bytes descomprimidos
    with pytest.raises(zipfile.BadZipFile, match="header1"):
        extract(path)


def test_footnotes_sobre_tope_lanza_badzipfile(monkeypatch, tmp_path):
    """footnotes.xml gigante (2000 bytes descomprimidos) con tope a 1000 → BadZipFile."""
    import pytest
    monkeypatch.setattr("validator.extractor.TAMANO_MAXIMO_PARTE_BYTES", 1_000)
    path = "/tmp/mini_footnotes.docx"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("word/document.xml", _DOC_MINIMO)  # 5 bytes
        z.writestr("word/footnotes.xml", b"Y" * 2000)  # 2000 bytes descomprimidos
    with pytest.raises(zipfile.BadZipFile, match="footnotes"):
        extract(path)


def test_documento_minimo_pasa_extraccion():
    """Un DOCX sintético mínimo se extrae sin errores (regression)."""
    from docx_factory import compilar_docx, configuracion_base
    path = compilar_docx(configuracion_base())
    doc = extract(path)
    assert doc.document is not None
    assert doc.headers  # el factory siempre trae header1.xml
    assert doc.footer is not None
