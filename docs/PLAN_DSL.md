# Plan integral: consolidación del motor DSL — VistoBueno

**Estado**: F1, F2 y F3 **cerradas** (25/11/2025… 2026-09-09). Quedan F4, F5, F6
(ver sección 7 para las decisiones aún pendientes).
**Fecha**: 2026-09-07

## 1. Objetivo

Consolidar el motor DSL (autómatas, analizadores y gramáticas) y extenderlo
con migración completa al DSL, nuevas reglas mecanizadas, mejoras de
ingeniería, traza para el reporte y tests de propiedad. **El contrato de la
API y de `validate_docx` se preserva** (forma: `List[RuleResult]`).

## 2. Contexto medido

- 32 reglas legacy con mecanismo (de 44 totales).
- Checks legacy por tipo: `xml_atributo` 20, `xml_presencia` 13,
  `texto_regex` 5, `secuencia_titulos` 3, `imagen_presencia` 1,
  `texto_en_lista` 1.
- 12 reglas sin mecanismo: `caratula_orcid`, `resumen_longitud`,
  `palabras_clave_minimo`, `sistema_citas`, `referencias_minimo_cuantitativo`,
  `referencias_minimo_cualitativo`, `referencias_minimo_revision`,
  `anexos_minimos_cuantitativo`, `anexos_minimos_cualitativo`,
  `proyecto_formato_general`, `proyecto_caratula_texto`,
  `suficiencia_profesional_formato`.
- 19 ítems en la sección `no_deterministas` del YAML.

## 3. Fases

### F1 — Migración completa al DSL (A) ✅ cerrada 2026-09-08

Script `scripts/migrar_legacy_a_dsl.py` con tabla de mapeo legacy → DSL:

| Legacy check | Sección DSL | Nota crítica de migración |
|---|---|---|
| `xml_atributo` | `atributo_xml` | `eq`/`all_eq`/`contains` directo |
| `xml_presencia` | `presencia_xml` | `exists`/`not_exists` |
| `texto_regex` | `patron_texto` | Los 5 usan **fullmatch** — fijar `comparacion: fullmatch` (default es `search`) |
| `texto_en_lista` | `lista_texto` | `ignore_case`, misma lista |
| `imagen_presencia` | `imagen` | `cantidad_minima`/`cantidad_maxima` |
| `secuencia_titulos` | `automata_secuencia` | Generar `estados` desde `valor_esperado`: `"(opcional)"` → `opcional: true`; indentación → `nivel_titulo`; patrón desde título normalizado |

- `tests/test_paridad_formatos.py`: mismo documento → mismo `List[RuleResult]`
  en ambos formatos (rule_id, passed, found).
- Salida: DSL unificado + `engine.py` sin bifurcación + legacy archivado
  (según decisión 2).

### F2 — Extender autómatas y gramáticas (B) ✅ cerrada 2026-09-09

- `validator/tokenizer.py`: flujo tipado `TITULO(nivel, texto)`, `PARRAFO`,
  `TABLA`, `IMAGEN`, `SALTO_SECCION`. `automata_secuencia` gana
  `tipo_flujo: titulos | documento` (hoy solo consume headings).
- `PDA` (push/pop) en `validator/automata.py` para estructuras anidadas;
  nueva sección DSL `automata_pila`.
- `GramaticaEstructura` capaz de consumir tokens del tokenizer (no solo
  headings).

### F3 — Mecanizar no_deterministas (C) ✅ cerrada 2026-09-09

Nuevos analizadores (implementados y con tests):

| Analizador | Uso | Reglas que mecaniza |
|---|---|---|
| `patron_cantidad` | contar palabras / matches regex / entradas (`;`/`,`); min/máx/rango | `resumen_longitud` (≥159 palabras), `palabras_clave_minimo` (≥3) |
| `conteo_nodos` | contador genérico de nodos XPath o párrafos de una sección (refactor de `imagen`; `cantidades_multiples` opcional) | `referencias_minimo_*` (≥20/30) |
| `lista_obligatoria` | subcadenas obligatorias por sección (ignore case) | `anexos_minimos_*` |
| `hipervinculo_texto` | detecta enlaces (w:hyperlink) que matcheen regex ORCID | `caratula_orcid` |

Más `proyecto_caratula_texto` (patron_texto + atributo_xml, 13pt).

**Decisión 4 (resuelta)**: se mecanizaron las **9 reglas claramente
verificables** (32 → **41/44**), aplicando las 3 de referencias mínimas sin
detectar tipo y con su severidad `warning` original. Quedan documentadas
como no-automatizables: `sistema_citas`, `proyecto_formato_general`,
`suficiencia_profesional_formato` (ver `reglas_unt.yaml`, bloque F3).
Ver `docs/CAMBIOS_MOTOR_DSL.md` Paso 11 y `tests/test_f3_mecanizacion.py` (21 tests).

### F4 — Mejoras de ingeniería (D)

- Cache de consultas XML por `(parte, contexto, xpath)` en `ExtractedDocx`
  — evita re-ejecutar XPath por analizador.
- Traza del autómata (ruta de estados recorridos) en `DFA`/`AutomataSecuencia`.
- Linter del DSL (`validator/dsl_check.py`): al compilar, detectar estados
  inalcanzables, ciclos, regex inválida, `comparacion` sin `esperado` —
  errores en carga, no en runtime.
- Evaluación paralela opcional (según decisión 3).

### F5 — Traza en el reporte (E)

- `RuleResult.detalle_traza` (opcional): "reconoció CARÁTULA→INTRODUCCIÓN,
  falta RESULTADOS".
- **Impacto contrato**: `tests/test_api_contract.py::test_resultados_campos`
  exige `set(keys) == CAMPOS_RESULTADO`. Campo nuevo = cambio **aditivo**
  al contrato → subir `CONTRATO_API.md` a v1.1 + coordinar con Integrante 1
  (AGENTS.md). Alternativa sin tocar la API: codificar la traza dentro de
  `encontrado` (ya existe). (decisión 1).

### F6 — Tests de propiedad (F)

- `tests/docx_factory.py` (extraer el helper de `tests/test_dsl.py`).
- `tests/test_propiedad.py` con generadores deterministas de DOCX sintéticos.
- Propiedades: todo DOCX "bueno" pasa; todo DOCX con una regla violada
  falla **solo** esa regla.

## 4. Dependencias y orden

```
F1 (A) migración ──► F4 (D) ingeniería ──► F5 (E) traza/UX
        │                                   │
        ▼                                   ▼
F2 (B) tokenizer+PDA ──► F3 (C) mecanizar ◄─)  (necesita B)
        ▼
F6 (F) tests de propiedad (sobre todo lo anterior)
```

## 5. Cobertura de archivos prevista

Nuevos:
- `scripts/migrar_legacy_a_dsl.py`
- `validator/tokenizer.py`
- `validator/dsl_check.py`
- `tests/test_paridad_formatos.py`
- `tests/test_propiedad.py`
- `tests/docx_factory.py`
- `reglas_unt.yaml`
- `docs/PLAN_DSL.md`

Modificados:
- `validator/automata.py` (PDA, traza)
- `validator/compilador.py` (nuevos tipos, linter)
- `validator/analizadores.py` (patron_cantidad, conteo_nodos, hipervinculo)
- `validator/models.py` (detalle_traza, según decisión 1)
- `validator/api_models.py` (según decisión 1)
- `validator/engine.py` (sin bifurcación)
- `docs/CONTRATO_API.md` (según decisión 1)
- `tests/test_api_contract.py` (según decisión 1)

## 6. Contrato preservado

- `validate_docx(path, rules) -> List[RuleResult]` — sin cambio.
- `build_report(results) -> {semaforo, resumen, resultados}` — sin cambio.
- `RuleResult.to_dict()` — campos actuales sin cambio.
- CLI `python -m validator.cli` — sin cambio.
- API `ValidarResponse` — solo cambio **aditivo opcional** en `resultados[]`
  (decisión 1).

## 7. Decisiones de confirmación (estado)

1. **Contrato API (E)**: ¿agregar `detalle_traza` a `resultados[]` (cambio
   aditivo, sube `CONTRATO_API.md` a v1.1, requiere coordinar con Integrante 1)
   o embeber la traza en `encontrado` sin tocar la API? — pendiente (F5).
2. **YAML unificado (A)**: ✅ **tomada (transición)**. Se mantienen ambos
   formatos durante la transición: `unt_format_rules_schema.yaml` (legacy,
   sin cambios) y `reglas_unt.yaml` (DSL, 41 reglas). El motor auto-detecta
   por la clave `rules`/`reglas`.
3. **Evaluación paralela (D)**: ¿incluirla o dejarla como pendiente opcional
   (agrega complejidad a cambio de velocidad en documentos grandes)? —
   pendiente (F4, opcional).
4. **Scope de (C)**: ✅ **tomada**. Se mecanizaron **9 reglas**
   (`resumen_longitud`, `palabras_clave_minimo`, 3 `referencias_minimo_*`,
   2 `anexos_minimos_*`, `caratula_orcid`, `proyecto_caratula_texto`),
   aplicando las referencias mínimas sin detectar tipo (severidad `warning`).
   Las 3 restantes más difíciles quedan documentadas como no-automatizables.

## 8. Notas

- La migración debe preservar la semántica `fullmatch` de los 5 checks
  `texto_regex` legacy (el DSL `patron_texto` fija `comparacion: fullmatch`).
- El DFA mantiene reconocimiento `greedy` (puntero no retrocede) para
  preservar el comportamiento histórico; `backtracking` queda disponible.
- La carátula se satisface con el primer párrafo que contenga "universidad"
  (no usa estilo de encabezado), igual que el motor legacy.