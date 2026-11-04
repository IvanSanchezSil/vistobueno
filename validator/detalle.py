"""Formato único del detalle de las reglas (`encontrado`).

Una sola fuente de verdad para el texto que ve el estudiante: la usan el
motor legacy (`validator/checks.py`) y el DSL (`validator/analizadores.py`).
Así la paridad legacy↔DSL se mantiene literal (el test de paridad compara
el texto completo) y no hay dos copias del formateo.

Por qué existe (AUD-03): el detalle se armaba con los 3 primeros valores
(`vals[:3]`, `incumplen[:3]`), así que una regla que fallaba en todas las
líneas —por ejemplo la sangría— llegaba al frontend con 3 líneas de error
de las N que había, y además mostraba primero los valores conformes, que
esconden al culpable.

Reglas del formato:
- Los incumplimientos van PRIMERO, con su posición (`#1`, `#2`, ...) y su
  valor, y se listan **todos**: no se pierde información en silencio. Si
  superan el tope, se dice cuántos más hay.
- El conteo de incumplimientos sale de la misma comparación que produce el
  veredicto, así que el detalle nunca puede contradecir al semáforo (un
  detalle que dice "0 incumplen" en una regla que falla es un bug).
- El valor esperado y la tolerancia van al final.
- Cuando el valor tiene unidades conocidas (puntos, centímetros), se
  muestran en la unidad que entiende el estudiante, no en twips.

Cada motor pasa sus propios datos; este módulo solo compara y formatea.
"""

from __future__ import annotations

MAX_INCUMPLIMIENTOS = 200
"""Tope de incumplimientos listados en un detalle (alto, para no perder
casos reales). Si se supera, el detalle dice cuántos más hay."""

MAX_TEXTO = 60
"""Máximo de caracteres por texto citado en el detalle."""

UNIDAD_TWIPS_A_CM = 1 / 567.0
"""1 cm = 567 twips (Word guarda las medidas en twips)."""

UNIDAD_MEDIOS_PUNTOS_A_PT = 0.5
"""Word guarda `w:sz` en medios puntos (26 = 13 pt)."""


def _valor(valor: object, unidad: str, factor: float) -> str:
    """Formatea un valor con su unidad (si la tiene)."""
    if not unidad:
        return str(valor)
    try:
        numero = float(str(valor)) * factor
    except TypeError, ValueError:
        return str(valor)
    if unidad == "pt":
        return f"{numero:g} pt"
    return f"{numero:.2f} cm"


def _elemento_del_xpath(xpath: str) -> str:
    """Nombre local del elemento al que pertenece el atributo leído.

    Se toma el último paso del xpath (`.../w:pPr/w:ind` → `w:ind`), no una
    búsqueda de subcadena: un xpath que mencione `w:ind` dentro de un
    predicado no convierte el valor a centímetros.
    """
    paso = str(xpath).split("/")[-1]
    # Se quitan los predicados: "w:ind[1]" → "w:ind".
    paso = paso.split("[")[0]
    return paso.rsplit(":", 1)[-1]


def _unidad(config: dict) -> tuple[str, float]:
    """Unidad del valor leído según el elemento que lleva el atributo.

    - `sz` / `szCs`: Word guarda medios puntos → se muestra en puntos.
    - `pgMar`, `pgSz`, `ind`: Word guarda twips → se muestra en cm.
    - Cualquier otro atributo: el valor crudo (texto, enumeraciones...).
    """
    elemento = _elemento_del_xpath(config.get("xpath", ""))
    if elemento in ("sz", "szCs"):
        return "pt", UNIDAD_MEDIOS_PUNTOS_A_PT
    if elemento in ("pgMar", "pgSz", "ind"):
        return "cm", UNIDAD_TWIPS_A_CM
    return "", 1.0


def _incidencias(items: list[str]) -> str:
    """Une las incidencias sin truncar en silencio."""
    if not items:
        return ""
    if len(items) <= MAX_INCUMPLIMIENTOS:
        return ", ".join(items)
    faltan = len(items) - MAX_INCUMPLIMIENTOS
    return ", ".join(items[:MAX_INCUMPLIMIENTOS]) + f" (+{faltan} más)"


def _pagina(pagina: int | None) -> str:
    return f" (pág. {pagina})" if pagina else ""


def _texto_corto(texto: str) -> str:
    limpio = " ".join(str(texto).split())
    if len(limpio) <= MAX_TEXTO:
        return limpio
    return limpio[:MAX_TEXTO] + "…"


def evaluar_atributo(
    config: dict, pares: list[tuple[int, object, int | None]]
) -> tuple[bool, list[tuple[int, object, int | None]]]:
    """Compara los valores leídos con lo esperado (fuente única de verdad).

    `pares` son las tuplas `(posición, valor, página)` de los nodos leídos,
    en orden de documento. Devuelve `(pasó, incumplimientos)`.

    Los dos motores llaman a esta función, así que el veredicto y la lista
    de incumplimientos (y por lo tanto el conteo que muestra el detalle)
    no pueden divergir: una regla que falla siempre tiene al menos un
    incumplimiento nombrado, o el detalle dice que no había valores que
    comparar.
    """
    comp = config.get("comparacion", "exists")
    esperado = config.get("esperado")
    tolerancia = config.get("tolerancia")
    ignore_case = bool(config.get("ignore_case", False))
    con_valor = [p for p in pares if p[1] is not None]

    def _acepta(valor: object) -> bool:
        """Igualdad exacta, o con tolerancia numérica si la hay."""
        if tolerancia is None:
            return valor == esperado
        try:
            return abs(float(str(valor)) - float(str(esperado))) <= float(str(tolerancia))
        except TypeError, ValueError:
            return valor == esperado

    if comp == "eq":
        # La comparación evalúa SOLO el primer valor: el culpable es ese.
        if not con_valor:
            return False, []
        pos, valor, pagina = con_valor[0]
        if _acepta(valor):
            return True, []
        return False, [(pos, valor, pagina)]

    if comp == "all_eq":
        incumplen = [(i, v, p) for i, v, p in con_valor if not _acepta(v)]
        return (bool(con_valor) and not incumplen), incumplen

    if comp == "contains":

        def _contiene(valor: object) -> bool:
            if ignore_case:
                return str(esperado).lower() in str(valor).lower()
            return str(esperado) in str(valor)

        incumplen = [(i, v, p) for i, v, p in con_valor if not _contiene(v)]
        return (bool(con_valor) and not incumplen), incumplen

    raise ValueError(f"comparación '{comp}' no soportada")


def detalle_xml_atributo(
    config: dict,
    valores: list,
    incumplimientos: list[tuple[int, object, int | None]],
    esperado: object,
    tolerancia: object = None,
) -> str:
    """Detalle de una comparación de atributo XML (`atributo_xml`).

    `incumplimientos` son las tuplas `(posición, valor, página)` de los
    nodos que NO cumplen, en el orden en que aparecen en el documento.
    """
    unidad, factor = _unidad(config)
    atributo = config.get("atributo", "?")
    if not valores:
        # No se leyó ningún valor: no hay nada que comparar y la regla
        # falla. Decirlo evita el "0 incumplen" de una regla en rojo.
        detalle = f"{atributo}: sin valores que comparar"
    else:
        detalle = f"{atributo}: {len(valores)} valores evaluados, {len(incumplimientos)} incumplen"
        if incumplimientos:
            items = [
                f"#{pos}={_valor(val, unidad, factor)}{_pagina(pag)}"
                for pos, val, pag in incumplimientos
            ]
            detalle += f": {_incidencias(items)}"
    if tolerancia is not None:
        detalle += f"; tolerancia ±{_valor(tolerancia, unidad, factor)}"
    detalle += f"; esperado={_valor(esperado, unidad, factor)}"
    return detalle


def detalle_texto_regex(textos: list[str], incumplimientos: list[tuple[int, str]]) -> str:
    """Detalle de una comprobación por expresión regular (`patron_texto`)."""
    detalle = f"textos={len(textos)} textos; {len(incumplimientos)} incumplen"
    if incumplimientos:
        items = [f"#{pos}={_texto_corto(texto)}" for pos, texto in incumplimientos]
        detalle += f": {_incidencias(items)}"
    return detalle


def detalle_texto_lista(valores: list[str], incumplimientos: list[tuple[int, str]]) -> str:
    """Detalle de una comprobación por lista de valores permitidos (`lista_texto`)."""
    detalle = f"textos: {len(valores)} evaluados, {len(incumplimientos)} en_lista_faltan"
    if incumplimientos:
        items = [f"#{pos}={_texto_corto(texto)}" for pos, texto in incumplimientos]
        detalle += f": {_incidencias(items)}"
    return detalle


def detalle_jerarquia(fallos: list[str]) -> str:
    """Detalle de una comprobación de jerarquía (`automata_pila` y similar)."""
    if not fallos:
        return "jerarquia_ok"
    return "jerarquia_incorrecta; " + _incidencias(fallos)
