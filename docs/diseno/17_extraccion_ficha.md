# Diseño: extracción de la ficha de depósito (motor)

**Fecha**: 2026-10-20
**Semana**: 9
**Área**: Motor de reglas (Int3)
**Pedido**: `docs/HANDOVER_MOTOR_FICHA_DEPOSITO.md` (Int1)
**Plan de producto**: `docs/PLAN_FICHA_DEPOSITO.md`

## 1. Qué se construye

Los analizadores ya **localizan** título, autores, asesor, resumen, palabras
clave y escuela, pero solo publican pass/fail y un `found` resumido. La pantalla
de depósito (SPA I2) necesita **el texto completo, con su página**, para
pre-llenar el formulario oficial de DSpace.

El motor debe entregar, por dato (contrato §4 del handover):

```
{"campo": "dc.title", "valor": "...", "pagina": 1, "detectado": true}
```

Solo lectura: no cambia el semáforo, no agrega reglas de validación, no toca
`validator/api.py` ni `validator/dspace.py`.

## 2. Mecanismo elegido

El handover ofrece dos opciones. Se elige un **híbrido** porque ninguna de las
dos, sola, cubre bien los campos del contrato (8 capturados desde 2026-11-23,
más `renati.juror`, que sigue en viabilidad):

- La ficha captura **párrafos de carátula** (título, autores, asesor, escuela,
  año) que **no** son las reglas ya mecanizadas de la carátula (esas validan
  tamaño/negrita, no capturan el nodo del dato). Son localizaciones nuevas,
  baratas, sobre la carátula.
- La ficha también reusa las reglas existentes de **sección** (resumen,
  palabras clave), que ya tienen su propio `xpath`/`seccion` en el YAML.

Por lo tanto:

1. **Sección DSL nueva `extraccion`** (`AnalizadorExtraccion`): un analizador
   de hoja que **captura el texto del nodo** (o de los nodos) que su XPath
   localiza, y lo publica en un acumulador de la corrida. Se usa para los
   párrafos de carátula, donde la localización es nueva y declarativa.
2. **Sección DSL `extraccion` anidada en reglas existentes**: las reglas que
   ya localizan una sección/texto (resumen, palabras clave, línea) declaran
   `extraccion` en su misma config; el analizador que ya trae el XPath lo
   reutiliza. Evita duplicar XPath en el YAML.
3. **Campo `ficha` en `RuleResult`** (opcional): el analizador, al capturar,
   deja el `(campo, valor, nodo)`; `ReglaCompilada.ejecutar` lo adjunta al
   `RuleResult`, que calcula `pagina` con `extracted.pagina_de(nodo)`.
   `to_dict()` expone `ficha`. La API recolecta los `ficha` de todos los
   resultados y arma `extraidos[]`.

Así el formato es uniforme (lo decide el motor, no cada regla a mano), la API
no parsea `found`, y el costo es acotado: un analizador de hoja nuevo + un
campo opcional en `RuleResult` + el acumulador.

## 3. Alternativas descartadas

- **Campo `valores` genérico en cada regla** (opción (a) pura): obliga a que
  cada regla decida su formato a mano; sin `extraccion` declarativa no queda
  uniforme. Se conserva solo el transporte (`ficha` en `RuleResult`), no la
  captura ad-hoc.
- **Dict de contexto** (`contexto["ficha"]`, opción (b) pura): el contexto hoy
  es `dict[str, str]` para `expone`/`aplicar_si`; meterle una lista de dicts lo
  ensucia y no viaja al DTO (la API consume `RuleResult`, no el contexto).
- **Detección de año fuera del motor** (regex en la API): rompe la regla "la
  API no parsea texto para inventar heurísticas por regla".

## 4. Campos y claves (contrato §2 y §4)

| Campo (clave) | Origen | Estado |
|---------------|--------|--------|
| `dc.title` | párrafo de título en carátula | localización nueva |
| `dc.contributor.author` | párrafo de autor(es); lista si hay varios | localización nueva |
| `dc.contributor.advisor` | párrafo de asesor | localización nueva |
| `dc.description.abstract` | sección Resumen | reusa `resumen_longitud` |
| `dc.subject` | palabras clave del resumen | reusa `palabras_clave_minimo` |
| `dc.date.issued` | año en carátula | localización nueva |
| `escuela` | línea "ESCUELA ACADÉMICO PROFESIONAL DE…" | localización nueva |
| `renati.advisor.orcid` | párrafo de la etiqueta del asesor o hasta dos párrafos siguientes | detectado desde 2026-11-23 (PR 1 del reparto ORCID) |
| `renati.juror` | sección de firmas / jurado | **viabilidad**: ver §6 |

`valor` es `str` o `list[str]` (autores, palabras clave, jurado). `pagina` se
calcula del nodo capturado (mayoría en carátula → página 1). `detectado` es
`false` cuando el XPath no encontró el nodo: la ficha publica el campo igual,
para que la SPA muestre el hueco vacío.

**Fuera del pedido** (handover §2, actualización 2026-10-19): el servidor de
DSpace pre-llena por colección 16 campos, así que el motor **no** captura:

- **Grado/título al que opta** (`thesis.degree.name`): pre-lleno.
- **Línea de investigación** (`dc.subject.ocde`): pre-llena. El **mapeo
  línea→OCDE queda cancelado** para el depósito (no era una fase pendiente, se
  descarta).
- DNI del autor/asesor, DOI e ISBN: los teclea el operador; el motor no los
  busca. El ORCID del **autor** sigue siendo manual.

**Cambio de decisión (2026-11-23, PR 1 del reparto ORCID con Int1 e Int2):**
el ORCID del **asesor** pasa de campo manual a campo detectado. Sale de la
carátula con `ficha_orcid_asesor`: se acepta en el párrafo de la etiqueta o en
los dos párrafos no vacíos siguientes, con o sin `https://orcid.org/`. En el
mismo cambio, `ficha_asesor` y `ficha_autores` dejan de descartar párrafos por
contener `orcid.org`: ahora separan la línea pura con `filtro` y recortan el
ORCID pegado al nombre con `quitar_sufijo`. La detección del checksum y su
publicación en la API son del PR 2 (Int1); en este PR el contrato HTTP no
cambia porque `CAMPOS_EXTRAIDOS_FICHA` aún no incluye la clave.

**Ajustes de la revisión (2026-11-24, PR #124):** el corte en «Línea de
investigación:» se acotó a una línea que tenga un párrafo de asesor precedente
(y el equivalente en `ficha_autores`, con un párrafo de autor precedente). Sin
ese ámbito, una línea previa al bloque tumbaba la captura del asesor o de los
autores. `quitar_sufijo` acepta ahora el prefijo opcional «(Código) ORCID:»
para que el identificador sin URL no quede pegado al nombre. Se cubren con
tests el ORCID desnudo, el ORCID con etiqueta y la línea de investigación
previa. La clave ausente cuando no hay ORCID se mantiene: retblast confirmó
que la API garantiza la forma del contrato en el PR 2.

Por eso `escuela` no es un campo del formulario de DSpace, sino el dato de la
columna ESCUELAS del registro de la biblioteca (el operador lo usa fuera de la
pantalla).

## 5. Notas de implementación

- El analizador de extracción **nunca falla** la validación: es captura, no
  chequeo. `analizar` devuelve `True` siempre (si el nodo existe captura; si
  no, no captura). No altera el semáforo.
- Los párrafos se localizan sobre `//w:body/w:p` con el contexto `caratula`
  donde aplique, y `pagina_de` resuelve la página física.
- La lista de autores se separa como lo hace `caratula_autores_*` (un valor
  por párrafo/autor); si la plantilla pone "Autores: A y B" en un párrafo, se
  guarda el texto completo y la SPA lo divide (no se inventa un separador).
- Se sincroniza `tests/_mutations.py` si la `extraccion` anidada cambia el
  `found` de una regla existente (regla de `AGENTS.md`): **no debería**, porque
  la captura no modifica el fallo previo; se verifica con la suite.

## 6. `renati.juror` — conclusión de viabilidad

El handover pide evaluar si los nombres del jurado salen de forma confiable de
la sección de firmas. Se inspeccionaron la plantilla oficial y una tesis real:

- **Plantilla** (`EDUCACION INICIAL-PLANTILLA...docx`, párr. 31-52): título
  "Jurado Evaluador" seguido de tres bloques `____` + "(Dr. o Mg. o Lic.)
  (Apellidos completos, Nombres completos)" + `Presidente` / `Secretario (a)` /
  `Miembro`. Son **placeholders**: el operador los rellena a mano.
- **Tesis real** (`recursos/tesis/tesis_linares_2026.docx`, párr. 43): título
  "Jurado Dictaminador" y luego **líneas en blanco** hasta "Agradecimiento".
  Los nombres no están en el DOCX.

**Conclusión**: los nombres del jurado **no** salen de forma confiable del
DOCX. Dependen de que el autor los escriba (a veces no lo hace; cuando lo
hace, la disposición varía entre "Evaluador" y "Dictaminador", con o sin
cargos). Inventar una heurística produciría datos falsos en un metadato
oficial. Por eso **no se implementa captura de `renati.juror`**: queda
`detectado: false` y el operador lo teclea en la pantalla, como preveía el
handover. Se reevaluará si la facultad estandariza la sección de firmas con
nombres reales.


## 7. Verificación pedida (handover §5)

- Tests de que cada campo de la §2 expone su valor con el factory determinista.
- Paridad: la ficha extrae los placeholders en las 5 plantillas (esperable).
- Suite completa verde y `tests/_mutations.py` sincronizado si aplica.

## 8. Wiring de la API (Int1)

El motor ya entrega `reporte["ficha"]` con el diccionario que la API espera.
Falta que `POST /validar` evalúe el ruleset de captura en la misma pasada:

```python
from validator.engine import load_ficha_rules
...
resultados_motor = await run_in_threadpool(
    validate_docx, tmp_path, rules_data, load_ficha_rules()
)
```

`_ficha_desde_reporte` y `FichaDeposito` ya están en `validator/api.py` y
`validator/api_models.py`; no requieren cambio: recorren las claves de la §2 y
rellenan `detectado=false` para las ausentes (`renati.juror`, o cualquier
campo que el XPath no encontró). Este cambio vive en el área de Int1; el motor
no lo hace (handover §6: "no tocar la API").

## 9. RI-07 — acotar el XPath de carátula (2026-11-24)

Retblast midó, sobre la tesis no aprobada, 14,33 s en
`caratula_autores_tamano` y 26,41 s en `ficha_autores`: 40,74 de 44,29 s.
Ambas consultas usan `following-sibling::` / `preceding-sibling::`, y
`ExtractedDocx.xpath()` evaluaba el XPath en **todo** el `word/document.xml`
para recién después filtrar por `contexto: caratula`.

**Mecanismo elegido.** Para `parte: document` con contexto `caratula` o
`caratula_ficha`, `xpath()` evalúa sobre un `w:body` copia que contiene solo
los párrafos de la carátula, en el mismo orden. Un mapa nodo copia → nodo
original traduce los resultados antes de devolverlos: así la paginación
(`pagina_de`) y los conjuntos `_caratula`/`_caratula_ficha` siguen
indexados por los nodos reales. Los resultados que no son elementos
(atributos, texto, escalares) caen al camino anterior, sin traducción.

**Invariantes que se preservan** (son los que retblast pidió explícitamente):

- el orden de los autores (`dc.contributor.author` es una lista);
- los cortes por «ASESOR(A):» y «Línea de Investigación:» introducidos en el
  PR #124, que solo rigen si hay una etiqueta precedente;
- la separación del ORCID respecto del nombre del asesor y de los autores;
- el semáforo, el resumen y las 8 capturas de la ficha.

**Alcance del supuesto.** El catálogo actual solo consulta, desde un nodo de
carátula, hermanos **dentro** de la carátula; no usa `last()`/`position()`
sobre el cuerpo ni mira párrafos posteriores al salto de sección. Si una
regla futura necesita esos ejes, debe evaluarse con el árbol completo o
actualizarse este mecanismo. `tests/test_caratula_xpath.py` compara, para
**todas** las expresiones de carátula de `reglas_unt.yaml` y
`reglas_ficha.yaml`, el resultado reducido contra el filtro anterior; esa
regresión avisa si el supuesto deja de valer.

**Medición sintética.** Con 250 párrafos de cuerpo y una pasada por consulta:
`caratula_autores_tamano` 0,204 s → 0,001 s (×227) y `ficha_autores`
1,493 s → 0,002 s (×792). Con 1500 párrafos, la primera pasó de 6,254 s a
0,001 s.

**Medición con el corpus real (2026-11-24).** Se usaron las dos versiones de
la tesis (la que lleva `(1)` es la aprobada) y las cinco plantillas oficiales
que aportó retblast, sin copiar ningún documento al repo. Herramienta
reproducible: `python scripts/medir_caratula.py <docx...>` (ejecuta la
validación con el motor actual y con la implementación previa a RI-07,
compara el reporte completo e imprime los tiempos).

| Documento | Antes | Después | Resultado |
|---|---|---|---|
| Tesis aprobada `(1)` | 37,65 s | 2,63 s | verde, 0 errores, 5 advertencias, 42/54 |
| Tesis no aprobada | 37,20 s | 2,22 s | rojo, 4 errores, 5 advertencias, 42/54 |
| Educación Inicial | 0,26 s | 0,14 s | rojo, 2 errores, 9 advertencias |
| Otras cuatro plantillas | 0,26–0,27 s | 0,11–0,17 s | rojo, 4 errores, 9 advertencias |

Las dos consultas críticas, medidas por separado en la tesis no aprobada,
pasaron de 10,30 s a 0,007 s (`caratula_autores_tamano`) y de 16,60 s a
0,010 s (`ficha_autores`). En los siete documentos el reporte completo
—semáforo, resumen, IDs/estados/severidades de las reglas y las 8 claves de
la ficha— fue **idéntico** antes y después. Los cuatro errores de la tesis no
aprobada siguen siendo `tamano_cuerpo`, `interlineado`, `alineacion_cuerpo` y
`estructura_tinv_cuantitativo`; la aprobada mantiene las siete capturas
esperadas (incluidos los dos autores) más `renati.advisor.orcid`.

