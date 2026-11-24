"""Tests del resumen impreso por `scripts/reglas_activas.py` (RI-09).

El script debe repetir los conteos de `build_report()`, no inventar un total:
las reglas no aplicables no se cuentan como evaluadas y las capturas de la
ficha no se cuentan como reglas que se cumplen.
"""

import os
import subprocess
import sys
from pathlib import Path

from docx_factory import compilar_docx, configuracion_base

from validator.engine import build_report, load_rules, validate_docx

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "reglas_activas.py"


def test_el_script_repite_el_resumen_del_motor():
    """Los cinco conteos del script coinciden con los del reporte del motor."""
    ruta = compilar_docx(configuracion_base())
    try:
        resultados = validate_docx(ruta, load_rules("reglas_unt.yaml"))
        resumen = build_report(resultados)["resumen"]
        visibles = [r for r in resultados if r.aplicable and not r.captura]
        aprobadas = sum(1 for r in visibles if r.passed)
        entorno = dict(os.environ)
        entorno["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(RAIZ), entorno.get("PYTHONPATH", "")])
        )
        salida = subprocess.run(
            [sys.executable, str(SCRIPT), ruta],
            capture_output=True,
            text=True,
            cwd=RAIZ,
            env=entorno,
        )
    finally:
        Path(ruta).unlink(missing_ok=True)

    assert salida.returncode == 0, salida.stderr
    # Hay reglas de otros tipos de documento: el caso elegido las tiene y
    # por eso la diferencia entre catálogo y evaluadas no es trivial.
    assert resumen["reglas_no_aplicables"] > 0
    assert f"Reglas del catálogo (captura excluida): {resumen['total']}" in salida.stdout
    assert f"  - Evaluadas: {resumen['total_evaluadas']}" in salida.stdout
    assert f"  - No aplicables: {resumen['reglas_no_aplicables']}" in salida.stdout
    assert f"  - Errores: {resumen['fallidos_error']}" in salida.stdout
    assert f"  - Advertencias: {resumen['fallidos_warning']}" in salida.stdout
    assert f"  - Aprobadas: {aprobadas}" in salida.stdout
