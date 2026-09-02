"""Validador de formato de tesis (UNT) — motor de reglas de producción.

Re-arquitecturado a partir del prototipo `eval_checks2.py`: separa
extracción del DOCX, ejecución de checks, y agregación de reporte en
módulos independientes, y agrega filtro de severidad al reporte.

Uso típico:

    from validator.engine import load_rules, validate_docx, build_report

    rules = load_rules("unt_format_rules_schema.yaml")
    resultados = validate_docx("tesis.docx", rules)
    reporte = build_report(resultados)                      # sin filtrar
    reporte_solo_errores = build_report(resultados, severities=["error"])
"""
