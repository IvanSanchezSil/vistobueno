#!/usr/bin/env python3
"""Verifica por paridad exacta el motor legacy vs el DSL contra DOCX reales.

Mismo objetivo que tests/test_paridad_formatos.py pero sobre los archivos
reales de `recursos/` (plantillas oficiales y manual). Fase F1: confirma
que `reglas_unt.yaml` (generado por scripts/migrar_legacy_a_dsl.py) se
comporta idéntico a `unt_format_rules_schema.yaml` pese a no ser el YAML
que carga la API.

Para cada .docx ejecuta ambos formatos y compara, regla por regla,
`passed` y `found`. Salida 0 si todo coincide; ≠ 0 si hay diferencias.

Uso:
    python scripts/evaluar_paridad_plantillas.py [carpeta]
    # por defecto: recursos/ (plantillas y manual)
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from validator.engine import load_rules, validate_docx  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent


def main() -> None:
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "recursos"

    legacy_data = load_rules(str(RAIZ / "unt_format_rules_schema.yaml"))
    dsl_data = load_rules(str(RAIZ / "reglas_unt.yaml"))

    docs = sorted(carpeta.rglob("*.docx"))
    if not docs:
        print(f"No se encontraron .docx en {carpeta}")
        return

    errores_totales = 0
    for docx_path in docs:
        try:
            legacy = {r.rule_id: r for r in validate_docx(str(docx_path), legacy_data)}
            dsl = {r.rule_id: r for r in validate_docx(str(docx_path), dsl_data)}
        except Exception as e:  # noqa: BLE001
            print(f"== {docx_path.name[:60]}  ERROR ejecutando: {type(e).__name__}: {e}")
            errores_totales += 1
            continue

        if not set(legacy) <= set(dsl):
            print(f"== {docx_path.name[:60]}  CONJUNTOS DISTINTOS (faltan reglas legacy en el DSL)")
            errores_totales += 1
            continue

        diffs = []
        for rid in sorted(legacy):
            l, d = legacy[rid], dsl[rid]
            if l.passed != d.passed or l.found != d.found:
                diffs.append(f"    {rid}: legacy={l.found!r} dsl={d.found!r} (passed {l.passed})")

        fallos = sum(1 for r in legacy.values() if not r.passed)
        estado = "OK" if not diffs else f"{len(diffs)} DIFERENCIAS"
        print(f"== {docx_path.name[:60]}  PASS {len(legacy) - fallos}/{len(legacy)}  [{estado}]")
        for d in diffs:
            print(d)
        errores_totales += len(diffs)

    print()
    print("PARIDAD: OK" if errores_totales == 0 else f"PARIDAD: {errores_totales} error(es)")
    sys.exit(1 if errores_totales else 0)


if __name__ == "__main__":
    main()