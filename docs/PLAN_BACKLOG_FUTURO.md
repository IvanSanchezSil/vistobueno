# Plan de backlog futuro del Motor

> **Estado**: backlog de trabajo — parcialmente ejecutado.
> **Fecha de creación**: 2026-09-15.
> **Alcance**: motor de validación DSL, extractor y API. El módulo de IA queda fuera hasta que el integrante lo indique.
>
> **Ejecutado 2026-09-15/16 (Fase 1 parcial)**:
> - **15 — Calidad de ingeniería** ✅: *ruff + mypy + coverage + pre-commit* agregados a `flake.nix`; config en `pyproject.toml`; `.pre-commit-config.yaml`; CI `.github/workflows/ci.yml` (Nix); `nix flake check` verde. Detalle: [`docs/diseno/10_calidad_y_exportacion.md`](diseno/10_calidad_y_exportacion.md).
> - **16 — Exportación de reporte** ✅ (solo CLI): `validator/exportador.py` (Markdown + PDF vía WeasyPrint) + `--formato/--salida` en CLI. **Pendiente para el compañero de API/frontend**: exponer `formato` en `POST /validar` (afecta `CONTRATO_API.md` v1.2.0 y `openapi_spec.json`). Detalle: [`docs/diseno/10_calidad_y_exportacion.md`](diseno/10_calidad_y_exportacion.md).
> - **1 — Paginación real** ✅ (parcial, 2026-09-21, F2 ítem 1): mapa párrafo→página en `extractor._paginacion_para()` (`w:lastRenderedPageBreak` + `w:br w:type="page"`), `ExtractedDocx.pagina_de()`, sección DSL `paginacion` (`AnalizadorPaginacion`, `paginas_distintas`) y regla `indice_paginas_separadas` (warning). **Pendiente**: enriquecer `location` a `"página 14 (párr. 124-125)"` vía render DOCX→PDF (ver "Decisiones pendientes").

---

## Bloque A — Territorio no validado hoy (extractor/analizadores)

Nuevas reglas para zonas del DOCX que hoy el motor no toca.

| # | Línea de trabajo | Dónde vive |
|---|---|---|
| 1 | **Paginación real + ubicación por página** (parcial ✅): correlacionar párrafos con página (DOCX→render→PyMuPDF) → `location` pasa de `"párr. 124"` a `"página 14 (párr. 124-125)"`. Hecho: mapa párrafo→página (`w:lastRenderedPageBreak`/`w:br page`), `AnalizadorPaginacion`, `indice_paginas_separadas`. Pendiente: el enriquecimiento de `location`. También pendientes: reglas de carátula sin enumerar. | extractor + reglas nuevas |
| 2 | **Encabezados y pies de página** (`w:hdr`/`w:ftr`): número de página, logo repetido, formato del encabezado. | extractor + analizador nuevo |
| 3 | **Notas al pie** (`w:footnote`): presencia, consistencia de numeración. | extractor + analizador nuevo |
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
| 11 | **TOC bien formado**: el `indice_subdivisiones` ya existe (`reglas_unt.yaml:889`); el nuevo analizador valida que el índice **apunte** a secciones reales del documento. | analizador nuevo |
| 12 | **Numeración jerárquica** (`1 → 1.1 → 1.2 → 2`, sin saltos) — autómata contador, evidencia LFA directa. | analizador nuevo |

---

## Bloque E — Operación y calidad

Mejoras que no tocan reglas pero sí el ecosistema del motor.

| # | Línea de trabajo | Dónde vive |
|---|---|---|
| 13 | **Benchmark real**: repositorio de tesis anonimizadas (más allá de las 5 plantillas) + métricas (reglas que pasan en la práctica, precisión). | carpeta nueva + tests |
| 14 | **Rendimiento**: perfilado con tesis de 150+ páginas, cache a nivel de regla (no solo XPath). | `engine.py` / benchmark |
| 15 | **Calidad de ingeniería**: mypy, lint, coverage, pre-commit, CI (hoy no hay). | config nueva + GitHub Actions |
| 16 | **Exportación de reporte** a Markdown/PDF además de JSON. | `engine.py` / módulo nuevo |

---

## Orden sugerido (por dependencias, no por semana)

- **Fase 1** (independiente, bajo riesgo, toca alrededor del motor): `15 → 16 → 13 → 14`.
- **Fase 2** (mismo territorio, extractor): `1 → 2 → 3 → 4 → 5`.
- **Fase 3** (sobre el DSL, usa F4/F5): `6/7 (usa traza F4) → 9/10 → 11/12`.
- **Fase 4** (producto/API): `8 (último, necesita petición/estado)`.

---

## Decisiones pendientes

- **Render DOCX→PDF**: PyMuPDF ya está en `flake.nix`, pero obtener el número de página real requiere renderizar el DOCX a PDF. Opciones: LibreOffice headless (dependencia nueva en Nix) u otro método de estimación de página.
- **Reglas nuevas como `warning`**: para no cambiar el semáforo de las plantillas oficiales existentes, las reglas nuevas deberían entrar como `warning` hasta que se validen contra las 5 plantillas y el benchmark del punto 13.
