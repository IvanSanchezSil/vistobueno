"""Genera, por cada RuleResult fallido, un bloque "cómo preguntar a una IA"
listo para copiar y pegar. Es puramente template-based: no llama a ningún
LLM en tiempo de ejecución, para que el prompt sugerido sea siempre
consistente y no dependa de que un modelo "recuerde" bien qué falló
(ver README, sección "Restricción de diseño clave").
"""

from .models import RULES_CENTINELA, RuleResult

# NM-07: una paráfrasis, un localizador o un derivado de plantilla no son una
# cita literal del reglamento. La etiqueta debe decir de dónde viene la
# referencia para no atribuir al manual texto que no aparece palabra por
# palabra en él. El valor por defecto (`literal`) conserva la etiqueta
# histórica; los demás valores los declara cada regla en el YAML.
_ETIQUETAS_ORIGEN = {
    "literal": "Cita del reglamento",
    "parafasis": "Paráfrasis del reglamento",
    "localizador": "Localizador en el reglamento",
    "plantilla": "plantilla institucional",
    "calidad_tecnica": "calidad técnica",
    "matriz_interna": "matriz de auditoría interna",
    "norma_institucional": "Norma institucional",
}

TEMPLATE = """Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:

- Regla incumplida: {message}
- Valor esperado según el reglamento: {expected}
- Lo que encontró el validador: {found}
{cita_line}
¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?"""


def build_prompt(result: RuleResult) -> str:
    if result.cita:
        etiqueta = _ETIQUETAS_ORIGEN.get(result.origen_cita, "Referencia")
        cita_line = f"- {etiqueta}: {result.cita}\n"
    else:
        cita_line = ""
    return TEMPLATE.format(
        message=result.message,
        expected=result.expected,
        found=result.found,
        cita_line=cita_line,
    )


def build_ai_help_section(results: list[RuleResult]) -> list[dict]:
    """Devuelve, por cada regla fallida, {rule_id, prompt} para la sección
    "cómo preguntar a una IA" del reporte. Incluye warnings, no solo errores
    — el estudiante puede querer corregirlos aunque no bloqueen la entrega.

    Excluye los resultados centinela (`RULES_CENTINELA`): no son reglas del
    YAML sino avisos del estado de la detección de tipo documental, y no se
    corrigen en Word (revisión PR #45, punto 4).
    """
    return [
        {"rule_id": r.rule_id, "prompt": build_prompt(r)}
        for r in results
        if not r.passed and r.rule_id not in RULES_CENTINELA
    ]
