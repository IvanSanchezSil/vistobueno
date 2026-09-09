"""Analizadores de hoja para el DSL declarativo.

Definen la clase base `Analizador` y los analizadores atómicos:
- AnalizadorXML: atributos y presencia de nodos XML (xpath).
- AnalizadorRegex: patrones de texto sobre el contenido del documento.
- AnalizadorLista: pertenencia a una lista de valores permitidos.
- AnalizadorConteoNodos: contador genérico de nodos / párrafos (conteo_nodos).
- AnalizadorImagen: presencia de imágenes (blips) — subclase del anterior.
- AnalizadorCantidadPatron: cuenta palabras/matches/entradas (patron_cantidad).
- AnalizadorListaObligatoria: ítems obligatorios en una sección (lista_obligatoria).
- AnalizadorHipervinculo: hipervínculos que matchean un patrón (hipervinculo_texto).

Los analizadores de tipo compuesto (secuencia, gramática, pila) viven en
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
from .tokenizer import PARRAFO, seccion, tokenizar

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
                # Sin strip para preservar el comportamiento del motor legacy
                # (checks.run_check usa `patron.fullmatch` sobre el w:t tal cual).
                return bool(rx.fullmatch(s))
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


class AnalizadorConteoNodos(Analizador):
    """Cuenta nodos (XPath) o párrafos de una sección y compara min/máx.

    Es el contador genérico para `conteo_nodos` (F3). Si la config lleva
    `seccion`, cuenta los PÁRRAFOS no vacíos de esa sección vía el
    tokenizer en lugar de XPath (p. ej. referencias mínimas).
    """

    def _etiqueta(self) -> str:
        return self.config.get("label", "nodos")

    def _cuenta(self, extracted: ExtractedDocx) -> int:
        sec = self.config.get("seccion")
        if sec:
            corte = seccion(tokenizar(extracted), sec["inicio"], sec.get("fin"))
            return sum(1 for t in corte if t.tipo == PARRAFO and t.texto.strip())
        nodos = self._nodos(
            extracted,
            self.config.get("parte", "document"),
            self.config.get("contexto", "todos"),
        )
        return len(nodos)

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        minimo = self.config.get("cantidad_minima", 1)
        maximo = self.config.get("cantidad_maxima")
        multiples = self.config.get("cantidades_multiples")
        n = self._cuenta(extracted)
        etq = self._etiqueta()
        if multiples:
            # Se cumple si la cantidad alcanza CUALQUIER mínimo declarado
            # (p. ej. mínimo según tipo de investigación: [20, 30, 20]).
            ok = any(n >= m for m in multiples)
            return ok, f"{etq}={n} minimos={multiples}"
        if n < minimo:
            return False, f"{etq}={n} minimo={minimo}"
        if maximo is not None and n > maximo:
            return False, f"{etq}={n} maximo={maximo}"
        return True, f"{etq}={n} minimo={minimo}"


class AnalizadorImagen(AnalizadorConteoNodos):
    """Verifica la presencia (y cantidad) de imágenes embebidas.

    Misma semántica que el legacy `imagen_presencia` (checks.run_check):
    detalle `imagenes=N minimo=M`. Es un caso particular de
    `AnalizadorConteoNodos` con etiqueta "imagenes".
    """

    def _etiqueta(self) -> str:
        return "imagenes"


class AnalizadorCantidadPatron(Analizador):
    r"""Cuenta palabras, matches de regex o entradas en una sección/texto.

    Sección DSL `patron_cantidad` (F3). `operacion`:
      count_words   — palabras (`\w+`) del texto contado
      count_matches — matches de `patron`
      count_entries — entradas separadas por ',' o ';' del texto tras
                      el primer ':' (p. ej. "Palabras clave: a, b, c").
    El texto contado proviene de una `seccion` (tokenizer + `filtro`
    opcional por párrafo) o de nodos XPath.
    """

    def _piezas(self, extracted: ExtractedDocx) -> List[str]:
        sec = self.config.get("seccion")
        xpath_cfg = self.config.get("xpath")
        if sec:
            corte = seccion(tokenizar(extracted), sec["inicio"], sec.get("fin"))
            piezas = [t.texto for t in corte if t.tipo == PARRAFO and t.texto.strip()]
        elif xpath_cfg:
            nodos = self._nodos(
                extracted,
                self.config.get("parte", "document"),
                self.config.get("contexto", "todos"),
            )
            piezas = [text_of(n).strip() for n in nodos if text_of(n).strip()]
        else:
            return []
        filtro = self.config.get("filtro")
        if filtro:
            rx = re.compile(
                filtro, re.IGNORECASE if self.config.get("ignore_case", True) else 0
            )
            piezas = [p for p in piezas if rx.search(p)]
        return piezas

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        operacion = self.config.get("operacion", "count_words")
        minimo = self.config.get("cantidad_minima", 1)
        maximo = self.config.get("cantidad_maxima")
        texto = " ".join(self._piezas(extracted))

        if operacion == "count_words":
            n = len(re.findall(r"\w+", texto))
            detalle = f"palabras={n}"
        elif operacion == "count_matches":
            patron = self.config.get("patron", "")
            flags = re.IGNORECASE if self.config.get("ignore_case", False) else 0
            n = len(re.findall(patron, texto, flags))
            detalle = f"matches={n}"
        elif operacion == "count_entries":
            cuerpo = texto.split(":", 1)[1] if ":" in texto else texto
            n = len([x for x in re.split(r"[,;]", cuerpo) if x.strip()])
            detalle = f"entradas={n}"
        else:
            return False, f"operación '{operacion}' no soportada"

        if n < minimo:
            return False, f"{detalle} minimo={minimo}"
        if maximo is not None and n > maximo:
            return False, f"{detalle} maximo={maximo}"
        return True, f"{detalle} minimo={minimo}"


class AnalizadorListaObligatoria(Analizador):
    """Verifica que cada ítem de `items` aparezca en la sección/texto.

    Sección DSL `lista_obligatoria` (F3) para anexos mínimos: substring
    normalizado (colapso de whitespace y, por defecto, ignore_case).
    """

    def _texto(self, extracted: ExtractedDocx) -> str:
        sec = self.config.get("seccion")
        if sec:
            corte = seccion(tokenizar(extracted), sec["inicio"], sec.get("fin"))
            return " ".join(t.texto for t in corte if t.tipo == PARRAFO)
        nodos = self._nodos(
            extracted,
            self.config.get("parte", "document"),
            self.config.get("contexto", "todos"),
        )
        return " ".join(text_of(n) for n in nodos)

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        items = self.config.get("items", [])
        texto = self._texto(extracted)
        ignore = self.config.get("ignore_case", True)

        def _norm(s: str) -> str:
            s = re.sub(r"\s+", " ", s).strip()
            return s.lower() if ignore else s

        texto_norm = _norm(texto)
        faltan = [it for it in items if _norm(it) not in texto_norm]
        if not faltan:
            return True, f"items_obligatorios={len(items)} completo"
        return False, f"items_obligatorios={len(items)} faltan={faltan[:8]}"


class AnalizadorHipervinculo(Analizador):
    """Detecta hipervínculos (w:hyperlink) cuyo texto coincida con un patrón.

    Sección DSL `hipervinculo_texto` (F3), p. ej. ORCID:
    `https://orcid.org/XXXXXXXXXXXXXXXX` (16 dígitos).
    """

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        parte = self.config.get("parte", "document")
        contexto = self.config.get("contexto", "todos")
        patron = self.config.get("patron", "")
        ignore_case = self.config.get("ignore_case", True)
        minimo = self.config.get("cantidad_minima", 1)
        maximo = self.config.get("cantidad_maxima")

        nodos = self._nodos(extracted, parte, contexto)
        rx = re.compile(patron, re.IGNORECASE if ignore_case else 0)
        coinciden = [n for n in nodos if rx.search(text_of(n))]
        n = len(coinciden)
        if n < minimo:
            return False, f"hipervinculos={n} minimo={minimo}"
        if maximo is not None and n > maximo:
            return False, f"hipervinculos={n} maximo={maximo}"
        return True, f"hipervinculos={n} minimo={minimo}"
