# Semana 10 — Bitácora de trabajo

**Integrante**: IvanSanchezSil ( — Motor de reglas / Procesamiento)  
**Fecha**: 2026-10-27 — 2026-11-10  
**Rama**: `semana10-auditoria-motor`  
**Base**: `origin/master` (`20e0fe5`, merge del PR #90)  
**Estado**: Correcciones de la revisión del PR #73 aplicadas  
**Contexto**: Auditoría `AUDIT_COMPORTAMIENTO_VISTOBUENO_2026-10-26.md`

## Objetivo de la semana

Corregir los hallazgos de la auditoría que corresponden a  (Motor/Reglas), documentando y planificando primero, sin tocar código hasta tenerlo claro. Priorizar correctitud del motor (falsos positivos / hallazgos erróneos).

## Hallazgos asignados a 

| ID | Severidad | Archivos | Acción prevista | Estado |
|----|-----|----------|-----------------|--------|
| AUD-01 | Alta | `validator/analizadores.py` (`_norm_indice`) | `_norm_titulo_cuerpo` para el cuerpo y `_norm_indice` híbrido: preservar `w:tab` como espacio al leer el índice y recortar la página aunque venga pegada (`1.2.1.General17`, `Dedicatoriaii`). Falso positivo con "General" y títulos acabados en i/l/v/x/c. | Hecho (PR #73; revisión 2026-11-10) |
| AUD-02 | Alta | `validator/analizadores.py`, `validator/dsl_check.py`, `docs/DSL.md`, `reglas_unt.yaml` | Arreglar `anexos_minimos_*`: `seccion(hasta_final)`, incluir títulos `Anexo N.` en `_texto()`, mostrar **todos** los faltantes y añadir `encontrados=N/M`. Documentar `hasta_final` y validarlo en el linter. | Hecho (PR #73; revisión 2026-11-10) |
| AUD-03 | Media | `validator/analizadores.py`, `validator/checks.py`, `tests/test_auditoria_motor.py` | `encontrado` legible: culpables primero, valores sin repr crudo, página del nodo infractor. Formato replicado en el motor legacy (paridad literal). | Hecho (166553f) |
| AUD-04 | Media | `reglas_unt.yaml` | Notas `EVALUADO (2026-10-27):` con decisión en `caratula_titulo_trabajo_tamano` y `caratula_optar_grado_tamano` (plantilla usa 13pt/12pt). | Hecho (PR #73; revisión 2026-11-10) |
| AUD-05 | Media | `reglas_unt.yaml` / analizadores | Decisión: endurecer selectores frágiles (`/w:r[1]`, `following-sibling::w:p[1]`) o documentar. | Hecho: documentado y diferido (nota EVALUADO en el bloque de carátula) |
| AUD-06 | Baja | `validator/analizadores.py` (`_sigpalabra`) | Decisión: revisar umbral `>= 4` auto-pasa entradas cortas. | Hecho: umbral mantenido y documentado en el docstring + test |
| AUD-07 | Baja | `reglas_unt.yaml`, `validator/compilador.py` | Acotar `caratula_optar_grado_tamano` a "bachiller" y propagar el n/a real: `aplicable=False`, `found="no aplica a este documento"`. | Hecho (PR #73; revisión 2026-11-10) |
| AUD-20 | Media | `tests/_docx_builder.py`, `tests/docx_factory.py`, `tests/test_auditoria_motor.py` | Fixtures con estructura real (anexos Título1 "Anexo N.", índice con `w:tab` y página pegada) y tests de regresión para AUD-01/AUD-02. | Hecho (PR #73; revisión 2026-11-10) |
| AUD-15 | Media | `validator/exportador.py` | Escape de `&`, `<`, `>` y `|` en `message`/`found`/`expected`; el prompt de IA **no** se escapa (va en bloque de código). | Hecho (integrado desde `master`, PR #78) |

**Coordinar:** AUD-21 (paridad) con AUD-03.

## Plan de trabajo

Orden propuesto:

1. **Documentación y planificación** (hecho) — crear bitácora semana 10 + plan detallado.
2. **AUD-01** — Separar normalización de títulos del cuerpo e ítems del índice. (Hecho)
3. **AUD-02** — `seccion(hasta_final)`, incluir TITULO en búsqueda y quitar el truncado. (Hecho)
4. **AUD-20** — Blindar AUD-01/AUD-02 con fixtures de estructura real y tests de regresión. (Hecho)
5. **AUD-03** — Culpables primero, valores legibles y página del nodo infractor; paridad legacy↔DSL verificada. (Hecho)
6. **AUD-04** — Notas `EVALUADO:` en los tamaños de carátula, verificadas contra la plantilla oficial. (Hecho)
7. **AUD-05/AUD-06/AUD-07** — Decisiones tomadas: documentar y diferir los selectores frágiles (AUD-05), mantener el umbral `>= 4` documentado (AUD-06) y acotar la regla de "optar" a "bachiller" (AUD-07). (Hecho)
8. **AUD-15** — Escape HTML en `message`/`found`/`expected`/`prompt` en `validator/exportador.py` para prevenir rotura de tablas Markdown y XSS en PDF. (Hecho)

## Criterios de aceptación

- [x] AUD-01 corregido con test que falle antes y pase después
- [x] AUD-02 corregido: detecta anexos con estructura Título1 "Anexos" + "Anexo N.", muestra todos los faltantes
- [x] AUD-20: fixtures de estructura real y tests de regresión para AUD-01/AUD-02
- [x] AUD-03: `encontrado` legible, culpables primero, página correcta
- [x] AUD-04: notas `EVALUADO:` añadidas
- [x] AUD-05: selectores frágiles documentados (endurecimiento diferido)
- [x] AUD-06: umbral `>= 4` mantenido y documentado
- [x] AUD-07: `caratula_optar_grado_tamano` acotada a "bachiller" (n/a en otras titulaciones)
- [x] AUD-15: `message`/`found`/`expected` escapados (`&`, `<`, `>`, `|`); el prompt de IA no se escapa
- [x] `tests/_mutations.py` sin cambios: no se agregaron reglas nuevas (no requiere sincronización)
- [x] `pytest tests/ -q` tras el merge con `master`: **757 passed, 4 skipped, 6 xfailed**
- [x] linter DSL limpio en `reglas_unt.yaml`, `reglas_unt_pendientes.yaml` y `reglas_ficha.yaml`
- [x] `tests/test_paridad_formatos.py` OK
- [x] `ruff check`, `ruff format --check`, `mypy validator/ scripts/` OK
- [ ] `nix flake check`: no ejecutado en este entorno (sin `nix`); se apoya en el CI

## Riesgos

- Cambiar `found` puede romper paridad → revisar `test_paridad_formatos.py` siguiendo el patrón de `7ff5cd3`
- Añadir `hasta_final` a `seccion()` puede afectar otras reglas → opcional, por defecto mantener comportamiento actual
- Incluir `TITULO` en búsqueda de anexos → limitar al contexto de esa regla, no global

## Evidencia

Plan detallado en `docs/PLAN_SEMANA10_AUDITORIA_MOTOR.md`

Fixtures y regresiones: `tests/test_auditoria_motor.py`. Los tests nuevos se
verificaron contra el comportamiento anterior (AUD-01:
`indice_apunta_secciones=False`; AUD-02: `anexos_minimos_cuantitativo=False`;
AUD-03: la página era la del primer nodo, no la del culpable). AUD-04:
tamaños de la plantilla oficial verificados (`Título` sz 26 = 13 pt;
`Para Optar` sz 24 = 12 pt). `docs/ejemplo_respuesta_motor.json` regenerado
con el CLI contra el MANUAL real (solo lectura).

### Revisión del PR #73 (2026-11-04) y cierre (2026-11-10)

La revisión de `retblast` encontró un bloqueante en AUD-01 (21 entradas del
índice real sin sección), duplicación del formato de AUD-03 y un escape
incompleto en AUD-15. Tras fusionar `origin/master` (`20e0fe5`) y aplicar las
correcciones:

- **AUD-01**: `_norm_titulo_cuerpo` se mantiene; `_norm_indice` recorta la
  página aunque venga pegada y `_entradas_indice` preserva `w:tab` como
  espacio. Test con `1.4.1.<tab>GENERAL<tab>9` y `RESUMEN<tab>x`.
- **AUD-03/AUD-15**: se adopta `validator/detalle.py` y el escape de `master`
  (PR #78); se retira la duplicación y `html.escape`.
- **AUD-02**: `hasta_final` documentado en `docs/DSL.md`, validado por el
  linter y con conteo `encontrados=N/M`.
- **AUD-04**: fecha en las notas `EVALUADO`.
- **AUD-07**: la regla acotada a «bachiller» usa el camino n/a existente
  (`aplicable=False`, `found="no aplica a este documento"`).
- **AUD-20**: fixture con tabuladores reales y regresión.
- **Cierre documental**: handover §11, aviso de `AGENTS.md`,
  `docs/CONTRATO_API.md`, este documento y el ejemplo del motor.

Verificación final sobre el merge: **757 passed, 4 skipped, 6 xfailed**;
`ruff check`, `ruff format --check` y `mypy validator/ scripts/` OK; linter
DSL limpio en los tres rulesets. `tests/_mutations.py` no necesitó cambios:
no se agregaron reglas nuevas.
