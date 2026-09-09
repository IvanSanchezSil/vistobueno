"""Mutaciones del factory de DOCX sintéticos (soporte de F6).

Cada regla de `reglas_unt.yaml` tiene aquí UNA mutación: un desvío MÍNIMO
sobre la configuración base que la hace fallar (solo a ella, o a su par
acoplado). También centraliza la metadata de cobertura de reglas
(`REGLAS`, `REGLAS_ACOPLADAS`, `EXCLUIDAS_BASE`).

Sincronización obligatoria: al importar este módulo se verifica que
`_MUTACIONES` tenga exactamente las mismas reglas que `reglas_unt.yaml`.
Si alguien agrega una regla al YAML sin mutación (o muere una mutación
sin quitarse del YAML), el import falla con un error claro — fallo en
recolecta de tests, no un test más que recordar actualizar.
"""
import copy
from pathlib import Path

import yaml

from _docx_builder import _ANADIDAS_REVISION, _HEADINGS_CUANT, _headings_insertadas

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


# ---------------------------------------------------------------------------
# Aplicación de mutaciones.
# ---------------------------------------------------------------------------


def aplicar_mutacion(rule_id: str, cfg: dict) -> dict:
    """Devuelve una copia de `cfg` con el desvío mínimo para `rule_id`.

    Levanta `KeyError` si la regla no tiene mutación definida.
    """
    nuevo = _copia(cfg)
    _MUTACIONES[rule_id](nuevo)
    return nuevo


def _copia(cfg: dict) -> dict:
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


# ---------------------------------------------------------------------------
# Sincronización con reglas_unt.yaml (garantía en import, no solo a runtime).
# ---------------------------------------------------------------------------

RUTA_REGLAS_YAML = Path(__file__).resolve().parent.parent / "reglas_unt.yaml"


def _validar_sincronizacion() -> None:
    """Falla el import si `_MUTACIONES` no cubre exactamente las 41 reglas.

    Evita la desincronización silenciosa factory↔YAML: el error ocurre en la
    recolecta de tests (cuando se importa el factory), no cuando un test
    específico decide recordar revisar el YAML.
    """
    datos = yaml.safe_load(RUTA_REGLAS_YAML.read_text(encoding="utf-8"))
    ids_yaml = {r["id"] for r in datos["reglas"]}
    ids_mut = set(_MUTACIONES)
    faltan = ids_yaml - ids_mut
    sobra = ids_mut - ids_yaml
    if faltan or sobra:
        raise RuntimeError(
            "docx_factory desincronizado con reglas_unt.yaml: "
            f"reglas en YAML sin mutación={sorted(faltan)} "
            f"mutaciones sin regla en YAML={sorted(sobra)}"
        )


_validar_sincronizacion()


# Conveniencia: exposición del resultado esperado del documento base.
DESVIOS_BASE = len(EXCLUIDAS_BASE)
TOTAL_REGLAS = len(REGLAS)
REGLAS_OK_BASE = TOTAL_REGLAS - DESVIOS_BASE