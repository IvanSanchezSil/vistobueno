# Plan de correcciones — PR #73 (auditoría de motor, semana 10)

**Fecha:** 2026-11-09
**Responsable:** IvanSanchezSil
**Rama:** `semana10-auditoria-motor` (PR #73)
**Base de la revisión:** `retblast/vistobueno@b48d8b2`, head revisado `72e7e38`
**Revisión atendida:** comentario de `retblast` del 2026-11-04

## Principio

Documentar y planificar primero. Sin tocar código hasta tener claro el
enfoque. Commits atómicos por hallazgo, mensajes en español, **sin
`Co-Authored-By`**. Tests unitarios suficientes (no de integración de API).

## Estado de la revisión

| ID | Estado en la revisión | Acción en este plan |
|----|-----------------------|---------------------|
| AUD-01 | **Bloqueante** | Corregir con la estructura real del índice (tabuladores/página pegada) + test |
| AUD-03 | Importante | Adoptar `validator/detalle.py` de `master` (PR #78), que ya implementa la opción 1 |
| AUD-15 | Importante | Adoptar el escape de `master` (`& < > |`, sin escapar el prompt) + sus tests |
| AUD-02 | Parcial | Documentar/registrar `hasta_final` y añadir conteo de hallados |
| AUD-04 | Parcial | Añadir fecha a las notas `EVALUADO` |
| AUD-07 | Parcial/bloqueante | Propagar la señal n/a: `aplicable=False`, `found="no aplica a este documento"` |
| AUD-20 | Parcial | Fixtures con estructura real (tabuladores) + regresión |
| Cierre | Parcial | Handover §11, `AGENTS.md`, `docs/CONTRATO_API.md`, conteos y `_mutations.py` |

## Diagnóstico

### AUD-01 — índice con página pegada

`_norm_indice` exige whitespace antes de la página (`\s+[IVXLC]{1,5}$` /
`\s+\d+$`). En la tesis real el texto extraído queda pegado
(`1.2.1.General17`, `Dedicatoriaii`) porque `text_of()` solo concatena
`w:t` e ignora `w:tab`, así que el recorte no aplica y 21 entradas no
encuentran su sección. `master` falla 2 porque el título del cuerpo
`General` se normalizaba con el heurístico de página romana y perdía la
`l` (`GENERA`).

**Enfoque (el que verificó retblast):**
1. Mantener `_norm_titulo_cuerpo` (sin recorte romano) para los títulos del
   cuerpo.
2. Preservar `w:tab` como espacio al extraer las entradas del índice, y
   restaurar el recorte de página previo en `_norm_indice` (tolera página
   pegada como respaldo).
3. Test con la estructura real: `1.2.1.<tab>General<tab>17` y una entrada
   de una sola palabra `Resumen<tab>x`.

### AUD-03 — módulo único de detalle

`master` ya trae `validator/detalle.py` (PR #78) con culpables primero,
página del nodo infractor, tolerancia y unidades, y lo usan los dos
motores. La rama duplica el formato en `checks.py`/`analizadores.py`.
Al fusionar `master` se adopta su versión; se conserva de la rama lo que
no toca ese formato (AUD-01/AUD-02/AUD-07).

### AUD-15 — escape correcto

`master` ya escapa `& < > |` con `_escapar()` y **no** escapa el prompt de
IA (va en bloque de código), con tests de tabla y `<script>`. La rama usó
`html.escape`, que no escapa `|` y sí escapa el prompt. Al fusionar se
adopta `master` y se descarta el enfoque de la rama.

### AUD-07 — n/a real

`AnalizadorXML` devuelve `(True, "no aplica (sin nodos)")` cuando
`n_a_si_sin_nodos` y no hay nodos, pero `ReglaCompilada.ejecutar` ignora
ese detalle y publica `passed=True`, `found="cumple"`, `aplicable=True`.
El contrato exige `aplicable=False` y `found="no aplica a este documento"`.

**Enfoque:** bandera `no_aplica` en `Analizador`, activada en los caminos
`n_a_si_sin_nodos` y `n_a_si_ausente`; `ejecutar` devuelve
`self.no_aplicable()` si no hay fallos y algún analizador la activó.

### AUD-02 — `hasta_final` y conteo

`hasta_final` funciona en `seccion()`, pero no está documentado en
`docs/DSL.md` ni validado por `validator/dsl_check.py`. El `found` de
`lista_obligatoria` no dice cuántos ítems se hallaron.

**Enfoque:** documentar en `DSL.md`, registrar/validar la sub-configuración
`seccion` en `dsl_check.py` (claves conocidas, `inicio` obligatorio,
`hasta_final` booleano) y añadir `encontrados=N/M` al detalle de fallo.

### AUD-04 — fecha en `EVALUADO`

Las notas de `caratula_titulo_trabajo_tamano` y
`caratula_optar_grado_tamano` tienen decisión pero no fecha. Añadir
`EVALUADO (YYYY-MM-DD):`, como `sangria_parrafo`.

### AUD-20 — fixtures reales

`configuracion_base()` mantiene estructura plana y el índice sintético usa
espacios. Añadir un fixture con tabuladores reales (`w:tab`) y una entrada
de una sola palabra con página romana pegada.

### Cierre documental

- Handover §11: marcar AUD-01/02/03/04/15/20 cerrados con el PR #73 y las
  decisiones de dominio AUD-05/06/07.
- `AGENTS.md`: actualizar el aviso (no borrarlo si quedan otros hallazgos).
- `docs/CONTRATO_API.md`: corregir el ejemplo `@w:val=['26']` al formato
  real de `detalle.py`.
- Body del PR y bitácora: conteos reales de la suite y aclarar el estado de
  `tests/_mutations.py`.

## Orden de ejecución

1. Fusionar `origin/master` y resolver conflictos (adoptar `detalle.py`,
   `checks.py`, `exportador.py` y tests de `master`; reincorporar
   AUD-01/AUD-02/AUD-07).
2. AUD-01 + tests de tabuladores.
3. AUD-07 + tests n/a.
4. AUD-02 + docs/linter + conteo.
5. AUD-04 fechas.
6. AUD-20 fixture real + regresión.
7. Cierre documental (handover, AGENTS, CONTRATO_API, bitácora).
8. Verificación final y push al fork.

## Verificación

```bash
PYTHONPATH=/tmp/opencode/pylibs:.:tests python3 -m pytest tests/ -q
/tmp/opencode/pylibs/bin/ruff check validator/ scripts/ tests/
/tmp/opencode/pylibs/bin/ruff format --check validator/ scripts/ tests/
/tmp/opencode/pylibs/bin/mypy validator/ scripts/
```

Además: linter DSL sobre `reglas_unt.yaml`, `reglas_unt_pendientes.yaml` y
`reglas_ficha.yaml`.

## Estado final (2026-11-10)

| Paso | Estado | Evidencia |
|------|--------|-----------|
| Merge con `origin/master` (`20e0fe5`) | Hecho | merge `85fc141` |
| AUD-01 + tests de tabuladores | Hecho | `624db11` |
| AUD-07 + tests n/a | Hecho | `624db11` |
| AUD-02 + docs/linter + conteo | Hecho | `624db11` |
| AUD-04 fechas | Hecho | `ed630b3` |
| AUD-20 fixture real + regresión | Hecho | `624db11` |
| Cierre documental | Hecho | commit de documentación de esta revisión |
| Verificación final | Hecho | 757 passed, 4 skipped, 6 xfailed; ruff/mypy OK |

La suite se ejecutó con `PYTHONPATH=/tmp/opencode/pylibs:.:tests`. El linter
DSL quedó cubierto por `test_yaml_de_produccion_pasa_el_linter` sobre los tres
rulesets. `nix flake check` no se ejecutó en este entorno (no hay `nix`); queda
a cargo del CI.

## Notas

- Sin `Co-Authored-By`.
- No tocar `~/proyectos/vistobueno_src`; se trabaja en `/tmp/opencode/vb`.
- `origin` (retblast) es de solo lectura; el push va a `fork`.
