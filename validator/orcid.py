"""Identificadores ORCID: extracción, dígito de control y lectura de la carátula.

El manual exige que **cada autor y el asesor** muestren su ORCID como
hipervínculo debajo del nombre (párr. 179-180). El identificador tiene 16
dígitos y un dígito de control ISO 7064 MOD 11-2 que puede ser ``X``.

Este módulo no toca la red: solo valida la forma del identificador y la
correspondencia entre el texto visible y el destino del hipervínculo. La
identidad del perfil (que el ORCID pertenezca a esa persona) no se puede
comprobar sin consultar el servicio de ORCID, y queda fuera del alcance
(M8/VA-16).
"""

from __future__ import annotations

import re

from .extractor import W, text_of

# 16 dígitos con guiones opcionales; el último puede ser X. Los guards evitan
# aceptar un fragmento de un número más largo.
_ORCID = re.compile(r"(?<![\dXx])(\d{4})-?(\d{4})-?(\d{4})-?(\d{3}[\dXx])(?![\dXx])")

# Línea de ORCID completa: el identificador solo, o la URL del perfil, con
# paréntesis opcionales (el manual pide «entre paréntesis») y una etiqueta
# «ORCID:» opcional, que algunas plantillas agregan delante.
_LINEA_ORCID = re.compile(
    r"^\(?\s*(?:orcid\s*:\s*)?(?:https?://(?:www\.)?orcid\.org/)?"
    r"\d{4}-?\d{4}-?\d{4}-?\d{3}[\dXx]\s*\)?$",
    re.IGNORECASE,
)

_ACENTOS = str.maketrans("ÁÉÍÓÚÜÑáéíóúüñ", "AEIOUUNaeiouun")

# Etiquetas de la carátula que abren/cierran los bloques de personas.
_FIN_BLOQUE = re.compile(
    r"^(linea|trujillo|ciudad|ano|resumen|indice|dedicatoria|agradecimiento|"
    r"abstract|universidad|facultad|escuela|programa|tesis|para optar|titulo|proyecto)\b"
)


def extraer(texto: str | None) -> str | None:
    """Primer ORCID del texto, normalizado a ``dddd-dddd-dddd-dddd``.

    Devuelve ``None`` si no hay ninguno. El último carácter se normaliza a
    mayúscula (``x`` → ``X``).
    """
    m = _ORCID.search(texto or "")
    if m is None:
        return None
    return "-".join(m.groups()).upper()


def checksum_valido(orcid: str) -> bool:
    """¿El dígito de control del ORCID es correcto? (ISO 7064 MOD 11-2)."""
    digitos = orcid.replace("-", "").upper()
    if len(digitos) != 16 or not digitos[:15].isdigit():
        return False
    total = 0
    for caracter in digitos[:15]:
        total = (total + int(caracter)) * 2
    resto = (12 - total % 11) % 11
    esperado = "X" if resto == 10 else str(resto)
    return digitos[15] == esperado


def destino_corresponde(destino: str | None, orcid: str) -> bool:
    """¿El destino del hipervínculo es el perfil del ORCID visible?

    El destino debe apuntar a ``orcid.org`` y llevar **el mismo**
    identificador que el texto. Un texto correcto con destino falso (otro
    identificador, otro dominio o sin relación) no cumple (VA-16).
    """
    if not destino:
        return False
    if not re.match(r"^https?://(?:www\.)?orcid\.org/", destino.strip(), re.IGNORECASE):
        return False
    return extraer(destino) == orcid


def tiene_orcid_en_parrafo(parrafo) -> bool:
    """¿El párrafo contiene un hipervínculo cuyo texto es un ORCID?"""
    for enlace in parrafo.iter(W + "hyperlink"):
        if _ORCID.search(text_of(enlace)):
            return True
    return False


def _norm(texto: str) -> str:
    """Texto en minúsculas, sin acentos y con espacios colapsados."""
    return " ".join(texto.translate(_ACENTOS).lower().split())


def _resto_tras_etiqueta(texto: str) -> str:
    """Parte del párrafo posterior a la primera etiqueta con dos puntos."""
    _, separador, resto = texto.partition(":")
    return resto.strip() if separador else ""


def _es_linea_orcid(texto: str) -> bool:
    """¿El párrafo es solo la línea del ORCID (con o sin paréntesis)?"""
    return bool(_LINEA_ORCID.match(texto.strip()))


def revisar_caratula(parrafos: list[tuple[str, bool]]) -> tuple[int, list[str]]:
    """Cuenta las personas de la carátula y las que no tienen ORCID.

    ``parrafos`` son ``(texto, tiene_orcid)`` en orden de documento, donde
    ``tiene_orcid`` indica si ese párrafo contiene un hipervínculo ORCID.
    Se reconocen los bloques «AUTORES:»/«AUTORA:» y «ASESOR(A):» del manual:
    dentro de cada bloque, cada párrafo de nombre es una persona, y su ORCID
    debe estar en el mismo párrafo o en el siguiente. Una línea de ORCID sin
    hipervínculo no satisface la regla (se exige el enlace).

    Devuelve ``(total_personas, nombres_sin_orcid)``. Si la estructura de la
    carátula no se reconoce, ``total_personas`` es 0 y el analizador se queda
    con la comprobación global de cantidad.
    """
    estado: str | None = None
    personas = 0
    faltan: list[str] = []
    pendiente: list | None = None  # [nombre, tiene_orcid]

    def cerrar() -> None:
        nonlocal pendiente
        if pendiente is not None and not pendiente[1]:
            faltan.append(pendiente[0])
        pendiente = None

    for texto, tiene in parrafos:
        normalizado = _norm(texto)
        if not normalizado:
            continue

        if estado is not None and _FIN_BLOQUE.match(normalizado):
            cerrar()
            break

        if normalizado.startswith("autor"):
            cerrar()
            estado = "autores"
            resto = _resto_tras_etiqueta(texto)
            if resto:
                personas += 1
                pendiente = [resto, tiene]
            continue

        if normalizado.startswith("asesor"):
            cerrar()
            estado = "asesor"
            resto = _resto_tras_etiqueta(texto)
            if resto:
                personas += 1
                pendiente = [resto, tiene]
            continue

        if estado is None:
            continue

        if _es_linea_orcid(texto):
            if pendiente is not None and tiene:
                pendiente[1] = True
            continue

        # Otro párrafo dentro del bloque: es una persona nueva.
        cerrar()
        personas += 1
        pendiente = [texto.strip(), tiene]

    cerrar()
    return personas, faltan
