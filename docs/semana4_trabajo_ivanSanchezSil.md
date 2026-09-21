# Semana 4 — Trabajo realizado

**Integrante**: IvanSanchezSil
**Rol**: Integrante 3 — Motor de reglas / Procesamiento
**Semana**: 4 de 14 (14/09/2026 – 18/09/2026)
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)
**Rama de trabajo**: `semana4` (PR #22 hacia master de retblast)

---

## Objetivos de la semana

1. **Documentación de diseño a posteriori** del motor (10 docs + 38 diagramas) y
   alineación de fechas con la cronología real.
2. **F5** (pendiente del plan DSL): conexión de la API al DSL + traza de autómatas
   en el reporte (Opción A).
3. **Cronología real** del trabajo del integrante (semana 2 = OCR+legacy, semana 3 =
   motor DSL, semana 4 = docs+F5) y renombrado de los PRs del integrante.
4. **Tarea 15** del backlog: calidad de ingeniería del motor
   (ruff, mypy, coverage, pre-commit, CI con Nix).
5. **Tarea 16** del backlog: exportación del reporte a **Markdown y PDF** (solo CLI;
   el formato en API queda delegado al compañero de API/frontend).

---

## Actividades realizadas

### 15/09/2026 — Docs de diseño, F5 y cronología

#### Diseño a posteriori (commit `9f65964`)

Se creó el paquete `docs/diseno/00…09` reconstruyendo el diseño del motor que ya
estaba implementado (F1–F6):

| Doc | Contenido |
|-----|-----------|
| 00 | Índice (mapa de documentos + diagrama de fases) |
| 01 | Arquitectura del motor (componentes, secuencia) |
| 02 | Extracción del DOCX (OPC + tokenizer) |
| 03 | Autómatas (DFA, PDA, backtracking) — LFA |
| 04 | Gramática del DSL y BNF — Compiladores |
| 05 | Compilador + linter |
| 06 | Migración legacy → DSL + paridad |
| 07 | Arquitectura de tests (factory + propiedades) |
| 08 | OCR de reglamentos |
| 09 | F5: enlace API → DSL (propuesta, luego implementada) |

**38 diagramas Mermaid** en total (GitHub los renderiza nativamente).

#### F5 implementada (commit `97630c4`) — Opción A

- `validator/api.py`: `REGLAS_YAML_PATH` → `reglas_unt.yaml` (la API ahora carga
  el DSL, 41 reglas, incluidas las 9 de F3).
- `validator/compilador.py`: `_detalle_con_traza()` para la regla `found` en la
  ruta de estados del autómata (`ruta_estados` / `ultima_ruta`).
- Docs: `09_f5_enlace_api_propuesta.md` marcado **IMPLEMENTADA**; `NOTA_F5_Y_API_DSL.md`
  con estado actualizado.

#### Cronología real (commit `f539dcc` + `9260870`)

Se creó `docs/cronologia_trabajo.md` mapeando el trabajo real del integrante:

| Semana | Contenido | PRs |
|--------|-----------|-----|
| 2 | OCR + formato legacy YAML | #3 (actual) |
| 3 | Motor DSL: DFA, analizadores, compilador, F6 paridad | #6, #11 (cerrados #2, #7, #9) |
| 4 | Docs de diseño + F5 + backlog/tareas 15–16 | #22 (actual) |

Se **renombraron** los PRs #3, #6, #11 y #22 para reflejar el contenido real y se
reclasificó la bitácora F4 (`semana4_...` → `semana3_3_...`). Con esto, las
**fechas** de `README.md`, `CONTRATO_API.md`, `FLUJO_API.md`, `PLAN_DSL.md` y
`NOTA_F5_Y_API_DSL.md` quedaron alineadas.

### 15/09/2026 — Plan de trabajo futuro

- Se consolidó `docs/PLAN_BACKLOG_FUTURO.md` (bloques A–E, 16 ítems de trabajo
  **nuevo** — el módulo de IA queda fuera hasta que el integrante lo indique).

### 16/09/2026 — Tareas 15 y 16 (Fase 1 del backlog)

#### Tarea 15 — Calidad de ingeniería

Hueco detectado: el repo **no tenía** linters, typechecker, pre-commit ni CI.

Herramientas integradas (todo en Nix):

- **ruff** (lint + format, reglas E/F/I/UP/W/B) sobre `validator/`, `scripts/` y `tests/`.
- **mypy** (moderado) sobre `validator/` y `scripts/`.
- **coverage** solo reporta (sin umbral bloqueante).
- **pre-commit** (hooks: ruff, ruff-format, mypy, EOF, whitespace).
- **CI** `.github/workflows/ci.yml` con `install-nix-action` + `cachix`.

Cambios de configuración:

- `flake.nix`: deps nuevas (`ruff`, `mypy`, `pre-commit`, `pytest-cov`, `coverage`,
  `markdown`, `weasyprint`); el check `default` corre pytest + ruff + mypy.
- `pyproject.toml`: `[tool.ruff]`, `[tool.mypy]`, `addopts --cov`.
- `.gitignore`: `.coverage`, `htmlcov/`, `.mypy_cache/`.

**Refactor inducido** (~30 archivos): se corrigieron **220+ hallazgos de ruff**
(170+ auto-fixables: `List[str]` → `list[str]`, imports ; 11 manuales) y **9 de
mypy**. Detalle completo y justificación en
`docs/diseno/10_calidad_y_exportacion.md`.

#### Tarea 16 — Exportación del reporte a Markdown/PDF

Nuevo módulo `validator/exportador.py`:

- `reporte_a_markdown(reporte) -> str`: semáforo, resumen, tabla, detalle de
  fallidas y bloque de prompts IA.
- `reporte_a_pdf(reporte) -> bytes`: Markdown → HTML (`markdown`) → PDF
  (**WeasyPrint**, elegido por mejor calidad de render).
- CLI: `python -m validator.cli tesis.docx reglas.yaml --formato {json,markdown,pdf}
  --salida ruta`; `--json` se conserva como atajo.
- Utilidad standalone: `python -m validator.exportador reporte.json salida.{md,pdf}`.
- Tests: `tests/test_exportador.py` (6 tests).
- **Delegado al compañero de API/frontend**: exponer `formato` en `POST /validar`
  (afectaría `CONTRATO_API.md` v1.2 — se anotó en el backlog).

---

## Verificaciones

- `pytest tests/` → **148 tests verdes** (142 previos + 6 del exportador).
- `nix flake check` → **verde** (tests + ruff + mypy).
- Coverage: **88%** de `validator/`.
- PDF generado desde plantilla real: 58 KB, firma `%PDF` válida.
- Markdown generado: semáforo + tabla de 41 reglas.

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| 10 docs de diseño (38 diagramas) | `docs/diseno/00…10` | LFA · Compiladores · Es. de Software |
| F5 (API→DSL + traza) | `validator/api.py`, `validator/compilador.py` | Ingeniería de Software I/II |
| Cronología + PRs renombrados | `docs/cronologia_trabajo.md` | Comunicación oral/escrita |
| Backlog futuro (16 ítems) | `docs/PLAN_BACKLOG_FUTURO.md` | Ingeniería de Software I (planificación) |
| Config de calidad | `pyproject.toml`, `flake.nix`, `.pre-commit-config.yaml` | Ingeniería de Software II |
| CI con Nix | `.github/workflows/ci.yml` | Ingeniería de Software II |
| Exportador Markdown/PDF | `validator/exportador.py`, `validator/cli.py` | Ingeniería de Software I |
| Tests de exportador | `tests/test_exportador.py` (6) | Ingeniería de Software II |
| Bitácora | `docs/semana4_trabajo_ivanSanchezSil.md` | — |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Lenguajes Formales y Autómatas** | Traza de estados de DFA/PDA en el reporte (F5); diagramas de estados en `docs/diseno/03` |
| **Compiladores** | Gramática BNF del DSL documentada; linter en carga |
| **Estructura de Datos** | Cache de XPath por `(parte, contexto, xpath)` |
| **Ingeniería de Software II** | F5; tooling de calidad (ruff/mypy/coverage/pre-commit/CI) |
| **Ingeniería de Software I** | Documentación técnica (10 docs, cronología, backlog), exportación a Markdown/PDF |

---

## Dificultades y aprendizajes

- **La base nunca se linteó**: 208 errores iniciales de ruff la primera vez que
  corrió `nix flake check`; la mayoría auto-fixables, 11 requerían decisión
  (StrEnum, `raise from`, nombres ambiguos).
- **Mypy y `Any | None`**: lxml devuelve `Any`; para `sorted()`/conjuntos hubo
  que filtrar con `isinstance` y anotar estructuras como `epsilon_ady`.
- **`_FABRICAS` abstracta**: el dict de fábricas de analizadores necesitó la
  anotación `dict[str, Callable[[dict], Analizador]]` porque `Analizador` es una
  clase abstracta.
- **WeasyPrint vs. alternativas**: se comparó con reportlab y pymupdf.Story; se
  eligió WeasyPrint por CSS real (tablas y acentos correctos).
- **Banner de `nix develop`**: ensucia stdout; por eso las pruebas de CLI usaron
  `--salida` a archivo en vez de tuberías.

---

## Pendiente / Plan semana siguiente

- [x] Docs de diseño (00…09) + F5 + cronología + renombrado de PRs
- [x] `PLAN_BACKLOG_FUTURO.md` (fase 1: tareas 15 y 16 ejecutadas)
- [ ] Tarea 13 (benchmark con tesis reales) — requiere tesis anonimizadas
- [ ] Tarea 14 (rendimiento 150+ páginas) — requiere documentos grandes reales
- [ ] API: `formato` en `POST /validar` — **delegado al compañero de API/frontend**
- [ ] Módulo de IA — se tocará solo cuando el integrante lo indique (no es la
      semana adecuada)