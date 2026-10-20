"""Tests de la Funcionalidad 1 — revisión semántica advisory (`asistente.revision_semantica`).

Sin `pytest-asyncio`: las corrutinas se ejecutan con `asyncio.run(...)`.
Todo con `StubLLM`; sin red ni GPU en el CI.
"""

import asyncio
import json
import tempfile
import zipfile

import pytest
from _xml_constants import CONTENT_TYPES, RELS, WNS
from docx_factory import compilar_docx, configuracion_base

from validator.asistente import (
    CHECKS_SEMANTICOS,
    MAX_RESUMEN,
    NIVELES_VALIDOS,
    HallazgoSemantico,
    HallazgosSemanticos,
    RespuestaIAInvalida,
    construir_prompt_semantico,
    extraer_fragmentos,
    parse_hallazgos,
    revision_semantica,
)
from validator.extractor import extract
from validator.llm import LLMError, StubLLM

CHECK_RESUMEN = CHECKS_SEMANTICOS[0]
CHECK_INDICE = CHECKS_SEMANTICOS[1]
CHECK_CITAS = CHECKS_SEMANTICOS[2]


# ---------------------------------------------------------------------------
# DOCX mínimo (para secciones que el factory no trae: citas, secciones ausentes)
# ---------------------------------------------------------------------------


def _esc(texto: str) -> str:
    return texto.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _docx_minimo(parrafos: list[tuple[str | None, str]]) -> str:
    """Crea un DOCX mínimo con pares (estilo, texto) y devuelve su ruta.

    `estilo=None` es un párrafo normal; `estilo="Heading1"` un título.
    """
    bloques = []
    for estilo, texto in parrafos:
        pPr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>' if estilo else ""
        bloques.append(f'<w:p>{pPr}<w:r><w:t xml:space="preserve">{_esc(texto)}</w:t></w:r></w:p>')
    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{"".join(bloques)}</w:body></w:document>'
    )
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", document)
    return path


def _respuesta_valida(check: str = "coherencia_resumen") -> str:
    return json.dumps(
        {"hallazgos": [{"nivel": "advertencia", "descripcion": "observación", "ubicacion": check}]},
        ensure_ascii=False,
    )


# ---------------------------------------------------------------------------
# extraer_fragmentos
# ---------------------------------------------------------------------------


def test_extrae_las_cuatro_secciones_del_doc_del_factory():
    doc = extract(compilar_docx(configuracion_base()))

    frag = extraer_fragmentos(doc)

    assert frag["resumen"].startswith("resumen0")
    assert "Palabras clave" in frag["resumen"]
    assert "PRESENTACIÓN iii" in frag["indice"]
    assert "Autor, A. (1990)" in frag["referencias"]
    assert "INTRODUCCIÓN" in frag["titulos"]
    # El cuerpo del factory no tiene citas con año: no se inventa el fragmento.
    assert "citas_texto" not in frag


def test_el_indice_usa_la_seccion_especifica_y_no_el_indice_previo():
    # El doc trae DOS títulos candidatos: "ÍNDICE" y "INDICE DE CONTENIDOS".
    doc = extract(compilar_docx(configuracion_base()))

    frag = extraer_fragmentos(doc)

    assert frag["indice"].startswith("PRESENTACIÓN iii")
    assert "INDICE DE TABLAS" not in frag["indice"]


def test_resumen_se_trunca_en_el_maximo_configurado():
    largo = " ".join(f"palabra{i}" for i in range(600))
    doc = extract(_docx_minimo([("Heading1", "RESUMEN"), (None, largo)]))

    frag = extraer_fragmentos(doc)

    assert len(frag["resumen"]) <= MAX_RESUMEN
    assert frag["resumen"].startswith("palabra0")


def test_citas_texto_solo_escanea_antes_de_referencias():
    doc = extract(
        _docx_minimo(
            [
                ("Heading1", "INTRODUCCIÓN"),
                (None, "Las estrategias lúdicas mejoran la motricidad (Pérez, 2020)."),
                ("Heading1", "REFERENCIAS"),
                (None, "Pérez, A. (2020). Juego y motricidad."),
            ]
        )
    )

    frag = extraer_fragmentos(doc)

    # La referencia "Pérez, A. (2020)." no debe colarse como cita del texto.
    assert frag["citas_texto"] == "(Pérez, 2020)"


def test_seccion_ausente_no_genera_fragmento():
    doc = extract(_docx_minimo([("Heading1", "INTRODUCCIÓN"), (None, "Texto suelto.")]))

    frag = extraer_fragmentos(doc)

    assert "referencias" not in frag
    assert "resumen" not in frag
    assert "indice" not in frag


def test_documento_sin_titulos_no_genera_fragmentos():
    doc = extract(_docx_minimo([(None, "Un párrafo cualquiera sin estructura.")]))

    assert extraer_fragmentos(doc) == {}


# ---------------------------------------------------------------------------
# construir_prompt_semantico
# ---------------------------------------------------------------------------


def test_prompt_lleva_regla_y_sus_fragmentos():
    fragmentos = {"indice": "A", "titulos": "B", "citas_texto": "NO VA"}

    system, user, esquema = construir_prompt_semantico(CHECK_INDICE, fragmentos)

    assert isinstance(system, str) and system
    payload = json.loads(user)
    assert payload["check"] == "indice_vs_titulos"
    assert payload["regla"] == CHECK_INDICE.regla
    # Solo los fragmentos que este chequeo declara: los demás no viajan.
    assert payload["fragmentos"] == {"indice": "A", "titulos": "B"}


def test_prompt_de_un_solo_check_por_llamada():
    _, user, _ = construir_prompt_semantico(CHECK_RESUMEN, {"resumen": "R", "titulos": "T"})

    assert set(json.loads(user)) == {"check", "regla", "fragmentos"}


def test_esquema_restringe_el_nivel_al_catalogo_advisory():
    _, _, esquema = construir_prompt_semantico(CHECK_RESUMEN, {"resumen": "R", "titulos": "T"})

    assert esquema["properties"]["hallazgos"]["items"]["properties"]["nivel"]["enum"] == [
        "advertencia",
        "informativo",
    ]
    assert set(NIVELES_VALIDOS) == {"advertencia", "informativo"}


# ---------------------------------------------------------------------------
# parse_hallazgos (torturas)
# ---------------------------------------------------------------------------


def test_parse_valido_adscribe_el_check():
    data = {"hallazgos": [{"nivel": "advertencia", "descripcion": "X", "ubicacion": "resumen"}]}

    hallazgos = parse_hallazgos(data, "coherencia_resumen", modelo="stub")

    assert hallazgos == [
        HallazgoSemantico(
            check="coherencia_resumen",
            nivel="advertencia",
            descripcion="X",
            ubicacion="resumen",
        )
    ]


def test_parse_ubicacion_ausente_se_omite():
    data = {"hallazgos": [{"nivel": "informativo", "descripcion": "dato menor"}]}

    hallazgos = parse_hallazgos(data, "indice_vs_titulos")

    assert hallazgos[0].ubicacion == ""


def test_parse_lista_vacia_es_valida():
    assert parse_hallazgos({"hallazgos": []}, "citas_huerfanas") == []


@pytest.mark.parametrize(
    "data",
    [
        {"hallazgos": "no-es-lista"},
        {"hallazgos": [42]},
        {"hallazgos": [{"nivel": "error", "descripcion": "X"}]},  # fuera del catálogo
        {"hallazgos": [{"nivel": 1, "descripcion": "X"}]},
        {"hallazgos": [{"nivel": "advertencia"}]},  # sin descripcion
        {"hallazgos": [{"nivel": "advertencia", "descripcion": ""}]},
        {"hallazgos": [{"nivel": "advertencia", "descripcion": 7}]},
        {"hallazgos": [{"nivel": "advertencia", "descripcion": "X", "ubicacion": 7}]},
        {"hallazgos": [{"descripcion": "X"}]},  # sin nivel
        {},
    ],
)
def test_parse_rechaza_estructuras_invalidas(data):
    with pytest.raises(RespuestaIAInvalida):
        parse_hallazgos(data, "coherencia_resumen")


# ---------------------------------------------------------------------------
# revision_semantica (orquestación con StubLLM)
# ---------------------------------------------------------------------------


def test_revision_e2e_con_stub_y_los_chequeos_ejecutables():
    # El doc del factory no trae citas: se omiten 1 de 3 chequeos (2 llamadas).
    doc = extract(compilar_docx(configuracion_base()))
    stub = StubLLM(_respuesta_valida())

    salida = asyncio.run(revision_semantica(doc, client=stub))

    assert isinstance(salida, HallazgosSemanticos)
    assert salida.modelo == "stub"
    assert len(stub.llamadas) == 2
    assert {h.check for h in salida.hallazgos} == {"coherencia_resumen", "indice_vs_titulos"}


def test_revision_omite_el_chequeo_cuyo_fragmento_falta():
    doc = extract(compilar_docx(configuracion_base()))
    stub = StubLLM(_respuesta_valida())

    salida = asyncio.run(revision_semantica(doc, client=stub, checks=(CHECK_CITAS,)))

    assert salida.hallazgos == []
    assert stub.llamadas == []


def test_revision_sin_fragmentos_no_llama_a_la_ia():
    doc = extract(_docx_minimo([(None, "Un párrafo cualquiera.")]))
    stub = StubLLM(_respuesta_valida())

    salida = asyncio.run(revision_semantica(doc, client=stub))

    assert salida.hallazgos == []
    assert stub.llamadas == []


def test_revision_reintenta_una_vez_ante_json_invalido():
    doc = extract(compilar_docx(configuracion_base()))
    stub = StubLLM(["esto no es json", _respuesta_valida()])

    salida = asyncio.run(revision_semantica(doc, client=stub, checks=(CHECK_RESUMEN,)))

    assert salida.hallazgos
    assert len(stub.llamadas) == 2


def test_revision_falla_tras_dos_respuestas_invalidas():
    doc = extract(compilar_docx(configuracion_base()))
    stub = StubLLM("nunca-json")

    with pytest.raises(RespuestaIAInvalida):
        asyncio.run(revision_semantica(doc, client=stub, checks=(CHECK_RESUMEN,)))

    assert len(stub.llamadas) == 2


def test_revision_propaga_error_de_servicio_sin_reintentar():
    doc = extract(compilar_docx(configuracion_base()))

    class ClienteCaido:
        modelo = "caido"
        intentos = 0

        async def chat(self, system, user, json_schema=None):
            self.intentos += 1
            raise LLMError("servicio caído")

        async def disponible(self):
            return False

    cliente = ClienteCaido()
    with pytest.raises(LLMError):
        asyncio.run(revision_semantica(doc, client=cliente, checks=(CHECK_RESUMEN,)))

    assert cliente.intentos == 1


def test_revision_acepta_json_entre_vallas_markdown():
    doc = extract(compilar_docx(configuracion_base()))
    contenido = "```json\n" + _respuesta_valida() + "\n```"
    stub = StubLLM(contenido)

    salida = asyncio.run(revision_semantica(doc, client=stub, checks=(CHECK_RESUMEN,)))

    assert len(salida.hallazgos) == 1
