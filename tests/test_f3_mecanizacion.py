"""Tests de la Fase F3: mecanización de reglas antes no-deterministas.

Cubre los analizadores nuevos del DSL:
- `patron_cantidad`: resumen ≥159 palabras y ≥3 palabras clave.
- `conteo_nodos`: referencias mínimas (párrafos de una sección).
- `lista_obligatoria`: anexos mínimos.
- `hipervinculo_texto`: ORCID en carátula.
- `proyecto_caratula_texto` (patron_texto + atributo_xml, 13pt).
- Helper `seccion()` del tokenizer (acotar secciones por títulos).
- Smoke: `reglas_unt.yaml` completa compila y valida sin excepción (54 reglas).

Uso:
    pytest tests/test_f3_mecanizacion.py -v
"""

import tempfile
import zipfile
from pathlib import Path

import pytest

from validator.engine import load_rules, validate_docx
from validator.extractor import extract
from validator.models import RuleResult
from validator.tokenizer import PARRAFO, seccion, tokenizar

WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId5" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink" Target="https://orcid.org/0000-0002-1825-0097" TargetMode="External"/>
</Relationships>"""


def _para(texto: str, estilo: str = "", sz=None) -> str:
    pPr = f'<w:pPr><w:pStyle w:val="{estilo}"/></w:pPr>' if estilo else ""
    rPr = f'<w:rPr><w:sz w:val="{sz}"/></w:rPr>' if sz else ""
    return f'<w:p>{pPr}<w:r>{rPr}<w:t xml:space="preserve">{texto}</w:t></w:r></w:p>'


def _hyperlink(texto: str) -> str:
    return (
        '<w:hyperlink r:id="rId5" xmlns:r="' + REL_NS + '">'
        f'<w:r><w:t xml:space="preserve">{texto}</w:t></w:r></w:hyperlink>'
    )


def _docxml(paras: list) -> str:
    body = "".join(paras)
    body += '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
    return (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{body}</w:body></w:document>'
    )


def _make_docx(paras: list) -> str:
    doc = _docxml(paras)
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", doc)
    return path


def _nw(n: int) -> str:
    """Párrafo con exactamente n palabras."""
    return " ".join(f"palabra{i}" for i in range(n))


# ---------------------------------------------------------------------------
# Helper seccion() del tokenizer
# ---------------------------------------------------------------------------


class TestSeccion:
    def _extracted(self, paras: list):
        path = _make_docx(paras)
        try:
            return tokenizar(extract(path))
        finally:
            Path(path).unlink(missing_ok=True)

    def test_recorta_entre_titulos(self):
        flujo = self._extracted(
            [
                _para("RESUMEN", "Ttulo1"),
                _para("cuerpo del resumen"),
                _para("ABSTRACT", "Ttulo1"),
                _para("abstract body"),
            ]
        )
        corte = seccion(flujo, "resumen")
        assert [t.tipo for t in corte] == [PARRAFO]
        assert corte[0].texto == "cuerpo del resumen"

    def test_fin_regex_opcional(self):
        flujo = self._extracted(
            [
                _para("REFERENCIAS", "Ttulo1"),
                _para("Autor, A. (2020). Título."),
                _para("ANEXOS", "Ttulo1"),
                _para("anexo 1"),
            ]
        )
        corte = seccion(flujo, "referencias", fin="anexos")
        assert [t.texto for t in corte] == ["Autor, A. (2020). Título."]

    def test_ultimo_titulo_toma_el_resto(self):
        flujo = self._extracted(
            [
                _para("REFERENCIAS", "Ttulo1"),
                _para("Una referencia."),
                _para("Otra referencia."),
            ]
        )
        corte = seccion(flujo, "referencias")
        paras = [t for t in corte if t.tipo == PARRAFO]
        assert len(paras) == 2

    def test_sin_match_devuelve_vacio(self):
        flujo = self._extracted(
            [
                _para("INTRODUCCIÓN", "Ttulo1"),
                _para("cuerpo"),
            ]
        )
        assert seccion(flujo, "resumen") == []

    def test_fin_anclado_no_corta_en_titulo_derivado(self):
        """`fin` con ^...$ no corta ante títulos que solo contienen la
        subcadena (p. ej. "ANEXOS Y RECURSOS") — el pitfall de no anclar."""
        flujo = self._extracted(
            [
                _para("REFERENCIAS", "Ttulo1"),
                _para("Autor, A. (2020). Título."),
                _para("ANEXOS Y RECURSOS", "Ttulo1"),
                _para("anexo 1"),
            ]
        )
        corte = seccion(flujo, r"^referencias$", fin=r"^anexos$")
        textos = [t.texto for t in corte]
        assert "Autor, A. (2020). Título." in textos
        assert "ANEXOS Y RECURSOS" in textos
        assert "anexo 1" in textos

    def test_patron_vacio_lanza_valueerror(self):
        """`inicio`/`fin` vacíos o en blanco fallan temprano con ValueError."""
        flujo = self._extracted(
            [
                _para("RESUMEN", "Ttulo1"),
                _para("cuerpo"),
            ]
        )
        with pytest.raises(ValueError):
            seccion(flujo, "resumen", fin="   ")
        with pytest.raises(ValueError):
            seccion(flujo, "")


# ---------------------------------------------------------------------------
# Reglas individuales (cada una con su mecanismo F3)
# ---------------------------------------------------------------------------


class TestResumenLongitud:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "resumen_longitud",
                "tipo": "estructura",
                "severidad": "warning",
                "descripcion": "Resumen ≥ 159 palabras",
                "patron_cantidad": {
                    "seccion": {"inicio": "resumen"},
                    "operacion": "count_words",
                    "cantidad_minima": 159,
                },
            }
        ],
    }

    def _res(self, n: int) -> str:
        path = _make_docx(
            [
                _para("RESUMEN", "Ttulo1"),
                _para(_nw(n)),
                _para("ABSTRACT", "Ttulo1"),
            ]
        )
        try:
            return validate_docx(path, self.RULES)[0]
        finally:
            Path(path).unlink(missing_ok=True)

    def test_cumple_con_160_palabras(self):
        r = self._res(160)
        assert r.passed is True

    def test_no_cumple_con_100(self):
        r = self._res(100)
        assert r.passed is False
        assert "palabras=100" in r.found


class TestPalabrasClave:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "palabras_clave",
                "tipo": "estructura",
                "severidad": "error",
                "descripcion": "≥ 3 palabras clave",
                "patron_cantidad": {
                    "seccion": {"inicio": "resumen"},
                    "operacion": "count_entries",
                    "filtro": "^palabras clave",
                    "ignore_case": True,
                    "cantidad_minima": 3,
                },
            }
        ],
    }

    def _res(self, etiquetas: str) -> Path:
        path = _make_docx(
            [
                _para("RESUMEN", "Ttulo1"),
                _para("Palabras clave: " + etiquetas),
                _para("ABSTRACT", "Ttulo1"),
            ]
        )
        return path

    def test_cumple_con_tres(self):
        path = self._res("educación, infancia, calidad")
        try:
            assert validate_docx(path, self.RULES)[0].passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_con_dos(self):
        path = self._res("educación; infancia")
        try:
            assert validate_docx(path, self.RULES)[0].passed is False
        finally:
            Path(path).unlink(missing_ok=True)


class TestM5ResumenAbstract:
    """Regresión de M5/VA-06 y VA-07 con la configuración de producción.

    Cubre los límites exactos del Resumen (159–220), las 3–5 palabras clave
    por idioma, el Abstract sin cuerpo y la exclusión de la línea de palabras
    clave del conteo de prosa.
    """

    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "resumen_longitud",
                "tipo": "estructura",
                "severidad": "warning",
                "descripcion": "Resumen de 159 a 220 palabras sin palabras clave",
                "patron_cantidad": {
                    "seccion": {"inicio": "resumen"},
                    "operacion": "count_words",
                    "excluir": r"^(palabras clave|keywords)\b",
                    "ignore_case": True,
                    "cantidad_minima": 159,
                    "cantidad_maxima": 220,
                },
            },
            {
                "id": "palabras_clave_minimo",
                "tipo": "estructura",
                "severidad": "error",
                "descripcion": "Entre 3 y 5 palabras clave en cada idioma",
                "patron_cantidad": {
                    "secciones": [
                        {"nombre": "resumen", "inicio": "resumen"},
                        {"nombre": "abstract", "inicio": "abstract"},
                    ],
                    "operacion": "count_entries",
                    "filtro": r"^(palabras clave|keywords)\b",
                    "ignore_case": True,
                    "cantidad_minima": 3,
                    "cantidad_maxima": 5,
                },
            },
            {
                "id": "abstract_contenido",
                "tipo": "estructura",
                "severidad": "warning",
                "descripcion": "El Abstract debe tener contenido además del título",
                "patron_cantidad": {
                    "seccion": {"inicio": "abstract"},
                    "operacion": "count_words",
                    "excluir": r"^(palabras clave|keywords)\b",
                    "ignore_case": True,
                    "cantidad_minima": 1,
                },
            },
        ],
    }

    def _validar(
        self,
        resumen_n: int = 175,
        claves_resumen: int = 3,
        abstract_n: int = 175,
        claves_abstract: int = 3,
        etiqueta_resumen: str = "Palabras clave",
        etiqueta_abstract: str = "Keywords",
    ) -> dict:
        claves_r = ", ".join(f"clave{i}" for i in range(claves_resumen))
        claves_a = ", ".join(f"keyword{i}" for i in range(claves_abstract))
        paras = [
            _para("RESUMEN", "Ttulo1"),
            _para(_nw(resumen_n)),
            _para(f"{etiqueta_resumen}: {claves_r}"),
            _para("ABSTRACT", "Ttulo1"),
        ]
        if abstract_n > 0:
            paras.append(_para(_nw(abstract_n)))
        if claves_abstract > 0:
            paras.append(_para(f"{etiqueta_abstract}: {claves_a}"))
        paras.append(_para("INTRODUCCIÓN", "Ttulo1"))
        path = _make_docx(paras)
        try:
            return {r.rule_id: r for r in validate_docx(path, self.RULES)}
        finally:
            Path(path).unlink(missing_ok=True)

    def test_resumen_158_falla_y_159_cumple(self):
        assert self._validar(resumen_n=158)["resumen_longitud"].passed is False
        assert self._validar(resumen_n=159)["resumen_longitud"].passed is True

    def test_resumen_220_cumple_y_221_falla(self):
        assert self._validar(resumen_n=220)["resumen_longitud"].passed is True
        assert self._validar(resumen_n=221)["resumen_longitud"].passed is False

    def test_palabras_clave_2_falla_y_3_cumple(self):
        assert self._validar(claves_resumen=2)["palabras_clave_minimo"].passed is False
        assert self._validar(claves_resumen=3)["palabras_clave_minimo"].passed is True

    def test_palabras_clave_5_cumple_y_6_falla(self):
        assert self._validar(claves_resumen=5)["palabras_clave_minimo"].passed is True
        assert self._validar(claves_resumen=6)["palabras_clave_minimo"].passed is False

    def test_abstract_vacio_falla(self):
        res = self._validar(abstract_n=0, claves_abstract=0)
        assert res["abstract_contenido"].passed is False
        assert res["palabras_clave_minimo"].passed is False

    def test_abstract_con_palabras_clave_pero_sin_cuerpo_falla(self):
        """El título ABSTRACT y su línea de claves no prueban que haya texto."""
        res = self._validar(abstract_n=0, claves_abstract=3)
        assert res["abstract_contenido"].passed is False
        assert res["palabras_clave_minimo"].passed is True

    def test_solo_un_idioma_correcto_falla(self):
        """Resumen correcto no compensa un Abstract con 2 claves."""
        res = self._validar(claves_resumen=3, claves_abstract=2)
        assert res["palabras_clave_minimo"].passed is False
        assert "resumen=3" in res["palabras_clave_minimo"].found
        assert "abstract=2" in res["palabras_clave_minimo"].found

    def test_palabras_clave_no_inflan_el_conteo_de_prosa(self):
        """220 palabras de prosa + 5 claves siguen siendo 220 de prosa."""
        assert self._validar(resumen_n=220, claves_resumen=5)["resumen_longitud"].passed is True
        # 158 de prosa + 5 claves no llegan al mínimo: las claves no cuentan.
        assert self._validar(resumen_n=158, claves_resumen=5)["resumen_longitud"].passed is False

    def test_mil_palabras_y_diez_claves_generan_observacion(self):
        res = self._validar(resumen_n=1000, claves_resumen=10)
        assert res["resumen_longitud"].passed is False
        assert "palabras=1000" in res["resumen_longitud"].found
        assert "maximo=220" in res["resumen_longitud"].found
        assert res["palabras_clave_minimo"].passed is False
        assert "resumen=10" in res["palabras_clave_minimo"].found
        assert "maximo=5" in res["palabras_clave_minimo"].found

    def test_admite_las_etiquetas_de_cada_idioma(self):
        res = self._validar(etiqueta_resumen="Palabras Clave", etiqueta_abstract="Keywords")
        assert res["resumen_longitud"].passed is True
        assert res["palabras_clave_minimo"].passed is True
        assert res["abstract_contenido"].passed is True


class TestReferenciasMinimas:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "referencias_min",
                "tipo": "estructura",
                "severidad": "warning",
                "descripcion": "≥ 20 referencias",
                "conteo_nodos": {
                    "seccion": {"inicio": "referencias"},
                    "cantidad_minima": 20,
                },
            }
        ],
    }

    def _res(self, n: int) -> Path:
        paras = [_para("REFERENCIAS", "Ttulo1")]
        paras += [_para(f"Autor, A. ({1990 + i}). Fuente bibliográfica {i}.") for i in range(n)]
        return _make_docx(paras)

    def test_cumple_con_20(self):
        path = self._res(20)
        try:
            assert validate_docx(path, self.RULES)[0].passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_con_19(self):
        path = self._res(19)
        try:
            r = validate_docx(path, self.RULES)[0]
            assert r.passed is False
            assert "nodos=19" in r.found
        finally:
            Path(path).unlink(missing_ok=True)


class TestAnexosMinimos:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "anexos_min",
                "tipo": "estructura",
                "severidad": "warning",
                "descripcion": "Anexos obligatorios",
                "lista_obligatoria": {
                    "seccion": {"inicio": "anexo"},
                    "ignore_case": True,
                    "items": ["Matriz de consistencia", "Consentimiento informado"],
                },
            }
        ],
    }

    def test_cumple_con_todos(self):
        path = _make_docx(
            [
                _para("ANEXOS", "Ttulo1"),
                _para("Anexo 1. Matriz de consistencia"),
                _para("Anexo 2. Consentimiento informado"),
            ]
        )
        try:
            assert validate_docx(path, self.RULES)[0].passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_falta_uno(self):
        path = _make_docx(
            [
                _para("ANEXOS", "Ttulo1"),
                _para("Anexo 1. Matriz de consistencia"),
            ]
        )
        try:
            r = validate_docx(path, self.RULES)[0]
            assert r.passed is False
            assert "Consentimiento informado" in r.found
        finally:
            Path(path).unlink(missing_ok=True)


class TestOrcid:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "caratula_orcid",
                "tipo": "formato_texto",
                "severidad": "warning",
                "descripcion": "ORCID como hipervínculo",
                "hipervinculo_texto": {
                    "parte": "document",
                    "contexto": "todos",
                    "xpath": "//w:body//w:hyperlink",
                    "patron": r"https?://orcid\.org/\d{4}-?\d{4}-?\d{4}-?\d{4}",
                    "cantidad_minima": 1,
                },
            }
        ],
    }

    def test_cumple_con_hyperlink(self):
        path = _make_docx(
            [
                _para("AUTOR PRINCIPAL"),
                _hyperlink("https://orcid.org/0000-0002-1825-0097"),
            ]
        )
        try:
            assert validate_docx(path, self.RULES)[0].passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_sin_hyperlink(self):
        path = _make_docx([_para("AUTOR PRINCIPAL"), _para("0000-0002-1825-0097")])
        try:
            assert validate_docx(path, self.RULES)[0].passed is False
        finally:
            Path(path).unlink(missing_ok=True)


class TestProyectoCaratulaTexto:
    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "proyecto_caratula_texto",
                "tipo": "formato_texto",
                "severidad": "error",
                "descripcion": "Línea de tipo del Proyecto 13pt",
                "patron_texto": {
                    "parte": "document",
                    "contexto": "todos",
                    "xpath": "//w:body/w:p[contains(translate(normalize-space(.), "
                    '"ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑÜ", "abcdefghijklmnopqrstuvwxyzáéíóúñü"), '
                    '"proyecto de investigación")]//w:t',
                    "patron": "proyecto de investigación",
                    "coincidencia": "alguno",
                    "comparacion": "regex",
                    "ignore_case": True,
                },
                "atributo_xml": {
                    "parte": "document",
                    "contexto": "todos",
                    "xpath": "//w:body/w:p[contains(translate(normalize-space(.), "
                    '"ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑÜ", "abcdefghijklmnopqrstuvwxyzáéíóúñü"), '
                    '"proyecto de investigación")][1]/w:r[1]/w:rPr/w:sz',
                    "atributo": "@w:val",
                    "comparacion": "eq",
                    "esperado": "26",
                },
            }
        ],
    }

    def _doc(self, sz=None) -> Path:
        return _make_docx(
            [
                _para("PROYECTO DE INVESTIGACIÓN", sz=sz),
                _para("Para optar el título profesional"),
            ]
        )

    def test_cumple_con_13pt(self):
        path = self._doc(sz="26")
        try:
            r = validate_docx(path, self.RULES)[0]
            assert r.passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_tamano_incorrecto(self):
        path = self._doc(sz="24")
        try:
            assert validate_docx(path, self.RULES)[0].passed is False
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_sin_la_linea(self):
        path = _make_docx([_para("UNIVERSIDAD NACIONAL DE TRUJILLO")])
        try:
            assert validate_docx(path, self.RULES)[0].passed is False
        finally:
            Path(path).unlink(missing_ok=True)


class TestConteoNodosMultiples:
    """`cantidades_multiples`: cumple si la cantidad alcanza cualquiera."""

    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "refs_multiples",
                "tipo": "estructura",
                "severidad": "warning",
                "descripcion": "Mínimos por tipo",
                "conteo_nodos": {
                    "seccion": {"inicio": "referencias"},
                    "cantidades_multiples": [20, 30, 20],
                },
            }
        ],
    }

    def _res(self, n: int) -> str:
        paras = [_para("REFERENCIAS", "Ttulo1")]
        paras += [_para(f"Autor, A. ({1990 + i}). Fuente.") for i in range(n)]
        return _make_docx(paras)

    def test_cumple_con_25(self):
        path = self._res(25)
        try:
            assert validate_docx(path, self.RULES)[0].passed is True
        finally:
            Path(path).unlink(missing_ok=True)

    def test_no_cumple_con_19(self):
        path = self._res(19)
        try:
            r = validate_docx(path, self.RULES)[0]
            assert r.passed is False
            assert "minimos=[20, 30, 20]" in r.found
        finally:
            Path(path).unlink(missing_ok=True)


class TestImagenRefactor:
    """El refactor de imagen debe conservar el detalle 'imagenes='."""

    RULES = {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "imagen",
                "tipo": "imagen",
                "severidad": "warning",
                "imagen": {
                    "parte": "document",
                    "xpath": "//w:drawing//a:blip",
                    "cantidad_minima": 1,
                },
            }
        ],
    }

    def test_detalle_imagenes(self):
        path = _make_docx([_para("sin imagen")])
        try:
            r = validate_docx(path, self.RULES)[0]
            assert r.passed is False
            assert "imagenes=0" in r.found
        finally:
            Path(path).unlink(missing_ok=True)


class TestReglasUntCompletas:
    """Smoke: las 54 reglas de reglas_unt.yaml validan sin excepción."""

    def test_54_reglas_validan(self):
        rules = load_rules("reglas_unt.yaml")
        assert len(rules["reglas"]) == 54
        path = _make_docx([_para("RESUMEN", "Ttulo1"), _para("cuerpo breve")])
        try:
            resultados = validate_docx(path, rules)
            # 54 del YAML + 1 centinela: este docx mínimo no se puede
            # clasificar (ni Anexo 10 ni firmas), y el paso 6 agrega el error
            # `tipo_documento_no_determinado` como resultado adicional.
            assert len(resultados) == 55
            assert all(isinstance(r, RuleResult) for r in resultados)
        finally:
            Path(path).unlink(missing_ok=True)
