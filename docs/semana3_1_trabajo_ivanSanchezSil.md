# Semana 3.1 — Trabajo realizado (F2 + F3 del plan DSL)

**Integrante**: IvanSanchezSil
**Rol**: Integrante 3 — Motor de reglas / Procesamiento
**Semana**: 3.1 de 14 (09/09/2026)
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)
**Rama de trabajo**: `semana3.1` (PR desde `fork/semana3.1` hacia master de retblast)

---

## Objetivos del día

1. **F2** del plan `docs/PLAN_DSL.md`: subir la jerarquía de Chomsky del DSL
   — añadir un **tokenizer** (análisis léxico del DOCX) y un **PDA
   (autómata de pila)** para estructuras anidadas (sección `automata_pila`),
   reutilizando el DFA de la F1.
2. **F3**: **mecanizar las reglas no-deterministas** — convertir 9 de las 12
   reglas "semánticas" en reglas verificables mediante 4 analizadores nuevos
   (`patron_cantidad`, `conteo_nodos`, `lista_obligatoria`,
   `hipervinculo_texto`) y el tokenizer para acotar por sección.
3. Mantener la **paridad exacta** con el motor legacy (32 reglas) y el
   contrato de la API intacto.

---

## Actividades realizadas

### Tarea 1 (F2): Tokenizer del documento

**Fecha**: 09/09/2026

Se creó `validator/tokenizer.py`: convierte `<w:body>` en un flujo tipado de
tokens en orden documental — `TITULO(nivel, texto)`, `PARRAFO`,
`TABLA`, `IMAGEN`, `SALTO_SECCION` — reconociendo headings con la misma
condición que el motor legacy ("eading"/"tulo") para no romper la paridad.
Se refactorizaron `AutomataSecuencia._headings()` y la ruta de títulos de la
gramática BNF para consumir `solo(tokenizar(...), [TITULO])` en lugar de
recorrer el XML dos veces (se eliminó el import `W` del compilador).

### Tarea 2 (F2): Autómata de pila (PDA) y sección `automata_pila`

**Fecha**: 09/09/2026

En `validator/automata.py`: `TransicionPDA` extiende `Transicion` con
`push`/`pop`; `PDA` reutiliza el motor greedy del DFA, acepta solo con
**pila vacía** (estructura cerrada) y rechaza `pop` con tope inesperado.
En `validator/compilador.py`: nueva sección `automata_pila`
(`tipo_flujo`, `inicial`, `aceptacion`, `transiciones` con `push`/`pop`) +
opción `tipo_flujo: titulos | documento` compartida por DFA y gramática.

Regla de ejemplo: `estructura_capitulos_pila` en `reglas_dsl_ejemplo.yaml`.

### Tarea 3 (F3): `seccion()` en el tokenizer

**Fecha**: 09/09/2026

`seccion(tokens, inicio, fin=None)` devuelve los tokens posteriores al primer
`TITULO` que matchea la regex `inicio` (ignore case), hasta el siguiente
título (o el final del flujo). Sin match → `[]` (la regla cae como fallo).
Permite a las reglas F3 validar **solo la sección** (Resumen, Referencias,
Anexos) y no todo el documento.

### Tarea 4 (F3): Analizadores nuevos

**Fecha**: 09/09/2026

En `validator/analizadores.py`, 4 analizadores nuevos + refactor:

| Sección DSL | Analizador | Uso |
|---|---|---|
| `patron_cantidad` | `AnalizadorCantidadPatron` | cuenta palabras, matches regex o entradas (`count_words` / `count_matches` / `count_entries`), con `filtro` por párrafo |
| `conteo_nodos` | `AnalizadorConteoNodos` | cuenta párrafos de una sección o nodos XPath; min/máx y `cantidades_multiples` |
| `lista_obligatoria` | `AnalizadorListaObligatoria` | verifica subcadenas obligatorias (ignore case) por sección |
| `hipervinculo_texto` | `AnalizadorHipervinculo` | cuenta `w:hyperlink` cuyo texto matchea una regex (ORCID) |

`AnalizadorImagen` pasó a ser **subclase** de `AnalizadorConteoNodos` con
etiqueta fija `imagenes` (detalle `imagenes=N minimo=M` del legacy intacto).
Se registraron las 4 secciones en `SECCIONES_ANALIZADOR` y `_FABRICAS` de
`validator/compilador.py`.

### Tarea 5 (F3): Reglas mecanizadas en `reglas_unt.yaml` (32 → 41)

**Fecha**: 09/09/2026

Se agregaron a mano (antes de `_migracion:`, que se anotó) las 9 reglas:
`resumen_longitud`, `palabras_clave_minimo`, `referencias_minimo_cuantitativo`,
`referencias_minimo_cualitativo`, `referencias_minimo_revision`,
`anexos_minimos_cuantitativo`, `anexos_minimos_cualitativo`, `caratula_orcid`,
`proyecto_caratula_texto`. Todas con su severidad original. Las 3 restantes
(`sistema_citas`, `proyecto_formato_general`, `suficiencia_profesional_formato`)
se documentan como **no-automatizables**. Las 3 de referencias mínimas se
aplican sin detectar tipo de investigación (severidad warning, no bloquean).

> Advertencia: `scripts/migrar_legacy_a_dsl.py` regenera solo las 32 legacy;
> re-ejecutarlo **descartaría** esta fase (anotado en `_migracion`).

### Tarea 6 (F3): Tests y paridad

**Fecha**: 09/09/2026

`tests/test_f3_mecanizacion.py` (21 tests): helper `seccion()`, cada
analizador F3 con DOCX sintéticos (Resumen/Referencias/Anexos con conteos
controlados), `cantidades_multiples`, refactor de imagen y smoke de las 41
reglas de `reglas_unt.yaml`. Se ajustó la aserción de paridad
(`set(legacy) <= set(dsl)` + comparación 1:1 de las 32) en
`tests/test_paridad_formatos.py` y `scripts/evaluar_paridad_plantillas.py`.

**Resultado**: suite completa **74 tests verdes** + `PARIDAD: OK` en los 6
`.docx` reales (5 plantillas + manual).

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Tokenizer del documento | `validator/tokenizer.py` | Compiladores (análisis léxico) |
| PDA (Chomsky tipo 2) | `validator/automata.py` (`PDA`, `TransicionPDA`) | Lenguajes Formales y Autómatas |
| Sección DSL `automata_pila` | `validator/compilador.py` | Lenguajes Formales y Autómatas |
| 4 analizadores F3 | `validator/analizadores.py` | Compiladores |
| Reglas mecanizadas (32→41) | `reglas_unt.yaml` | Compiladores |
| Ejemplos de las familias nuevas | `reglas_dsl_ejemplo.yaml` (13 reglas, 12 familias) | Compiladores |
| Tests F2 y F3 | `tests/test_f2_automatas.py`, `tests/test_f3_mecanizacion.py` | Ingeniería de Software II |
| Documentación (DSL, cambios, decisiones) | `docs/DSL.md`, `docs/CAMBIOS_MOTOR_DSL.md` (Paso 11), `docs/PLAN_DSL.md` | Ingeniería de Software I |
| Bitácora | `docs/semana3_1_trabajo_ivanSanchezSil.md` | — |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Lenguajes Formales y Autómatas** | PDA push/pop con pila vacía como aceptación; jerarquía regular → libre de contexto |
| **Compiladores** | Análisis léxico (tokenizer), nuevo analizadores de hoja, compilador del DSL |
| **Estructura de Datos** | Pila del PDA, slices del flujo tipado de tokens |
| **Ingeniería de Software II** | Refactor aditivo sin romper contrato; 21 tests nuevos; paridad re-verificada |
| **Ingeniería de Software I** | Documentación técnica (DSL.md, CAMBIOS_MOTOR_DSL Paso 11, PLAN_DSL actualizado) |

---

## Dificultades y aprendizajes

- **Paridad de detalle**: en los analizadores del motor el `found` solo
  muestra la cuenta en fallos (`found="cumple"` al pasar) — los tests de F3
  se ajustaron a esa semántica del reporte.
- **Off-by-one en conteos**: el párrafo de conteo incluía una palabra extra;
  los builders de prueba ahora garantizan exactamente `n` palabras/entradas.
- **`cantidades_multiples`**: el mínimo según tipo de investigación se
  implementó como "cumple si se alcanza cualquiera de los mínimos", listo
  para cuando se automatice la detección de tipo.
- **Reglas a mano vs migrador**: las reglas F3 viven en `reglas_unt.yaml`
  fuera del alcance del migrador; re-ejecutarlo sin coordinar las descartaría.
- **Entorno**: igual que en F2, la sesión corrió **sin Nix** (`/nix/store`
  ausente); se usó Python 3.14 del sistema con `pytest` como runner local y
  **sin tocar `flake.nix`** (F3 solo necesita `lxml`, `re` y stdlib).

---

## Pendiente / Plan semana siguiente

- [x] F2 completa (tokenizer + PDA + `automata_pila`), tests y parity
- [x] F3: 9 reglas mecanizadas (32 → 41) en `reglas_unt.yaml`
- [x] Suite completa verde (74 tests) y `PARIDAD: OK` en plantillas reales
- [x] Docs: `DSL.md`, `CAMBIOS_MOTOR_DSL.md` Paso 11, `PLAN_DSL.md`,
      `README.md`, `reglas_dsl_ejemplo.yaml`
- [x] Commit atómico y push a `fork/semana3.1` (PR desde `semana3.1`)
- [ ] **F6** (siguiente, según orden aprobado F3 → F6 → F4 → F5): factory de
      DOCX + tests de propiedad ("todo doc bueno pasa; una regla violada
      falla solo esa regla")
- [ ] **F4** opcional: linter del DSL (`dsl_check.py`), cache de XPath, traza