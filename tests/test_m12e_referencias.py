"""Regresiones de M12e / NM-05: contar referencias, no párrafos.

El contador histórico de `conteo_nodos` suma párrafos no vacíos de la
sección REFERENCIAS. Eso infla el total cuando una entrada está partida en
varios párrafos y suma texto ajeno (incluida prosa con un año entre
paréntesis). Estas pruebas fijan el criterio nuevo:

- `unidad: entrada` cuenta entradas con patrón autor-año, no párrafos.
- Los mínimos 20/30/20 de TINV siguen vigentes.
- Proyecto e informe piden 30 cuando el tipo se puede detectar.
- TSP separa el mínimo 20 del informe del máximo 10 de la sesión.
- APA, la sangría francesa y la relación cita-referencia NO se comprueban
  con este conteo; quedan para revisión humana (REQ-50).

Uso:
    pytest tests/test_m12e_referencias.py -v
"""

from __future__ import annotations

import copy
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest
import yaml

from validator.dsl_check import linter
from validator.engine import validate_docx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))

from _mutations import _voltear_cualitativo, _voltear_revision  # noqa: E402
from docx_factory import compilar_docx, configuracion_base  # noqa: E402
from test_dsl import CONTENT_TYPES, RELS, WNS, _para  # noqa: E402

REGLAS_REFERENCIAS = {
    "referencias_minimo_cuantitativo",
    "referencias_minimo_cualitativo",
    "referencias_minimo_revision",
    "referencias_minimo_proyecto",
    "referencias_minimo_informe",
    "referencias_minimo_tsp_informe",
    "referencias_maximo_tsp_sesion",
}


def _yaml() -> dict:
    return yaml.safe_load((ROOT / "reglas_unt.yaml").read_text(encoding="utf-8"))


def _entradas(n: int, anio_inicial: int = 1990) -> list[str]:
    """Entradas sintéticas con patrón autor-año (sin datos reales)."""
    return [
        _para(f"Autor, A. ({anio_inicial + i}). Fuente bibliográfica {i + 1}.") for i in range(n)
    ]


def _docx(paras: list[str]) -> str:
    """DOCX mínimo con párrafos arbitrarios (cabeceras y entradas)."""
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
        path = f.name
    xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{WNS}"><w:body>{"".join(paras)}'
        '<w:sectPr><w:pgSz w:w="11906" w:h="16838"/></w:sectPr>'
        "</w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CONTENT_TYPES)
        z.writestr("_rels/.rels", RELS)
        z.writestr("word/document.xml", xml)
    return path


def _referencias(n: int, titulo: str = "REFERENCIAS", anio_inicial: int = 1990) -> list[str]:
    return [_para(titulo, "Ttulo1")] + _entradas(n, anio_inicial)


def _conteo(unidad: str, minimo: int, maximo: int | None = None) -> dict:
    config = {
        "seccion": {"inicio": "referencias"},
        "unidad": unidad,
        "label": "referencias",
        "cantidad_minima": minimo,
    }
    if maximo is not None:
        config["cantidad_maxima"] = maximo
    return {
        "namespaces": {"w": WNS},
        "reglas": [
            {
                "id": "conteo_referencias",
                "tipo": "estructura",
                "severidad": "warning",
                "descripcion": "Conteo de entradas de la sección Referencias",
                "conteo_nodos": config,
            }
        ],
    }


def _resultado(path: str, reglas: dict, regla_id: str):
    return {r.rule_id: r for r in validate_docx(path, reglas)}[regla_id]


def _subconjunto(ids: set[str]) -> dict:
    datos = _yaml()
    datos["reglas"] = [r for r in datos["reglas"] if r["id"] in ids]
    return datos


def _con_factory(cfg: dict, ids: set[str]) -> dict:
    path = compilar_docx(cfg)
    try:
        return {r.rule_id: r for r in validate_docx(path, _subconjunto(ids))}
    finally:
        Path(path).unlink(missing_ok=True)


def _anadir(cfg: dict, *cabeceras: str) -> None:
    cfg["headings"] = list(cfg["headings"]) + list(cabeceras)


def _voltear_proyecto(cfg: dict) -> None:
    _anadir(cfg, "PLAN DE INVESTIGACIÓN", "RECURSOS Y MATERIALES")


def _voltear_proyecto_cualitativo(cfg: dict) -> None:
    _anadir(cfg, "SELECCIÓN DE PARTICIPANTES", "ESCENARIO", "UNIDAD DE ANÁLISIS")


def _voltear_informe_cuantitativo(cfg: dict) -> None:
    _anadir(
        cfg,
        "SITUACIÓN PROBLEMATIZADA",
        "DISEÑO DE CONTRASTACIÓN",
        "OPERACIONALIZACIÓN DE LAS VARIABLES",
    )


def _voltear_informe_cualitativo(cfg: dict) -> None:
    _anadir(
        cfg,
        "SITUACIÓN PROBLEMATIZADA",
        "PARTICIPANTES",
        "INSTRUMENTOS USADOS EN LA RECOLECCIÓN",
    )


def _doc_tsp(n_informe: int = 20, n_sesion: int = 10) -> str:
    paras = [_para(h, "Ttulo1") for h in ("SECUENCIA DIDÁCTICA", "SUSTENTO PSICOPEDAGÓGICO")]
    paras += _referencias(n_informe, "REFERENCIAS DEL INFORME")
    paras += _referencias(n_sesion, "REFERENCIAS DE LA SESIÓN DE APRENDIZAJE", 2010)
    return _docx(paras)


class TestContadorDeEntradas:
    def test_reglas_de_referencias_declaran_unidad_entrada(self):
        """Ninguna regla de referencias debe seguir contando párrafos."""
        for regla in _yaml()["reglas"]:
            if regla["id"] in REGLAS_REFERENCIAS:
                assert regla["conteo_nodos"].get("unidad") == "entrada", regla["id"]

    @pytest.mark.parametrize(
        "parrafo_ajeno",
        [
            "Continuación de la entrada anterior: editorial y ciudad.",
            "Esta lista fue revisada por el comité académico.",
            "La revisión bibliográfica (2020) quedó registrada en el acta.",
        ],
    )
    def test_texto_ajeno_y_continuaciones_no_suman(self, parrafo_ajeno):
        """19 entradas + 1 párrafo ajeno son 19 referencias, no 20."""
        paras = _referencias(19) + [_para(parrafo_ajeno)]
        path = _docx(paras)
        try:
            r = _resultado(path, _conteo("entrada", 20), "conteo_referencias")
            assert r.passed is False
            assert "referencias=19" in r.found
        finally:
            Path(path).unlink(missing_ok=True)

    def test_una_entrada_partida_no_cuenta_como_varias(self):
        """El mínimo 20 no se alcanza partiendo una entrada en 3 párrafos."""
        paras = _referencias(19)
        paras += _entradas(1)[:1]
        paras += [
            _para("Segunda línea de la misma entrada."),
            _para("Tercera línea de la misma entrada."),
        ]
        path = _docx(paras)
        try:
            r = _resultado(path, _conteo("entrada", 20), "conteo_referencias")
            assert r.passed is False
            assert "referencias=20" not in r.found
            assert "referencias=19" in r.found
        finally:
            Path(path).unlink(missing_ok=True)

    def test_unidad_parrafo_sigue_siendo_el_comportamiento_por_defecto(self):
        """Otras reglas con `conteo_nodos` no cambian su semántica."""
        paras = _referencias(2) + [_para("Texto ajeno.")]
        path = _docx(paras)
        try:
            reglas = _conteo("entrada", 20)
            reglas["reglas"][0]["conteo_nodos"].pop("unidad")
            r = _resultado(path, reglas, "conteo_referencias")
            assert "referencias=3" in r.found
        finally:
            Path(path).unlink(missing_ok=True)

    def test_linter_rechaza_unidad_desconocida(self):
        datos = copy.deepcopy(_yaml())
        for regla in datos["reglas"]:
            if regla["id"] == "referencias_minimo_cuantitativo":
                regla["conteo_nodos"]["unidad"] = "parrafooo"
        hallazgos = linter(datos)
        assert any("unidad" in h for h in hallazgos), hallazgos


class TestMinimosPorTipo:
    @pytest.mark.parametrize(
        "volteo,regla,cumple,falla",
        [
            (None, "referencias_minimo_cuantitativo", 20, 19),
            (_voltear_cualitativo, "referencias_minimo_cualitativo", 30, 29),
            (_voltear_revision, "referencias_minimo_revision", 20, 19),
        ],
        ids=["tinv_cuantitativo", "tinv_cualitativo", "tinv_revision"],
    )
    def test_minimos_tinv(self, volteo, regla, cumple, falla):
        ids = {"deteccion_tipo_documento", regla}
        for n, esperado in ((cumple, True), (falla, False)):
            cfg = configuracion_base()
            cfg["referencias_n"] = n
            if volteo:
                volteo(cfg)
            assert _con_factory(cfg, ids)[regla].passed is esperado

    @pytest.mark.parametrize(
        "volteo,tipo,regla",
        [
            (_voltear_proyecto, "proyecto_cuantitativo", "referencias_minimo_proyecto"),
            (
                _voltear_proyecto_cualitativo,
                "proyecto_cualitativo",
                "referencias_minimo_proyecto",
            ),
            (
                _voltear_informe_cuantitativo,
                "informe_cuantitativo",
                "referencias_minimo_informe",
            ),
            (
                _voltear_informe_cualitativo,
                "informe_cualitativo",
                "referencias_minimo_informe",
            ),
        ],
        ids=[
            "proyecto_cuantitativo",
            "proyecto_cualitativo",
            "informe_cuantitativo",
            "informe_cualitativo",
        ],
    )
    def test_proyecto_e_informe_piden_30(self, volteo, tipo, regla):
        ids = {"deteccion_tipo_documento", regla}
        for n, esperado in ((30, True), (29, False)):
            cfg = configuracion_base()
            cfg["referencias_n"] = n
            volteo(cfg)
            res = _con_factory(cfg, ids)
            assert res["deteccion_tipo_documento"].found.startswith(f"inferido={tipo}")
            assert res[regla].passed is esperado

    def test_tsp_separa_el_minimo_del_informe_del_maximo_de_la_sesion(self):
        ids = {
            "deteccion_tipo_documento",
            "referencias_minimo_tsp_informe",
            "referencias_maximo_tsp_sesion",
        }
        min_id = "referencias_minimo_tsp_informe"
        max_id = "referencias_maximo_tsp_sesion"

        path = _doc_tsp()
        try:
            res = {r.rule_id: r for r in validate_docx(path, _subconjunto(ids))}
        finally:
            Path(path).unlink(missing_ok=True)
        assert res["deteccion_tipo_documento"].found.startswith("inferido=tsp")
        assert res[min_id].passed is True
        assert res[max_id].passed is True

        path = _doc_tsp(n_informe=19)
        try:
            res = {r.rule_id: r for r in validate_docx(path, _subconjunto(ids))}
        finally:
            Path(path).unlink(missing_ok=True)
        assert res[min_id].passed is False
        assert "referencias=19" in res[min_id].found
        assert res[max_id].passed is True

        path = _doc_tsp(n_sesion=11)
        try:
            res = {r.rule_id: r for r in validate_docx(path, _subconjunto(ids))}
        finally:
            Path(path).unlink(missing_ok=True)
        assert res[min_id].passed is True
        assert res[max_id].passed is False
        assert "referencias=11" in res[max_id].found
