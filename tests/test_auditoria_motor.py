"""Regresiones de la auditoría de motor de la semana 10 (AUD-01…AUD-03, AUD-20).

Blinda los arreglos con fixtures que reproducen la estructura real de las
plantillas:

- AUD-01: títulos del cuerpo que acaban en letra romana no deben perder su
  última letra al normalizarse (falso positivo de `indice_apunta_secciones`).
- AUD-02: los anexos se buscan hasta el final del documento y los Títulos1
  cuentan como texto (en las plantillas cada "Anexo N." es un Título1).
- AUD-03: al fallar `all_eq` el `found` muestra primero a los culpables y la
  `location` apunta a la página del nodo infractor, no a la del primero.

Uso:
    pytest tests/test_auditoria_motor.py -v
"""

import tempfile
import zipfile
from pathlib import Path

from docx_factory import (
    compilar_docx,
    configuracion_anexos_titulos,
    configuracion_base,
    configuracion_indice_tabs,
    configuracion_titulo_romano,
)

from validator.analizadores import _norm_indice, _norm_titulo_cuerpo, _sigpalabra
from validator.engine import load_rules, validate_docx

RULES = load_rules("reglas_unt.yaml")

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""


def _por_regla(resultados):
    return {r.rule_id: r for r in resultados}


def _sin_archivo(path: str):
    Path(path).unlink(missing_ok=True)


def test_norm_titulo_cuerpo_no_recorta_sufijo_de_palabra():
    """AUD-01: el título del cuerpo conserva su última letra."""
    assert _norm_titulo_cuerpo("General") == "GENERAL"
    assert _norm_titulo_cuerpo("GENERAL") == "GENERAL"


def test_norm_indice_recorta_pagina_pegada():
    """AUD-01: la página se recorta aunque venga pegada al título.

    Es la estructura real del índice de la tesis: `text_of()` ignora el
    tabulador y deja `1.2.1.General17`, `Dedicatoriaii`, `Resumenx`.
    """
    assert _norm_indice("1.2.1.General17") == "GENERAL"
    assert _norm_indice("Dedicatoriaii") == "DEDICATORIA"
    assert _norm_indice("Resumenx") == "RESUMEN"


def test_norm_indice_si_recorta_pagina_arabiga_y_romana():
    """AUD-01: con separador, la página también se recorta."""
    assert _norm_indice("1.4. OBJETIVOS 9") == "OBJETIVOS"
    assert _norm_indice("OBJETIVOS iv") == "OBJETIVOS"


def test_aud01_titulo_romano_apunta_a_seccion_real():
    """AUD-01/AUD-20: "GENERAL" del cuerpo y "1.4.1. GENERAL 9" del índice."""
    path = compilar_docx(configuracion_titulo_romano())
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["indice_apunta_secciones"].passed


def test_aud01_indice_con_tabuladores_reales():
    """AUD-01/AUD-20: índice con `w:tab` y páginas pegadas de una letra.

    Reproduce la estructura real: `1.4.1.<tab>GENERAL<tab>9` y
    `RESUMEN<tab>x`. Sin preservar el tabulador, la entrada se extraía
    pegada y no encontraba su sección.
    """
    path = compilar_docx(configuracion_indice_tabs())
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["indice_apunta_secciones"].passed, res["indice_apunta_secciones"].found
    assert res["indice_numeracion_jerarquica"].passed


def test_aud02_anexos_como_titulos_satisfacen_minimos():
    """AUD-02/AUD-20: los "Anexo N." como Título1 se detectan igual."""
    path = compilar_docx(configuracion_anexos_titulos())
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["anexos_minimos_cuantitativo"].passed


def test_aud02_reporta_todos_los_faltantes_sin_truncar():
    """AUD-02/AUD-20: `found` lista los 9 anexos faltantes (antes [:8])."""
    cfg = configuracion_anexos_titulos()
    cfg["anexos_items"] = []
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["anexos_minimos_cuantitativo"]
    assert not regla.passed
    # El noveno ítem obligatorio quedaría fuera con el truncado antiguo.
    assert "Carta de autorización de publicación" in regla.found


def _anexos_con(nombre: str | None) -> dict:
    """Fixture con el ítem 5 renombrado o eliminado (M6/VA-14).

    Un plan cuantitativo no lleva el anexo «Base de datos cualitativa»: se
    retira para que la ausencia del ítem 5 no quede oculta por esa cadena.
    """
    cfg = configuracion_anexos_titulos()
    items = cfg["anexos_items"]
    items.remove("Base de datos cuantitativa")
    items.remove("Base de datos cualitativa")
    if nombre is not None:
        items.insert(4, nombre)
    return cfg


def test_m6_reconoce_el_titulo_real_base_de_datos():
    """VA-14: la tesis real titula «Base de datos», no «... cuantitativa»."""
    path = compilar_docx(_anexos_con("Base de datos"))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["anexos_minimos_cuantitativo"]
    assert regla.passed, regla.found
    assert regla.severity.value == "warning"


def test_m6_informa_la_ausencia_del_anexo():
    """VA-14: si el anexo no está, la regla lo informa (no queda verde)."""
    path = compilar_docx(_anexos_con(None))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["anexos_minimos_cuantitativo"]
    assert not regla.passed
    assert "Base de datos" in regla.found
    assert "items_obligatorios=9" in regla.found


_RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_ANS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_PNS = "http://schemas.openxmlformats.org/drawingml/2006/picture"
_WPN = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"


def _docx_logo(
    logo: tuple[float, float] | None,
    cuerpo: tuple[float, float] | None = None,
) -> str:
    """Carátula delimitada por salto de sección, con dibujos opcionales.

    La carátula termina en el `w:pPr/w:sectPr` (primera sección), así que
    una imagen del cuerpo no pertenece a ella. Se usa en las regresiones
    M7/VA-15 para probar la delimitación sin depender del fixture grande.
    """

    def dibujo(cm: tuple[float, float]) -> str:
        cx, cy = (round(v * 360000) for v in cm)
        return (
            "<w:r><w:drawing><wp:inline>"
            f'<wp:extent cx="{cx}" cy="{cy}"/>'
            "<a:graphic><a:graphicData "
            'uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            '<pic:pic><pic:blipFill><a:blip r:embed="rIdImg"/></pic:blipFill>'
            "<pic:spPr/></pic:pic></a:graphicData></a:graphic></wp:inline>"
            "</w:drawing></w:r>"
        )

    paras = [_para_sz("UNIVERSIDAD NACIONAL DE TRUJILLO", "24")]
    if logo:
        paras.append(f"<w:p>{dibujo(logo)}</w:p>")
    paras.append("<w:p><w:pPr><w:sectPr/></w:pPr></w:p>")
    if cuerpo:
        paras.append(f"<w:p>{dibujo(cuerpo)}</w:p>")
    body = "".join(paras) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}" xmlns:r="{_RNS}" xmlns:a="{_ANS}" '
        f'xmlns:pic="{_PNS}" xmlns:wp="{_WPN}"><w:body>{body}</w:body></w:document>'
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def test_m7_logo_con_el_tamano_correcto_pasa():
    """VA-15: el logo de la carátula mide 6,73 × 4,84 cm."""
    path = _docx_logo((6.73, 4.84))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_logotipo_tamano"]
    assert regla.passed, regla.found
    assert regla.severity.value == "warning"


def test_m7_logo_con_tamano_incorrecto_genera_warning():
    """VA-15: la regla no puede anunciar un tamaño que no comprueba."""
    path = _docx_logo((5.0, 4.84))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_logotipo_tamano"]
    assert not regla.passed
    assert "incumplen=1" in regla.found
    assert "5.00x4.84" in regla.found


def test_m7_logo_solo_en_el_cuerpo_no_satisface_la_caratula():
    """VA-15: una imagen en el cuerpo no es el logo de la carátula."""
    path = _docx_logo(None, (6.73, 4.84))
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_logotipo_tamano"]
    assert not regla.passed
    assert "imagenes=0" in regla.found


def _para_sz(texto: str, sz: str) -> str:
    return (
        "<w:p><w:r><w:rPr>"
        '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
        f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
        "</w:rPr>"
        f'<w:t xml:space="preserve">{texto}</w:t></w:r></w:p>'
    )


def _p_break() -> str:
    return "<w:p><w:r><w:lastRenderedPageBreak/></w:r></w:p>"


def _docx_sz(paras: list[str]) -> str:
    body = "".join(paras) + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{body}</w:body></w:document>'
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def _docx_caratula(texto: str, sz: str) -> str:
    paras = [
        _para_sz("UNIVERSIDAD NACIONAL DE TRUJILLO", "24"),
        _para_sz(texto, sz),
    ]
    # El `w:pPr/w:sectPr` cierra la portada: los párrafos anteriores son la
    # carátula para `contexto: caratula`.
    body = (
        "".join(paras)
        + "<w:p><w:pPr><w:sectPr/></w:pPr></w:p>"
        + '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
    )
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{body}</w:body></w:document>'
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def _para_runs(runs: list[tuple[str, str]]) -> str:
    """Párrafo con varios runs; cada run lleva su texto y su `w:sz`."""
    out = ["<w:p>"]
    for texto, sz in runs:
        out.append(
            "<w:r><w:rPr>"
            '<w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman"/>'
            f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
            "</w:rPr>"
            f'<w:t xml:space="preserve">{texto}</w:t></w:r>'
        )
    out.append("</w:p>")
    return "".join(out)


def _docx_caratula_runs(paras: list[list[tuple[str, str]]]) -> str:
    """DOCX de carátula con párrafos de varios runs (texto, sz)."""
    body = "".join(_para_runs(p) for p in paras)
    body += "<w:p><w:pPr><w:sectPr/></w:pPr></w:p>"
    body += '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
    doc = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{body}</w:body></w:document>'
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def _regla_sz(comparacion: str = "all_eq", esperado: str = "24") -> dict:
    return {
        "id": "sz_test",
        "tipo": "atributo_xml",
        "descripcion": "Tamaño de letra del cuerpo",
        "valor_esperado": "12pt",
        "severidad": "error",
        "ubicacion": "Cuerpo",
        "fuente": "MANUAL.docx",
        "cita": '"Times New Roman: 12 puntos"',
        "atributo_xml": {
            "parte": "document",
            "contexto": "todos",
            "xpath": "//w:body/w:p/w:r/w:rPr/w:sz",
            "atributo": "@w:val",
            "comparacion": comparacion,
            "esperado": esperado,
        },
    }


def _validar_sz(comparacion: str, esperado: str):
    path = _docx_sz([_para_sz("A", "24"), _p_break(), _para_sz("B", "30"), _para_sz("C", "24")])
    try:
        return validate_docx(
            path, {"namespaces": {"w": WNS}, "reglas": [_regla_sz(comparacion, esperado)]}
        )[0]
    finally:
        _sin_archivo(path)


def test_aud03_culpables_primero_y_pagina_del_nodo_infractor():
    """AUD-03: los incumplimientos van primero y con la página del culpable."""
    r = _validar_sz("all_eq", "24")
    assert not r.passed
    assert r.found == (
        "@w:val: 3 valores evaluados, 1 incumplen: #2=15 pt (pág. 2); esperado=12 pt"
    )
    # El primer nodo (A) está en la página 1; el culpable (B) en la 2. La
    # página viene de la caché de render de Word: se declara estimada (M3).
    assert r.location == "Cuerpo; página 2 (estimada)"


def test_aud03_valores_en_puntos_sin_repr_crudo():
    """AUD-03: el valor se muestra en puntos, sin comillas de lista Python."""
    r = _validar_sz("eq", "26")
    assert not r.passed
    assert r.found == (
        "@w:val: 3 valores evaluados, 1 incumplen: #1=12 pt (pág. 1); esperado=13 pt"
    )


def test_aud05_valida_todos_los_autores_y_sus_runs():
    """AUD-05: el segundo autor (tras un ORCID) también se evalúa.

    Antes solo se leía el primer run del párrafo siguiente a «AUTORES:», así
    que un segundo autor con otro tamaño pasaba inadvertido. El asesor no
    entra: el bloque de autores termina en «ASESOR(A):».
    """
    path = _docx_caratula_runs(
        [
            [("UNIVERSIDAD NACIONAL DE TRUJILLO", "36")],
            [("AUTORES:", "24")],
            [("Br. Linares Azañero, Angie Lizbeth", "24")],
            [("https://orcid.org/0009-0000-0910-930X", "24")],
            [("Br. Morales Saldaña, Victor Alberto", "20")],
            [("https://orcid.org/0009-0006-6563-9579", "24")],
            [("ASESORA:", "24")],
            [("Dra. Vásquez Mondragón, Cecilia Del Pilar", "20")],
        ]
    )
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_autores_tamano"]
    assert not regla.passed
    assert regla.aplicable
    assert "1 incumplen" in regla.found
    assert "#3=10 pt" in regla.found


def test_aud05_ignora_runs_sin_texto_y_no_mira_al_asesor():
    """AUD-05: un run vacío inicial no se evalúa y el asesor no entra.

    El run vacío lleva 14 pt (sz 28) a propósito: si se leyera, la regla
    fallaría. El asesor lleva 10 pt (sz 20) para probar que el bloque de
    autores termina antes de «ASESOR(A):». Línea, ciudad y año se incluyen
    a 12 pt porque RI-08 también los mide en esta misma regla.
    """
    path = _docx_caratula_runs(
        [
            [("UNIVERSIDAD NACIONAL DE TRUJILLO", "36")],
            [("AUTORES:", "24")],
            [("", "28"), ("Ana María Pérez García", "24")],
            [("ASESORA:", "24")],
            [("Dra. Cecilia Del Pilar Vásquez Mondragón", "20")],
            [("Línea de Investigación:", "24")],
            [
                (
                    "Educación y Ciencias de la Comunicación y Desarrollo Sostenible",
                    "24",
                )
            ],
            [("Trujillo – Perú", "24")],
            [("2026", "24")],
        ]
    )
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_autores_tamano"]
    assert regla.passed, regla.found
    assert regla.found == "cumple"


def test_aud05_valida_los_runs_intermedios_del_mismo_autor():
    """AUD-05: si Word parte el nombre, se valida cada run con texto."""
    path = _docx_caratula_runs(
        [
            [("AUTORES:", "24")],
            [("Ana María ", "24"), ("Pérez García", "20")],
            [("ASESOR:", "24")],
        ]
    )
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_autores_tamano"]
    assert not regla.passed
    assert "1 incumplen" in regla.found
    assert "#2=10 pt" in regla.found


def test_aud06_entrada_sin_palabra_larga_se_omite():
    """AUD-06: sin token de 4+ caracteres no hay señal para verificar."""
    assert _sigpalabra("1.2 IV") == ""
    assert _sigpalabra("FASE I") == "FASE"


def test_aud06_igualdad_no_oculta_seccion_bajo_otro_titulo():
    """AUD-06: la subcadena ocultaba una sección faltante.

    La entrada «1.4. OBJETIVOS» coincide por subcadena con el título
    «OBJETIVOS ESPECÍFICOS», pero no apunta a esa sección. Con igualdad
    normalizada el faltante se reporta.
    """
    cfg = configuracion_base()
    cfg["headings"] = ["OBJETIVOS ESPECÍFICOS" if h == "OBJETIVOS" else h for h in cfg["headings"]]
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["indice_apunta_secciones"]
    assert not regla.passed
    assert "OBJETIVOS" in regla.found


def test_aud06_igualdad_normalizada_tolera_mayusculas_y_tildes():
    """AUD-06: la igualdad compara títulos normalizados, no el texto crudo."""
    cfg = configuracion_base()
    cfg["tdc_entradas"] = [
        (nivel, "2.2. Bases Teoricas 17" if texto == "2.2. BASES TEÓRICAS 17" else texto)
        for nivel, texto in cfg["tdc_entradas"]
    ]
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["indice_apunta_secciones"].passed, res["indice_apunta_secciones"].found


def test_aud06_entrada_corta_usa_el_respaldo_y_se_omite():
    """AUD-06: con menos de 4 caracteres no hay señal y se omite.

    El respaldo `_sigpalabra` conserva el auto-pase para entradas como
    «1.6. IV» que no alcanzan para exigir igualdad con un título.
    """
    cfg = configuracion_base()
    cfg["tdc_entradas"].append((2, "1.6. IV 40"))
    path = compilar_docx(cfg)
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    assert res["indice_apunta_secciones"].passed, res["indice_apunta_secciones"].found


def test_aud07_linea_bachiller_se_evalua():
    """AUD-07: la línea de Bachiller sí se compara contra los 13 pt."""
    path = _docx_caratula(
        "Trabajo de Investigación para optar el grado de Bachiller en Educación Inicial",
        "24",
    )
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_optar_grado_tamano"]
    assert not regla.passed
    assert regla.aplicable
    assert regla.found == (
        "w:sz/@w:val: 1 valores evaluados, 1 incumplen: #1=12 pt (pág. 1); esperado=13 pt"
    )


def test_aud07_otras_titulaciones_tambien_se_evaluan():
    """AUD-07: la línea de Licenciatura se evalúa y advierte el desvío.

    La tesis aprobada de la auditoría y las 5 plantillas oficiales usan 12 pt
    en esa línea, pero el manual exige 13 pt (párr. 1056 y 1076). La decisión
    del equipo (2026-11-08) es seguir el manual, así que la regla debe
    advertir (warning) en vez de declararse no aplicable.
    """
    path = _docx_caratula(
        "Para Optar el Título Profesional de Licenciada en Educación Inicial",
        "24",
    )
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_optar_grado_tamano"]
    assert not regla.passed
    assert regla.aplicable
    assert regla.found == (
        "w:sz/@w:val: 1 valores evaluados, 1 incumplen: #1=12 pt (pág. 1); esperado=13 pt"
    )


def test_aud07_sin_linea_para_optar_es_no_aplicable():
    """AUD-07: sin la línea "para optar", la regla sí queda como n/a.

    `n_a_si_sin_nodos` se conserva para los documentos que no llevan la
    línea; el camino n/a exige `aplicable=False` y el texto del contrato.
    """
    path = _docx_caratula("Documento sin la línea de grado", "24")
    try:
        res = _por_regla(validate_docx(path, RULES))
    finally:
        _sin_archivo(path)
    regla = res["caratula_optar_grado_tamano"]
    assert regla.passed
    assert not regla.aplicable
    assert regla.found == "no aplica a este documento"
