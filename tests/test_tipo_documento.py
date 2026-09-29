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
import tempfile
import zipfile
from pathlib import Path

import pytest
import yaml

from validator.compilador import CompilerDSL
from validator.dsl_check import DSLValidationError, linter
from validator.engine import build_report, load_rules, validate_docx

sys.path.insert(0, str(Path(__file__).parent))
from test_dsl import WNS, _make_docx, _para  # noqa: E402

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
    """Con el YAML real, la regla nueva solo informa: no filtra ni altera el semáforo."""

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
        assert len(res) == 48
        assert all(r.aplicable for r in res)

    def test_plantilla_oficial_mismo_reporte_que_antes(self):
        """Guarda de que el semáforo no se movió al añadir la regla
        discriminadora: es `warning`, así que no puede poner en rojo.

        `recursos/` está en `.gitignore`, así que en el build de Nix la
        plantilla no existe y el test se omite (igual que los demás tests
        que dependen de las plantillas).
        """
        base = self._ruta_plantilla()
        if not base.exists():
            pytest.skip("las plantillas de recursos/ no están disponibles en este entorno")
        res = validate_docx(str(base), load_rules(str(RUTA_REGLAS)))
        assert len(res) == 48
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


# ---------------------------------------------------------------------------
# Paso 2: DeteccionTipo
# ---------------------------------------------------------------------------

from validator.analizadores import (  # noqa: E402
    NIVEL_DECLARADO,
    NIVEL_INFERIDO,
    NIVEL_NO_DETERMINADO,
    TIPO_CONTRADICTORIO,
    TIPO_SIN_DETERMINAR,
    DeteccionTipo,
)
from validator.extractor import extract  # noqa: E402

# Firmas tal como las fija docs/diseno/15_tipo_documento_grupos.md, en el
# orden de especificidad de la decisión 2 (el informe gana al proyecto).
FIRMAS = [
    {
        "tipo": "tsp",
        "evidencia": [
            "SECUENCIA DIDÁCTICA",
            "SUSTENTO PSICOPEDAGÓGICO",
            "SUSTENTO TEÓRICO CIENTÍFICO",
        ],
        "minimo": 2,
    },
    {
        "tipo": "informe_cualitativo",
        "evidencia": [
            "SITUACIÓN PROBLEMATIZADA",
            "PARTICIPANTES",
            "INSTRUMENTOS USADOS EN LA RECOLECCIÓN",
        ],
        "minimo": 2,
    },
    {
        "tipo": "informe_cuantitativo",
        "evidencia": [
            "SITUACIÓN PROBLEMATIZADA",
            "DISEÑO DE CONTRASTACIÓN",
            "OPERACIONALIZACIÓN DE LAS VARIABLES",
        ],
        "minimo": 2,
    },
    {
        "tipo": "proyecto_cuantitativo",
        "evidencia": ["PLAN DE INVESTIGACIÓN", "RECURSOS Y MATERIALES", "LÍNEA DE INVESTIGACIÓN"],
        "minimo": 2,
    },
    {
        "tipo": "proyecto_cualitativo",
        "evidencia": ["SELECCIÓN DE PARTICIPANTES", "ESCENARIO", "UNIDAD DE ANÁLISIS"],
        "minimo": 2,
    },
    {
        "tipo": "tinv_revision_literatura",
        "evidencia": ["ESTADO DEL ARTE", "TÉCNICAS DE PROCESAMIENTO DE DATOS"],
        "minimo": 1,
    },
    {
        "tipo": "tinv_cualitativo",
        "evidencia": ["DEFINICIÓN DE TÉRMINOS", "CATEGORIZACIÓN"],
        "minimo": 1,
    },
    {
        "tipo": "tinv_cuantitativo",
        "evidencia": ["VARIABLE", "POBLACIÓN Y MUESTRA", "INSTRUMENTO"],
        "minimo": 1,
    },
]

# Etiquetas del Anexo 10, con el vocabulario del formulario (no el del manual).
ETIQUETAS = {
    "tsp": ["TRABAJO DE SERVICIO", "SERVICIO SOCIAL"],
    "informe_cualitativo": ["INFORME DE PROYECTO DE INVESTIGACIÓN CUALITATIVO"],
    "informe_cuantitativo": ["INFORME DE PROYECTO DE INVESTIGACIÓN CUANTITATIVO"],
    "proyecto_cuantitativo": ["PROYECTO DE INVESTIGACIÓN CUANTITATIVO"],
    "proyecto_cualitativo": ["PROYECTO DE INVESTIGACIÓN CUALITATIVO"],
    "tinv_revision_literatura": ["TESIS PARA OBTENER EL GRADO DE BACHILLER EN INVESTIGACIÓN"],
    "tinv_cualitativo": ["TESIS PARA OBTENER EL TÍTULO PROFESIONAL EN INVESTIGACIÓN CUALITATIVA"],
    "tinv_cuantitativo": ["TESIS PARA OBTENER EL TÍTULO PROFESIONAL EN INVESTIGACIÓN CUANTITATIVA"],
}


def _cfg_deteccion(declaracion=None, firmas=None):
    cfg = {
        "expone": "tipo_documento",
        "firmas": FIRMAS if firmas is None else firmas,
        "minimo_global": 1,
    }
    if declaracion is not None:
        cfg["declaracion"] = declaracion
    return cfg


def _docx_de_parrafos(parrafos_xml: list[str]) -> str:
    """DOCX mínimo a partir de XML de párrafos crudo (para poder meter
    `w:sym`, que un builder de texto plano no sabe escribir)."""
    from test_dsl import CONTENT_TYPES, RELS

    body = "".join(parrafos_xml)
    doc = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{body}'
        f'<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
        f"</w:body></w:document>"
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def _detectar(parrafos_xml, declaracion=None, firmas=None):
    """Ejecuta el analizador y devuelve (ok, nivel, valor, evidencia, detalle)."""
    path = _docx_de_parrafos(parrafos_xml)
    try:
        analizador = DeteccionTipo(_cfg_deteccion(declaracion, firmas))
        ok, detalle = analizador.analizar(extract(path))
        return ok, analizador.nivel, analizador.valor, analizador.evidencia, detalle
    finally:
        Path(path).unlink(missing_ok=True)


def _t(texto, estilo="Ttulo1"):
    return _para(texto, estilo)


def _con_sym(char, texto=""):
    """Casilla Wingdings. Word la escribe como un `w:sym` en el MISMO párrafo
    que su etiqueta, que es como se lee un formulario."""
    return (
        f'<w:p><w:r><w:sym w:font="Wingdings" w:char="{char}"/></w:r>'
        f'<w:r><w:t xml:space="preserve"> {texto}</w:t></w:r></w:p>'
    )


def _con_casilla(texto, marcada=True):
    return (
        f'<w:p><w:r><w:t xml:space="preserve">☒ {texto}</w:t></w:r></w:p>'
        if marcada
        else (f'<w:p><w:r><w:t xml:space="preserve">☐ {texto}</w:t></w:r></w:p>')
    )


class TestDeteccionNivelInferido:
    """Nivel 2: firmas estructurales. Un conjunto mínimo por tipo."""

    @pytest.mark.parametrize(
        ("tipo_esperado", "titulos"),
        [
            ("tsp", ["SECUENCIA DIDÁCTICA", "SUSTENTO PSICOPEDAGÓGICO"]),
            ("informe_cualitativo", ["SITUACIÓN PROBLEMATIZADA", "PARTICIPANTES"]),
            ("informe_cuantitativo", ["SITUACIÓN PROBLEMATIZADA", "DISEÑO DE CONTRASTACIÓN"]),
            ("proyecto_cuantitativo", ["PLAN DE INVESTIGACIÓN", "RECURSOS Y MATERIALES"]),
            ("proyecto_cualitativo", ["SELECCIÓN DE PARTICIPANTES", "UNIDAD DE ANÁLISIS"]),
            ("tinv_revision_literatura", ["ESTADO DEL ARTE"]),
            ("tinv_cualitativo", ["DEFINICIÓN DE TÉRMINOS"]),
            ("tinv_cuantitativo", ["POBLACIÓN Y MUESTRA"]),
        ],
    )
    def test_detecta_los_ocho_tipos(self, tipo_esperado, titulos):
        ok, nivel, valor, evidencia, detalle = _detectar([_t(t) for t in titulos])
        assert valor == tipo_esperado, detalle
        assert ok is True
        assert nivel == NIVEL_INFERIDO
        assert evidencia, "el nivel inferido debe decir qué firmas encontró"
        assert f"inferido={tipo_esperado}" in detalle

    def test_todos_los_tipos_del_diseno_son_detectables(self):
        """Los 8 identificadores canónicos del diseño tienen firma."""
        assert {f["tipo"] for f in FIRMAS} == set(ETIQUETAS)

    def test_informe_gana_al_proyecto(self):
        """Decisión 2: el informe es la versión revisada del proyecto, así que
        sus firmas son más específicas y se evalúan antes."""
        titulos = ["SITUACIÓN PROBLEMATIZADA", "DISEÑO DE CONTRASTACIÓN", "PLAN DE INVESTIGACIÓN"]
        _, _nivel, valor, _ev, _ = _detectar([_t(t) for t in titulos])
        assert valor == "informe_cuantitativo"

    def test_tsp_gana_a_informe(self):
        titulos = ["SECUENCIA DIDÁCTICA", "SUSTENTO PSICOPEDAGÓGICO", "SITUACIÓN PROBLEMATIZADA"]
        _, _nivel, valor, _ev, _ = _detectar([_t(t) for t in titulos])
        assert valor == "tsp"

    def test_normaliza_acentos_y_sangria(self):
        """Los títulos reales vienen con tildes, numeración y sangría: la
        comparación no debe depender de eso."""
        _, _nivel, valor, _ev, _ = _detectar(
            [_t("   2.1  Definición de Términos   ", "Ttulo2")], None
        )
        assert valor == "tinv_cualitativo"

    def test_firma_por_subcadena(self):
        """'VARIABLE' debe casar con 'VARIABLE(S) Y OPERACIONALIZACIÓN'."""
        _, _nivel, valor, _ev, _ = _detectar([_t("VARIABLE(S) Y OPERACIONALIZACIÓN")])
        assert valor == "tinv_cuantitativo"

    def test_minimo_no_alcanzado_no_dispara(self):
        """Una sola firma de un tipo que exige 2 no basta."""
        ok, _nivel, valor, _ev, detalle = _detectar([_t("PLAN DE INVESTIGACIÓN")])
        assert valor == TIPO_SIN_DETERMINAR
        assert ok is False
        assert "sin_determinado" in detalle

    def test_titulo_desconocido_queda_sin_determinar(self):
        ok, nivel, valor, evidencia, detalle = _detectar([_t("RESUMEN"), _t("INTRODUCCIÓN")])
        assert valor == TIPO_SIN_DETERMINAR
        assert nivel == NIVEL_NO_DETERMINADO
        assert evidencia == []
        assert ok is False
        assert "sin_determinado" in detalle

    def test_documento_vacio_queda_sin_determinar(self):
        ok, _nivel, valor, _ev, _ = _detectar([])
        assert valor == TIPO_SIN_DETERMINAR
        assert ok is False


class TestDeteccionNivelDeclarado:
    """Nivel 1: casilla marcada del Anexo 10."""

    def test_casilla_marcada_por_texto(self):
        parrafos = [
            _con_casilla("PROYECTO DE INVESTIGACIÓN CUANTITATIVO"),
            _t("PLAN DE INVESTIGACIÓN"),
            _t("RECURSOS Y MATERIALES"),
        ]
        ok, nivel, valor, evidencia, detalle = _detectar(
            parrafos, {"anexo": "Anexo 10", "etiquetas": ETIQUETAS}
        )
        assert valor == "proyecto_cuantitativo"
        assert nivel == NIVEL_DECLARADO
        assert evidencia == ["PROYECTO DE INVESTIGACIÓN CUANTITATIVO"]
        assert "declarado=proyecto_cuantitativo" in detalle
        assert ok is True

    def test_casilla_marcada_wingdings(self):
        """Word dibuja las casillas como símbolo Wingdings, no como texto."""
        parrafos = [
            _con_sym(
                "F0FE",
                "TESIS PARA OBTENER EL TÍTULO PROFESIONAL EN INVESTIGACIÓN CUANTITATIVA",
            ),
            _t("POBLACIÓN Y MUESTRA"),
        ]
        _, _nivel, valor, _ev, detalle = _detectar(
            parrafos, {"anexo": "Anexo 10", "etiquetas": ETIQUETAS}
        )
        assert valor == "tinv_cuantitativo", detalle
        assert "declarado=" in detalle

    def test_casilla_vacia_wingdings_no_declara(self):
        """F0A8 es la casilla VACÍA: no puede leerse como declaración."""
        parrafos = [
            _con_sym(
                "F0A8",
                "TESIS PARA OBTENER EL TÍTULO PROFESIONAL EN INVESTIGACIÓN CUANTITATIVA",
            ),
            _t("POBLACIÓN Y MUESTRA"),
        ]
        _, _nivel, valor, _ev, detalle = _detectar(
            parrafos, {"anexo": "Anexo 10", "etiquetas": ETIQUETAS}
        )
        assert valor == "tinv_cuantitativo"
        assert "inferido=" in detalle

    def test_casilla_sin_marcar_no_declara(self):
        """El error más fácil de cometer al leer: una casilla vacía junto a una
        etiqueta NO es una declaración."""
        parrafos = [
            _con_casilla("PROYECTO DE INVESTIGACIÓN CUANTITATIVO", marcada=False),
            _t("PLAN DE INVESTIGACIÓN"),
            _t("RECURSOS Y MATERIALES"),
        ]
        _, _nivel, valor, _ev, detalle = _detectar(
            parrafos, {"anexo": "Anexo 10", "etiquetas": ETIQUETAS}
        )
        assert valor == "proyecto_cuantitativo"
        assert "inferido=" in detalle, "debió caer al nivel 2, no declarar"

    def test_sin_declaracion_configurada_no_hay_nivel_1(self):
        _, _nivel, valor, _ev, detalle = _detectar(
            [_con_casilla("PROYECTO DE INVESTIGACIÓN CUANTITATIVO"), _t("POBLACIÓN Y MUESTRA")]
        )
        assert valor == "tinv_cuantitativo"
        assert "inferido=" in detalle

    def test_declarado_e_inferido_que_coinciden(self):
        parrafos = [
            _con_casilla("PROYECTO DE INVESTIGACIÓN CUANTITATIVO"),
            _t("PLAN DE INVESTIGACIÓN"),
            _t("RECURSOS Y MATERIALES"),
        ]
        _, _nivel, valor, _ev, detalle = _detectar(
            parrafos, {"anexo": "Anexo 10", "etiquetas": ETIQUETAS}
        )
        assert valor == "proyecto_cuantitativo"
        assert "declarado=" in detalle and "contradictorio" not in detalle

    def test_contradiccion_se_publica(self):
        """El autor declara un tipo pero el documento tiene la estructura de
        otro: se dice, no se elige en silencio."""
        parrafos = [
            _con_casilla("TESIS PARA OBTENER EL TÍTULO PROFESIONAL EN INVESTIGACIÓN CUALITATIVA"),
            _t("PLAN DE INVESTIGACIÓN"),
            _t("RECURSOS Y MATERIALES"),
        ]
        ok, nivel, valor, evidencia, detalle = _detectar(
            parrafos, {"anexo": "Anexo 10", "etiquetas": ETIQUETAS}
        )
        assert valor == TIPO_CONTRADICTORIO
        assert nivel == NIVEL_NO_DETERMINADO
        assert evidencia == [
            "TESIS PARA OBTENER EL TÍTULO PROFESIONAL EN INVESTIGACIÓN CUALITATIVA",
            "PLAN DE INVESTIGACIÓN",
            "RECURSOS Y MATERIALES",
        ], "la contradicción debe reportar las dos evidencias"
        assert ok is False
        assert "declarado=tinv_cualitativo" in detalle
        assert "inferido=proyecto_cuantitativo" in detalle

    def test_etiqueta_variante_del_anexo(self):
        parrafos = [
            _con_casilla("TRABAJO DE SERVICIO"),
            _t("SECUENCIA DIDÁCTICA"),
            _t("SUSTENTO PSICOPEDAGÓGICO"),
        ]
        _, _nivel, valor, _ev, _ = _detectar(
            parrafos, {"anexo": "Anexo 10", "etiquetas": ETIQUETAS}
        )
        assert valor == "tsp"


class TestLinterDeteccionTipo:
    def test_config_valida_no_reporta_hallazgos(self):
        datos = {
            "namespaces": {"w": WNS},
            "reglas": [
                {
                    "id": "deteccion_tipo_documento",
                    "severidad": "warning",
                    "descripcion": "detecta el tipo",
                    "deteccion_tipo": _cfg_deteccion({"anexo": "Anexo 10", "etiquetas": ETIQUETAS}),
                }
            ],
        }
        assert linter(datos) == []

    def test_falta_expone(self):
        cfg = _cfg_deteccion()
        del cfg["expone"]
        datos = {"reglas": [{"id": "d", "deteccion_tipo": cfg}]}
        assert any("falta 'expone'" in h for h in linter(datos))

    def test_expone_a_nivel_de_regla_tambien_sirve(self):
        datos = {
            "reglas": [{"id": "d", "expone": "tipo_documento", "deteccion_tipo": _cfg_deteccion()}]
        }
        assert linter(datos) == []

    def test_firmas_vacia(self):
        datos = {"reglas": [{"id": "d", "deteccion_tipo": {"expone": "x", "firmas": []}}]}
        assert any("'firmas' debe ser una lista no vacía" in h for h in linter(datos))

    def test_evidencia_vacia(self):
        cfg = _cfg_deteccion(firmas=[{"tipo": "t", "evidencia": [], "minimo": 1}])
        assert any(
            "necesita 'evidencia' no vacía" in h
            for h in linter({"reglas": [{"id": "d", "deteccion_tipo": cfg}]})
        )

    def test_tipo_repetido(self):
        cfg = _cfg_deteccion(
            firmas=[
                {"tipo": "t", "evidencia": ["A"], "minimo": 1},
                {"tipo": "t", "evidencia": ["B"], "minimo": 1},
            ]
        )
        assert any(
            "repetido en 'firmas'" in h
            for h in linter({"reglas": [{"id": "d", "deteccion_tipo": cfg}]})
        )

    def test_minimo_menor_que_uno(self):
        cfg = _cfg_deteccion(firmas=[{"tipo": "t", "evidencia": ["A"], "minimo": 0}])
        assert any(
            "necesita 'minimo' >= 1" in h
            for h in linter({"reglas": [{"id": "d", "deteccion_tipo": cfg}]})
        )

    def test_minimo_por_debajo_de_minimo_global(self):
        cfg = _cfg_deteccion(firmas=[{"tipo": "t", "evidencia": ["A", "B"], "minimo": 1}])
        cfg["minimo_global"] = 2
        assert any(
            "por debajo de 'minimo_global'" in h
            for h in linter({"reglas": [{"id": "d", "deteccion_tipo": cfg}]})
        )

    def test_minimo_inevitable(self):
        """Exigir más firmas de las declaradas la dejaría siempre inactiva."""
        cfg = _cfg_deteccion(firmas=[{"tipo": "t", "evidencia": ["A"], "minimo": 2}])
        assert any(
            "nunca puede cumplirse" in h
            for h in linter({"reglas": [{"id": "d", "deteccion_tipo": cfg}]})
        )

    def test_declaracion_sin_etiquetas(self):
        cfg = _cfg_deteccion()
        cfg["declaracion"] = {"anexo": "Anexo 10"}
        assert any(
            "'declaracion.etiquetas' debe mapear" in h
            for h in linter({"reglas": [{"id": "d", "deteccion_tipo": cfg}]})
        )

    def test_etiqueta_de_tipo_desconocido(self):
        cfg = _cfg_deteccion()
        cfg["declaracion"] = {"anexo": "Anexo 10", "etiquetas": {"inventado": ["X"]}}
        assert any(
            "no aparece en 'firmas'" in h
            for h in linter({"reglas": [{"id": "d", "deteccion_tipo": cfg}]})
        )

    def test_expone_anidado_alimenta_el_contexto(self):
        """Una condición puede apuntar a la clave que publica la sección
        `deteccion_tipo`, no solo a la de nivel de regla."""
        cfg = _cfg_deteccion()
        datos = {
            "reglas": [
                {"id": "d", "deteccion_tipo": cfg},
                {
                    "id": "e",
                    "aplicar_si": {"tipo_documento": "tinv_cuantitativo"},
                    "atributo_xml": {
                        "parte": "document",
                        "xpath": "//w:sectPr[1]/w:pgSz",
                        "atributo": "@w:w",
                        "comparacion": "eq",
                        "esperado": "11906",
                    },
                },
            ]
        }
        assert linter(datos) == []


class TestDeteccionDesdeElMotor:
    """La detección se invoca como cualquier otra regla del DSL."""

    def _regla(self, cfg):
        return {
            "id": "deteccion_tipo_documento",
            "tipo": "deteccion",
            "severidad": "warning",
            "descripcion": "Detecta el tipo de documento",
            "deteccion_tipo": cfg,
        }

    def test_publica_el_tipo_en_el_contexto(self):
        cfg = _cfg_deteccion()
        datos = {"namespaces": {"w": WNS}, "reglas": [self._regla(cfg)]}
        path = _docx_de_parrafos([_t("POBLACIÓN Y MUESTRA"), _t("INSTRUMENTO")])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        assert len(res) == 1
        assert res[0].passed is True

    def test_el_detalle_llega_al_reporte(self):
        """El hueco que este test fijaba quedó cerrado en el paso 3.

        `ReglaCompilada.ejecutar` ya no fuerza `found="cumple"` en las reglas
        que declaran `expone`: ahora muestran el tipo y su evidencia
        (decisión 4 del diseño). El resumen agrupado ("Tipo detectado: X.
        Motivo: ...") se construye en el paso 5.
        """
        cfg = _cfg_deteccion()
        datos = {"namespaces": {"w": WNS}, "reglas": [self._regla(cfg)]}
        path = _docx_de_parrafos([_t("POBLACIÓN Y MUESTRA"), _t("INSTRUMENTO")])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        assert res[0].found != "cumple"
        assert "tinv_cuantitativo" in res[0].found
        assert "POBLACIÓN Y MUESTRA" in res[0].found

    def test_una_condicion_consume_el_tipo_publicado(self):
        cfg = _cfg_deteccion()
        datos = {
            "namespaces": {"w": WNS},
            "reglas": [
                self._regla(cfg),
                {
                    "id": "estructura_cualitativa",
                    "severidad": "error",
                    "descripcion": "solo si es cualitativo",
                    "aplicar_si": {"tipo_documento": "tinv_cualitativo"},
                    "atributo_xml": {
                        "parte": "document",
                        "xpath": "//w:sectPr[1]/w:pgSz",
                        "atributo": "@w:w",
                        "comparacion": "eq",
                        "esperado": "999",
                    },
                },
            ],
        }
        path = _docx_de_parrafos([_t("POBLACIÓN Y MUESTRA")])
        try:
            res = validate_docx(path, datos)
        finally:
            Path(path).unlink(missing_ok=True)
        por_id = {r.rule_id: r for r in res}
        assert por_id["deteccion_tipo_documento"].passed is True
        assert por_id["estructura_cualitativa"].aplicable is False


# ---------------------------------------------------------------------------
# Paso 3: la regla discriminadora en reglas_unt.yaml
# ---------------------------------------------------------------------------

TIPOS_ESPERADOS = {
    "tsp",
    "informe_cuantitativo",
    "informe_cualitativo",
    "proyecto_cuantitativo",
    "proyecto_cualitativo",
    "tinv_revision_literatura",
    "tinv_cualitativo",
    "tinv_cuantitativo",
}


def _regla_deteccion():
    reglas = load_rules(str(RUTA_REGLAS))
    return next(r for r in reglas["reglas"] if r["id"] == "deteccion_tipo_documento")


def _validar_factory():
    """Valida el documento bueno del factory y devuelve (resultados, reporte)."""
    from docx_factory import compilar_docx, configuracion_base

    path = compilar_docx(configuracion_base())
    try:
        res = validate_docx(path, load_rules(str(RUTA_REGLAS)))
    finally:
        Path(path).unlink(missing_ok=True)
    return res, build_report(res)


class TestReglaDeteccionEnElYaml:
    def test_es_la_primera_regla_del_yaml(self):
        """Debe ir primera: evalúa en fase 1 y alimenta el contexto."""
        reglas = load_rules(str(RUTA_REGLAS))
        assert reglas["reglas"][0]["id"] == "deteccion_tipo_documento"

    def test_total_de_reglas(self):
        assert len(load_rules(str(RUTA_REGLAS))["reglas"]) == 48

    def test_severidad_warning(self):
        assert _regla_deteccion()["severidad"] == "warning"

    def test_expone_tipo_documento(self):
        assert _regla_deteccion()["deteccion_tipo"]["expone"] == "tipo_documento"

    def test_ocho_tipos_detectables(self):
        firmas = _regla_deteccion()["deteccion_tipo"]["firmas"]
        assert {f["tipo"] for f in firmas} == TIPOS_ESPERADOS
        assert len(firmas) == len(TIPOS_ESPERADOS)

    def test_minimo_global_uno(self):
        assert _regla_deteccion()["deteccion_tipo"]["minimo_global"] == 1

    def test_todas_las_firmas_declaran_etiquetas_de_declaracion(self):
        cfg = _regla_deteccion()["deteccion_tipo"]
        assert set(cfg["declaracion"]["etiquetas"]) == TIPOS_ESPERADOS

    def test_toda_firma_tiene_minimo_positivo(self):
        for f in _regla_deteccion()["deteccion_tipo"]["firmas"]:
            assert f["minimo"] >= 1


class TestDeteccionEnDocumentosReales:
    def test_doc_bueno_se_detecta_como_cuantitativo(self):
        res, _ = _validar_factory()
        r = next(x for x in res if x.rule_id == "deteccion_tipo_documento")
        assert r.passed is True
        assert "tinv_cuantitativo" in r.found

    def test_plantilla_oficial_se_detecta_como_cuantitativo(self):
        """`recursos/` está en `.gitignore`: se omite si no está disponible."""
        base = TestSinCambioDeComportamiento._ruta_plantilla()
        if not base.exists():
            pytest.skip("las plantillas de recursos/ no están disponibles en este entorno")
        res = validate_docx(str(base), load_rules(str(RUTA_REGLAS)))
        r = next(x for x in res if x.rule_id == "deteccion_tipo_documento")
        assert r.passed is True
        assert "tinv_cuantitativo" in r.found

    def test_una_tesis_con_revision_no_se_toma_como_revision(self):
        """`ESTADO DEL ARTE` está en el marco teórico de cualquier tesis: por
        eso la firma de revisión exige además METODOLOGÍA DE REVISIÓN."""
        res, _ = _validar_factory()
        r = next(x for x in res if x.rule_id == "deteccion_tipo_documento")
        assert "tinv_revision_literatura" not in r.found


class TestInformeMuestraElTipo:
    def test_found_no_es_el_generico_cumple(self):
        """Regla `expone` = informativa: el reporte dice qué encontró."""
        res, _ = _validar_factory()
        r = next(x for x in res if x.rule_id == "deteccion_tipo_documento")
        assert r.found != "cumple"
        assert "inferido=tinv_cuantitativo" in r.found

    def test_las_demas_reglas_siguen_diciendo_cumple(self):
        """El cambio es exclusivo de las reglas que `expone`."""
        res, _ = _validar_factory()
        for r in res:
            if r.rule_id == "deteccion_tipo_documento":
                continue
            if r.passed:
                assert r.found == "cumple", r.rule_id

    def test_semaforo_no_cambia_por_ser_warning(self):
        """Con la regla añadida el semáforo es el mismo que sin ella."""
        reglas = load_rules(str(RUTA_REGLAS))
        from docx_factory import compilar_docx, configuracion_base

        path = compilar_docx(configuracion_base())
        try:
            completo = build_report(validate_docx(path, reglas))
            sin_deteccion = build_report(
                validate_docx(path, {**reglas, "reglas": reglas["reglas"][1:]})
            )
        finally:
            Path(path).unlink(missing_ok=True)
        assert completo["semaforo"] == sin_deteccion["semaforo"] == "rojo"


class TestMutacionDeLaDeteccion:
    def _validar_mutado(self):
        from docx_factory import aplicar_mutacion, compilar_docx, configuracion_base

        path = compilar_docx(aplicar_mutacion("deteccion_tipo_documento", configuracion_base()))
        try:
            res = validate_docx(path, load_rules(str(RUTA_REGLAS)))
        finally:
            Path(path).unlink(missing_ok=True)
        return res, build_report(res)

    def test_declaracion_contraria_se_reporta_como_contradiccion(self):
        res, _ = self._validar_mutado()
        r = next(x for x in res if x.rule_id == "deteccion_tipo_documento")
        assert r.passed is False
        assert "contradictorio" in r.found
        assert "proyecto_cualitativo" in r.found

    def test_no_rompe_ninguna_otra_regla(self):
        """La mutación añade un anexo, no toca títulos: no hay acoplamiento."""
        limpio, _ = _validar_factory()
        sucio, _ = self._validar_mutado()
        antes = {r.rule_id: (r.passed, r.found) for r in limpio}
        despues = {r.rule_id: (r.passed, r.found) for r in sucio}
        for rid, valor in antes.items():
            if rid == "deteccion_tipo_documento":
                continue
            assert despues[rid] == valor, rid

    def test_el_semaforo_tampoco_cambia_al_fallar(self):
        _, sucio = self._validar_mutado()
        _, limpio = _validar_factory()
        assert sucio["semaforo"] == limpio["semaforo"] == "rojo"
