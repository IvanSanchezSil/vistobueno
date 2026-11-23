"""Contrato de captura de la ficha de depósito (auditoría 2026-10-26).

La ficha pre-llena el formulario oficial de DSpace y alimenta las
constancias y el registro: si la captura parte un autor en dos o se
queda vacía, el papeleo sale mal (y el operador no ve el error).

Este archivo fija el **criterio de aceptación** de los hallazgos del
motor (AUD-24, AUD-25, AUD-26, AUD-27) sobre un DOCX con la
**estructura real** de la carátula (ver `tests/_caratula_real.py`): la
etiqueta `AUTORES:` en su propio párrafo, un autor por párrafo, líneas
de ORCID intercaladas, la etiqueta `ASESORA:` en su propio párrafo y el
año en la última línea de la portada.

Los criterios de aceptación quedaron cubiertos por el arreglo de Int3
(semana 11): las capturas se contrastan aquí contra la estructura real,
no contra el factory idealizado (AUD-20). Los casos del ORCID del asesor
los agrega Int3 en el PR 1 del reparto de 2026-11-23 con autorización de
retblast, para que ese PR sea integrable por sí solo.

Uso:
    pytest tests/test_captura_ficha.py -v
"""

from pathlib import Path

import pytest
from _caratula_real import capturar_ficha, crear_docx_caratula, valor

from validator.api import _ficha_desde_reporte


@pytest.fixture(scope="module")
def ficha() -> dict:
    """Las capturas que publica el motor para el DOCX de carátula real."""
    ruta = crear_docx_caratula()
    try:
        return capturar_ficha(ruta)
    finally:
        Path(ruta).unlink(missing_ok=True)


def _ficha_de(portada: list[str], **kwargs) -> dict:
    """Captura la ficha de una portada alternativa (casos límite del PR #75)."""
    ruta = crear_docx_caratula(portada=portada, **kwargs)
    try:
        return capturar_ficha(ruta)
    finally:
        Path(ruta).unlink(missing_ok=True)


# Portada mínima realista: título, "para optar" (lo usa la regla del título)
# y autores. El resto de líneas lo agrega cada test.
def _portada(*lineas: str) -> list[str]:
    return [
        "UNIVERSIDAD NACIONAL DE TRUJILLO",
        "FACULTAD DE EDUCACIÓN Y CIENCIAS DE LA COMUNICACIÓN",
        "Título del trabajo de investigación: Estrategias lúdicas, Trujillo 2024",
        "TESIS",
        "Para Optar el Título Profesional de Licenciado en Educación Primaria",
        *lineas,
    ]


# ---------------------------------------------------------------------------
# AUD-24 — los autores se parten por la coma de "Apellidos, Nombres"
# ---------------------------------------------------------------------------


def test_autores_un_por_parrafo(ficha):
    """Dos párrafos de autor → DOS autores, sin partir por la coma."""
    assert valor(ficha, "dc.contributor.author") == [
        "Br. Apellido, Nombre",
        "Br. Apellido2, Nombre2",
    ]


# ---------------------------------------------------------------------------
# AUD-25 — el asesor llega vacío marcado como detectado
# ---------------------------------------------------------------------------


def test_asesor_toma_el_parrafo_siguiente(ficha):
    """El asesor es el párrafo que sigue a la etiqueta."""
    assert valor(ficha, "dc.contributor.advisor") == "Dra. Apellido, Nombre"


# ---------------------------------------------------------------------------
# AUD-26 — el año se lee del final del título
# ---------------------------------------------------------------------------


def test_anio_toma_el_anio_de_portada(ficha):
    """El año es el de la portada (2026), no el que aparece en el título."""
    assert valor(ficha, "dc.date.issued") == "2026"


# ---------------------------------------------------------------------------
# AUD-27 — la última palabra clave conserva el punto final
# ---------------------------------------------------------------------------


def test_palabras_clave_sin_puntuacion_final(ficha):
    """Las palabras clave van limpias de puntuación final."""
    assert valor(ficha, "dc.subject") == ["Educación", "Cultura", "Identidad cultural"]


# ---------------------------------------------------------------------------
# Título y resumen: el prefijo se recorta y la sección se encuentra
# ---------------------------------------------------------------------------


def test_titulo_sin_prefijo(ficha):
    """El título llega sin la etiqueta «Título del trabajo de investigación:»."""
    titulo = valor(ficha, "dc.title")
    assert titulo == (
        "Estrategias lúdicas para mejorar la identidad cultural en estudiantes "
        "de primaria de una institución educativa, Trujillo 2024"
    )
    assert "Título del trabajo de investigación" not in titulo


def test_resumen_capturado(ficha):
    """El abstract es el texto de la sección RESUMEN, no la carátula."""
    assert valor(ficha, "dc.description.abstract") == (
        "El presente estudio analiza la relación entre las estrategias lúdicas "
        "y la identidad cultural en estudiantes de primaria."
    )


# ---------------------------------------------------------------------------
# Revisión del PR #75 — casos límite de la carátula
# ---------------------------------------------------------------------------


def test_autores_cortan_en_linea_con_tilde_sin_asesor():
    """«Línea de Investigación:» (con tilde) corta aunque no haya ASESOR.

    Antes el `translate` solo normalizaba mayúsculas: la comparación
    `'linea'` no casaba con «línea» y la captura seguía hasta el final de la
    carátula, tomando la línea, el año y el resumen como autores.
    """
    ficha = _ficha_de(
        _portada(
            "AUTORES:",
            "Br. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación y Ciencias de la Comunicación y Desarrollo Sostenible",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.author") == ["Br. Apellido, Nombre"]


@pytest.mark.parametrize("etiqueta", ["AUTORES:", "AUTORA:"])
def test_autores_en_el_mismo_parrafo_de_la_etiqueta(etiqueta):
    """«AUTORES: Br. Apellido, Nombre» no pierde al primer autor."""
    ficha = _ficha_de(
        _portada(
            f"{etiqueta} Br. Apellido, Nombre",
            "ASESORA:",
            "Dra. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.author") == ["Br. Apellido, Nombre"]


def test_asesor_salta_parrafos_vacios():
    """Un párrafo vacío entre «ASESORA:» y el nombre no pierde al asesor."""
    ficha = _ficha_de(
        _portada(
            "AUTORES:",
            "Br. Apellido, Nombre",
            "ASESORA:",
            "",
            "Dra. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.advisor") == "Dra. Apellido, Nombre"


def test_anio_ignora_referencias_sin_salto_de_seccion():
    """Sin `sectPr`, una referencia «López, J. 2024.» no le gana al año.

    El fixture de python-docx no trae saltos de sección, así que
    `caratula_ficha` cae al fallback: se corta en el primer encabezado
    (RESUMEN/REFERENCIAS) y las referencias quedan fuera del contexto.
    """
    ficha = _ficha_de(
        _portada(
            "AUTORES:",
            "Br. Apellido, Nombre",
            "ASESORA:",
            "Dra. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        ),
        referencias=["López, J. 2024."],
    )
    assert valor(ficha, "dc.date.issued") == "2026"


def test_autor_a_en_el_mismo_parrafo_no_publica_la_etiqueta():
    """«AUTOR(A): Br. Apellido, Nombre» captura el nombre, no la etiqueta.

    Es el caso de un template lleno: si el prefijo no cubre «AUTOR(A):», la
    ficha publica la etiqueta como autor y la constancia sale falsa.
    """
    ficha = _ficha_de(
        _portada(
            "AUTOR(A): Br. Apellido, Nombre",
            "ASESOR(A):",
            "Dra. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.author") == ["Br. Apellido, Nombre"]


def test_estructura_de_los_templates_oficiales():
    """Las plantillas oficiales usan «Título del trabajo:» y «AUTOR(A):».

    Seguimiento del PR #75: el prefijo del título solo cubría la variante
    «de investigación» y el de autores no cubría «AUTOR(A):». En un template
    lleno, la etiqueta se publicaba como un autor falso.
    """
    ficha = _ficha_de(
        [
            "UNIVERSIDAD NACIONAL DE TRUJILLO",
            "FACULTAD DE EDUCACIÓN Y CIENCIAS DE LA COMUNICACIÓN",
            "ESCUELA PROFESIONAL DE EDUCACIÓN PRIMARIA",
            "Título del trabajo: Título de la investigación",
            "TESIS",
            "Para Optar el Título Profesional de Licenciado en Educación Primaria",
            "AUTOR(A):",
            "(Apellidos completos, Nombres completos)",
            "ASESOR(A):",
            "(Dr. o Mg. o Lic.) (Apellidos completos, Nombres completos)",
            "Línea de Investigación:",
            "Educación y Ciencias de la Comunicación y Desarrollo Sostenible",
            "Trujillo – Perú",
            "2026",
        ]
    )
    assert valor(ficha, "dc.title") == "Título de la investigación"
    assert valor(ficha, "dc.contributor.author") is None
    assert ficha["dc.contributor.author"]["detectado"] is False


# ---------------------------------------------------------------------------
# ORCID del asesor — decisión 2026-11-23 (PR 1 del reparto con Int1 e Int2)
# ---------------------------------------------------------------------------


def _detectado(ficha: dict, campo: str) -> bool:
    """Estado publicado por el motor; un campo ausente cuenta como no detectado."""
    return bool((ficha.get(campo) or {}).get("detectado", False))


def test_orcid_asesor_en_parrafo_propio_bajo_la_etiqueta(ficha):
    """La línea de ORCID que sigue al nombre del asesor se captura aparte."""
    assert valor(ficha, "renati.advisor.orcid") == "0000-0000-0000-0002"
    assert _detectado(ficha, "renati.advisor.orcid") is True
    assert valor(ficha, "dc.contributor.advisor") == "Dra. Apellido, Nombre"


def test_orcid_asesor_en_el_mismo_parrafo_que_el_nombre():
    """«ASESORA: Nombre ORCID» captura nombre y ORCID sin pegarlos."""
    ficha = _ficha_de(
        _portada(
            "AUTORES:",
            "Br. Apellido, Nombre",
            "ASESORA: Dra. Apellido, Nombre https://orcid.org/0000-0000-0000-0002",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.advisor") == "Dra. Apellido, Nombre"
    assert valor(ficha, "renati.advisor.orcid") == "0000-0000-0000-0002"


def test_asesor_sin_nombre_solo_orcid_no_publica_el_orcid_como_nombre():
    """Sin nombre, el asesor queda no detectado y el ORCID sí se publica."""
    ficha = _ficha_de(
        _portada(
            "AUTORES:",
            "Br. Apellido, Nombre",
            "ASESORA:",
            "https://orcid.org/0000-0000-0000-0002",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.advisor") is None
    assert _detectado(ficha, "dc.contributor.advisor") is False
    assert valor(ficha, "renati.advisor.orcid") == "0000-0000-0000-0002"


def test_autor_y_orcid_en_el_mismo_parrafo_se_captura_sin_el_orcid():
    """El autor no desaparece por llevar su ORCID en el mismo párrafo."""
    ficha = _ficha_de(
        _portada(
            "AUTORES:",
            "Br. Apellido, Nombre https://orcid.org/0000-0000-0000-0000",
            "ASESORA:",
            "Dra. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.author") == ["Br. Apellido, Nombre"]


def test_linea_de_orcid_pura_no_es_autor_ni_asesor(ficha):
    """Las líneas de ORCID intercaladas no se publican como personas."""
    autores = valor(ficha, "dc.contributor.author")
    assert autores == ["Br. Apellido, Nombre", "Br. Apellido2, Nombre2"]
    assert all("orcid" not in autor.lower() for autor in autores)
    assert "orcid" not in valor(ficha, "dc.contributor.advisor").lower()


def test_documento_sin_orcid_no_detecta_el_campo():
    """Sin ORCID en la carátula el campo no se publica como detectado."""
    ficha = _ficha_de(
        _portada(
            "AUTORES:",
            "Br. Apellido, Nombre",
            "ASESORA:",
            "Dra. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "renati.advisor.orcid") is None
    assert _detectado(ficha, "renati.advisor.orcid") is False


def test_la_etiqueta_del_asesor_no_toma_una_frase_que_mentione_asesoria():
    """`starts-with` evita confundir «Sobre la asesoría…» con la etiqueta."""
    ficha = _ficha_de(
        _portada(
            "Sobre la asesoría académica de esta facultad",
            "AUTORES:",
            "Br. Apellido, Nombre",
            "ASESORA:",
            "Dra. Apellido, Nombre",
            "Línea de Investigación:",
            "Educación",
            "Trujillo – Perú",
            "2026",
        )
    )
    assert valor(ficha, "dc.contributor.advisor") == "Dra. Apellido, Nombre"


# ---------------------------------------------------------------------------
# F-4 — el motor no publica un valor inservible como detectado
# ---------------------------------------------------------------------------


class _AnalizadorFalso:
    """Analizador mínimo que deja un único item en `ficha`."""

    def __init__(self, valor):
        self.ficha = [{"campo": "dc.contributor.author", "valor": valor, "nodo": object()}]


class _ExtraidoFalso:
    """ExtractedDocx mínimo: solo resuelve la página de un nodo."""

    def pagina_de(self, nodo):
        return 1


@pytest.mark.parametrize("valor", ["", "   ", [], [""], ["  "], None])
def test_el_motor_no_publica_valores_inservibles(valor):
    """Cadena vacía, solo espacios o lista vacía → `detectado=False`.

    El contrato exige que un valor inservible viaje como `None` y sin
    página: el formulario de DSpace, la constancia y el registro no deben
    recibir un dato fantasma (AUD-24 y AUD-25).
    """
    from validator.compilador import ReglaCompilada

    regla = ReglaCompilada(rule={"id": "ficha_autores"}, analizadores=[_AnalizadorFalso(valor)])
    assert regla._ficha(_ExtraidoFalso()) == [
        {
            "campo": "dc.contributor.author",
            "valor": None,
            "pagina": None,
            "detectado": False,
        }
    ]


def test_la_api_degrada_el_valor_inservible_a_no_detectado():
    """El contrato de la API: detectado=true implica valor utilizable."""
    ficha_api = _ficha_desde_reporte(
        {
            "ficha": {
                "dc.contributor.advisor": {"valor": "", "pagina": 1, "detectado": True},
                "dc.date.issued": {"valor": "Trujillo - Perú", "pagina": 1, "detectado": True},
            }
        }
    )
    por_campo = {campo.campo: campo for campo in ficha_api.extraidos}

    asesor = por_campo["dc.contributor.advisor"]
    assert asesor.detectado is False
    assert asesor.valor is None
    assert asesor.pagina is None

    anio = por_campo["dc.date.issued"]
    assert anio.detectado is False
    assert anio.valor is None
    assert anio.pagina is None
