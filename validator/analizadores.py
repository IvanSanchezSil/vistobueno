"""Analizadores de hoja para el DSL declarativo.

Definen la clase base `Analizador` y los analizadores atómicos:
- AnalizadorXML: atributos y presencia de nodos XML (xpath).
- AnalizadorRegex: patrones de texto sobre el contenido del documento.
- AnalizadorLista: pertenencia a una lista de valores permitidos.
- AnalizadorImagen: presencia de imágenes (blips).

Los analizadores de tipo compuesto (secuencia, gramática) viven en
`automata.py`; la clase base `Analizador` los integra a todos.

A diferencia del `checks.py` legacy (que opera sobre una regla completa
`{"checks": [...]}`), los analizadores del DSL reciben **una sola**
comprobación declarada y la ejecutan de forma autocontenida. Esto los
hace componibles y testables por separado.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Tuple

from .extractor import W, ExtractedDocx, NS, text_of

# Prefijos de namespace para resolver names en atributos (ej. "@w:val").
PREFIX_NS = NS


def _resolve_attr_key(atributo: str) -> str:
    """Convierte '@w:val' en '{namespace}val' para lxml .get()."""
    name = atributo[1:]
    if ":" in name:
        prefix, local = name.split(":", 1)
        if prefix in PREFIX_NS:
            return "{" + PREFIX_NS[prefix] + "}" + local
    return name


class Analizador(ABC):
    """Interfaz común de todos los analizadores del DSL.

    Cada analizador se construye a partir de la configuración declarada
    en una sección del YAML (p. ej. `analizador_xml`, `patron_texto`) y
    ejecuta `analizar(extracted)` para producir (pasó, detalle).
    """

    def __init__(self, config: dict):
        self.config = config or {}

    @abstractmethod
    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        ...

    # -- utilidades compartidas -------------------------------------------
    def _nodos(self, extracted: ExtractedDocx, parte: str, contexto: str):
        tree = extracted.part(parte)
        if tree is None:
            raise ValueError(f"parte '{parte}' no disponible en este archivo")
        nodes = tree.xpath(self.config.get("xpath", ""), namespaces=NS)
        if contexto == "cuerpo":
            return [n for n in nodes if extracted.is_cuerpo(n)]
        return nodes


class AnalizadorXML(Analizador):
    """Verifica atributos o presencia de nodos vía XPath.

    Se usa para los DSL `atributo_xml` y `presencia_xml`.
    """

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        parte = self.config.get("parte", "document")
        contexto = self.config.get("contexto", "todos")
        comp = self.config.get("comparacion", "exists")

        nodes = self._nodos(extracted, parte, contexto)

        # Presencia simple
        if comp in ("exists", "not_exists"):
            if comp == "exists":
                return len(nodes) > 0, f"exists {len(nodes)} nodos"
            return len(nodes) == 0, f"not_exists {len(nodes)} nodos"

        # Atributo
        atributo = self.config.get("atributo")
        esperado = self.config.get("esperado")
        if atributo is None:
            return False, "falta 'atributo' para comparación de atributo"
        key = _resolve_attr_key(atributo)
        vals = [n.get(key) for n in nodes]
        vals = [v for v in vals if v is not None]

        if comp == "eq":
            ok = bool(vals) and vals[0] == esperado
        elif comp == "all_eq":
            ok = bool(vals) and all(v == esperado for v in vals)
        elif comp == "contains":
            ignore_case = self.config.get("ignore_case", False)
            if ignore_case:
                ok = bool(vals) and all(
                    str(esperado).lower() in str(v).lower() for v in vals
                )
            else:
                ok = bool(vals) and all(esperado in v for v in vals)
        else:
            return False, f"comparación '{comp}' no soportada"
        return ok, f"{atributo}={vals[:3]} esperado={esperado}"


class AnalizadorRegex(Analizador):
    """Aplica una expresión regular al contenido textual de nodos.

    `coincidencia`: `todos` (todos los nodos deben matchear, por defecto),
    `alguno` (al menos uno), `ninguno` (ninguno).
    """

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        parte = self.config.get("parte", "document")
        contexto = self.config.get("contexto", "todos")
        patron = self.config.get("patron", "")
        coincidencia = self.config.get("coincidencia", "todos")
        ignore_case = self.config.get("ignore_case", False)

        nodes = self._nodos(extracted, parte, contexto)
        textos = [t.text for n in nodes for t in n.iter(W + "t") if t.text]
        if not textos:
            return False, "sin nodos w:t que evaluar"

        flags = re.IGNORECASE if ignore_case else 0
        rx = re.compile(patron, flags)

        def _matchea(s: str) -> bool:
            c = self.config.get("comparacion", "regex")
            if c == "fullmatch":
                return bool(rx.fullmatch(s.strip()))
            return bool(rx.search(s))

        if coincidencia == "todos":
            incumplen = [t for t in textos if not _matchea(t)]
            return not incumplen, f"textos={len(textos)} incumplen={len(incumplen)}"
        if coincidencia == "alguno":
            ok = any(_matchea(t) for t in textos)
            return ok, f"textos={len(textos)} alguno_matchea={ok}"
        if coincidencia == "ninguno":
            ok = not any(_matchea(t) for t in textos)
            return ok, f"textos={len(textos)} ninguno_matchea={ok}"

        return False, f"coincidencia '{coincidencia}' no soportada"


class AnalizadorLista(Analizador):
    """Verifica que el texto de los nodos pertenezca a una lista permitida."""

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        parte = self.config.get("parte", "document")
        contexto = self.config.get("contexto", "todos")
        lista = self.config.get("lista", [])
        ignore_case = self.config.get("ignore_case", False)

        nodes = self._nodos(extracted, parte, contexto)
        textos = [text_of(n).strip() for n in nodes if text_of(n).strip()]
        if not textos:
            return False, "sin nodos de texto que evaluar"

        def _norm(s: str) -> str:
            s = re.sub(r"\s+", " ", s).strip()
            return s.lower() if ignore_case else s

        valores = [_norm(t) for t in textos]
        permitidos = [_norm(x) for x in lista]
        incumplen = [v for v in valores if v not in permitidos]
        return not incumplen, f"textos={valores[:3]} en_lista_faltan={incumplen[:3]}"


class AnalizadorImagen(Analizador):
    """Verifica la presencia (y cantidad) de imágenes embebidas."""

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        parte = self.config.get("parte", "document")
        contexto = self.config.get("contexto", "todos")
        minimo = self.config.get("cantidad_minima", 1)
        maximo = self.config.get("cantidad_maxima")

        nodes = self._nodos(extracted, parte, contexto)
        n = len(nodes)
        if n < minimo:
            return False, f"imágenes={n} mínimo={minimo}"
        if maximo is not None and n > maximo:
            return False, f"imágenes={n} máximo={maximo}"
        return True, f"imágenes={n} mínimo={minimo}"
