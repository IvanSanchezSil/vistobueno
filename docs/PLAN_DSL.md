# Plan integral: consolidación del motor DSL — VistoBueno

**Estado**: Pendiente de decisiones (sección 7).
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

### F1 — Migración completa al DSL (A)

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

### F2 — Extender autómatas y gramáticas (B)

- `validator/tokenizer.py`: flujo tipado `TITULO(nivel, texto)`, `PARRAFO`,
  `TABLA`, `IMAGEN`, `SALTO_SECCION`. `automata_secuencia` gana
  `tipo_flujo: titulos | documento` (hoy solo consume headings).
- `PDA` (push/pop) en `validator/automata.py` para estructuras anidadas;
  nueva sección DSL `automata_pila`.
- `GramaticaEstructura` capaz de consumir tokens del tokenizer (no solo
  headings).

### F3 — Mecanizar no_deterministas (C)

Nuevos analizadores:

| Analizador | Uso | Reglas que mecaniza |
|---|---|---|
| `patron_cantidad` | contar matches de una regex en texto; comparar min/máx/rango | `resumen_longitud` (≥159 palabras), `palabras_clave_minimo` (≥3), `sistema_citas` (heurístico parcial) |
| `conteo_nodos` | contador genérico de nodos XPath con min/max (refactor de `imagen`) | `referencias_minimo_*` (≥20/30), `anexos_minimos_*` |
| `hipervinculo_texto` | detecta enlaces (w:hyperlink) que matcheen regex ORCID | `caratula_orcid` |

Cobertura esperada: **32/44 → ~40/44**. Quedan fuera las genuinamente
semánticas (redacción en prosa, verbos en infinitivo, traducción del
abstract, etc.).

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

## 7. Decisiones pendientes de confirmar

1. **Contrato API (E)**: ¿agregar `detalle_traza` a `resultados[]` (cambio
   aditivo, sube `CONTRATO_API.md` a v1.1, requiere coordinar con Integrante 1)
   o embeber la traza en `encontrado` sin tocar la API?
2. **YAML unificado (A)**: ¿reemplazar `unt_format_rules_schema.yaml` por el
   DSL nuevo (`reglas_unt.yaml`) y archivar el legacy, o mantener ambos
   formatos durante una transición?
3. **Evaluación paralela (D)**: ¿incluirla o dejarla como pendiente opcional
   (agrega complejidad a cambio de velocidad en documentos grandes)?
4. **Scope de (C)**: ¿apuntar a las ~8 reglas claramente mecanizables
   (subir a ~40/44) y dejar las semánticas documentadas como
   no-automatizables?

## 8. Notas

- La migración debe preservar la semántica `fullmatch` de los 5 checks
  `texto_regex` legacy (el DSL `patron_texto` fija `comparacion: fullmatch`).
- El DFA mantiene reconocimiento `greedy` (puntero no retrocede) para
  preservar el comportamiento histórico; `backtracking` queda disponible.
- La carátula se satisface con el primer párrafo que contenga "universidad"
  (no usa estilo de encabezado), igual que el motor legacy.