# Semana 3 — Trabajo realizado

**Integrante**: IvanSanchezSil  
**Rol**: Integrante 3 — Motor de reglas / Procesamiento  
**Semana**: 3 de 14 (07/09/2026 – 11/09/2026)  
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Diseñar y construir un DSL de reglas de validación (fase F1 del plan en `docs/PLAN_DSL.md`): migrar las 32 reglas mecanizadas de `unt_format_rules_schema.yaml` a un formato declarativo.
2. Garantizar **paridad exacta** de comportamiento entre el motor legacy y el DSL (misma `rule_id`, `passed` y `found`), sin romper el contrato API de Integrante 1 ni el frontend.

---

## Actividades realizadas

### Tarea 1: Analizadores declarativos del DSL

**Fecha**: 07/09/2026  
**Acción**: Se crearon los analizadores del DSL en `validator/analizadores.py` (analizador XML por atributo, XML por presencia, regex sobre texto, lista de texto, presencia de imágenes). Se agregó el DFA para secuencias de títulos (`validator/automata.py`) y la gramática BNF (`validator/gramatica.py`).

**Prueba**: 16 tests de DSL con DOCX sintéticos (`tests/test_dsl.py`).

---

### Tarea 2: Compilador DSL → analizadores

**Fecha**: 07-08/09/2026  
**Acción**: Se creó `validator/compilador.py` con `CompilerDSL.compilar()`, que interpreta el YAML DSL y devuelve los analizadores a ejecutar sobre el XML extraído, manteniendo intacto el motor para el YAML legacy (`engine.validate_docx` decide por detección de `reglas`).

**Soporte extra (aprobado en revisión)**: secciones con **listas** de configuraciones (misma regla con varios checks del mismo tipo), para las reglas `papel_tamano`, `interlineado`, `numeracion_posicion` e `indice_subdivisiones`.

---

### Tarea 3: Paridad de comportamiento con el motor legacy

**Fecha**: 08/09/2026  
**Acción**: Se alinearon los detalles de salida y la semántica de evaluación con el motor legacy (`validator/checks.py`):

- Matcher de secuencias idéntico al legacy (startswith + prefijo `[:25]` + token significativo), inyectado al DFA vía hook (`automata.py`).
- La carátula solo se exige como ítem de la secuencia cuando no se detecta portada (`cover_ok`).
- Reporte de `faltantes` idéntico al legacy (escaneo en orden, ítems originales del `valor_esperado`, tope 6), en lugar del conjunto de transiciones alcanzables del DFA.
- Detalles de imagen y regex sin tildes y sin `strip()` extra, igual que legacy.
- `compilar()` itera las secciones en el orden en que aparecen en la regla (corrige el orden de detalles de `numeracion_posicion`).

---

### Tarea 4: Migración legacy → DSL y reglas_unt.yaml

**Fecha**: 08/09/2026  
**Acción**: Se creó `scripts/migrar_legacy_a_dsl.py`, que convierte los checks de cada una de las 32 reglas mecanizadas al formato DSL. Salida: `reglas_unt.yaml` (32 reglas, 43 analizadores: 33 XML atributo/presencia, 5 regex, 1 lista, 1 imagen, 3 DFA de secuencia). Las 12 reglas sin mecanismo se omiten (no ejecutan nada hoy).

> La API NO usa `reglas_unt.yaml` todavía: `validator/api.py` sigue cargando `unt_format_rules_schema.yaml` (contrato intacto, sin coordinación requerida con Integrante 1 para esta fase).

---

### Tarea 5: Tests y verificación de paridad

**Fecha**: 08/09/2026  
**Acción**: Se creó `tests/test_paridad_formatos.py` con DOCX sintéticos (conforme, rebelde, estructura incompleta) que comparan regla por regla (`rule_id`, `passed`, `found`) entre ambos motores. Se creó `scripts/evaluar_paridad_plantillas.py` para correr la misma comparación contra los `.docx` reales de `recursos/`.

**Resultado**: paridad **exacta** en los 3 documentos sintéticos y en los 6 `.docx` reales (5 plantillas + manual). Suite completa: **37 tests pasando**.

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Documento de diseño del DSL | `docs/DSL.md`, `docs/PLAN_DSL.md` | Lenguajes Formales y Autómatas, Compiladores |
| Analizadores declarativos | `validator/analizadores.py` | Lenguajes Formales y Autómatas |
| DFA para secuencia de títulos | `validator/automata.py` | Lenguajes Formales y Autómatas |
| Gramática BNF e intérprete | `validator/gramatica.py` | Compiladores |
| Compilador DSL → analizadores | `validator/compilador.py` | Compiladores |
| Migrador legacy → DSL | `scripts/migrar_legacy_a_dsl.py` | Compiladores |
| Reglas migradas | `reglas_unt.yaml` (32 reglas) | Compiladores |
| Tests de paridad | `tests/test_paridad_formatos.py` | Ingeniería de Software II |
| Evaluación contra plantillas | `scripts/evaluar_paridad_plantillas.py` | Ingeniería de Software II |
| Registro de cambios del motor | `docs/CAMBIOS_MOTOR_DSL.md` | Ingeniería de Software I |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Lenguajes Formales y Autómatas** | DFA para reconocer secuencias de títulos; matcher de transiciones |
| **Compiladores** | Gramática BNF del DSL, analizadores e intérprete/compilador |
| **Ingeniería de Software II** | Tests de paridad, refactor con contrato estable motor/API |
| **Ingeniería de Software I** | Documentación del DSL, plan de fases y cambios del motor |

---

## Pendiente

- [x] Analizadores XML, regex, lista, imagen
- [x] DFA + gramática BNF
- [x] Compilador DSL con soporte de listas en secciones
- [x] Paridad exacta con el motor legacy (sintéticos y plantillas reales)
- [x] `reglas_unt.yaml` generado por migrador
- [x] Suite completa verde (37 tests)
- [x] Commits atómicos y push a `semana3-DSL` (PR #6 creado)

---

## Plan semana siguiente (semana 4)

- Fase F2 del plan DSL: probar el comportamiento de la API **con** `reglas_unt.yaml` (coordinando con Integrante 1 antes de tocar `api.py`) y verificar paridad API = CLI con el DSL.
- Fase F3 (inicio): migrar las 12 reglas sin mecanismo a un placeholder explícito en el DSL o documento de decisión.
- Documentar el resultado de la F1 en `docs/CAMBIOS_MOTOR_DSL.md` (sección F1 completa).