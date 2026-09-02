"""CLI de referencia para correr el validador localmente contra un DOCX.

Uso:
    python -m validator.cli tesis.docx unt_format_rules_schema.yaml
    python -m validator.cli tesis.docx unt_format_rules_schema.yaml --severity error
    python -m validator.cli tesis.docx unt_format_rules_schema.yaml --json
"""
import argparse
import json
import sys

from .engine import build_report, load_rules, validate_docx
from .prompts import build_ai_help_section


def main():
    parser = argparse.ArgumentParser(description="Validador de formato de tesis (UNT)")
    parser.add_argument("docx", help="Ruta al archivo .docx a validar")
    parser.add_argument("rules", help="Ruta al YAML de reglas")
    parser.add_argument(
        "--severity",
        choices=["error", "warning"],
        action="append",
        help="Filtra el reporte detallado por severidad (repetible). Por defecto muestra todas.",
    )
    parser.add_argument("--json", action="store_true", help="Imprime el reporte en JSON")
    args = parser.parse_args()

    rules_data = load_rules(args.rules)
    results = validate_docx(args.docx, rules_data)
    reporte = build_report(results, severities=args.severity)

    if args.json:
        reporte["como_preguntar_a_una_ia"] = build_ai_help_section(
            [r for r in results if not r.passed]
        )
        print(json.dumps(reporte, ensure_ascii=False, indent=2))
        return

    print(f"Semáforo: {reporte['semaforo'].upper()}")
    print(f"Total reglas evaluadas: {reporte['resumen']['total']}")
    print(f"  Errores fallidos:  {reporte['resumen']['fallidos_error']}")
    print(f"  Warnings fallidos: {reporte['resumen']['fallidos_warning']}")
    print()
    for r in reporte["resultados"]:
        estado = "OK  " if r["passed"] else f"FAIL[{r['severity']}]"
        print(f"{estado} {r['rule_id']}: {r['message']}")
        if not r["passed"]:
            print(f"      esperado:   {r['expected']}")
            print(f"      encontrado: {r['found']}")

    if reporte["semaforo"] == "rojo":
        sys.exit(1)


if __name__ == "__main__":
    main()
