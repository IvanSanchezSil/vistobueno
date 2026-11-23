"""Regresiones de M12g / NM-07: procedencia honesta de las citas.

NM-07 distingue cuatro orígenes que hoy se presentan igual bajo la etiqueta
«Cita del reglamento»:

- cita literal del manual;
- paráfrasis o localizador (no son citas literales);
- derivado de plantillas institucionales;
- control de calidad técnica sin mandato literal en el manual.

El campo interno `origen_cita` NO se expone en la API: solo cambia la forma
de presentar la referencia en prompts y mensajes. Estas pruebas fallan antes
del arreglo.

Uso:
    pytest tests/test_m12g_origen_reglas.py -v
"""

from __future__ import annotations

import copy
import sys
from pathlib import Path

import pytest
import yaml

from validator.compilador import CompilerDSL
from validator.dsl_check import linter
from validator.models import RuleResult, Severity
from validator.prompts import build_prompt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

ORIGENES_ESPERADOS = {
    "deteccion_tipo_documento": "parafasis",
    "estructura_tinv_cuantitativo": "localizador",
    "estructura_tinv_cualitativo": "localizador",
    "estructura_tinv_revision_literatura": "localizador",
    "anexos_minimos_cuantitativo": "localizador",
    "anexos_minimos_cualitativo": "localizador",
    "alineacion_caratula_todos_elementos": "parafasis",
    "numeracion_preliminares_romano": "parafasis",
    "caratula_asesor_negrita": "parafasis",
    "resumen_longitud": "parafasis",
    "caratula_orcid": "parafasis",
    "indice_paginas_separadas": "localizador",
    "abstract_contenido": "matriz_interna",
    "caratula_linea_investigacion": "norma_institucional",
    "encabezado_membrete": "plantilla",
    "encabezado_formato": "plantilla",
    "notas_al_pie_consistencia": "calidad_tecnica",
    "track_changes_sin_resolver": "calidad_tecnica",
}

# Citas que hoy se presentan como literales pero están recortadas con
# elipsis o «etc.», o no llevan comillas: deben declarar otro origen.
REGLAS_NO_LITERALES = set(ORIGENES_ESPERADOS)

DOCS_CON_CONTEO_46 = (
    "docs/CAMBIOS_MOTOR_DSL.md",
    "docs/diseno/15_tipo_documento_grupos.md",
    "docs/pruebas/INFORME_diagnostico_conversion_pdf.md",
    "docs/pruebas/MENSAJE_para_companero.md",
    "docs/AUDITORIA_NORMATIVA_2026-11-12.md",
    "docs/HANDOVER_CORRECTITUD_INT3_2026-11-12.md",
)


def _yaml() -> dict:
    return yaml.safe_load((ROOT / "reglas_unt.yaml").read_text(encoding="utf-8"))


def _por_id(datos: dict) -> dict:
    return {r["id"]: r for r in datos["reglas"]}


def _resultado(**extra) -> RuleResult:
    base = {
        "rule_id": "regla_prueba",
        "passed": False,
        "severity": Severity.WARNING,
        "message": "Regla de prueba",
        "expected": "valor esperado",
        "found": "valor encontrado",
        "cita": "Texto de referencia",
    }
    base.update(extra)
    return RuleResult(**base)


class TestOrigenDeclarado:
    def test_reglas_sensibles_declaran_su_origen(self):
        reglas = _por_id(_yaml())
        faltan = sorted(set(ORIGENES_ESPERADOS) - set(reglas))
        assert not faltan, f"reglas ausentes del YAML: {faltan}"
        for rule_id, esperado in ORIGENES_ESPERADOS.items():
            assert reglas[rule_id].get("origen_cita") == esperado, rule_id

    def test_las_demas_reglas_siguen_siendo_literales_por_defecto(self):
        reglas = _por_id(_yaml())
        declaradas = {k for k, r in reglas.items() if "origen_cita" in r}
        # Las reglas señaladas por NM-07 declaran su origen; el resto usa el
        # valor por defecto `literal`, sin tocar su texto ni la API.
        assert declaradas == REGLAS_NO_LITERALES

    def test_linter_rechaza_origen_desconocido(self):
        datos = copy.deepcopy(_yaml())
        datos["reglas"][0]["origen_cita"] = "inventado"
        hallazgos = linter(datos)
        assert any("origen_cita:" in h and "no es válido" in h for h in hallazgos), hallazgos

    def test_linter_rechaza_cita_literal_recortada(self):
        datos = copy.deepcopy(_yaml())
        regla = _por_id(datos)["fuente_principal"]
        regla["origen_cita"] = "literal"
        regla["cita"] = '"Times New Roman: 12 puntos..."'
        hallazgos = linter(datos)
        assert any("elipsis" in h for h in hallazgos), hallazgos

    def test_linter_acepta_el_yaml_real(self):
        assert linter(_yaml()) == []


class TestPresentacionDelOrigen:
    @pytest.mark.parametrize(
        "origen,etiqueta",
        [
            ("parafasis", "Paráfrasis del reglamento"),
            ("localizador", "Localizador en el reglamento"),
            ("plantilla", "plantilla institucional"),
            ("calidad_tecnica", "calidad técnica"),
            ("matriz_interna", "matriz de auditoría interna"),
            ("norma_institucional", "Norma institucional"),
        ],
    )
    def test_prompt_no_llama_cita_literal_a_otro_origen(self, origen, etiqueta):
        prompt = build_prompt(_resultado(origen_cita=origen))
        assert "Cita del reglamento" not in prompt
        assert etiqueta in prompt

    def test_prompt_conserva_la_etiqueta_para_la_cita_literal(self):
        prompt = build_prompt(_resultado(origen_cita="literal"))
        assert "- Cita del reglamento: Texto de referencia" in prompt

    def test_prompt_por_defecto_sigue_siendo_literal(self):
        prompt = build_prompt(_resultado())
        assert "- Cita del reglamento: Texto de referencia" in prompt

    def test_el_origen_no_se_expone_en_la_api(self):
        serializado = _resultado(origen_cita="plantilla").to_dict()
        assert "origen_cita" not in serializado

    def test_el_compilador_propaga_el_origen_declarado(self):
        compiladas = {r.rule["id"]: r for r in CompilerDSL().compilar(_yaml())}
        assert (
            compiladas["notas_al_pie_consistencia"].no_aplicable().origen_cita == "calidad_tecnica"
        )
        assert compiladas["fuente_principal"].no_aplicable().origen_cita == "literal"


class TestConteoDocumental:
    def test_catalogo_de_lineas_sigue_teniendo_50_entradas(self):
        reglas = _por_id(_yaml())
        catalogo = reglas["caratula_linea_investigacion"]["lista_texto"]["lista"]
        assert len(catalogo) == 50

    @pytest.mark.parametrize("ruta", DOCS_CON_CONTEO_46)
    def test_docs_ya_no_dicen_catalogo_de_46(self, ruta):
        texto = (ROOT / ruta).read_text(encoding="utf-8")
        assert "catálogo de 46" not in texto
        assert "dice 46" not in texto
