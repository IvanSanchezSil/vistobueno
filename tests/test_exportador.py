"""Tests del exportador de reportes a Markdown y PDF (tarea 16).

Verifica que:
- `reporte_a_markdown` produzca encabezados, resumen y tabla con las reglas;
- el detalle de reglas fallidas aparezca (esperado/encontrado);
- `reporte_a_pdf` devuelva bytes de PDF válido (%PDF) no vacíos;
- `_main` exporte correctamente a .md y .pdf desde un JSON.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from validator.exportador import _main, reporte_a_markdown, reporte_a_pdf

REPORTE = {
    "semaforo": "rojo",
    "resultados": [
        {
            "rule_id": "papel_tamano",
            "passed": True,
            "severity": "error",
            "message": "El tamaño del papel debe ser A4",
            "expected": "210 x 297 mm",
            "found": "cumple",
            "location": 'Sección "Formato general"',
            "fuente": "MANUAL.docx",
            "cita": '"Tamaño A4"',
        },
        {
            "rule_id": "margen_superior",
            "passed": False,
            "severity": "error",
            "message": "El margen superior debe ser 2,5 cm",
            "expected": "2,5 cm",
            "found": "1,5 cm",
            "location": 'Sección "Formato general"',
            "fuente": "MANUAL.docx",
            "cita": '"Margen superior 2,5 cm"',
        },
    ],
    "resumen": {"total": 42, "fallidos_error": 1, "fallidos_warning": 0},
    "como_preguntar_a_una_ia": [
        {"rule_id": "margen_superior", "prompt": "¿Cómo corrijo el margen superior?"}
    ],
}


def test_markdown_contiene_semaforo_resumen_y_tabla():
    md = reporte_a_markdown(REPORTE)
    assert "# Reporte de validación" in md
    assert "ROJO" in md
    assert "Total de reglas evaluadas: **42**" in md
    assert "`papel_tamano`" in md
    assert "`margen_superior`" in md
    assert "✅ cumple" in md
    assert "❌ **falla**" in md


def test_markdown_detalla_reglas_fallidas():
    md = reporte_a_markdown(REPORTE)
    assert "## Detalle de reglas fallidas" in md
    assert "**Esperado:** 2,5 cm" in md
    assert "**Encontrado:** 1,5 cm" in md
    assert '**Ubicación:** Sección "Formato general"' in md


def test_markdown_incluye_prompt_ia():
    md = reporte_a_markdown(REPORTE)
    assert "## Cómo preguntar a una IA" in md
    assert "¿Cómo corrijo el margen superior?" in md


def test_pdf_devuelve_bytes_validos():
    pdf = reporte_a_pdf(REPORTE)
    assert isinstance(pdf, bytes)
    assert len(pdf) > 500
    assert pdf[:4] == b"%PDF"


def test_main_exporta_markdown_y_pdf(tmp_path: Path):
    reporte_json = tmp_path / "reporte.json"
    reporte_json.write_text(json.dumps(REPORTE, ensure_ascii=False), encoding="utf-8")
    md_out = tmp_path / "salida.md"
    sys.argv = ["exportador", str(reporte_json), str(md_out)]
    _main()
    assert "ROJO" in md_out.read_text(encoding="utf-8")

    pdf_out = tmp_path / "salida.pdf"
    sys.argv = ["exportador", str(reporte_json), str(pdf_out)]
    _main()
    assert pdf_out.read_bytes()[:4] == b"%PDF"


def test_main_rechaza_extension_desconocida(tmp_path: Path, capsys: pytest.CaptureFixture):
    reporte_json = tmp_path / "reporte.json"
    reporte_json.write_text(json.dumps(REPORTE), encoding="utf-8")
    sys.argv = ["exportador", str(reporte_json), str(tmp_path / "salida.txt")]
    with pytest.raises(SystemExit) as exc:
        _main()
    assert exc.value.code == 2
    assert "no soportada" in capsys.readouterr().out
