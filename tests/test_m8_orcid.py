"""M8/VA-16: ORCID por persona, dígito de control y destino del vínculo.

El manual exige que **cada autor y el asesor** muestren su ORCID como
hipervínculo debajo del nombre (párr. 179-180). La regla `caratula_orcid`
ya no se conforma con un único enlace global: valida el dígito de control
ISO 7064 MOD 11-2 (admite ``X``), que el destino apunte al mismo perfil y
que cada persona de la carátula tenga su enlace.

La identidad del perfil no se verifica por red (fuera de alcance).
"""

import re
from pathlib import Path

import pytest
from docx_factory import compilar_docx, configuracion_base

from validator import orcid
from validator.engine import load_rules, validate_docx
from validator.extractor import extract

RULES = load_rules("reglas_unt.yaml")

ORCID_AUTOR = "https://orcid.org/0000-0002-1825-0097"
ORCID_ASESOR = "https://orcid.org/0000-0002-1694-233X"


def _resultado(cfg: dict):
    """Resultado de `caratula_orcid` para un DOCX compilado desde `cfg`."""
    path = compilar_docx(cfg)
    try:
        return next(r for r in validate_docx(path, RULES) if r.rule_id == "caratula_orcid")
    finally:
        Path(path).unlink(missing_ok=True)


def _insertar_despues(portada: dict, ancla: str, clave: str, spec: dict) -> dict:
    """Copia `portada` insertando `clave` justo después de `ancla`."""
    nueva = {}
    for nombre, valor in portada.items():
        nueva[nombre] = valor
        if nombre == ancla:
            nueva[clave] = spec
    return nueva


# ---------------------------------------------------------------------------
# Unidad: extracción, checksum y destino
# ---------------------------------------------------------------------------


def test_extraer_normaliza_el_identificador_y_la_x():
    assert orcid.extraer(f"({ORCID_AUTOR})") == "0000-0002-1825-0097"
    assert orcid.extraer("https://orcid.org/0000-0002-1694-233x") == "0000-0002-1694-233X"
    assert orcid.extraer("sin identificador") is None


@pytest.mark.parametrize(
    "identificador",
    [
        "0000-0002-1825-0097",
        "0000-0002-1694-233X",
        "0009-0000-0910-930X",
        "0009-0006-6563-9579",
    ],
)
def test_checksum_acepta_identificadores_validos(identificador):
    assert orcid.checksum_valido(identificador) is True


@pytest.mark.parametrize(
    "identificador",
    ["0000-0000-0000-0000", "0000-0000-0000-0002", "0000-0002-1825-0098"],
)
def test_checksum_rechaza_identificadores_invalidos(identificador):
    assert orcid.checksum_valido(identificador) is False


def test_destino_corresponde_exige_el_mismo_perfil_y_dominio():
    assert orcid.destino_corresponde(ORCID_AUTOR, "0000-0002-1825-0097") is True
    assert orcid.destino_corresponde("http://orcid.org/0000-0002-1825-0097", "0000-0002-1825-0097")
    assert orcid.destino_corresponde(ORCID_ASESOR, "0000-0002-1825-0097") is False
    assert (
        orcid.destino_corresponde("https://example.org/0000-0002-1825-0097", "0000-0002-1825-0097")
        is False
    )
    assert orcid.destino_corresponde(None, "0000-0002-1825-0097") is False


def test_revisar_caratula_lee_la_estructura_real_por_personas():
    """Etiqueta en un párrafo, nombre en el siguiente y ORCID intercalado."""
    parrafos = [
        ("AUTORES:", False),
        ("Br. Pérez, Ana", False),
        (ORCID_AUTOR, True),
        ("ASESORA:", False),
        ("Dra. Ruiz, María", False),
        (ORCID_ASESOR, True),
        ("Línea de investigación: Educación", False),
    ]
    assert orcid.revisar_caratula(parrafos) == (2, [])


def test_revisar_caratula_acepta_la_etiqueta_orcid():
    """Algunas plantillas escriben «ORCID:» delante del identificador."""
    parrafos = [
        ("AUTORA:", False),
        ("Br. Pérez, Ana", False),
        (f"ORCID: {ORCID_AUTOR}", True),
        ("Línea de investigación: Educación", False),
    ]
    assert orcid.revisar_caratula(parrafos) == (1, [])


def test_revisar_caratula_informa_la_persona_sin_orcid():
    parrafos = [
        ("AUTORES:", False),
        ("Br. Pérez, Ana", False),
        (ORCID_AUTOR, True),
        ("ASESORA:", False),
        ("Dra. Ruiz, María", False),
        ("Línea de investigación: Educación", False),
    ]
    total, faltan = orcid.revisar_caratula(parrafos)
    assert total == 2
    assert faltan == ["Dra. Ruiz, María"]


# ---------------------------------------------------------------------------
# Extractor: relaciones del paquete
# ---------------------------------------------------------------------------


def test_extractor_resuelve_el_destino_de_cada_orcid():
    path = compilar_docx(configuracion_base())
    try:
        extraido = extract(path)
    finally:
        Path(path).unlink(missing_ok=True)

    assert extraido.destino_relacion("rIdOrc") == ORCID_AUTOR
    assert extraido.destino_relacion("rIdOrc2") == ORCID_ASESOR
    assert extraido.destino_relacion("rIdInexistente") is None


# ---------------------------------------------------------------------------
# Integración: regla `caratula_orcid` del YAML real
# ---------------------------------------------------------------------------


def test_documento_base_cumple_por_persona():
    resultado = _resultado(configuracion_base())
    assert resultado.passed is True


def test_falta_un_autor_sin_orcid():
    """Dos autores: el segundo no tiene su línea ORCID."""
    cfg = configuracion_base()
    cfg["portada"] = _insertar_despues(
        cfg["portada"],
        "orcid_autor",
        "autores_nombre2",
        {"texto": "Luis Alberto Gómez Ruiz", "negrita": False, "sz": 24},
    )
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "sin_orcid=" in resultado.found
    assert "Luis Alberto Gómez Ruiz" in resultado.found


def test_solo_hay_orcid_del_asesor():
    cfg = configuracion_base()
    cfg["portada"].pop("orcid_autor")
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "sin_orcid=" in resultado.found
    assert "Ana María Pérez García" in resultado.found


def test_texto_correcto_con_destino_falso():
    cfg = configuracion_base()
    cfg["portada"]["orcid_autor"]["destino"] = ORCID_ASESOR
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "destino" in resultado.found


def test_orcid_valido_terminado_en_x():
    cfg = configuracion_base()
    valido_x = "https://orcid.org/0009-0000-0910-930X"
    cfg["portada"]["orcid_autor"].update(texto=valido_x, destino=valido_x)
    resultado = _resultado(cfg)
    assert resultado.passed is True


def test_checksum_incorrecto():
    cfg = configuracion_base()
    invalido = "https://orcid.org/0000-0000-0000-0000"
    cfg["portada"]["orcid_autor"].update(texto=invalido, destino=invalido)
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "checksum" in resultado.found


def test_linea_orcid_sin_hipervinculo_no_satisface():
    cfg = configuracion_base()
    cfg["portada"]["orcid_autor"] = {"texto": ORCID_AUTOR, "sz": 24}
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "sin_orcid=" in resultado.found
    assert "Ana María Pérez García" in resultado.found


# ---------------------------------------------------------------------------
# Revisión de #115: forma del manual, delimitación de carátula y detalle
# ---------------------------------------------------------------------------


def _config_con_codigo_entre_parentesis(texto: str, destino: str) -> dict:
    """Texto visible entre paréntesis, tal como lo pide el manual (párr. 179)."""
    cfg = configuracion_base()
    cfg["portada"]["orcid_autor"].update(texto=f"({texto})", destino=destino)
    return cfg


def test_codigo_orcid_entre_parentesis_con_destino_correcto_pasa():
    """Antes el `patron` de URL no veía el código: falso rojo."""
    identificador = "0000-0002-1825-0097"
    resultado = _resultado(_config_con_codigo_entre_parentesis(identificador, ORCID_AUTOR))
    assert resultado.passed is True
    assert "invalidos=" not in resultado.found
    assert "sin_orcid=" not in resultado.found


def test_codigo_orcid_entre_parentesis_con_destino_ajeno_falla():
    """Antes no se validaba el destino: falso verde."""
    identificador = "0000-0002-1825-0097"
    cfg = _config_con_codigo_entre_parentesis(identificador, ORCID_ASESOR)
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "destino" in resultado.found


def test_codigo_orcid_entre_parentesis_con_checksum_invalido_falla():
    """Antes no se validaba el checksum: falso verde."""
    identificador = "0000-0000-0000-0000"
    cfg = _config_con_codigo_entre_parentesis(identificador, f"https://orcid.org/{identificador}")
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "checksum" in resultado.found


def test_referencias_no_abren_un_bloque_de_autores():
    """«Autor, A. (1990)…» no tiene la etiqueta `AUTORES:` del manual."""
    parrafos = [
        ("Autor, A. (1990). Fuente bibliográfica.", False),
        ("Bautista, B. (1991). Otra fuente.", False),
    ]
    assert orcid.revisar_caratula(parrafos) == (0, [])


def test_nota_de_plantilla_entre_parentesis_no_es_persona():
    """Estructura medida en las plantillas oficiales (2026-11-19)."""
    parrafos = [
        ("AUTORA:", False),
        ("Br. Apellidos completos, Nombres completos", False),
        (ORCID_AUTOR, True),
        ("(en caso de un autor(a) adicional, ubicar en orden alfabético)", False),
        ("ASESORA:", False),
        ("(Dr. o Mg. o Lic.) (Apellidos completos, Nombres completos)", False),
        (ORCID_ASESOR, True),
        ("Línea de Investigación", False),
    ]
    assert orcid.revisar_caratula(parrafos) == (1, [])


@pytest.mark.parametrize("etiqueta", ["ANEXOS", "JURADO", "REFERENCIAS", "PRESENTACIÓN"])
def test_etiquetas_posteriores_cierran_el_bloque(etiqueta):
    """Sin salto de sección, estas etiquetas cortan la cuenta de personas."""
    parrafos = [
        ("AUTORES:", False),
        ("Br. Pérez, Ana", False),
        (etiqueta, False),
        ("Texto que no es una persona", False),
    ]
    total, faltan = orcid.revisar_caratula(parrafos)
    assert total == 1
    assert faltan == ["Br. Pérez, Ana"]


def test_linea_orcid_acepta_codigo_y_punto_final():
    """Variante escrita por plantillas: «Código ORCID: (…).»"""
    parrafos = [
        ("AUTORA:", False),
        ("Br. Pérez, Ana", False),
        (f"Código ORCID: ({ORCID_AUTOR}).", True),
        ("Línea de investigación: Educación", False),
    ]
    assert orcid.revisar_caratula(parrafos) == (1, [])


def test_orcid_del_cuerpo_no_satisface_la_regla_de_caratula():
    """`contexto: caratula` solo rige con la carátula delimitada por `sectPr`."""
    cfg = configuracion_base()
    cfg["portada"].pop("orcid_autor")
    cfg["portada"].pop("orcid_asesor")
    cfg["cuerpo_hipervinculo"] = {"texto": ORCID_AUTOR}

    # Sin el salto de sección, `is_caratula` cubre casi todo el documento y
    # el enlace del cuerpo se cuenta como si fuera de la portada.
    sin_delimitar = _resultado(cfg)
    assert int(re.search(r"hipervinculos=(\d+)", sin_delimitar.found).group(1)) > 0

    cfg["caratula_con_sect"] = True
    delimitada = _resultado(cfg)
    assert delimitada.passed is False
    assert "hipervinculos=0" in delimitada.found
    assert "personas=2" in delimitada.found
    assert "sin_orcid=" in delimitada.found


def test_detalle_de_personas_va_acotado():
    """El detalle no puede crecer sin límite con `repr` de muchos nombres."""
    cfg = configuracion_base()
    cfg["portada"].pop("orcid_autor")
    for i in range(12):
        cfg["portada"] = _insertar_despues(
            cfg["portada"],
            "autores_nombre" if i == 0 else f"autor_extra_{i - 1}",
            f"autor_extra_{i}",
            {"texto": f"Autor sin ORCID número {i} con un nombre bastante largo", "sz": 24},
        )
    resultado = _resultado(cfg)
    assert resultado.passed is False
    assert "[" not in resultado.found
    assert "más" in resultado.found
