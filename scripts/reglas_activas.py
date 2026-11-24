#!/usr/bin/env python3
"""Script utility: lista las reglas que aplican a un DOCX y resume sus fallos.

Usa el motor de validación para el análisis, sin modificar el validador. Los
conteos salen del mismo `resumen` que produce `build_report()` (RI-09): las
reglas no aplicables no se cuentan entre las evaluadas y las reglas de
captura de la ficha no se cuentan como reglas que se cumplen.

Uso:
    python scripts/reglas_activas.py /ruta/al/documento.docx
"""

import argparse
import sys
from pathlib import Path

from validator.engine import build_report, load_rules, validate_docx
from validator.models import Severity

REGLAS_YAML_PATH = "reglas_unt.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lista las reglas activas y los fallos de un DOCX."
    )
    parser.add_argument("docx", type=Path, help="Ruta al archivo .docx a validar.")
    parser.add_argument(
        "--reglas",
        type=Path,
        default=Path(REGLAS_YAML_PATH),
        help=f"YAML de reglas (por defecto: {REGLAS_YAML_PATH}).",
    )
    args = parser.parse_args()

    if not args.docx.is_file():
        print(f"Error: el archivo {args.docx} no existe", file=sys.stderr)
        return 1

    reglas_data = load_rules(str(args.reglas))
    resultados = validate_docx(str(args.docx), reglas_data)
    resumen = build_report(resultados)["resumen"]

    # El resumen del motor ya excluye las capturas; para el detalle se
    # filtran también las reglas no aplicables (no se miraron, no pasaron).
    visibles = [r for r in resultados if r.aplicable and not r.captura]
    errores = [r for r in visibles if not r.passed and r.severity is Severity.ERROR]
    advertencias = [r for r in visibles if not r.passed and r.severity is Severity.WARNING]
    aprobadas = [r for r in visibles if r.passed]

    print(f"=== Reporte de reglas activas para: {args.docx.name} ===")
    print()
    print(f"Reglas del catálogo (captura excluida): {resumen['total']}")
    print(f"  - Evaluadas: {resumen['total_evaluadas']}")
    print(f"  - No aplicables: {resumen['reglas_no_aplicables']}")
    print(f"  - Errores: {resumen['fallidos_error']}")
    print(f"  - Advertencias: {resumen['fallidos_warning']}")
    print(f"  - Aprobadas: {len(aprobadas)}")

    if errores:
        print()
        print("Detalle de reglas Error:")
        for r in errores:
            print(f"  - [{r.rule_id}] {r.message}")

    if advertencias:
        print()
        print("Detalle de reglas Warning:")
        for r in advertencias:
            print(f"  - [{r.rule_id}] {r.message}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
