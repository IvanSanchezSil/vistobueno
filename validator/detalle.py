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
- Los incumplimientos van con su posición (`#1`, `#2`, ...) y su valor, y
  se listan **todos**: no se pierde información en silencio. Si superan el
  tope, se dice cuántos más hay.
- El valor esperado y la tolerancia van al final.
- Cuando el valor tiene unidades conocidas (puntos, centímetros), se
  muestran en la unidad que entiende el estudiante, no en twips.

Cada motor pasa sus propios datos; este módulo solo formatea.
"""

from __future__ import annotations

MAX_INCUMPLIMIENTOS = 200
"""Tope de incumplimientos listados en un detalle (alto, para no perder
casos reales). Si se supera, el detalle dice cuántos más hay."""

MAX_TEXTO = 60
"""Máximo de caracteres por texto citado en el detalle."""


def _muestra(valores: list, unidad: str, factor: float) -> str:
    """Representación de los primeros valores leídos (los que ya se veían)."""
    return repr([_valor(v, unidad, factor) for v in valores[:3]])


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


def _unidad(config: dict) -> tuple[str, float]:
    """Unidad del valor leído según el xpath y el atributo de la comprobación.

    - `w:sz` / `w:szCs`: Word guarda medios puntos → se muestra en puntos.
    - `pgMar`, `pgSz`, `w:ind`: Word guarda twips → se muestra en cm.
    - Cualquier otro atributo: el valor crudo (texto, enumeraciones...).
    """
    xpath = str(config.get("xpath", ""))
    if "pgMar" in xpath or "pgSz" in xpath or "w:ind" in xpath:
        return "cm", 1 / 567.0
    if "w:sz" in xpath:
        return "pt", 0.5
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
    detalle = (
        f"{atributo}={_muestra(valores, unidad, factor)} de {len(valores)} valores; "
        f"{len(incumplimientos)} incumplen"
    )
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
    detalle = (
        f"textos={_muestra(valores, '', 1.0)} de {len(valores)} textos; "
        f"{len(incumplimientos)} en_lista_faltan"
    )
    if incumplimientos:
        items = [f"#{pos}={_texto_corto(texto)}" for pos, texto in incumplimientos]
        detalle += f": {_incidencias(items)}"
    return detalle


def detalle_jerarquia(fallos: list[str]) -> str:
    """Detalle de una comprobación de jerarquía (`automata_pila` y similar)."""
    if not fallos:
        return "jerarquia_ok"
    return "jerarquia_incorrecta; " + _incidencias(fallos)
