# Plan de backlog futuro del Motor

> **Estado**: backlog de trabajo — parcialmente ejecutado.
> **Fecha de creación**: 2026-09-15.
> **Alcance**: motor de validación DSL, extractor y API. El módulo de IA queda fuera hasta que el integrante lo indique.
>
> **Ejecutado 2026-09-15/16 (Fase 1 parcial)**:
> - **15 — Calidad de ingeniería** ✅: *ruff + mypy + coverage + pre-commit* agregados a `flake.nix`; config en `pyproject.toml`; `.pre-commit-config.yaml`; CI `.github/workflows/ci.yml` (Nix); `nix flake check` verde. Detalle: [`docs/diseno/10_calidad_y_exportacion.md`](diseno/10_calidad_y_exportacion.md).
> - **16 — Exportación de reporte** ✅ (solo CLI): `validator/exportador.py` (Markdown + PDF vía WeasyPrint) + `--formato/--salida` en CLI. **Pendiente para el compañero de API/frontend**: exponer `formato` en `POST /validar` (afecta `CONTRATO_API.md` v1.2.0 y `openapi_spec.json`). Detalle: [`docs/diseno/10_calidad_y_exportacion.md`](diseno/10_calidad_y_exportacion.md).
> - **1 — Paginación real** ✅ (2026-09-21, F2 ítem 1): mapa párrafo→página en `extractor._paginacion_para()` (`w:lastRenderedPageBreak` + `w:br w:type="page"`), `ExtractedDocx.pagina_de()`, sección DSL `paginacion` (`AnalizadorPaginacion`, `paginas_distintas`), regla `indice_paginas_separadas` (warning) **y enriquecimiento de `location`** con "página N" cuando el analizador falla (`ultimo_nodo` en la base `Analizador` + fallback heurístico **sin** LibreOffice; ver "Decisiones pendientes"). La regla de carátula sin enumerar (`caratula_no_se_enumera`) ya estaba mecanizada (presencia de `w:titlePg`). Detalle: [`docs/diseno/11_ubicacion_pagina.md`](diseno/11_ubicacion_pagina.md).

> - **2 — Encabezados y pies** ✅ (2026-09-21, F2 ítem 2): extractor multi-parte y reglas `encabezado_membrete`/`encabezado_formato` (warning). Detalle: [`docs/diseno/12_encabezados_pies.md`](diseno/12_encabezados_pies.md).
> - **3 — Notas al pie** ✅ (2026-09-21, F2 ítem 3): `notas_al_pie_consistencia` con `AnalizadorNotaPie` (numeración 1..N). Detalle: [`docs/diseno/13_notas_al_pie.md`](diseno/13_notas_al_pie.md).

---

## Bloque A — Territorio no validado hoy (extractor/analizadores)

Nuevas reglas para zonas del DOCX que hoy el motor no toca.

| # | Línea de trabajo | Dónde vive |
|---|---|---|
| 1 | **Paginación real + ubicación por página** ✅: `location` se enriquece con "página N" desde la **heurística actual** (`w:lastRenderedPageBreak`/`w:br page`; decisión del 2026-09-21: sin LibreOffice). Hecho: mapa párrafo→página, `pagina_de()`, `AnalizadorPaginacion`, `indice_paginas_separadas`, enriquecimiento en `compilador.ejecutar()` (`base Analizador.ultimo_nodo`). Nota: `caratula_no_se_enumera` (carátula sin enumerar) ya estaba mecanizada vía `w:titlePg`. | extractor + compilador |
| 2 | **Encabezados y pies de página** ✅: el extractor lee TODAS las partes `header*.xml`/`footer*.xml`; reglas `encabezado_membrete` (logo = `w:drawing`) y `encabezado_formato` (TNR), ambas `warning` (estándar institucional, el manual no las define). | extractor + reglas nuevas |
| 3 | **Notas al pie** ✅: regla `notas_al_pie_consistencia` (warning) — ids `1..N` consecutivos, sin duplicados y definidos en `footnotes.xml`; sin notas → pasa (n/a). Sección DSL `nota_pie` + `AnalizadorNotaPie`. | extractor + analizador nuevo |
| 4 | **Track changes**: detectar `w:ins`/`w:del` pendientes de aceptar/rechazar → advertencia de "documento con cambios sin resolver". | extractor + regla nueva |
| 5 | **Metadatos del DOCX** (`core.xml`): autor, título, fechas; regla de consistencia con carátula. | extractor + regla nueva |

---

## Bloque B — Explicabilidad sin IA

Dar contexto al estudiante de **por qué** falla cada regla, sin usar LLM.

| # | Línea de trabajo | Dónde vive |
|---|---|---|
| 6 | **Explicación determinista** con la traza `ruta_estados` (F4): `"reconoció CARÁTULA→INTRODUCCIÓN, falta RESULTADOS"` por regla. | `compilador.py` / `engine.py` |
| 7 | **Corrección sugerida por template** a partir de `(expected, found)` → `"cambiar margen superior a 2,5 cm en Formato→Párrafo"`. Template puro, sin IA. | `prompts.py` o módulo nuevo |

---

## Bloque C — Comparador (sin DB)

| # | Línea de trabajo | Dónde vive |
|---|---|---|
| 8 | **Comparador V1 vs V2**: mismo documento, dos versiones; delta `desaparecieron / aparecieron / persisten`. Estado por sesión en memoria o en una misma petición. | endpoint nuevo / CLI nuevo |

---

## Bloque D — Nuevos analizadores del DSL

Expandir el lenguaje con tipos de analizador que hoy no existen.

| # | Línea de trabajo | Dónde vive |
|---|---|---|
| 9 | **Tablas** (`w:tbl`): encabezado, título "Tabla N", no cortar entre páginas. | analizador nuevo |
| 10 | **Figuras con pie** (`w:drawing` + párrafo-pie). | analizador nuevo |
| 11 | **TOC apunta** ⏸️ DIFERIDO (2026-09-22): el analizador validaba que el índice **apunte** sin números de página. **Falso positivo**: las plantillas UNT usan puntillado con números de página. Requiere redefinir el criterio antes de mecanizar. | analizador nuevo |
| 12 | **Numeración jerárquica** ⏸️ DIFERIDO (2026-09-22) (`1 → 1.1 → 1.2 → 2`, sin saltos) — autómata contador, evidencia LFA directa. **Falso positivo**: la estructura oficial usa "1.3. EL PROBLEMA" → "1.5 VARIABLE(S)…" (sin "1.", sin "1.4"); la regla estricta marcaría a la propia plantilla. Requiere definir variante débil o evaluar contra plantillas (ítem 13) primero. | analizador nuevo |

---

## Bloque E — Operación y calidad

Mejoras que no tocan reglas pero sí el ecosistema del motor.

| # | Línea de trabajo | Dónde vive |
|---|---|---|
| 13 | **Benchmark real**: repositorio de tesis anonimizadas (más allá de las 5 plantillas) + métricas (reglas que pasan en la práctica, precisión). | carpeta nueva + tests |
| 14 | **Rendimiento**: perfilado con tesis de 150+ páginas, cache a nivel de regla (no solo XPath). | `engine.py` / benchmark |
| 15 | **Calidad de ingeniería**: mypy, lint, coverage, pre-commit, CI (hoy no hay). | config nueva + GitHub Actions |
| 16 | **Exportación de reporte** a Markdown/PDF además de JSON. | `engine.py` / módulo nuevo |

> **PENDIENTE → Integrante 1 (Backend)**: el motor DSL pasó de **41 a 45 reglas**
> (Semana 5, ítems 1-3 de la F2). Coordinar para:
> 1. Exponer `formato` en `POST /validar` (exportación, ítem 16, `CONTRATO_API.md` v1.2.0).
> 2. Actualizar `docs/CONTRATO_API.md` (changelog: hoy dice "41 reglas" en v1.1.0;
>    agregar entrada v1.2.0 con 45 reglas). No se editó aquí por ser archivo del área backend.

---

## Orden sugerido (por dependencias, no por semana)

- **Fase 1** (independiente, bajo riesgo, toca alrededor del motor): `15 → 16 → 13 → 14`.
- **Fase 2** (mismo territorio, extractor): `1 → 2 → 3 → 4 → 5`.
- **Fase 3** (sobre el DSL, usa F4/F5): `6/7 (usa traza F4) → 9/10 → 11/12`.
- **Fase 4** (producto/API): `8 (último, necesita petición/estado)`.

---

## Decisiones tomadas / pendientes

- **Render DOCX→PDF** ✅ (2026-09-21): **no se agrega LibreOffice**. El enriquecimiento de `location` usa la heurística con `w:lastRenderedPageBreak` y `w:br w:type="page"`; si un párrafo no tiene página en el mapa, se omite el sufijo (sin ruido "página no disponible"). PyMuPDF queda disponible en el flake para otros usos.
- **Reglas nuevas como `warning`**: para no cambiar el semáforo de las plantillas oficiales existentes, las reglas nuevas entran como `warning` hasta que se validen contra las 5 plantillas y el benchmark del punto 13.
