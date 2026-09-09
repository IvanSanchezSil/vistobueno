"""Linter del DSL de reglas (F4).

Valida la configuración de las reglas en TIEMPO DE CARGA: un error de
configuración debe fallar al COMPILAR, no al ejecutar contra un documento.

Detecta:
- regex inválida en cualquier campo `patron`/`filtro`;
- `comparacion` de atributo (eq/all_eq/contains) sin `esperado` o sin
  `atributo`;
- estados inalcanzables en autómatas (`automata_pila`) y estados
  duplicados / esquema vacío en `automata_secuencia`;
- ciclos épsilon (transiciones que no consumen y forman un ciclo): riesgo
  de bucle infinito en el reconocedor greedy de DFA/PDA.

El compilador invoca `linter_o_alzar` al principio de `compilar()`.
"""
from __future__ import annotations

import re
from typing import List

# Las mismas secciones que conoce el compilador (sin importarlo para
# evitar una dependencia circular: compilador -> dsl_check).
_SECCIONES = (
    "atributo_xml",
    "presencia_xml",
    "patron_texto",
    "lista_texto",
    "imagen",
    "automata_secuencia",
    "gramatica_estructura",
    "automata_pila",
    "patron_cantidad",
    "conteo_nodos",
    "lista_obligatoria",
    "hipervinculo_texto",
)

# Campos interpretados como expresiones regulares por los analizadores.
_CAMPOS_REGEX = ("patron", "filtro")


class DSLValidationError(ValueError):
    """Error en tiempo de carga: el DSL no pasa el linter."""


def _regex_invalida(valor: str) -> str:
    try:
        re.compile(valor)
    except re.error as e:
        return str(e)
    return ""


def _escanear_regex(config: dict, hallazgos: List[str], rule_id: str,
                    seccion: str, contexto: str = "") -> None:
    for clave in _CAMPOS_REGEX:
        valor = config.get(clave)
        if isinstance(valor, str) and valor:
            err = _regex_invalida(valor)
            if err:
                etiqueta = f"{seccion} ({contexto})" if contexto else seccion
                hallazgos.append(
                    f"[{rule_id}] {etiqueta}: regex inválida en '{clave}': {err}"
                )


def _lint_xml(config: dict, hallazgos: List[str], rule_id: str,
              seccion: str) -> None:
    comp = config.get("comparacion", "exists")
    if comp in ("eq", "all_eq", "contains"):
        if config.get("esperado") is None:
            hallazgos.append(
                f"[{rule_id}] {seccion}: 'comparacion: {comp}' requiere 'esperado'"
            )
        if not config.get("atributo"):
            hallazgos.append(
                f"[{rule_id}] {seccion}: 'comparacion: {comp}' requiere 'atributo'"
            )


def _lint_automata_secuencia(config: dict, hallazgos: List[str],
                             rule_id: str) -> None:
    estados = config.get("estados", [])
    if not estados:
        hallazgos.append(f"[{rule_id}] automata_secuencia: sin 'estados'")
        return
    nombres = [e.get("nombre") for e in estados if isinstance(e, dict)]
    duplicados = {n for n in nombres if nombres.count(n) > 1}
    if duplicados:
        hallazgos.append(
            f"[{rule_id}] automata_secuencia: estados duplicados {sorted(duplicados)}"
        )
    # Esquema "solo opcional": tras omitir los opcionales no queda ningún
    # estado obligatorio -> el DFA no tendría estado de aceptación.
    obligatorios = [e for e in estados if not e.get("opcional")]
    if not obligatorios:
        hallazgos.append(
            f"[{rule_id}] automata_secuencia: todos los estados son opcionales "
            "(sin estado de aceptación)"
        )
    for e in estados:
        if isinstance(e, dict):
            if not e.get("nombre"):
                hallazgos.append(f"[{rule_id}] automata_secuencia: estado sin 'nombre'")
            _escanear_regex(e, hallazgos, rule_id, "automata_secuencia",
                            e.get("nombre", ""))


def _lint_automata_pila(config: dict, hallazgos: List[str],
                        rule_id: str) -> None:
    transiciones = config.get("transiciones", [])
    if not transiciones:
        hallazgos.append(f"[{rule_id}] automata_pila: sin 'transiciones'")
        return

    inicial = config.get("inicial", "__inicio__")
    aceptacion = config.get("aceptacion", [])
    aristas: List[tuple] = []
    for t in transiciones:
        if not isinstance(t, dict):
            hallazgos.append(f"[{rule_id}] automata_pila: transición inválida {t!r}")
            continue
        if not t.get("patron"):
            hallazgos.append(
                f"[{rule_id}] automata_pila: transición {t.get('desde', '?')}"
                " sin 'patron'"
            )
        _escanear_regex(t, hallazgos, rule_id, "automata_pila", t.get("desde", ""))
        if "desde" in t and "hacia" in t:
            aristas.append((t["desde"], t["hacia"], bool(t.get("consumir", True))))

    # Alcance: nodos alcanzables desde el inicial.
    alcanzables = set()
    pila_nodos = [inicial]
    while pila_nodos:
        s = pila_nodos.pop()
        if s in alcanzables:
            continue
        alcanzables.add(s)
        for desde, hacia, _ in aristas:
            if desde == s and hacia not in alcanzables:
                pila_nodos.append(hacia)
    todos = {s for a in aristas for s in (a[0], a[1])}
    no_alcanzables = sorted(todos - alcanzables)
    if no_alcanzables:
        hallazgos.append(
            f"[{rule_id}] automata_pila: estados inalcanzables {no_alcanzables}"
        )
    acept_no_alcanzables = sorted((set(aceptacion) or set()) - alcanzables)
    if acept_no_alcanzables:
        hallazgos.append(
            f"[{rule_id}] automata_pila: aceptación inalcanzable {acept_no_alcanzables}"
        )

    # Ciclos épsilon: ciclos de transiciones que NO consumen -> el
    # reconocedor greedy iteraría sin avanzar la entrada.
    epsilon_ady = {}
    for desde, hacia, consumir in aristas:
        if not consumir:
            epsilon_ady.setdefault(desde, []).append(hacia)
    visitados = set()
    en_pila = set()

    def _ciclo(nodo: str) -> bool:
        if nodo in en_pila:
            return True
        if nodo in visitados:
            return False
        visitados.add(nodo)
        en_pila.add(nodo)
        for vecino in epsilon_ady.get(nodo, []):
            if _ciclo(vecino):
                return True
        en_pila.remove(nodo)
        return False

    if any(_ciclo(n) for n in list(epsilon_ady)):
        hallazgos.append(
            f"[{rule_id}] automata_pila: ciclo de transiciones épsilon "
            "(no consumen -> riesgo de bucle infinito)"
        )


def linter(rules_data: dict) -> List[str]:
    """Devuelve la lista de hallazgos (vacía si el DSL está sano)."""
    hallazgos: List[str] = []
    for rule in rules_data.get("reglas", []):
        rule_id = rule.get("id", "<sin id>")
        for seccion in _SECCIONES:
            cfg = rule.get(seccion)
            if cfg is None:
                continue
            configs = cfg if isinstance(cfg, list) else [cfg]
            for c in configs:
                if not isinstance(c, dict):
                    continue
                _escanear_regex(c, hallazgos, rule_id, seccion)
                if seccion in ("atributo_xml", "presencia_xml"):
                    _lint_xml(c, hallazgos, rule_id, seccion)
                elif seccion == "automata_secuencia":
                    _lint_automata_secuencia(c, hallazgos, rule_id)
                elif seccion == "automata_pila":
                    _lint_automata_pila(c, hallazgos, rule_id)
    return hallazgos


def linter_o_alzar(rules_data: dict) -> None:
    """Levanta `DSLValidationError` si el DSL tiene errores de carga."""
    hallazgos = linter(rules_data)
    if hallazgos:
        detalle = "\n  - ".join(hallazgos)
        raise DSLValidationError(
            f"{len(hallazgos)} error(es) de configuración DSL:\n  - {detalle}"
        )