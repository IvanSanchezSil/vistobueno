"""Guarda integral de los ejemplos versionados (`docs/ejemplos/`).

Los dos DOCX y sus JSON son la evidencia pública del resultado esperado del
validador. La guardia usa los bytes que están versionados. No regenera un
documento nuevo durante el test, porque esa forma detectaría el contenido, pero
no el daño del archivo entregado.

Qué comprueba:

- cada DOCX abre con `python-docx`;
- cada relación interna apunta a una parte existente del paquete OPC;
- la API recibe los bytes exactos del DOCX versionado;
- la respuesta completa coincide con el JSON golden, incluida la ficha de
  depósito, la lista completa de reglas y la lista completa de prompts.

Si el test falla, la respuesta correcta es regenerar el par:

    python scripts/ejemplo_bueno_malo.py

y revisar el diff antes de commitearlo.
"""

from __future__ import annotations

import json
import posixpath
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import docx
import pytest
from conftest import CLIENTE, MIME_DOCX

RAIZ = Path(__file__).resolve().parent.parent
EJEMPLOS = RAIZ / "docs" / "ejemplos"

REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _respuesta_del_docx_versionado(nombre: str) -> dict:
    """Envía a la API los bytes del DOCX versionado y devuelve su respuesta."""
    ruta = EJEMPLOS / f"{nombre}.docx"
    with ruta.open("rb") as archivo:
        respuesta = CLIENTE.post(
            "/validar",
            files={"archivo": (ruta.name, archivo, MIME_DOCX)},
        )
    respuesta.raise_for_status()
    return respuesta.json()


def _directorio_base(parte_rels: str) -> str:
    """Devuelve el directorio de la parte que declara un archivo ``.rels``."""
    directorio_rels = posixpath.dirname(parte_rels)
    if posixpath.basename(directorio_rels) != "_rels":
        raise AssertionError(f"archivo de relaciones fuera de _rels: {parte_rels}")

    directorio_parte = posixpath.dirname(directorio_rels)
    nombre_parte = posixpath.basename(parte_rels)[: -len(".rels")]
    return posixpath.dirname(posixpath.join(directorio_parte, nombre_parte))


def _destino_de_relacion(parte_rels: str, objetivo: str) -> str | None:
    """Resuelve un ``Target`` interno a su ruta dentro del paquete OPC."""
    uri = urlsplit(objetivo)
    if uri.scheme or uri.netloc:
        return None

    ruta = unquote(uri.path)
    if not ruta:
        return None
    if ruta.startswith("/"):
        return ruta.lstrip("/")
    return posixpath.normpath(posixpath.join(_directorio_base(parte_rels), ruta))


@pytest.mark.parametrize(
    ("parte_rels", "objetivo", "esperado"),
    [
        ("_rels/.rels", "word/document.xml", "word/document.xml"),
        ("word/_rels/document.xml.rels", "media/logo.png", "word/media/logo.png"),
        ("word/_rels/document.xml.rels", "/word/document.xml", "word/document.xml"),
        ("word/_rels/document.xml.rels", "../media/logo.png", "media/logo.png"),
        ("word/_rels/document.xml.rels", "media%20logo.png", "word/media logo.png"),
        ("word/_rels/document.xml.rels", "document.xml#bookmark", "word/document.xml"),
        ("word/_rels/document.xml.rels", "https://example.test/relacion", None),
    ],
    ids=[
        "raiz-del-paquete",
        "relativo",
        "absoluto",
        "relativo-con-padre",
        "codificado",
        "con-fragmento",
        "externo",
    ],
)
def test_resolucion_de_destinos_opc(
    parte_rels: str,
    objetivo: str,
    esperado: str | None,
) -> None:
    """La resolución OPC conserva la base, decodifica y descarta el fragmento."""
    assert _destino_de_relacion(parte_rels, objetivo) == esperado


@pytest.mark.parametrize("nombre", ["doc_bueno", "doc_malo"])
def test_docx_versionado_abre_con_python_docx(nombre: str) -> None:
    """El paquete entregado debe abrir como documento de Word."""
    ruta = EJEMPLOS / f"{nombre}.docx"
    documento = docx.Document(ruta)

    assert documento.paragraphs
    assert documento.sections


@pytest.mark.parametrize("nombre", ["doc_bueno", "doc_malo"])
def test_destinos_de_relaciones_internas_existen(nombre: str) -> None:
    """Toda relación interna debe apuntar a una parte existente del OPC."""
    ruta = EJEMPLOS / f"{nombre}.docx"
    comprobadas = 0

    with zipfile.ZipFile(ruta) as paquete:
        partes = set(paquete.namelist())
        partes_rels = sorted(parte for parte in partes if parte.endswith(".rels"))

        for parte_rels in partes_rels:
            raiz = ET.fromstring(paquete.read(parte_rels))
            for relacion in raiz.findall(f"{{{REL_NS}}}Relationship"):
                if relacion.get("TargetMode") == "External":
                    continue

                objetivo = relacion.get("Target")
                assert objetivo, f"{parte_rels}: relación sin Target"
                destino = _destino_de_relacion(parte_rels, objetivo)
                assert destino is not None, f"{parte_rels}: destino externo {objetivo!r}"
                assert destino in partes, (
                    f"{parte_rels}: {relacion.get('Id')} apunta a {destino!r}, "
                    "pero esa parte no existe"
                )
                comprobadas += 1

    assert comprobadas > 0, f"{ruta.name} no declara relaciones internas"


@pytest.mark.parametrize("nombre", ["doc_bueno", "doc_malo"])
def test_respuesta_api_del_docx_versionado_coincide_con_golden(nombre: str) -> None:
    """La API debe producir exactamente la respuesta JSON versionada."""
    golden = json.loads((EJEMPLOS / f"respuesta_{nombre}.json").read_text(encoding="utf-8"))
    fresco = _respuesta_del_docx_versionado(nombre)

    assert fresco["ficha_deposito"] == golden["ficha_deposito"], (
        f"la ficha de depósito de {nombre} cambió; regenera el par"
    )
    assert fresco["resultados"] == golden["resultados"], (
        f"la lista de reglas de {nombre} cambió; regenera el par"
    )
    assert fresco["como_preguntar_a_una_ia"] == golden["como_preguntar_a_una_ia"], (
        f"la lista de prompts de {nombre} cambió; regenera el par"
    )
    assert fresco == golden, f"la respuesta completa de {nombre} cambió; regenera el par"
