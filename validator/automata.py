"""Autómatas y gramáticas para el DSL declarativo de validación.

Contiene el DFA (autómata finito determinista) usado para reconocer
secuencias de títulos en el documento, y la gramática BNF ligera para
validar estructuras jerárquicas completas (parseador descendente
recursivo). Ambos se alimentan de las reglas definidas en el DSL YAML
(secciones `automata_secuencia` y `gramatica_estructura`).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# DFA — Autómata finito determinista
# ---------------------------------------------------------------------------


@dataclass
class Transicion:
    """Una transición entre dos estados del DFA.

    `patron` es una expresión regular que, al matchear el token actual
    del flujo de entrada, dispara la transición desde `desde` hacia `hacia`.
    Si `consumir` es True, la transición avanza el puntero de entrada.
    """
    desde: str
    hacia: str
    patron: str
    consumir: bool = True


class DFA:
    """Autómata finito determinista.

    Reconoce flujos de tokens (listas de strings). Recorre la entrada
    manteniendo un único estado vigente; cada token que matchea una
    transición dispara el cambio de estado. El autómata acepta si el
    estado final pertenece al conjunto de aceptación.
    """

    def __init__(
        self,
        estados: List[str],
        transiciones: List[Transicion],
        inicial: str,
        aceptacion: List[str],
        prefijos_parciales: bool = True,
        reconocimiento_backtracking: bool = False,
    ):
        self.estados = estados
        self.transiciones = transiciones
        self.inicial = inicial
        self.aceptacion = set(aceptacion)
        # Si True, el match se hace por prefijo normalizado (comportamiento
        # histórico de secuencia_titulos) en lugar de fullmatch estricto.
        self.prefijos_parciales = prefijos_parciales
        self.reconocimiento_backtracking = reconocimiento_backtracking

        # normalizar patrones una sola vez
        self._trans_comp: List[Tuple[str, str, re.Pattern, bool]] = []
        for t in transiciones:
            self._trans_comp.append(
                (t.desde, t.hacia, re.compile(_normalizar_patron(t.patron)), t.consumir)
            )

    def reconocer(self, tokens: List[str]) -> Tuple[bool, List[str]]:
        """Reconoce una secuencia de tokens (búsqueda greedy dirigida).

        Equivalente a `reconocer_con_backtracking` pero sin retroceso:
        en cuanto una transición encuentra un match consume el token y
        avanza. Más rápido, pero puede fallar si el mismo token hubiera
        tenido que interpretarse para una transición posterior.
        """
        if self.reconocimiento_backtracking:
            return self.reconocer_con_backtracking(tokens)

        if not self._trans_comp:
            return False, ["autómata sin transiciones"]

        estado = self.inicial
        pos = 0
        ruta: List[str] = [estado]

        while True:
            # Buscar una transición saliente del estado actual.
            progreso = False
            for desde, hacia, patron, consumir in self._trans_comp:
                if desde != estado:
                    continue
                if not consumir:
                    # Épsilon: omitir el estado sin consumir token.
                    estado = hacia
                    ruta.append(estado)
                    progreso = True
                    break
                # Búsqueda greedy desde `pos` para esta transición.
                found = None
                for k in range(pos, len(tokens)):
                    if _matchea_token(tokens[k], patron, self.prefijos_parciales):
                        found = k
                        break
                if found is not None:
                    estado = hacia
                    pos = found + 1
                    ruta.append(estado)
                    progreso = True
                    break
            if not progreso:
                break

        if estado in self.aceptacion:
            return True, []

        # Faltantes: las transiciones alcanzables desde el estado donde
        # quedamos estancados (patrones que esperábamos reconocer).
        pendiente = self._siguientes_aceptables(estado)
        return False, pendiente or ["secuencia incompleta"]

    def reconocer_con_backtracking(self, tokens: List[str]) -> Tuple[bool, List[str]]:
        """Reconocimiento con retroceso (estilo NFA simulado).

        Explora todas las interpretaciones posibles de los tokens: en cada
        estado prueba cada transición y, para las que consumen, cada token
        desde `pos` que la matchee. Acepta si existe algún camino que lleve
        a un estado de aceptación. Devuelve (aceptado, faltantes).
        """
        # cache de visitados (estado, pos) para acotar la búsqueda
        visitados = set()

        def _dfs(estado: str, pos: int) -> bool:
            if estado in self.aceptacion:
                return True
            clave = (estado, pos)
            if clave in visitados:
                return False
            visitados.add(clave)
            for desde, hacia, patron, consumir in self._trans_comp:
                if desde != estado:
                    continue
                if not consumir:
                    if _dfs(hacia, pos):
                        return True
                    continue
                for k in range(pos, len(tokens)):
                    if _matchea_token(tokens[k], patron, self.prefijos_parciales):
                        if _dfs(hacia, k + 1):
                            return True
            return False

        if _dfs(self.inicial, 0):
            return True, []

        # Reportar cuántos estados quedaron sin cubrir.
        alcanzables = set()
        for desde, hacia, patron, _ in self._trans_comp:
            if desde in self._reconocidos_en(tokens):
                alcanzables.add(patron.pattern)
        return False, sorted(alcanzables) or ["secuencia incompleta"]

    def _reconocidos_en(self, tokens: List[str]) -> set:
        """Estados que se pudieron alcanzar en algún camino (para reporte)."""
        alcanzados = {self.inicial}

        def _dfs(estado: str, pos: int):
            for desde, hacia, patron, consumir in self._trans_comp:
                if desde != estado:
                    continue
                if not consumir:
                    if hacia not in alcanzados:
                        alcanzados.add(hacia)
                        _dfs(hacia, pos)
                    continue
                for k in range(pos, len(tokens)):
                    if _matchea_token(tokens[k], patron, self.prefijos_parciales):
                        if hacia not in alcanzados:
                            alcanzados.add(hacia)
                            _dfs(hacia, k + 1)
                        break

        _dfs(self.inicial, 0)
        return alcanzados

    def _siguientes_aceptables(self, estado: str) -> List[str]:
        """Patrones alcanzables desde `estado` y que aún no reconocimos."""
        alcanzables: List[str] = []
        visitados: set = set()
        cola = [estado]
        while cola:
            s = cola.pop(0)
            if s in visitados:
                continue
            visitados.add(s)
            for desde, hacia, patron, _ in self._trans_comp:
                if desde == s:
                    if hacia in self.aceptacion or hacia not in visitados:
                        alcanzables.append(patron.pattern)
                        cola.append(hacia)
        return list(dict.fromkeys(alcanzables))


def _normalizar_patron(patron: str) -> str:
    """Convierte un patrón del DSL en un regex normalizado.

    Quita `.*` inicial/final redundantes y espacios múltiples.
    El origen puede ser texto literal (patrón) o una plantilla con
    metacaracteres. Se interpreta de forma permisiva.
    """
    patron = re.sub(r"\s+", " ", patron.strip())
    return patron


def _matchea_token(token: str, patron: re.Pattern, prefijos: bool) -> bool:
    """Matching del token contra el patrón.

    Con `prefijos=True` se acepta que el token comience con el patrón
    (o que el patrón comience con el token normalizado), lo que da
    tolerancia razonable a variantes de redacción de los títulos.
    """
    if prefijos:
        return bool(
            patron.search(token)
            or token[: min(len(token), 25)] == patron.pattern[: min(len(patron.pattern), 25)]
        )
    return bool(patron.fullmatch(token))


# ---------------------------------------------------------------------------
# Gramática BNF ligera — parseador descendente recursivo
# ---------------------------------------------------------------------------


@dataclass
class GramaticaEstructura:
    """Gramática BNF (sin contexto) para validar estructuras jerárquicas.

    Se define en el YAML con:
      reglas_sintacticas: lista de producciones "NT → SÍMBOLO+"
      terminales:         tokens atómicos (nombres de sección/marcador)
      no_terminales:      símbolos derivables
      inicio:             símbolo raíz

    El parser recorre los tokens del documento (headings normalizados) y
    comprueba que el flujo derive de `inicio` usando las producciones.
    """
    reglas_sintacticas: List[str]
    terminales: List[str]
    no_terminales: List[str]
    inicio: str

    _producciones: Dict[str, List[List[str]]] = field(default_factory=dict, init=False)

    def __post_init__(self):
        # Parsear producciones "NT → A B C"
        self._producciones = {}
        for prod in self.reglas_sintacticas:
            if "→" not in prod:
                continue
            izq, der = prod.split("→", 1)
            nt = izq.strip()
            alternativas = [alt.strip().split() for alt in der.split("|")]
            self._producciones[nt] = self._producciones.get(nt, []) + alternativas

    def derivaciones(self, simbolo: str) -> List[List[str]]:
        """Expande un símbolo en secuencias de terminales.

        Mantiene los no-terminales sin expandir en la primera pasada;
        la expansión completa ocurre en `analizar`.
        """
        return self._producciones.get(simbolo, [[simbolo]] if simbolo in self.terminales else [])

    def _termina_en(self, simbolo: str) -> List[List[str]]:
        """Expansión transitiva hasta terminales (con prof. limitada)."""
        if simbolo in self.terminales:
            return [[simbolo]]
        resultado: List[List[str]] = []
        for alt in self._producciones.get(simbolo, []):
            if all(s in self.terminales for s in alt):
                resultado.append(alt)
                continue
            # expandir el primer no-terminal no-terminal de la alternativa
            for i, s in enumerate(alt):
                if s not in self.terminales:
                    for sub in self._termina_en(s):
                        nueva = alt[:i] + sub + alt[i + 1:]
                        resultado.append(nueva)
                    break
        return resultado

    def secuencias_esperadas(self) -> List[List[str]]:
        """Todas las secuencias de terminales que la gramática puede producir."""
        return self._termina_en(self.inicio)

    def analizar(
        self, tokens: List[str], normalizar: bool = True
    ) -> Tuple[bool, List[str]]:
        """Comprueba si `tokens` (headings) sigue la gramática.

        Devuelve (aceptado, faltantes). `faltantes` son los terminales de
        las secuencias esperadas que no aparecen en ningún token.
        """
        norm_tokens = [_n(t) for t in tokens] if normalizar else list(tokens)

        secuencias = self.secuencias_esperadas()
        if not secuencias:
            return False, ["gramática vacía o mal definida"]

        # Un tokens debe cubrir (en orden) una de las secuencias esperadas.
        mejores_faltantes: Optional[List[str]] = None
        for seq in secuencias:
            faltantes = self._faltantes_en_secuencia(seq, norm_tokens)
            if not faltantes:
                return True, []
            if mejores_faltantes is None or len(faltantes) < len(mejores_faltantes):
                mejores_faltantes = faltantes

        return False, mejores_faltantes or ["estructura incompleta"]

    def _faltantes_en_secuencia(self, seq: List[str], tokens: List[str]) -> List[str]:
        """Ítems de `seq` que no aparecen como tokens (en orden)."""
        faltantes: List[str] = []
        pos = 0
        for item in seq:
            found = None
            for k in range(pos, len(tokens)):
                if _item_matchea_token(item, tokens[k]):
                    found = k
                    break
            if found is None:
                faltantes.append(item)
            else:
                pos = found + 1
        return faltantes


def _n(s: str) -> str:
    return re.sub(r"\s+", " ", s.upper().replace("(OPCIONAL)", " ").strip(" ."))


def _item_matchea_token(item: str, token: str) -> bool:
    item_n = _n(item)
    if item_n in token or token[:25] == item_n[:25]:
        return True
    tk = re.sub(r"[^A-ZÁÉÍÓÚÑ0-9]+", "", item_n)
    if tk and tk == re.sub(r"[^A-ZÁÉÍÓÚÑ0-9]+", "", token):
        return True
    return False
