# Bitácora Semana 12 — ivanSanchezSil

- **Integrante**: ivanSanchezSil (Integrante 3 — Motor de reglas / Procesamiento)
- **Semana**: 12
- **Fechas**: 2026-11-12 → 2026-11-18 (semana en curso)
- **Rol**: extractor, motor, analizadores, reglas YAML, exportador/CLI y
  pruebas/factory del motor
- **Rama de trabajo**: `semana12-m11-factory-opc`
- **Base**: `upstream/master` `bf6be5e` (PR #94)
- **Plan**: [`PLAN_SEMANA12_MOTOR_CORRECTITUD.md`](PLAN_SEMANA12_MOTOR_CORRECTITUD.md)

---

## Objetivos de la semana

1. Ejecutar las tareas de correctitud del motor (`M1a`, `M1`–`M12`) en PRs
   pequeños, con regresión previa al arreglo.
2. Empezar por `M11` (paquete OPC del factory) y `M1a` (validación del
   extractor) porque desbloquean B6 y B5 de Int1.
3. Mantener intactos la API, la SPA, el userscript y `AGENTS.md`.

---

## Actividades realizadas

### 2026-11-12 — Plan de la Semana 12 (PR #97)

Se documentó el desglose de hallazgos `VA`/`NM` en tareas y PRs, con orden,
dependencias, criterios de aceptación, decisiones pendientes del encargado y
calendario de las semanas 12 y 13. El plan no declara corregido ningún
hallazgo.

### 2026-11-12 — M11 / VA-17: paquete OPC del factory (PR 12.1)

**Reproducción previa al arreglo**

```bash
PYTHONPATH=/home/ivan/pylibs:.:tests python3 - <<'PY'
import docx
from _docx_builder import compilar_docx, configuracion_base
docx.Document(compilar_docx(configuracion_base()))
PY
```

Resultado: `KeyError: "There is no item named 'media/logo.png' in the archive"`.
El ZIP solo tenía `[Content_Types].xml`, `_rels/.rels`, `word/document.xml`,
`word/header1.xml` y `word/footer1.xml`. Las relaciones de cabecera, pie,
imagen e hipervínculo estaban en `_rels/.rels` (raíz), no existía
`word/_rels/document.xml.rels` ni `word/_rels/header1.xml.rels`, y el PNG
nunca se escribía.

**Arreglo**

- `_rels/.rels` declara solo el documento principal.
- `word/_rels/document.xml.rels` declara cabecera, pie, imagen de portada e
  hipervínculo ORCID.
- `word/_rels/header1.xml.rels` declara el logo del membrete.
- Se escribe un PNG válido de 1×1 en `word/media/logo.png`.
- Si hay notas al pie, se agregan su relación y su `Override` en
  `[Content_Types].xml`; si no hay, no se declaran partes inexistentes.
- Regresión nueva en `tests/test_docx_factory_opc.py`: abre con
  `python-docx`, resuelve todos los destinos internos, comprueba que cada
  `r:id`/`r:embed` esté declarado en su parte, valida el PNG y exige tipo de
  contenido para cada parte.

**Verificación**

```bash
PYTHONPATH=/home/ivan/pylibs:.:tests python3 -m pytest tests/ -q
# 836 passed, 4 skipped, 6 xfailed

~/.local/bin/ruff check validator/ scripts/ tests/
~/.local/bin/ruff format --check validator/ scripts/ tests/
PYTHONPATH=/home/ivan/pylibs python3 -m mypy validator/ scripts/
# All checks passed / 81 files already formatted / Success
```

**Límites**

- No se regeneraron `docs/ejemplos/doc_bueno.docx` ni `doc_malo.docx`: B6 de
  Int1 es quien los regenera y refuerza la guardia. El comando es
  `python scripts/ejemplo_bueno_malo.py`.
- El PNG es un marcador de 1×1: las reglas solo cuentan nodos `a:blip`, no
  inspeccionan dimensiones ni píxeles.
- La medición real del logo sigue siendo M7 (VA-15), pendiente de decisión.

**Entrega a Int1**

- Commit `85690c5` (rama `semana12-m11-factory-opc`, PR 12.1).
- Comando de regeneración: `python scripts/ejemplo_bueno_malo.py`.

### 2026-11-13 a 2026-11-16 — M1 / VA-01, VA-02: formato efectivo y todo el texto (PR 12.3)

**Arreglo**

- `ResolvedorFormato` resuelve el formato efectivo con la precedencia de Word:
  formato directo → estilo de carácter → cadena `basedOn` del estilo de
  párrafo → `w:docDefaults`. Un ciclo de estilos se reporta como
  incumplimiento sin tumbar la validación, y `word/styles.xml` ausente o mal
  formado se trata como ausente.
- `AnalizadorFormato` (`formato_efectivo`) selecciona primero los párrafos y
  evalúa **todos** los runs con texto, incluidos los de hipervínculo. Una
  propiedad ausente se reporta como `(ausente)` y cuenta como incumplimiento.
- Se migran 16 reglas de fuente, tamaño, interlineado, alineación y negrita
  del cuerpo y de la carátula.
- El linter del DSL valida `parrafo_xpath` y `propiedad`.

**Corrección del alcance (`cuerpo_prosa`)**

`alineacion_cuerpo` con `contexto: cuerpo` ponía en rojo la tesis aprobada:
declaraba 270 valores evaluados y 19 incumplimientos, todos `(ausente)`. Los
19 no eran prosa: 5 ítems de lista, 13 títulos de tabla y figura y 1 línea de
leyenda de fórmula. Ninguno de esos estilos define `w:jc`, así que Word los
dibuja alineados a la izquierda.

- Se añade el contexto `cuerpo_prosa` sobre `_cuerpo_paras`: excluye los
  ítems de lista (`w:numPr` directo o estilo cuyo `w:name` sea `list
  paragraph`), los títulos de tabla y figura (estilo cuyo `w:name` contenga
  `caption`) y las líneas de nota o leyenda. La exclusión es por **nombre de
  estilo**, para que también funcione un Word en inglés.
- Solo `alineacion_cuerpo` cambia a ese contexto. `fuente_principal`,
  `tamano_cuerpo` e `interlineado` siguen con `contexto: cuerpo`, porque el
  texto de listas y títulos también debe revisarse en fuente, tamaño e
  interlineado.
- No se relaja `all_eq`: un párrafo de prosa sin `w:jc` sigue fallando.

**Corrección de integridad OPC**

La revisión de M11 señaló que `[Content_Types].xml` declaraba el `Override` de
`word/styles.xml` siempre, aunque el factory solo escribe esa parte cuando la
configuración trae `styles`. Un tipo de contenido que apunta a una parte
ausente rompe el paquete OPC.

- El `Override` de estilos se declara solo cuando la parte se escribe, igual
  que el de notas al pie.
- Regresión: `test_el_override_de_estilos_solo_se_declara_con_la_parte` y
  `test_cada_override_apunta_a_una_parte_existente`.

**Plantillas oficiales**

El resultado pasa de 1 error + 6 warnings a **2 errores + 6 warnings**: el
error nuevo es `caratula_titulo_negrita_mixta`, que se mantiene estricto por
decisión. La evaluación de plantillas es **orientativa** y un test
parametrizado fija ese resultado cuando `recursos/` está disponible.
`palabras_clave_minimo` se mantiene en `error` (decisión del 2026-11-08).

**Verificación**

```bash
PYTHONPATH=/home/ivan/pylibs:.:tests python3 -m pytest tests/ -q
# 863 passed, 9 skipped, 6 xfailed
```

**Límites**

- M1 queda como **implementado, pendiente de verificación**: el PR sigue
  abierto y la comprobación con la tesis aprobada y las cinco plantillas
  oficiales está en manos de la revisión.
- La heredad de estilos se resuelve por `basedOn`; los temas, la numeración,
  el formato condicional, los estilos de tabla y los cambios con seguimiento
  no se soportan (documentados en `ResolvedorFormato`).

**Entrega a Int1**

- Commits `2635879`, `0cac33e` y `f7a4795` (rama `semana12-m1-formato-efectivo`,
  PR 12.3).
### 2026-11-14 — M4 / VA-05: declaraciones múltiples (PR #103)

**Reproducción previa al arreglo:** los 6 casos nuevos de
`TestDeclaracionesMultiples` fallaban con el código anterior; las 3
declaraciones del mismo tipo ya pasaban.

**Arreglo:** `DeteccionTipo._tipo_declarado` devuelve todas las casillas
marcadas; `analizar` agrupa por tipo. Dos tipos distintos publican
`TIPO_CONTRADICTORIO` y el centinela `tipo_documento_contradictorio`; repetir
el mismo tipo no cambia la decisión. La evidencia queda ordenada por tipo.

**Verificación:** `924 passed, 4 skipped`; ruff, ruff format, mypy y linter
limpios; CI verde y PR `MERGEABLE`/`CLEAN`.

**Entrega:** commits `23a1314` (código, tests y DSL) y `75f2705` (handovers),
rama `semana12-m4-tipo-declarado`, PR #103 apilado sobre #75.

### 2026-11-15 — M5 / VA-06, VA-07: Resumen, Abstract y palabras clave

**Reproducción previa al arreglo:** `resumen_longitud` solo tenía mínimo 159 y
contaba la línea de palabras clave como prosa; `palabras_clave_minimo` solo
revisaba el Resumen, contaba tras el primer `:` global y no tenía máximo; no
existía ninguna regla que detectara un Abstract sin cuerpo.

**Arreglo:**

- `resumen_longitud`: 159–220 palabras; `excluir` descarta la línea de palabras
  clave antes de contar.
- `palabras_clave_minimo`: 3–5 claves; `secciones` cuenta Resumen y Abstract
  por separado; admite las etiquetas `Palabras clave` y `Keywords`.
- `abstract_contenido`: nuevo warning que exige al menos una palabra de cuerpo
  en el Abstract, sin contar su línea de claves.
- `patron_cantidad`: admite `secciones`, `excluir` y `cantidad_maxima`;
  `count_entries` cuenta por párrafo. El linter valida la forma nueva.

**Verificación:** `935 passed, 4 skipped`; 50 reglas (44 evaluadas en el
documento base); ruff, ruff format, mypy y linter limpios; ejemplos
regenerados.

**Decisiones pendientes:** ratificar la tokenización `\w+` del Resumen y la
severidad `warning` de `abstract_contenido`; confirmar si ambos idiomas son
obligatorios y si `Keywords` es la etiqueta inglesa documentada. El manual
local no está en el repo.

**Entrega:** commit `d85c6e0`, rama `semana12-m5-resumen-abstract`, PR apilado
sobre #103.

---

## Evidencias

| Evidencia | Archivo / comando |
|---|---|
| Plan de la semana | `docs/PLAN_SEMANA12_MOTOR_CORRECTITUD.md` (PR #97) |
| Reproducción de M11 | `KeyError: media/logo.png` con `python-docx` |
| Regresión | `tests/test_docx_factory_opc.py` (12 casos) |
| Arreglo | `tests/_xml_constants.py`, `tests/_docx_builder.py` |
| Suite M11 | 836 passed, 4 skipped, 6 xfailed |
| Regresión M4 | `tests/test_tipo_documento.py::TestDeclaracionesMultiples` (9 casos) |
| Regresión M5 | `tests/test_f3_mecanizacion.py::TestM5ResumenAbstract` (10 casos) |
| Suite M4 | 924 passed, 4 skipped |
| Suite M5 | 935 passed, 4 skipped |
| Estado de los hallazgos | §2 de `HANDOVER_CORRECTITUD_2026-11-12.md` |

---

## Dificultades y aprendizajes

- El extractor propio toleraba el paquete roto, así que la suite no lo
  detectaba; hizo falta abrir el DOCX con `python-docx` para reproducir el
  fallo que ve Int1.
- OPC exige que cada parte declare sus propias relaciones: un `Id` de
  `document.xml` no es visible desde `header1.xml`, aunque el nombre coincida.
- Declarar relaciones o tipos de contenido de partes ausentes también rompe
  el paquete; por eso las notas al pie se agregan solo cuando existen.
- El mismo criterio aplica a los estilos: M1 añadió `word/styles.xml` al
  factory y tuvo que declarar su `Override` de forma condicional, porque el
  paquete base no lleva esa parte. Un `Override` colgante no lo detecta el
  extractor propio (tolera el paquete roto), así que la única guarda es abrir
  el DOCX con `python-docx` y comprobar que cada tipo de contenido tiene su
  parte.

---

## Plan de la semana siguiente

1. Abrir y revisar el PR 12.1 (M11).
2. Implementar M1a: validar la entrada del extractor y documentar las partes
   OPC mínimas admitidas (desbloquea B5 de Int1).
3. Continuar con M1 (formato efectivo y revisión de todo el texto).
