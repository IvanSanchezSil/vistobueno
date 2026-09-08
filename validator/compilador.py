"""Compilador del DSL declarativo de reglas.

Convierte el YAML de reglas (formato DSL) en una colección de
`Analizador` ejecutables y los corre contra un `ExtractedDocx` para
producir `List[RuleResult]` — el mismo contrato que el motor legacy.

Formato DSL (la regla puede declarar cualquiera de estas secciones, y
**todas** deben cumplirse para que la regla pase):

    atributo_xml / presencia_xml -> AnalizadorXML
    patron_texto                -> AnalizadorRegex
    lista_texto                 -> AnalizadorLista
    imagen                      -> AnalizadorImagen
    automata_secuencia          -> AutomataSecuencia (DFA)
    gramatica_estructura        -> GramaticaEstructura (BNF)

La regla también conserva metadatos (descripcion, severidad, etc.) que
se propagan al `RuleResult` resultante.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from .analizadores import (
    Analizador,
    AnalizadorImagen,
    AnalizadorLista,
    AnalizadorRegex,
    AnalizadorXML,
)
from .automata import DFA, GramaticaEstructura, Transicion
from .extractor import ExtractedDocx, W, NS, text_of
from .models import RuleResult, Severity

# Secciones del DSL que indican que una regla es verificable.
SECCIONES_ANALIZADOR = (
    "atributo_xml",
    "presencia_xml",
    "patron_texto",
    "lista_texto",
    "imagen",
    "automata_secuencia",
    "gramatica_estructura",
)


# ---------------------------------------------------------------------------
# AutomataSecuencia con interfaz Analizador (se usa a través del DSL)
# ---------------------------------------------------------------------------


class AutomataSecuencia(Analizador):
    """Reconoce una secuencia de títulos usando un DFA.

    Construye el autómata a partir de `automata_secuencia.estados`,
    `inicial` y `aceptacion`. Cada estado es un patrón (regex sobre el
    heading normalizado) que, al ser reconocido, transita al siguiente.
    """

    def __init__(self, config: dict):
        super().__init__(config)
        self.nivel_titulo: List[int] = config.get("nivel_titulo", [1, 2, 3])
        self.normalizacion: List[str] = config.get("normalizacion", [])
        self.reconocimiento: str = config.get("reconocimiento", "greedy")

    def _build_dfa(self, estados_cfg: list) -> DFA:
        estados: List[str] = []
        transiciones: List[Transicion] = []
        aceptacion: List[str] = []

        # Estado previo obligatorio — los opcionales se omiten por completo
        # (comportamiento del motor legacy: los "(OPCIONAL)" simplemente no
        # se exigen). El ítem inicial del DFA es "__inicio__".
        origen = "__inicio__"
        for e in estados_cfg:
            if e.get("opcional"):
                continue
            estados.append(e["nombre"])
            transiciones.append(
                Transicion(
                    desde=origen,
                    hacia=e["nombre"],
                    patron=e.get("patron", e["nombre"]),
                    consumir=True,
                )
            )
            origen = e["nombre"]

        # Aceptación SOLO en el último estado obligatorio: llegar a él
        # implica que todos los anteriores fueron reconocidos en orden.
        aceptacion = [origen] if estados else []

        return DFA(
            estados=estados,
            transiciones=transiciones,
            inicial="__inicio__",
            aceptacion=aceptacion,
            reconocimiento_backtracking=self.reconocimiento == "backtracking",
        )

    def _headings(self, extracted: ExtractedDocx) -> List[str]:
        doc = extracted.document
        textos: List[str] = []
        for p in doc.xpath("//w:body//w:p", namespaces=NS):
            val = None
            pPr = p.find(W + "pPr")
            st = pPr.find(W + "pStyle") if pPr is not None else None
            if st is not None:
                val = st.get(W + "val")
            if val and ("eading" in val or "tulo" in val):
                textos.append(text_of(p).strip())
        return textos

    def _normalizar(self, s: str) -> str:
        if "mayusculas" in self.normalizacion:
            s = s.upper()
        if "ignorar_indent" in self.normalizacion:
            s = s.strip()
        s = re.sub(r"\s+", " ", s.replace("(OPCIONAL)", " ").strip(" ."))
        return s

    def _caratula_ok(self, extracted: ExtractedDocx) -> bool:
        """La carátula se satisface con el primer párrafo que contenga
        'universidad' (no usa estilo de encabezado)."""
        doc = extracted.document
        for p in doc.xpath("//w:body/w:p", namespaces=NS):
            t = text_of(p).strip()
            if t:
                return "universidad" in t.lower()
        return False

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        estados_cfg = self.config.get("estados", [])
        if not estados_cfg:
            return False, "sin estados definidos en automata_secuencia"

        # Satisface la carátula automáticamente si el primer párrafo del
        # documento menciona "universidad" (cover_ok del motor legacy).
        cover_nombres = {"carátula", "caratula"}
        if any(e.get("nombre", "").lower() in cover_nombres for e in estados_cfg):
            cover_ok = self._caratula_ok(extracted)
            estados_activos = [
                e for e in estados_cfg
                if not (e.get("nombre", "").lower() in cover_nombres)
            ]
        else:
            cover_ok = False
            estados_activos = estados_cfg

        dfa = self._build_dfa(estados_activos)

        headings = [self._normalizar(t) for t in self._headings(extracted) if t]
        aceptado, faltantes = dfa.reconocer(headings)
        if cover_ok:
            # La carátula fue satisfecha por detección de párrafo.
            faltantes = [f for f in faltantes if f.lower() not in cover_nombres]

        if aceptado:
            return True, f"headings={len(headings)} secuencia_ok"
        return False, f"headings={len(headings)} faltantes={faltantes[:6]}"


class GramaticaEstructuraAnalizador(Analizador):
    """Envuelve `GramaticaEstructura` como un Analizador del DSL."""

    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]:
        cfg = self.config
        gramatica = GramaticaEstructura(
            reglas_sintacticas=cfg.get("reglas_sintacticas", []),
            terminales=cfg.get("terminales", []),
            no_terminales=cfg.get("no_terminales", []),
            inicio=cfg.get("inicio", ""),
        )

        doc = extracted.document
        headings: List[str] = []
        for p in doc.xpath("//w:body//w:p", namespaces=NS):
            val = None
            pPr = p.find(W + "pPr")
            st = pPr.find(W + "pStyle") if pPr is not None else None
            if st is not None:
                val = st.get(W + "val")
            if val and ("eading" in val or "tulo" in val):
                headings.append(text_of(p).strip())

        aceptado, faltantes = gramatica.analizar(headings)
        if aceptado:
            return True, f"headings={len(headings)} gramática_ok"
        return False, f"headings={len(headings)} faltantes={faltantes[:6]}"


# ---------------------------------------------------------------------------
# Compilador
# ---------------------------------------------------------------------------

# Mapeo de sección del DSL -> fábrica de Analizador.
_FABRICAS = {
    "atributo_xml": AnalizadorXML,
    "presencia_xml": AnalizadorXML,
    "patron_texto": AnalizadorRegex,
    "lista_texto": AnalizadorLista,
    "imagen": AnalizadorImagen,
    "automata_secuencia": AutomataSecuencia,
    "gramatica_estructura": GramaticaEstructuraAnalizador,
}


@dataclass
class ReglaCompilada:
    """Una regla DSL compilada: sus analizadores + metadatos."""

    rule: dict
    analizadores: List[Analizador] = field(default_factory=list)

    def ejecutar(self, extracted: ExtractedDocx) -> RuleResult:
        fallos: List[str] = []
        for an in self.analizadores:
            try:
                ok, detalle = an.analizar(extracted)
            except Exception as e:  # noqa:BLE001
                ok, detalle = False, f"error ejecutando analizador: {type(e).__name__}: {e}"
            if not ok:
                fallos.append(detalle)

        esperados = self.rule.get("valor_esperado", "")
        if isinstance(esperados, list):
            esperados = "; ".join(map(str, esperados))
        return RuleResult(
            rule_id=self.rule["id"],
            passed=not fallos,
            severity=Severity(self.rule.get("severidad", "error")),
            message=self.rule.get("descripcion", self.rule["id"]),
            expected=str(esperados),
            found="; ".join(fallos) if fallos else "cumple",
            location=self.rule.get("ubicacion"),
            fuente=self.rule.get("fuente", ""),
            cita=self.rule.get("cita", ""),
        )


class CompilerDSL:
    """Compila el YAML DSL en un conjunto de `ReglaCompilada`."""

    def compilar(self, rules_data: dict) -> List[ReglaCompilada]:
        reglas: List[ReglaCompilada] = []
        for rule in rules_data.get("reglas", []):
            analizadores = []
            for seccion in SECCIONES_ANALIZADOR:
                if seccion in rule:
                    fabrica = _FABRICAS.get(seccion)
                    if fabrica is None:
                        continue
                    analizadores.append(fabrica(rule[seccion]))
            if not analizadores:
                # Regla declarada pero sin analizadores: no mecanizada.
                continue
            reglas.append(ReglaCompilada(rule=rule, analizadores=analizadores))
        return reglas

    def ejecutar(self, rules_data: dict, extracted: ExtractedDocx) -> List[RuleResult]:
        return [r.ejecutar(extracted) for r in self.compilar(rules_data)]
