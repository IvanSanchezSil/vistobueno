"""Genera, por cada RuleResult fallido, un bloque "cómo preguntar a una IA"
listo para copiar y pegar. Es puramente template-based: no llama a ningún
LLM en tiempo de ejecución, para que el prompt sugerido sea siempre
consistente y no dependa de que un modelo "recuerde" bien qué falló
(ver README, sección "Restricción de diseño clave").
"""
from typing import List

from .models import RuleResult

TEMPLATE = """Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:

- Regla incumplida: {message}
- Valor esperado según el reglamento: {expected}
- Lo que encontró el validador: {found}
{cita_line}
¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?"""


def build_prompt(result: RuleResult) -> str:
    cita_line = f"- Cita del reglamento: {result.cita}\n" if result.cita else ""
    return TEMPLATE.format(
        message=result.message,
        expected=result.expected,
        found=result.found,
        cita_line=cita_line,
    )


def build_ai_help_section(results: List[RuleResult]) -> List[dict]:
    """Devuelve, por cada regla fallida, {rule_id, prompt} para la sección
    "cómo preguntar a una IA" del reporte. Incluye warnings, no solo errores
    — el estudiante puede querer corregirlos aunque no bloqueen la entrega."""
    return [
        {"rule_id": r.rule_id, "prompt": build_prompt(r)}
        for r in results
        if not r.passed
    ]
