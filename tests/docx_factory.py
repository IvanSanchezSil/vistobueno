"""Factory determinista de DOCX sintéticos (Fase F6 — tests de propiedad).

Centraliza la construcción de documentos OPC (zip) de forma declarativa a
partir de un diccionario de configuración, de modo que los tests de propiedad
puedan pedir:

- `configuracion_base()`: el documento "bueno", que cumple TODAS las reglas
  mecánicas salvo las dos alternativas de estructura mutuamente excluyentes
  (cualitativo y revisión de literatura). Resultado esperado: 39/41.
- `aplicar_mutacion(rule_id, config)`: aplica un desvío MÍNIMO (una sola
  propiedad) contra el documento bueno, de forma que solo la regla
  `rule_id` cambie su resultado.

Los métodos de construcción reutilizan la semántica OPC ya usada en
`test_paridad_formatos.py` y `test_f3_mecanizacion.py`, sin depender de
esos archivos de test (es un módulo de soporte importable).

Uso desde tests:
    from docx_factory import configuracion_base, aplicar_mutacion, compilar_docx
"""
import tempfile
import zipfile
from pathlib import Path

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ANS = "http://schemas.openxmlformats.org/drawingml/2006/main"
PNS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
WPN = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Default Extension="png" ContentType="image/png"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rIdFooter" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer" Target="word/footer1.xml"/>
  <Relationship Id="rIdImg" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/logo.png"/>
  <Relationship Id="rIdOrc" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://orcid.org/0000-0002-1825-0097" TargetMode="External"/>
</Relationships>"""


# ---------------------------------------------------------------------------
# Nombres de las reglas de reglas_unt.yaml (41).
# ---------------------------------------------------------------------------

REGLAS = [
    "papel_tamano",
    "fuente_principal",
    "tamano_cuerpo",
    "caratula_universidad_tamano",
    "caratula_facultad_escuela_tamano",
    "caratula_titulo_trabajo_tamano",
    "caratula_optar_grado_tamano",
    "caratula_autores_tamano",
    "caratula_logotipo_tamano",
    "interlineado",
    "alineacion_cuerpo",
    "alineacion_caratula_todos_elementos",
    "margen_superior",
    "margen_inferior",
    "margen_derecho",
    "margen_izquierdo",
    "sangria_parrafo",
    "numeracion_posicion",
    "numeracion_preliminares_romano",
    "numeracion_cuerpo_arabigo",
    "caratula_no_se_enumera",
    "caratula_universidad_negrita_mayusculas",
    "caratula_facultad_negrita_mayusculas",
    "caratula_titulo_negrita_mixta",
    "caratula_autores_mayusculas_sin_negrita",
    "caratula_asesor_negrita",
    "caratula_ciudad_pais_negrita",
    "caratula_linea_investigacion",
    "estructura_tinv_cuantitativo",
    "estructura_tinv_cualitativo",
    "estructura_tinv_revision_literatura",
    "indice_subdivisiones",
    "resumen_longitud",
    "palabras_clave_minimo",
    "referencias_minimo_cuantitativo",
    "referencias_minimo_cualitativo",
    "referencias_minimo_revision",
    "anexos_minimos_cuantitativo",
    "anexos_minimos_cualitativo",
    "caratula_orcid",
    "proyecto_caratula_texto",
]

# Reglas cuyo mecanismo es IDÉNTICO entre sí (mismo conteo de nodos con la
# misma sección y mínimo): un desvío de cantidad las cambia a ambas a la vez.
# No existe un DOCX donde cambie solo una de ellas. Se documenta como
# exclusión de la propiedad "solo esa regla".
#
# - referencias_minimo_*_revision (mínimo 20) comparten conteo con la
#   cantidad mínima de referencias; al bajar una, caen los dos que usan 20 Y
#   el cualitativo (mínimo 30) porque 19 < 30. Los tres quedan acoplados.
# - caratula_universidad_negrita_mayusculas y caratula_ciudad_pais_negrita
#   seleccionan el MISMO párrafo: la línea "UNIVERSIDAD NACIONAL DE TRUJILLO"
#   contiene "trujillo", así que `[1]` de la regla de ciudad resuelve al
#   párrafo de la universidad. Un cambio de negrita en esa línea las afecta
#   a ambas (quirk del XPath heredado del reglamento).
REGLAS_ACOPLADAS = {
    "referencias_minimo_cuantitativo": {
        "referencias_minimo_cualitativo",
        "referencias_minimo_revision",
    },
    "referencias_minimo_revision": {
        "referencias_minimo_cuantitativo",
        "referencias_minimo_cualitativo",
    },
    "caratula_universidad_negrita_mayusculas": {"caratula_ciudad_pais_negrita"},
    "caratula_ciudad_pais_negrita": {"caratula_universidad_negrita_mayusculas"},
}

# Exclusión documentada: el documento base (plan tipo cuantitativo) no puede
# cumplir simultáneamente los esquemas alternativos (la estructura del
# documento define el tipo de investigación). Ver docs/PLAN_DSL.md, F6.
EXCLUIDAS_BASE = {"estructura_tinv_cualitativo", "estructura_tinv_revision_literatura"}

ANEXOS_BASE = [
    "Matriz de consistencia",
    "Instrumento(s) de recolección de datos",
    "Ficha técnica del instrumento",
    "Consentimiento informado",
    "Base de datos cuantitativa",
    "Reporte de similitud",
    "Carta de autorización institucional",
    "Declaración jurada",
    "Carta de autorización de publicación",
    "Juicio de expertos",
    "Base de datos cualitativa",
]

_HEADINGS_CUANT = [
    "DEDICATORIA",
    "JURADO EVALUADOR",
    "AGRADECIMIENTO",
    "ÍNDICE",
    "INDICE DE CONTENIDOS",
    "INDICE DE TABLAS",
    "INDICE DE FIGURAS",
    "PRESENTACIÓN",
    "RESUMEN",
    "ABSTRACT",
    "INTRODUCCIÓN",
    "1.3. EL PROBLEMA",
    "SITUACIÓN PROBLEMÁTICA",
    "ENUNCIADO DEL PROBLEMA",
    "JUSTIFICACIÓN O IMPORTANCIA",
    "OBJETIVOS",
    "1.5 VARIABLE(S) Y OPERACIONALIZACIÓN",
    "MARCO TEÓRICO",
    "ANTECEDENTES (ESTADO DEL ARTE)",
    "BASES TEÓRICAS",
    "METODOLOGÍA",
    "POBLACIÓN Y MUESTRA",
    "DISEÑO DE INVESTIGACIÓN",
    "INSTRUMENTO(S) USADO(S) EN LA RECOLECCIÓN DE DATOS",
    "MÉTODOS, TÉCNICAS Y PROCEDIMIENTOS USADOS EN EL ANÁLISIS E INTERPRETACIÓN DE DATOS",
    "RESULTADOS",
    "CONCLUSIONES",
    "REFERENCIAS",
    "ANEXOS",
]

# Cabeceras específicas del esquema cualitativo que, INSERTADAS entre las del
# plan cuantitativo, permiten reconocer AMBOS esquemas a la vez (el autómata
# salta las cabeceras que no matchean su transición actual).
_ANADIDAS_CUALITATIVO = [
    "CATEGORÍAS, MATRIZ DE CATEGORIZACIÓN Y UNIDAD DE ANÁLISIS",   # tras OBJETIVOS
    "PARTICIPANTES",                                               # tras METODOLOGÍA
    "INSTRUMENTOS USADOS EN LA RECOLECCIÓN DE INFORMACIÓN",        # tras DISEÑO DE INVESTIGACIÓN
    "MÉTODOS, TÉCNICAS, PROCEDIMIENTOS Y ESTRATEGIAS USADAS EN EL ANÁLISIS E INTERPRETACIÓN DE DATOS",  # tras MÉTODOS... DATOS
    "ANÁLISIS Y DISCUSIÓN DE RESULTADOS",                          # tras lo anterior
]

_ANADIDAS_REVISION = [
    ("INTRODUCCIÓN", "METODOLOGÍA DE REVISIÓN"),
    ("BASES TEÓRICAS", "DESARROLLO O ANÁLISIS CRÍTICO DE LA LITERATURA"),
    ("RESULTADOS", "CONCLUSIONES Y RECOMENDACIONES"),
]


# ---------------------------------------------------------------------------
# Helpers XML (portados de test_paridad_formatos / test_f3_mecanizacion).
# ---------------------------------------------------------------------------


def _run(texto: str, rpr_inner: str = "") -> str:
    rpr = f"<w:rPr>{rpr_inner}</w:rPr>" if rpr_inner else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{texto}</w:t></w:r>'


def _run_portada(spec: dict) -> str:
    rpr = ""
    if spec.get("negrita"):
        rpr += "<w:b/>"
    if spec.get("sz"):
        rpr += f'<w:sz w:val="{spec["sz"]}"/>'
    return _run(spec["texto"], rpr)


def _cover_para(spec: dict) -> str:
    """Párrafo de la portada con alineación controlada."""
    if spec.get("logo"):
        return f"<w:p>{_logo()}</w:p>"
    if spec.get("orcid"):
        return (
            f'<w:p><w:pPr><w:jc w:val="{spec.get("jc", "center")}"/></w:pPr>'
            f'<w:hyperlink r:id="rIdOrc" xmlns:r="{RNS}">'
            f"<w:r><w:t xml:space=\"preserve\">https://orcid.org/0000-0002-1825-0097</w:t></w:r>"
            f"</w:hyperlink></w:p>"
        )
    jc = spec.get("jc", "center")
    return f'<w:p><w:pPr><w:jc w:val="{jc}"/></w:pPr>{_run_portada(spec)}</w:p>'


def _body_para(texto: str) -> str:
    return f'<w:p>{_run(texto)}</w:p>'


def _cuerpo_para(texto: str, cfg: dict) -> str:
    """Párrafo de la última sección (contenido del cuerpo, estilos del manual)."""
    pPr = (
        f'<w:pPr><w:spacing w:line="{cfg["interlineado"]}" w:lineRule="auto"/>'
        f'<w:jc w:val="{cfg["jc_cuerpo"]}"/>'
        f'<w:ind w:firstLine="{cfg["sangria"]}"/></w:pPr>'
    )
    rpr = (
        f'<w:rFonts w:ascii="{cfg["fuente"]}" w:hAnsi="{cfg["fuente"]}"/>'
        f'<w:sz w:val="{cfg["sz_cuerpo"]}"/><w:szCs w:val="{cfg["sz_cuerpo"]}"/>'
    )
    return f"<w:p>{pPr}{_run(texto, rpr)}</w:p>"


def _nivel_heading(texto: str) -> int:
    if texto.startswith(("    ", "1.5 ")):
        return 3
    if texto.startswith("  "):
        return 2
    return 1


def _heading(texto: str) -> str:
    nivel = _nivel_heading(texto)
    return f'<w:p><w:pPr><w:pStyle w:val="Ttulo{nivel}"/></w:pPr>{_run(texto)}</w:p>'


def _logo() -> str:
    return (
        '<w:r><w:drawing><wp:inline><a:graphic><a:graphicData '
        f'uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:blipFill><a:blip r:embed="rIdImg"/></pic:blipFill>'
        "<pic:spPr/></pic:pic></a:graphicData></a:graphic></wp:inline>"
        "</w:drawing></w:r>"
    )


def _footer_xml(jc: str) -> str:
    if jc == "right":
        instr = (
            '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
            '<w:r><w:instrText xml:space="preserve"> PAGE \\* MERGEFORMAT </w:instrText></w:r>'
            '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        )
        texto = instr
    else:
        texto = '<w:r><w:t>UNIVERSIDAD</w:t></w:r>'
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:ftr xmlns:w="{WNS}">'
        f'<w:p><w:pPr><w:jc w:val="{jc}"/></w:pPr>{texto}'
        "</w:p></w:ftr>"
    )


# ---------------------------------------------------------------------------
# Configuración base del documento "bueno".
# ---------------------------------------------------------------------------


def configuracion_base() -> dict:
    """Devuelve la configuración del DOCX que pasa 39/41 reglas."""
    portada = {
        "univ": {"texto": "UNIVERSIDAD NACIONAL DE TRUJILLO", "negrita": True, "sz": 36},
        "logo": {"logo": True},
        "facultad": {"texto": "FACULTAD DE EDUCACIÓN Y CIENCIAS DE LA COMUNICACIÓN",
                     "negrita": True, "sz": 26},
        "escuela": {"texto": "ESCUELA PROFESIONAL DE EDUCACIÓN INICIAL",
                    "negrita": True, "sz": 26},
        "titulo": {"texto": "Título del trabajo de investigación: Estrategias lúdicas "
                            "para el desarrollo de la motricidad fina.",
                   "negrita": True, "sz": 28},
        "optar": {"texto": "Para optar el Grado de Bachiller en Educación Inicial",
                  "negrita": True, "sz": 26},
        "autores_label": {"texto": "Autores: ", "negrita": False, "sz": 24},
        "autores_nombre": {"texto": "ANA MARÍA PÉREZ GARCÍA", "negrita": False, "sz": 24},
        "asesor": {"texto": "Asesor(a): Mag. Carlos Alberto RODRÍGUEZ MIRANDA",
                   "negrita": True, "sz": 24},
        "linea_label": {"texto": "Línea de investigación: ", "negrita": False, "sz": 24},
        "linea": {"texto": "Educación y Ciencias de la Comunicación y Desarrollo Sostenible",
                  "negrita": False, "sz": 24},
        "ciudad": {"texto": "TRUJILLO - PERÚ, 2026", "negrita": True, "sz": 24},
        "proyecto": {"texto": "PROYECTO DE INVESTIGACIÓN", "negrita": False, "sz": 26},
        "orcid": {"orcid": True, "jc": "center"},
    }
    return {
        "portada": portada,
        "headings": list(_HEADINGS_CUANT),
        "fuente": "Times New Roman",
        "sz_cuerpo": 24,
        "interlineado": 360,
        "jc_cuerpo": "both",
        "sangria": 720,
        "margenes": {"top": 1418, "right": 1418, "bottom": 1418, "left": 1701},
        "pg": {"w": 11906, "h": 16838},
        "prel_numfmt": "lowerRoman",
        "final_numtype": None,
        "titlepg": True,
        "footer_jc": "right",
        "resumen_palabras": 175,
        "palabras_clave_n": 3,
        "referencias_n": 30,
        "anexos_items": list(ANEXOS_BASE),
    }


# ---------------------------------------------------------------------------
# Compilación del DOCX a partir de la configuración.
# ---------------------------------------------------------------------------


def _headings_insertadas(base: list, anadidas: list) -> list:
    """Inserta cabeceras nuevas después de un ancla, sin duplicar."""
    resultado = []
    for h in base:
        resultado.append(h)
        for ancla, nueva in anadidas:
            if h == ancla:
                resultado.append(nueva)
    return resultado


def _document_xml(cfg: dict) -> str:
    paras = []

    # Portada
    for spec in cfg["portada"].values():
        paras.append(_cover_para(spec))

    # Preliminares (resumen con su contenido, luego referencias y anexos)
    for h in cfg["headings"]:
        paras.append(_heading(h))
        if h == "RESUMEN":
            paras.append(_body_para(" ".join(f"resumen{i}" for i in range(cfg["resumen_palabras"]))))
            claves = ", ".join(f"clave{i}" for i in range(cfg["palabras_clave_n"]))
            paras.append(_body_para(f"Palabras clave: {claves}"))
        if h == "REFERENCIAS":
            paras.extend(
                _body_para(f"Autor, A. ({1990 + i}). Fuente bibliográfica {i}.")
                for i in range(cfg["referencias_n"])
            )
        if h == "ANEXOS":
            paras.extend(
                _body_para(f"Anexo {i + 1}. {item}")
                for i, item in enumerate(cfg["anexos_items"])
            )

    # Marcador de sección (fin de preliminares) y cuerpo
    paras.append(_sect_marker(cfg))
    paras.append(_cuerpo_para("La motricidad fina se desarrolla a través de estrategias lúdicas.", cfg))
    paras.append(_cuerpo_para("Se aplicó un estudio cuantitativo con diseño experimental.", cfg))
    paras.append(_cuerpo_para("Los resultados muestran una mejora significativa.", cfg))
    paras.append(_sect_final(cfg))

    body = "".join(paras)
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}" xmlns:r="{RNS}" xmlns:a="{ANS}" '
        f'xmlns:pic="{PNS}" xmlns:wp="{WPN}">'
        f"<w:body>{body}</w:body></w:document>"
    )


def _sect_marker(cfg: dict) -> str:
    m = cfg["margenes"]
    titlepg = "<w:titlePg/>" if cfg["titlepg"] else ""
    return (
        "<w:p><w:pPr><w:sectPr>"
        f'<w:pgSz w:w="{cfg["pg"]["w"]}" w:h="{cfg["pg"]["h"]}"/>'
        f'<w:pgMar w:top="{m["top"]}" w:right="{m["right"]}" '
        f'w:bottom="{m["bottom"]}" w:left="{m["left"]}"/>'
        f"{titlepg}{_footer_ref()}"
        f'<w:pgNumType w:fmt="{cfg["prel_numfmt"]}"/>'
        "</w:sectPr></w:pPr><w:r><w:t xml:space=\"preserve\"> </w:t></w:r></w:p>"
    )


def _footer_ref() -> str:
    return '<w:footerReference w:type="default" r:id="rIdFooter"/>'


def _sect_final(cfg: dict) -> str:
    m = cfg["margenes"]
    pgtype = f'<w:pgNumType w:fmt="{cfg["final_numtype"]}"/>' if cfg["final_numtype"] else ""
    return (
        "<w:sectPr>"
        f'<w:pgSz w:w="{cfg["pg"]["w"]}" w:h="{cfg["pg"]["h"]}"/>'
        f'<w:pgMar w:top="{m["top"]}" w:right="{m["right"]}" '
        f'w:bottom="{m["bottom"]}" w:left="{m["left"]}"/>'
        f"{_footer_ref()}{pgtype}"
        "</w:sectPr>"
    )


def compilar_docx(cfg: dict) -> str:
    """Compila la configuración a un DOCX temporal y devuelve la ruta."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", _document_xml(cfg))
        z.writestr("word/footer1.xml", _footer_xml(cfg["footer_jc"]))
    return path


# ---------------------------------------------------------------------------
# Mutaciones: un desvío mínimo por regla.
# ---------------------------------------------------------------------------


def aplicar_mutacion(rule_id: str, cfg: dict) -> dict:
    """Devuelve una copia de `cfg` con el desvío mínimo para `rule_id`.

    Levanta `KeyError` si la regla no tiene mutación definida.
    """
    nuevo = _copia(cfg)
    _MUTACIONES[rule_id](nuevo)
    return nuevo


def _copia(cfg: dict) -> dict:
    import copy

    return copy.deepcopy(cfg)


def _mut_margen(attr: str):
    def _f(cfg: dict) -> None:
        cfg["margenes"][attr] = 1300

    return _f


def _renombrar_heading(cfg: dict, actual: str, nuevo: str) -> None:
    cfg["headings"] = [nuevo if h == actual else h for h in cfg["headings"]]


def _interleaved_cualitativo() -> list:
    """Plan cuantitativo + cabeceras del esquema cualitativo intercaladas."""
    res = []
    for h in _HEADINGS_CUANT:
        res.append(h)
        if h == "OBJETIVOS":
            res.append("CATEGORÍAS, MATRIZ DE CATEGORIZACIÓN Y UNIDAD DE ANÁLISIS")
        if h == "METODOLOGÍA":
            res.append("PARTICIPANTES")
        if h == "DISEÑO DE INVESTIGACIÓN":
            res.append("INSTRUMENTOS USADOS EN LA RECOLECCIÓN DE INFORMACIÓN")
        if h == "MÉTODOS, TÉCNICAS Y PROCEDIMIENTOS USADOS EN EL ANÁLISIS E INTERPRETACIÓN DE DATOS":
            res.append("MÉTODOS, TÉCNICAS, PROCEDIMIENTOS Y ESTRATEGIAS USADAS EN EL ANÁLISIS E INTERPRETACIÓN DE DATOS")
            res.append("ANÁLISIS Y DISCUSIÓN DE RESULTADOS")
    return res


_MUTACIONES = {
    "papel_tamano": lambda c: c["pg"].update(w=10000),
    "fuente_principal": lambda c: c.update(fuente="Arial"),
    "tamano_cuerpo": lambda c: c.update(sz_cuerpo=30),
    "caratula_universidad_tamano": lambda c: c["portada"]["univ"].update(sz=24),
    "caratula_facultad_escuela_tamano": lambda c: c["portada"]["facultad"].update(sz=20),
    "caratula_titulo_trabajo_tamano": lambda c: c["portada"]["titulo"].update(sz=26),
    "caratula_optar_grado_tamano": lambda c: c["portada"]["optar"].update(sz=24),
    "caratula_autores_tamano": lambda c: c["portada"]["autores_nombre"].update(sz=30),
    "caratula_logotipo_tamano": lambda c: c["portada"].pop("logo"),
    "interlineado": lambda c: c.update(interlineado=300),
    "alineacion_cuerpo": lambda c: c.update(jc_cuerpo="left"),
    "alineacion_caratula_todos_elementos": lambda c: c["portada"]["asesor"].update(jc="left"),
    "margen_superior": _mut_margen("top"),
    "margen_inferior": _mut_margen("bottom"),
    "margen_derecho": _mut_margen("right"),
    "margen_izquierdo": _mut_margen("left"),
    "sangria_parrafo": lambda c: c.update(sangria=0),
    "numeracion_posicion": lambda c: c.update(footer_jc="center"),
    "numeracion_preliminares_romano": lambda c: c.update(prel_numfmt="decimal"),
    "numeracion_cuerpo_arabigo": lambda c: c.update(final_numtype="decimal"),
    "caratula_no_se_enumera": lambda c: c.update(titlepg=False),
    "caratula_universidad_negrita_mayusculas": lambda c: c["portada"]["univ"].update(negrita=False),
    "caratula_facultad_negrita_mayusculas": lambda c: c["portada"]["facultad"].update(negrita=False),
    "caratula_titulo_negrita_mixta": lambda c: c["portada"]["titulo"].update(negrita=False),
    "caratula_autores_mayusculas_sin_negrita": lambda c: c["portada"]["autores_nombre"].update(negrita=True),
    "caratula_asesor_negrita": lambda c: c["portada"]["asesor"].update(negrita=False),
    "caratula_ciudad_pais_negrita": lambda c: c["portada"]["univ"].update(negrita=False),
    "caratula_linea_investigacion": lambda c: c["portada"]["linea"].update(texto="Tecnologías disruptivas"),
    "estructura_tinv_cuantitativo": lambda c: _renombrar_heading(c, "SITUACIÓN PROBLEMÁTICA", "PROBLEMÁTICA Y CONTEXTO"),
    "estructura_tinv_cualitativo": lambda c: c.update(headings=_interleaved_cualitativo()),
    "estructura_tinv_revision_literatura": lambda c: c.update(
        headings=_headings_insertadas(_HEADINGS_CUANT, _ANADIDAS_REVISION)
    ),
    "indice_subdivisiones": lambda c: _renombrar_heading(c, "INDICE DE CONTENIDOS", "ÍNDICE GENERAL"),
    "resumen_longitud": lambda c: c.update(resumen_palabras=60),
    "palabras_clave_minimo": lambda c: c.update(palabras_clave_n=2),
    "referencias_minimo_cuantitativo": lambda c: c.update(referencias_n=19),
    "referencias_minimo_cualitativo": lambda c: c.update(referencias_n=29),
    "referencias_minimo_revision": lambda c: c.update(referencias_n=19),
    "anexos_minimos_cuantitativo": lambda c: c["anexos_items"].remove("Reporte de similitud"),
    "anexos_minimos_cualitativo": lambda c: c["anexos_items"].remove("Juicio de expertos"),
    "caratula_orcid": lambda c: c["portada"].pop("orcid"),
    "proyecto_caratula_texto": lambda c: c["portada"]["proyecto"].update(sz=24),
}


def resultado_por_regla(resultados):
    return {r.rule_id: r for r in resultados}


# Conveniencia: exposición del resultado esperado del documento base.
DESVIOS_BASE = len(EXCLUIDAS_BASE)
TOTAL_REGLAS = len(REGLAS)
REGLAS_OK_BASE = TOTAL_REGLAS - DESVIOS_BASE