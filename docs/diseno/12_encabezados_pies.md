# Diseño — Encabezados y pies de página (ítem 2 de la Fase 2)

> Documento: `12_encabezados_pies.md`
> Estado: ✅ **IMPLEMENTADA** (2026-09-21, Semana 5, rama `semana5-motor-calidad-paginacion`)
> Autor: IvanSanchezSil (Integrante 3 — Motor de reglas / DSL)
> Alcance: [ítem 2 del backlog](../PLAN_BACKLOG_FUTURO.md): número de página,
> membrete con logo y formato del encabezado.
> Relacionado: [`validator/extractor.py`](../../validator/extractor.py) ·
> [`reglas_unt.yaml`](../../reglas_unt.yaml) ·
> [`tests/test_f2_encabezados.py`](../../tests/test_f2_encabezados.py) ·
> [`tests/_docx_builder.py`](../../tests/_docx_builder.py)

## 1. Contexto

El motor solo leía las partes `word/footer1.xml` y `word/header1.xml` (una por
tipo). Un DOCX real usa tantos encabezados/pies como secciones diferentes
tenga (`header1.xml`, `header2.xml`, ...), así que había dos huecos:

1. **Extractor**: no se podían validar encabezados/pies de documentos con más
   de una parte del tipo.
2. **Reglas**: no existía ninguna regla de membrete/formato del encabezado.

## 2. Decisión de extracción: todas las partes, con compatibilidad

`ExtractedDocx` pasa a guardar `headers: list` y `footers: list` (todas las
partes `word/header*.xml`/`word/footer*.xml`, ordenadas). Las propiedades
`header`/`footer` devuelven la primera parte, preservando el contrato con el
motor legacy (`checks.py` llama `extracted.part("footer")`).

`xpath(parte, expr)` consulta **todas** las árboles de ese tipo y combina los
resultados, manteniendo la caché por `(parte, contexto, xpath)`. Un
`presencia_xml`/`atributo_xml` con `parte: header` o `parte: footer` funciona
igual para un encabezado que para diez.

## 3. Reglas nuevas (warning, estándar institucional)

El manual no define el membrete del encabezado (solo la posición de la
numeración, que ya cubre `numeracion_posicion`). Las dos reglas codifican el
**estándar institucional UNT** y entran como `warning`, con nota `EVALUADO:`
en el YAML (convención de desvíos documentados):

| Regla | DSL | Mecanismo |
|---|---|---|
| `encabezado_membrete` | `presencia_xml` | `//w:drawing` en `parte: header` → logo repetido |
| `encabezado_formato` | `atributo_xml` | `//w:r/w:rPr/w:rFonts/@w:ascii` all_eq `Times New Roman` |

No fue necesario un analizador nuevo: la sección `header_footer` del backlog
se resuelve con los analizadores existentes (`presencia_xml`/`atributo_xml`)
gracias a la extracción multi-parte.

## 4. Factory

- `configuracion_base()` gana `header_logo: True` y `header_fuente:
  "Times New Roman"`; `compilar_docx` escribe `word/header1.xml` (membrete:
  logo + "UNIVERSIDAD NACIONAL DE TRUJILLO") y las secciones referencian
  `rIdHeader`/`rIdFooter`.
- Mutaciones: `encabezado_membrete` (`header_logo=False`) y
  `encabezado_formato` (`header_fuente="Arial"`), cada una desvía **solo** su
  regla (aislamiento verificado por `test_propiedad`).

## 5. Evidencia

- `test_extractor_leer_todas_las_partes_header_footer` y
  `test_xpath_header_combina_todas_las_partes`: listas y consulta combinada.
- `test_xpath_sin_headers_levanta`: `ValueError` si no hay partes del tipo.
- `test_encabezados_base_pasan` / `test_encabezado_*_falla` + aislamiento
  entre membrete y formato.
- `test_fallo_de_encabezado_no_altera_ubicacion`: los párrafos de header/pie
  no están en el mapa de paginación (ítem 1), por lo que la ubicación queda
  intacta (sin sufijo "página N").

## 6. No-alcance

- Notas al pie (`w:footnote`) → ítem 3 (siguiente).
- Encabezados/pies **por sección** con numeración distinta (p. ej. romano en
  preliminares, arábigo en cuerpo): ya cubierto parcialmente por
  `numeracion_preliminares_romano`/`numeracion_cuerpo_arabigo`.