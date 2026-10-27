"""Tests de T2: endurecimiento del linter del DSL.

Cubre los cinco casos de configuración inválida que el linter NO detectaba
y que solo se manifestaban en runtime (o, peor, en silencio):

1. Sección mal escrita (`atributo_xmls`): la regla desaparecía del reporte
   sin ningún aviso, porque el compilador no la reconocía.
2. XPath con prefijo de namespace desconocido (`//wp:ind`): reventaba al
   EVALUAR contra el documento, con un `XPathEvalError` que la API
   mostraba al estudiante como si fuera un defecto de su tesis.
3. Severidad inventada (`aviso`): `Severity(...)` reventaba en runtime.
4. `aplicar_si` con un valor que no es un tipo documental declarado: la
   regla no aplicaba nunca y el semáforo quedaba verde sin comprobar.
5. `id` de regla duplicado: doble conteo en el resumen y dos observaciones
   indistinguibles con el mismo identificador.

Uso:
    pytest tests/test_t2_linter.py -v
"""

import pytest
import yaml

from validator.dsl_check import DSLValidationError, linter, linter_o_alzar

PAGINA = {
    "parte": "document",
    "xpath": "//w:pgSz",
    "atributo": "@w:w",
}


def _regla(rule_id: str, **extra) -> dict:
    regla = {
        "id": rule_id,
        "tipo": "atributo_xml",
        "severidad": "error",
        "descripcion": "descripción de prueba",
        "atributo_xml": dict(PAGINA),
    }
    regla.update(extra)
    return regla


def _dsl(*reglas: dict) -> dict:
    return {"reglas": list(reglas)}


def _hallazgos(*reglas: dict) -> list[str]:
    return linter(_dsl(*reglas))


def test_seccion_mal_escrita_se_detecta():
    hallazgos = _hallazgos(
        {
            "id": "r1",
            "tipo": "atributo_xml",
            "severidad": "error",
            "descripcion": "d",
            "atributo_xmls": dict(PAGINA),
        }
    )
    assert hallazgos, "una sección mal escrita debe producir un hallazgo"
    assert any("atributo_xmls" in h for h in hallazgos)


def test_seccion_mal_escrita_sugiere_la_correcta():
    hallazgos = _hallazgos(
        {
            "id": "r1",
            "tipo": "atributo_xml",
            "severidad": "error",
            "descripcion": "d",
            "atributo_xmls": dict(PAGINA),
        }
    )
    assert any("atributo_xml" in h and "quiso decir" in h for h in hallazgos)


def test_seccion_mal_escrita_era_silenciosa_antes():
    from validator.compilador import CompilerDSL

    dsl = _dsl(
        {
            "id": "r1",
            "tipo": "atributo_xml",
            "severidad": "error",
            "descripcion": "d",
            "atributo_xmls": dict(PAGINA),
        }
    )
    compiladas = CompilerDSL().compilar(dsl, linter=False)
    assert compiladas == [], "sin linter la regla se pierde (motivo del fallo)"

    with pytest.raises(DSLValidationError):
        CompilerDSL().compilar(dsl)


def test_clave_legitima_no_se_confunde_con_seccion():
    assert _hallazgos(_regla("r1", tipo="atributo_xml", valor_esperado="11906")) == []


def test_campo_propio_del_analizador_no_se_reporta():
    config = dict(PAGINA)
    config["campo_propio"] = 1
    assert _hallazgos(_regla("r1", atributo_xml=config)) == []


def test_prefijo_xpath_desconocido_se_detecta():
    hallazgos = _hallazgos(
        _regla("r1", atributo_xml={"parte": "document", "xpath": "//wp:ind"})
    )
    assert hallazgos
    assert any("wp" in h for h in hallazgos)


def test_prefijo_xpath_desconocido_antes_reventaba_en_runtime():
    from validator.compilador import CompilerDSL

    dsl = _dsl(_regla("r1", atributo_xml={"parte": "document", "xpath": "//wp:ind"}))
    compiladas = CompilerDSL().compilar(dsl, linter=False)
    assert len(compiladas) == 1, "sin linter la regla compila (y revienta al evaluar)"

    with pytest.raises(DSLValidationError):
        CompilerDSL().compilar(dsl)


@pytest.mark.parametrize(
    "xpath",
    [
        "//w:p[following-sibling::w:p]",
        "//w:p[preceding-sibling::w:tbl]",
        "//w:pgSz",
        "//a:blip",
        "//sectPr",
    ],
)
def test_xpath_valido_no_produce_hallazgo(xpath):
    assert _hallazgos(_regla("r1", atributo_xml={"parte": "document", "xpath": xpath})) == []


def test_prefijo_xpath_tambien_se_valida_en_paginacion():
    hallazgos = _hallazgos(
        _regla(
            "r1",
            paginacion={"xpaths": ["//wp:p", "//w:tbl"], "parrafo": "//w:p"},
        )
    )
    assert any("wp" in h for h in hallazgos)


def test_severidad_inventada_se_detecta():
    hallazgos = _hallazgos(_regla("r1", severidad="aviso"))
    assert hallazgos
    assert any("aviso" in h for h in hallazgos)


def test_severidad_inventada_antes_reventaba_en_runtime():
    from validator.compilador import CompilerDSL

    dsl = _dsl(_regla("r1", severidad="aviso"))
    CompilerDSL().compilar(dsl, linter=False)

    with pytest.raises(DSLValidationError):
        CompilerDSL().compilar(dsl)


@pytest.mark.parametrize("severidad", ["error", "warning"])
def test_severidad_valida_no_produce_hallazgo(severidad):
    assert _hallazgos(_regla("r1", severidad=severidad)) == []


DETECCION = {
    "id": "deteccion_tipo_documento",
    "tipo": "deteccion_tipo",
    "severidad": "error",
    "descripcion": "d",
    "deteccion_tipo": {
        "expone": "tipo_documento",
        "firmas": [
            {"tipo": "tinv_cuantitativo", "evidencia": ["cuantitativo"], "minimo": 1},
            {"tipo": "tinv_cualitativo", "evidencia": ["cualitativo"], "minimo": 1},
        ],
    },
}


def test_aplicar_si_con_valor_invalido_se_detecta():
    hallazgos = _hallazgos(
        DETECCION,
        _regla("consumidor", aplicar_si={"tipo_documento": "tinv_cuantiativo"}),
    )
    assert hallazgos
    assert any("tinv_cuantiativo" in h for h in hallazgos)


def test_aplicar_si_con_lista_de_valores_invalidos_se_detecta():
    hallazgos = _hallazgos(
        DETECCION,
        _regla("consumidor", aplicar_si={"tipo_documento": ["tinv_cuantitativo", "tinv_x"]}),
    )
    assert any("tinv_x" in h for h in hallazgos)


def test_aplicar_si_con_valor_valido_no_produce_hallazgo():
    assert (
        _hallazgos(
            DETECCION,
            _regla("consumidor", aplicar_si={"tipo_documento": "tinv_cuantitativo"}),
        )
        == []
    )


def test_aplicar_si_sobre_clave_no_documental_no_se_contrasta():
    assert (
        _hallazgos(
            _regla("expone", expone="mi_clave"),
            _regla("consumidor", aplicar_si={"mi_clave": "cualquier_cosa"}),
        )
        == []
    )


def test_id_duplicado_se_detecta():
    hallazgos = _hallazgos(_regla("dup"), _regla("dup"))
    assert hallazgos
    assert any("duplicado" in h for h in hallazgos)


def test_id_duplicado_antes_no_se_detectaba():
    assert len(linter(_dsl(_regla("dup"), _regla("dup")))) == 1


def test_ids_unicos_no_producen_hallazgo():
    assert _hallazgos(_regla("r1"), _regla("r2")) == []


@pytest.mark.parametrize(
    "archivo",
    ["reglas_unt.yaml", "reglas_unt_pendientes.yaml", "reglas_ficha.yaml"],
)
def test_yaml_de_produccion_pasa_el_linter(archivo):
    from pathlib import Path

    raiz = Path(__file__).resolve().parent.parent
    datos = yaml.safe_load((raiz / archivo).read_text(encoding="utf-8"))
    assert linter(datos) == [], f"{archivo} tiene hallazgos del linter"


def test_linter_o_alzar_mensaje_legible():
    with pytest.raises(DSLValidationError) as exc:
        linter_o_alzar(_dsl(_regla("dup"), _regla("dup")))
    assert "duplicado" in str(exc.value)
