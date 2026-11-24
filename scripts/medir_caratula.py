#!/usr/bin/env python3
"""Mide el XPath de carátula antes y después de RI-07 sobre DOCX reales.

Para cada archivo informa el tiempo de validación completa con el motor
actual y con la implementación previa a RI-07, y comprueba que el reporte
(semáforo, resumen, resultados y ficha) sea idéntico. Es una herramienta de
medición: no modifica el motor ni el contrato.

Uso:
    python scripts/medir_caratula.py tesis.docx plantillas/*.docx
"""

import argparse
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from validator.engine import build_report, load_ficha_rules, load_rules, validate_docx  # noqa: E402
from validator.extractor import NS, ExtractedDocx  # noqa: E402


def xpath_anterior(self, parte, xpath_expr, contexto="todos"):
    """Copia de `ExtractedDocx.xpath()` antes de RI-07 (solo para medir)."""
    clave = (parte, contexto, xpath_expr)
    if clave in self._cache:
        return self._cache[clave]
    arboles = self._arboles(parte)
    if not arboles:
        raise ValueError(f"parte '{parte}' no disponible en este archivo")
    nodos = []
    for tree in arboles:
        nodos.extend(tree.xpath(xpath_expr, namespaces=NS))
    if contexto == "cuerpo":
        nodos = [n for n in nodos if self.is_cuerpo(n)]
    if contexto == "cuerpo_prosa":
        nodos = [n for n in nodos if self.is_cuerpo_prosa(n)]
    if contexto == "seccion_cuerpo":
        nodos = [n for n in nodos if self.es_seccion_cuerpo(n)]
    if contexto == "caratula":
        nodos = [n for n in nodos if self.is_caratula(n)]
    if contexto == "caratula_ficha":
        nodos = [n for n in nodos if self.is_caratula_ficha(n)]
    self._cache[clave] = nodos
    return nodos


def _validar(ruta: Path, reglas, ficha) -> tuple[float, dict]:
    inicio = time.perf_counter()
    resultados = validate_docx(str(ruta), reglas, ficha)
    elapsed = time.perf_counter() - inicio
    informe = build_report(resultados)
    return elapsed, {
        "semaforo": informe["semaforo"],
        "resumen": informe["resumen"],
        "resultados": [(r.rule_id, r.passed, r.severity.value, r.found) for r in resultados],
        "ficha": informe.get("ficha", {}),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("docx", type=Path, nargs="+", help="DOCX a medir.")
    args = parser.parse_args()

    reglas = load_rules(str(RAIZ / "reglas_unt.yaml"))
    ficha = load_ficha_rules(str(RAIZ / "reglas_ficha.yaml"))
    for ruta in args.docx:
        if not ruta.is_file():
            print(f"Error: el archivo {ruta} no existe", file=sys.stderr)
            return 1
        nuevo_t, nuevo = _validar(ruta, reglas, ficha)
        original = ExtractedDocx.xpath
        ExtractedDocx.xpath = xpath_anterior
        try:
            anterior_t, anterior = _validar(ruta, reglas, ficha)
        finally:
            ExtractedDocx.xpath = original
        print(f"=== {ruta.name} ===")
        print(f"  anterior: {anterior_t:.2f} s | actual: {nuevo_t:.2f} s")
        print(f"  semáforo: {nuevo['semaforo']} | resumen: {nuevo['resumen']}")
        print(f"  reporte idéntico: {nuevo == anterior}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
