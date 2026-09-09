# Semana 3.2 — Trabajo realizado (F6 del plan DSL)

**Integrante**: IvanSanchezSil
**Rol**: Integrante 3 — Motor de reglas / Procesamiento
**Semana**: 3.2 de 14 (09/09/2026)
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)
**Rama de trabajo**: `semana3.2-f6` (PR desde `fork/semana3.2-f6` hacia master de retblast)

---

## Objetivos del día

1. **F6** del plan `docs/PLAN_DSL.md`: **tests de propiedad** — todo documento
   "bueno" pasa; un documento con una regla violada falla **solo** esa regla.
2. Crear un **factory determinista** de DOCX sintéticos
   (`tests/docx_factory.py`) que sirva de base declarativa para 41 mutaciones
   (una por regla) sin depender de las plantillas ni de otros tests.
3. Mantener la **paridad** con el motor legacy y la suite existente intacta.

---

## Actividades realizadas

### Tarea 1 (F6): `tests/docx_factory.py` — factory determinista

**Fecha**: 09/09/2026

Se centralizó la construcción OPC (portada, cabeceras de estructura, resumen
con palabras, referencias, anexos, footer con campo PAGE, numeración romana,
hipervínculo ORCID y línea de proyecto) en un módulo importable. La
configuración es un diccionario plano (tamaños, negritas, márgenes, conteos,
lista de cabeceras), de modo que cada **mutación** toca **un solo knob**:

- `configuracion_base()`: documento "bueno" que pasa **39/41** reglas.
- `aplicar_mutacion(rule_id, cfg)`: devuelve una copia con el desvío mínimo
  para una regla concreta.
- `compilar_docx(cfg)`: empaqueta el `.docx` temporal.

### Tarea 2 (F6): `tests/test_propiedad.py` — las dos propiedades

**Fecha**: 09/09/2026

- `test_doc_bueno_pasa_39`: el documento base falla **exactamente** los esquemas
  alternativos de estructura (`estructura_tinv_cualitativo` y
  `estructura_tinv_revision_literatura`), que son mutuamente excluyentes con
  el plan cuantitativo; las otras 39 pasan.
- `test_mutacion_afecta_solo_esa_regla` (41 casos `@parametrize`): compara
  punto a punto `(passed, found)` entre el documento base y el mutado;
  exige `diffs == {regla}` (o su conjunto acoplado).

### Tarea 3 (F6): Hallazgos y exclusión documentada

**Fecha**: 09/09/2026

Se diseñó el aislamiento empíricamente y se documentaron las limitaciones:

1. **No existe un DOCX 41/41**: los tres esquemas de estructura no pueden
   cumplirse a la vez (definen el tipo de investigación del documento).
2. Los autómatas de estructura embeben `headings=N` en `found`: el contador
   cambia ante cualquier inserción/renombrado de cabeceras (detalle interno).
   Para las reglas `estructura_tinv_*` se compara solo el observable `passed`.
3. **`REGLAS_ACOPLADAS`**: reglas con mecanismo idéntico (mismo conteo o mismo
   párrafo XPath) cuyo desvío las cambia juntas:
   - `referencias_minimo_cuantitativo`/`referencias_minimo_revision` (mínimo
     20) y `referencias_minimo_cualitativo` (30): todos usan el mismo conteo;
   - `caratula_universidad_negrita_mayusculas`/`caratula_ciudad_pais_negrita`:
     el XPath `[1]` de "trujillo" resuelve a la línea de la universidad.
4. Las reglas que **fallan en la base** (cualitativo, revisión) se "arreglan"
   en su mutación intercalando las cabeceras del esquema alternativo — el
   autómata salta cabeceras que no matchean su transición actual, así que el
   plan cuantitativo sigue pasando. Se valida el aislamiento en ambas
   direcciones (romper una regla y arreglar una regla).

### Tarea 4 (F6): Verificación dentro de `nix develop`

**Fecha**: 09/09/2026

Suite completa: **117 tests passed** (74 previos + 43 de F6) y
`PARIDAD: OK` en las 6 plantillas reales, todo dentro del entorno Nix.

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Factory determinista de DOCX | `tests/docx_factory.py` (41 mutaciones, `REGLAS_ACOPLADAS`, `EXCLUIDAS_BASE`) | Ingeniería de Software II |
| Tests de propiedad | `tests/test_propiedad.py` (43 tests) | Ingeniería de Software II |
| Documentación (cambios, decisiones) | `docs/CAMBIOS_MOTOR_DSL.md` (Paso 12), `docs/PLAN_DSL.md` (F6 ✅, decisión 5) | Ingeniería de Software I |
| Bitácora | `docs/semana3_2_trabajo_ivanSanchezSil.md` | — |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Lenguajes Formales y Autómatas** | Verificación empírica de los autómatas de estructura (greedy, salto de cabeceras no reconocidas) |
| **Estructura de Datos** | Construcción/inspección de paquete OPC (zip + XML) y de la config declarativa del factory |
| **Ingeniería de Software II** | Tests de propiedad, diseño por mutaciones, fixtures deterministas; suite 117 verde |
| **Ingeniería de Software I** | Documentación técnica: `CAMBIOS_MOTOR_DSL.md` Paso 12, `PLAN_DSL.md` |

---

## Dificultades y aprendizajes

- **Desvío mínimo no siempre aísla**: bajar las referencias de 30 a 19 rompe
  las tres reglas de referencias a la vez (mismos conteo y sección); y el
  párrafo "UNIVERSIDAD NACIONAL DE TRUJILLO" contiene "trujillo", entonces la
  regla de ciudad resuelve al párrafo de la universidad. Ambas son
  limitaciones **de las reglas**, no del factory: se documentaron en
  `REGLAS_ACOPLADAS` en vez de forzar una mutación artificial.
- **Remover ≠ Aislar**: quitar una cabecera cambia el contador `headings=N`
  del `found` de los tres autómatas. La solución fue **renombrar** la cabecera
  (rompe solo la regla objetivo) y comparar `passed` para `estructura_tinv_*`.
- **Bugs reales de la iteración**: inserción con el orden `(ancla, nueva)`
  invertido (la "revisión" no cambiaba) se detectó por `diffs=[]` en la sonda
  empírica antes de escribir la aserción final.

---

## Pendiente / Plan semana siguiente

- [x] F6 completa: `docx_factory.py` + `test_propiedad.py` (43 tests),
       suite 117 verde y `PARIDAD: OK` dentro de `nix develop`
- [x] Docs: `CAMBIOS_MOTOR_DSL.md` Paso 12, `PLAN_DSL.md` (F6 ✅)
- [x] Commit atómico y push a `fork/semana3.2-f6` (PR desde `semana3.2-f6`)
- [ ] **F4** (siguiente, según decisión 3): linter del DSL (`dsl_check.py`),
       cache de XPath y traza del autómata (opcional)
- [ ] **F5** (traza en el reporte): coordinar con Integrante 1 por el contrato
       API antes de tocar `resultados[]`