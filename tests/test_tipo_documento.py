"""Tests del contexto entre reglas: `expone`, `aplicar_si` y evaluación en
dos fases (Semana 6, Paso 1 del `docs/PLAN_TIPO_DOCUMENTO.md`).

Cubre el andamiaje, no la detección de tipo: aquí no hay todavía analizador
`deteccion_tipo`, solo la maquinaria que permite que una regla publique una
clave en el contexto y que otra se condicione a ella.

Incluye una guarda de regresión: con el YAML real (`reglas_unt.yaml`) ninguna
regla debe resultar no aplicable, y el orden del reporte debe seguir siendo el
del YAML.

Uso:
    pytest tests/test_tipo_documento.py -v
"""

import sys
from pathlib import Path

import pytest
import yaml

from validator.compilador import CompilerDSL
from validator.dsl_check import DSLValidationError, linter
from validator.engine import build_report, load_rules, validate_docx

sys.path.insert(0, str(Path(__file__).parent))
from test_dsl import WNS, _make_docx  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

RUTA_REGLAS = Path(__file__).resolve().parents[1] / "reglas_unt.yaml"


def _regla_simple(rule_id, severidad="error", **extra):
    """Regla mínima con un solo analizador, la base para las pruebas de
    contexto."""
    regla = {
        "id": rule_id,
        "tipo": "atributo_xml",
        "severidad": severidad,
        "descripcion": f"descripcion de {rule_id}",
        "valor_esperado": "11906",
        "atributo_xml": {
            "parte": "document",
            "xpath": "//w:sectPr[1]/w:pgSz",
            "atributo": "@w:w",
            "comparacion": "eq",
            "esperado": "11906",
        },
    }
    regla.update(extra)
    return regla


def _detector(rule_id="detector", clave="tipo"):
    """Regla que publica una clave en el contexto.

    Se apoya en `AnalizadorXML`, que sí deja un valor legible por máquina
    (`Analizador.valor`): el ancho de página del DOCX de prueba. Así el
    andamiaje se ejercita de punta a punta con analizadores que ya existen,
    sin necesitar un analizador `deteccion_tipo` que aún no se ha escrito.
    """
    return _regla_simple(rule_id, expone=clave)


def _datos(*reglas):
    return {"namespaces": {"w": WNS}, "reglas": list(reglas)}


def _ids(resultados):
    return [r.rule_id for r in resultados]


# ---------------------------------------------------------------------------
# Linter: validacion de `expone` y `aplicar_si`
# ---------------------------------------------------------------------------


class TestLinterContexto:
    def test_aplicar_si_valido_no_reporta_hallazgos(self):
        datos = _datos(
            _regla_simple("detector", expone="tipo"),
            _regla_simple("estructura", aplicar_si={"tipo": "cuantitativo"}),
        )
        assert linter(datos) == []

    def test_aplicar_si_a_clave_inexistente_es_error(self):
        """Una condicion que nadie puede satisfacer dejaria la regla siempre
        inactiva: es un fallo silencioso, tiene que ser error de carga."""
        datos = _datos(_regla_simple("estructura", aplicar_si={"tipo": "cuantitativo"}))
        hallazgos = linter(datos)
        assert len(hallazgos) == 1
        assert "aplicar_si" in hallazgos[0]
        assert "no la expone ninguna regla" in hallazgos[0]

    @pytest.mark.parametrize("invalido", [{}, [], "cuantitativo", None, ""])
    def test_aplicar_si_no_es_mapa_no_vacio(self, invalido):
        datos = _datos(
            _regla_simple("detector", expone="tipo"),
            _regla_simple("estructura"),
        )
        datos["reglas"][1]["aplicar_si"] = invalido
        assert any("aplicar_si" in h for h in linter(datos))

    def test_expone_duplicado_es_error(self):
        datos = _datos(
            _regla_simple("detector_a", expone="tipo"),
            _regla_simple("detector_b", expone="tipo"),
        )
        hallazgos = linter(datos)
        assert any("ya la expone" in h for h in hallazgos)

    def test_expone_y_aplicar_si_en_la_misma_regla_es_error(self):
        datos = _datos(
            _regla_simple("detector", expone="tipo"),
            _regla_simple("weird", expone="otro", aplicar_si={"tipo": "x"}),
        )
        assert any("expone y aplicar_si" in h for h in linter(datos))

    def test_expone_sin_analizador_es_error(self):
        """Sin seccion de analizador la regla se descarta al compilar, asi que
        nunca publicaria su clave y dejaria huerfana cualquier condicion."""
        datos = _datos(
            {"id": "fantasma", "expone": "tipo", "descripcion": "sin analizador"},
            _regla_simple("estructura", aplicar_si={"tipo": "cuantitativo"}),
        )
        assert any("nunca publica su clave" in h for h in linter(datos))

    def test_expone_no_textual_es_error(self):
        datos = _datos(_regla_simple("detector", expone=42))
        assert any("expone: debe ser un texto" in h for h in linter(datos))

    def test_linter_o_alzar_falla_al_cargar(self):
        datos = _datos(_regla_simple("estructura", aplicar_si={"tipo": "cuantitativo"}))
        with pytest.raises(DSLValidationError, match="aplicar_si"):
            CompilerDSL().compilar(datos)

    def test_condicion_puede_ir_antes_que_el_detector(self):
        """El orden en el YAML es irrelevante: la evaluación es en dos fases,
        así que una regla condicionada puede declararse antes que la que
        produce su clave."""
        datos = _datos(
            _regla_simple("estructura", aplicar_si={"tipo": "cuantitativo"}),
            _detector(),
        )
        assert linter(datos) == []

    def test_yaml_real_sigue_pasando_el_linter(self):
        assert linter(load_rules(str(RUTA_REGLAS))) == []


# ---------------------------------------------------------------------------
# Evaluacion en dos fases
# ---------------------------------------------------------------------------


class TestDosFases:
    """El detector de prueba publica '11906' (ancho de página A4), que es el
    valor contra el que se condicionan las reglas."""

    ANCHO = "11906"

    def test_aplicar_si_cumplido_se_evalua(self):
        datos = _datos(_detector(), _regla_simple("estructura", aplicar_si={"tipo": self.ANCHO}))
        path = _make_docx(headings=["RESULTADOS"])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        por_id = {r.rule_id: r for r in res}
        assert por_id["estructura"].aplicable is True
        assert por_id["estructura"].passed is True

    def test_aplicar_si_no_cumplido_queda_no_aplicable(self):
        datos = _datos(_detector(), _regla_simple("estructura", aplicar_si={"tipo": "OTRO"}))
        path = _make_docx(headings=["RESULTADOS"])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        por_id = {r.rule_id: r for r in res}
        assert por_id["estructura"].aplicable is False
        assert "no aplica" in por_id["estructura"].found

    def test_clave_ausente_del_contexto_no_aplica(self):
        """Ausencia de clave es 'valor desconocido', no 'vale cualquier cosa'.

        Se prueba sobre `aplica_en` directamente: con el linter en pie, toda
        clave usada en `aplicar_si` está expuesta por alguna regla, así que
        el caso es defensivo y no se puede llegar por el motor.
        """
        from validator.compilador import ReglaCompilada

        regla = ReglaCompilada(rule={"id": "x"}, aplicar_si={"tipo": "A4"})
        assert regla.aplica_en({"tipo": "A4"}) is True
        assert regla.aplica_en({"otro": "A4"}) is False
        assert regla.aplica_en({}) is False
        assert ReglaCompilada(rule={"id": "x"}, aplicar_si=None).aplica_en({}) is True

    def test_condiciones_conjuntas(self):
        """Varias claves en `aplicar_si` deben cumplirse todas."""
        datos = _datos(
            _detector("d1", clave="tipo"),
            _detector("d2", clave="programa"),
            _regla_simple("estructura", aplicar_si={"tipo": self.ANCHO, "programa": "OTRO"}),
        )
        path = _make_docx(headings=["RESULTADOS"])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        assert {r.rule_id: r for r in res}["estructura"].aplicable is False

    def test_regla_incondicional_siempre_aplica(self):
        datos = _datos(_regla_simple("sencilla"))
        path = _make_docx(headings=["RESULTADOS"])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        assert res[0].aplicable is True

    def test_no_aplicable_no_bloquea_el_semaforo(self):
        """Una regla inactiva no ha fallado, así que no puede poner el
        semáforo en rojo aunque su severidad sea `error`."""
        datos = _datos(_detector(), _regla_simple("estructura", aplicar_si={"tipo": "OTRO"}))
        path = _make_docx(headings=["RESULTADOS"])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        assert build_report(res)["semaforo"] == "verde"

    def test_orden_del_yaml_se_conserva(self):
        """Las fases no deben reordenar el reporte: el orden de salida es el
        del YAML, no el de ejecución. Aquí las reglas condicionadas están
        ANTES que el detector que produce su clave, que es justo el caso donde
        un `return` por fase las desordenaría."""
        datos = _datos(
            _regla_simple("condicional_1", aplicar_si={"tipo": "X"}),
            _detector(),
            _regla_simple("incondicional"),
            _regla_simple("condicional_2", aplicar_si={"tipo": "Y"}),
        )
        path = _make_docx(headings=["RESULTADOS"])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        assert _ids(res) == ["condicional_1", "detector", "incondicional", "condicional_2"]

    def test_todas_las_reglas_conservan_su_resultado(self):
        """Ninguna regla se pierde: las no aplicables también se reportan,
        con `aplicable=False`, para que el resumen pueda contarlas."""
        datos = _datos(_detector(), _regla_simple("estructura", aplicar_si={"tipo": "OTRO"}))
        path = _make_docx(headings=["RESULTADOS"])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        assert len(res) == 2


# ---------------------------------------------------------------------------
# Guardas de regresion sobre el YAML real
# ---------------------------------------------------------------------------


class TestSinCambioDeComportamiento:
    """Regla de oro del paso: con el YAML real no debe cambiar nada."""

    @staticmethod
    def _ruta_plantilla():
        return (
            Path(__file__).resolve().parents[1]
            / "recursos"
            / "EDUCACION INICIAL-PLANTILLA INVESTIGACIÓN CUANTITATIVA.docx"
        )

    def test_ninguna_regla_real_es_no_aplicable(self):
        reglas = load_rules(str(RUTA_REGLAS))
        assert not any(r.get("aplicar_si") for r in reglas["reglas"])
        assert not any(r.get("expone") for r in reglas["reglas"])

    def test_doc_bueno_todas_aplicables(self):
        from docx_factory import compilar_docx, configuracion_base

        path = compilar_docx(configuracion_base())
        try:
            res = validate_docx(path, load_rules(str(RUTA_REGLAS)))
        finally:
            Path(path).unlink(missing_ok=True)
        assert len(res) == 47
        assert all(r.aplicable for r in res)

    def test_plantilla_oficial_mismo_reporte_que_antes(self):
        """Guarda de que el número de reglas y el semáforo no se movieron:
        este paso no arregla el defecto, solo prepara la maquinaria.

        `recursos/` está en `.gitignore`, así que en el build de Nix la
        plantilla no existe y el test se omite (igual que los demás tests
        que dependen de las plantillas).
        """
        base = self._ruta_plantilla()
        if not base.exists():
            pytest.skip("las plantillas de recursos/ no están disponibles en este entorno")
        res = validate_docx(str(base), load_rules(str(RUTA_REGLAS)))
        assert len(res) == 47
        assert build_report(res)["semaforo"] == "rojo"
        assert all(r.aplicable for r in res)


# ---------------------------------------------------------------------------
# El YAML de reglas pendientes (Fase B) debe cargar y lintear
# ---------------------------------------------------------------------------


class TestYamlPendienteOpcional:
    """`reglas_unt_pendientes.yaml` solo existe a partir del paso 8. Si ya
    esta, tiene que cargar y pasar el linter: implementadas pero no probadas
    contra documentos reales."""

    RUTA = Path(__file__).resolve().parents[1] / "reglas_unt_pendientes.yaml"

    def test_carga_y_lintea(self):
        if not self.RUTA.exists():
            pytest.skip("reglas_unt_pendientes.yaml todavia no existe (se crea en el paso 8)")
        datos = yaml.safe_load(self.RUTA.read_text(encoding="utf-8"))
        assert linter(datos) == []
        assert datos["reglas"], "el archivo debe declarar al menos una regla"
