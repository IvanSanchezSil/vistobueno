# Bitácora Semana 5 — ivanSanchezSil

- **Integrante**: Iván Sánchez Silva (Integrante 3 — Motor de reglas)
- **Semana**: 5
- **Fechas**: 2026-09-15 → 2026-09-22
- **Rol**: Motor de reglas / Procesamiento (DSL, extractor, checks)

---

## Objetivos de la semana

1. Cerrar la fase **F2 (mecanización del territorio no validado)** del motor DSL:
   - Ítem 1: ubicación por página física (`location` enriquecido).
   - Ítem 2: encabezados y pies de página.
   - Ítem 3: notas al pie.
2. Mantener los invariantes de calidad (property tests, sincronización factory↔YAML).
3. Evaluar los ítems 11 y 12 (TOC y numeración jerárquica) contra la realidad de las plantillas antes de mecanizar.

## Actividades realizadas

### 2026-09-21 (planificación)

- Reunión de planificación de la F2; plan consolidado presentado y aprobado ("arranca").

### 2026-09-22 (implementación)

- **Ítem 1 — paginación + `location`** (commit `28b2c57`):
  - `Analizador.ultimo_nodo` setea el nodo objetivo en `_nodos()` y en `AnalizadorPaginacion`.
  - `ReglaCompilada.ejecutar()` anexa `"; página N"` a `ubicacion` cuando la regla FALLA y el nodo tiene página en el mapa.
  - Cita manual: párr. 139 "…la carátula no se enumera, pero se cuenta…" y párr. 184.
  - Verificado que `caratula_no_se_enumera` ya estaba mecanizada en el YAML (no se duplicó).
- **Ítem 2 — encabezados y pies** (commit `1cacd14`):
  - `ExtractedDocx` lee **todas** las partes `header*.xml`/`footer*.xml`; `xpath()` combinado con caché por (parte, contexto, xpath).
  - Reglas `encabezado_membrete` (logo/`w:drawing`) y `encabezado_formato` (Times New Roman), ambas `warning`, con nota `EVALUADO:` (el manual no las define; es estándar institucional UNT).
  - Factory: `header1.xml` con membrete, mutaciones `header_logo=False` y `header_fuente="Arial"`.
  - Evidencia LFA: defecto de la **automatización**
- **Ítem 3 — notas al pie** (commit `e38969a`):
  - Sección DSL `nota_pie` + `AnalizadorNotaPie` (numeración `1..N` consecutiva, sin duplicados, existencias en `footnotes.xml`; sin notas → n/a).
  - `ExtractedDocx.footnotes` (parte opcional `word/footnotes.xml`).
  - Factory: `notas_pie_ids` y mutación `[1,2,4]` (salto).
  - Evidencia LFA: diagramas de estados/transiciones del contador.
- Conteos sincronizados: **45 reglas**, doc bueno **43/45**, 45 mutaciones, suite **187 tests**.
- **Ítems 11-12 (TOC/numeración jerárquica)**: revisados a fondo → **diferidos**. La plantilla oficial usa "1.3. EL PROBLEMA" → "1.5 VARIABLE(S)…" (saltos) e índices con puntillado y números de página; las reglas aprobadas generarían falsos positivos contra la plantilla. Se documentó en `docs/PLAN_BACKLOG_FUTURO.md` con el criterio a definir.

## Evidencias producidas

| Tipo | Archivo / referencia |
|------|----------------------|
| Diseño | `docs/diseno/11_ubicacion_pagina.md`, `12_encabezados_pies.md`, `13_notas_al_pie.md` |
| Reglas | `reglas_unt.yaml` (44→45; encabezado_membrete, encabezado_formato, notas_al_pie_consistencia) |
| Motor | `validator/analizadores.py` (ultimo_nodo, AnalizadorNotaPie), `compilador.py`, `dsl_check.py`, `extractor.py` |
| Tests | `tests/test_f2_paginacion.py`, `tests/test_f2_encabezados.py`, `tests/test_f2_notaspie.py` |
| Factory | `tests/_docx_builder.py`, `tests/_xml_constants.py`, `tests/_mutations.py`, `tests/docx_factory.py` |
| Backlog | `docs/PLAN_BACKLOG_FUTURO.md` (ítems 1-3 ✅; 11-12 ⏸️ diferidos) |
| Commits | `28b2c57`, `1cacd14`, `e38969a` (rama `semana5-motor-calidad-paginacion`) |
| Gates | `pytest` 187 passed; `ruff` y `mypy` limpios |

## Relación con competencias curriculares

- **Estructura de Datos**: mapa párrafo→página, estructura de árboles XML multiparte, contador de notas.
- **Ingeniería de Software II**: property tests (invariante: toda regla con mutación), factory determinista, documentación de decisiones.
- **Redes de Computadoras I**: sin cambios de contrato HTTP; la API consume las 45 reglas (verificación con la suite de contrato del backend).

## Dificultades y aprendizajes

- El rango del manual es **manual normativo**, no descriptivo de Word: encabezados y notas no están regulados → reglas como `warning` con nota `EVALUADO:` y pase n/a cuando no aplican.
- **Lección clave**: validar las reglas propuestas contra las plantillas OFICIALES ANTES de mecanizar evitó dos reglas con falsos positivos (ítems 11-12): la propia estructura "1.3/1.5" y el puntillado de los índices las hacían inviables tal como se habían diseñado.
- Los cambios en la parte `footnotes.xml` deben manipularse con namespace (`{WNS}id`), no con prefijo "w:id".

## Plan de la semana siguiente

1. Push de `semana5-motor-calidad-paginacion` y actualización del PR #28.
2. Contar con el Backend para el ítem 16 (`formato` en `POST /validar`).
3. Ítems 11-12: redefinir criterio (variante débil de numeración o pase asegurado contra plantillas) y evaluar con `scripts/eval_contra_plantillas.py` (ítem 13 del backlog).