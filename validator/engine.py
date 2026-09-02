"""Motor de reglas: carga el YAML, ejecuta las reglas mecanizadas contra
un DOCX extraído, y arma el reporte agrupado con filtro de severidad.
"""
from typing import Iterable, List, Optional

import yaml

from .checks import run_check
from .extractor import extract
from .models import RuleResult, Severity


def load_rules(yaml_path: str) -> dict:
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_docx(docx_path: str, rules_data: dict) -> List[RuleResult]:
    """Ejecuta todas las reglas con `mecanismo_verificable` contra un DOCX.

    Las reglas SIN mecanismo_verificable (contenido semántico: mínimos de
    referencias, extensión del resumen, sistema de citas, etc.) se omiten
    aquí — no son verificables por estructura de archivo. Ver la sección
    `no_deterministas` / reglas sin mecanismo del YAML.
    """
    extracted = extract(docx_path)
    results: List[RuleResult] = []

    for rule in rules_data.get("rules", []):
        mecanismo = rule.get("mecanismo_verificable")
        if not mecanismo:
            continue

        fallos = []
        for check in mecanismo["checks"]:
            try:
                ok, detalle = run_check(check, extracted, rule)
            except Exception as e:
                # Un check mal formado o un XML inesperado no debe tumbar
                # el resto del reporte — se registra como fallo con detalle.
                ok, detalle = False, f"error ejecutando check: {type(e).__name__}: {e}"
            if not ok:
                fallos.append(detalle)

        results.append(
            RuleResult(
                rule_id=rule["id"],
                passed=not fallos,
                severity=Severity(rule.get("severidad", "error")),
                message=rule.get("descripcion", rule["id"]),
                expected=str(rule.get("valor_esperado", "")),
                found="; ".join(fallos) if fallos else "cumple",
                location=rule.get("ubicacion"),
                fuente=rule.get("fuente", ""),
                cita=rule.get("cita", ""),
            )
        )

    return results


def filter_by_severity(
    results: Iterable[RuleResult], severities: Optional[List[str]] = None
) -> List[RuleResult]:
    """Filtra resultados por severidad. Si severities es None, no filtra."""
    if severities is None:
        return list(results)
    wanted = {Severity(s) for s in severities}
    return [r for r in results if r.severity in wanted]


def build_report(
    results: List[RuleResult], severities: Optional[List[str]] = None
) -> dict:
    """Arma el reporte final.

    El semáforo SIEMPRE se calcula sobre TODOS los resultados con
    severidad "error" (independiente del filtro de severidad del reporte
    detallado) — un filtro de visualización nunca debe poder ocultar un
    bloqueo real de la entrega.
    """
    hay_error_bloqueante = any(
        (not r.passed) and r.severity == Severity.ERROR for r in results
    )
    reporte_resultados = filter_by_severity(results, severities)

    return {
        "semaforo": "rojo" if hay_error_bloqueante else "verde",
        "resultados": [r.to_dict() for r in reporte_resultados],
        "resumen": {
            "total": len(results),
            "fallidos_error": sum(
                1 for r in results if not r.passed and r.severity == Severity.ERROR
            ),
            "fallidos_warning": sum(
                1 for r in results if not r.passed and r.severity == Severity.WARNING
            ),
        },
    }
