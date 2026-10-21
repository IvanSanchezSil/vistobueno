#!/usr/bin/env python3
"""Script utility: lista las reglas que aplicarían a un DOCX dado.

Usa el motor de validación para análisis, sin modificar el validador.
Uso: python scripts/reglas_activas.py /ruta/al/documento.docx
"""

import sys
import os

from validator.engine import validate_docx, load_rules
from validator.api import REGLAS_YAML_PATH

def main():
    if len(sys.argv) < 2:
        print("Uso: python scripts/reglas_activas.py /ruta/al/documento.docx")
        sys.exit(1)

    docx_path = sys.argv[1]

    if not os.path.exists(docx_path):
        print(f"Error: el archivo {docx_path} no existe")
        sys.exit(1)

    try:
        rules_data = load_rules(REGLAS_YAML_PATH)
        resultados = validate_docx(docx_path, rules_data)

        # Contar por severidad
        error_count = sum(1 for r in resultados if not r.passed and r.severity.name == "ERROR")
        warning_count = sum(1 for r in resultados if not r.passed and r.severity.name == "WARNING")
        passed_count = sum(1 for r in resultados if r.passed)

        print(f"=== Reporte de reglas activas para: {os.path.basename(docx_path)} ===")
        print(f"")
        print(f"Reglas evaluadas: {len(resultados)}")
        print(f"  - Errores: {error_count}")
        print(f"  - Advertencias: {warning_count}")
        print(f"  - Aprobadas: {passed_count}")
        print(f"")
        print("Detalle de reglas Error:")
        for r in resultados:
            if not r.passed and r.severity.name == "ERROR":
                print(f"  - [{r.rule_id}] {r.message}")
        print()
        print("Detalle de reglas Warning:")
        for r in resultados:
            if not r.passed and r.severity.name == "WARNING":
                print(f"  - [{r.rule_id}] {r.message}")
    except Exception as e:
        print(f"Error al procesar el documento: {e}")

if __name__ == "__main__":
    main()
