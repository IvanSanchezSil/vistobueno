# Bitácora Semana 8 — ivanSanchezSil

- **Integrante**: Iván Sánchez Silva (Integrante 3 — Motor de reglas)
- **Semana**: 8
- **Fechas**: 2026-10-12 → 2026-10-16
- **Rol**: Motor de reglas / Procesamiento (DSL, extractor, checks)

---

## Objetivos de la semana

1. **Sangría de párrafo tolerante a 1.25 cm**: la regla `sangria_parrafo`
   exigía 720 twips (1.27 cm) con igualdad exacta, pero las plantillas y tesis
   reales usan 708/709 twips (~1.25 cm). Aceptar ese desvío menor sin perder
   la detección de sangrías realmente mal puestas.
2. **Autores de carátula "altas y bajas"**: la regla
   `caratula_autores_mayusculas_sin_negrita` exigía TODO en mayúsculas, cuando
   las tesis reales aprobadas (y el placeholder de la plantilla) escriben el
   nombre en mayúsculas y minúsculas. Validar "altas y bajas" sin descuidar la
   negrita.
3. Mantener la **paridad legacy↔DSL** literal (ambos motores al mismo cambio) y
   la suite completa en verde.

---

## Actividades realizadas

### 2026-10-12 — Tolerancia numérica en las comparaciones de atributo

- **Diagnóstico (sangría)**: la regla es `all_eq` sobre `@w:firstLine` con
  `esperado: '720'`. En la tesis real de Linares los párrafos de cuerpo usan
  708 twips (~1.25 cm) y, con igualdad exacta, TODOS fallaban —
  `@w:firstLine=['708','708','708'] ...; incumplen=[#1=708,#2=708,#3=708]`—,
  escondiendo los párrafos realmente mal (567 twips ≈ 1.0 cm). El equipo ya
  tenía documentado (`EVALUADO:`) que las 5 plantillas oficiales usan
  708 (cuerpo) / 709 (portada), no 720.
- **Decisión (en conjunto con el usuario)**: tolerar 1.25 cm. Se implementó un
  mecanismo general y opt-in: campo **`tolerancia`** (twips) en la sección
  `atributo_xml` (DSL) y en el check `xml_atributo` (legacy). El valor cumple
  si `|valor - esperado| <= tolerancia`; si el valor o el esperado no son
  numéricos, se mantiene la igualdad exacta. `tolerancia: 12` cubre 708/709
  frente a 720.
- **Implementación**:
  - `validator/checks.py`: rama `xml_atributo` con el helper `_acepta()`
    aplicado a `eq`/`all_eq` y al filtrado de `incumplen`.
  - `validator/analizadores.py`: misma lógica en `AnalizadorXML`, con el mismo
    formato de `found` para que la paridad siga comparando literal.
  - `reglas_unt.yaml`: `tolerancia: 12` en `sangria_parrafo` + comentario
    `EVALUADO:` del desvío plantilla vs manual.
  - `unt_format_rules_schema.yaml`: `tolerancia: 12` en el check y nota
    actualizada.
  - `docs/DSL.md`: documentado `tolerancia` en `atributo_xml`.

### 2026-10-12 — Autores de carátula en "altas y bajas"

- **Diagnóstico**: la regla tiene dos comprobaciones: run del autor **sin
  negrita** (`not_exists`) y patrón de texto **todo mayúsculas**
  (`^[A-ZÁÉÍÓÚÑ0-9 .,-]+$`). En Linares el nombre completo es
  "Br. Linares Azañero, Angie Lizbeth" (altas y bajas) y marcaba
  `textos=4 incumplen=3`; los runs del nombre incluyen minúsculas y fallaban.
- **Decisión (en conjunto con el usuario)**: validar **altas y bajas**
  (mayúsculas y minúsculas), sin negrita. Es lo que usan las tesis reales
  aprobadas y el placeholder de la plantilla. Se documentó como desvío
  `EVALUADO:` frente a la cita del manual ("letras mayúsculas", párr. 179).
- **Implementación**:
  - Patrón en ambos YAML:
    `^((.*[a-záéíóúñ].*)|[^A-ZÁÉÍÓÚÑa-záéíóúñ]*)$` con `comparacion: fullmatch`
    y `coincidencia: todos`. Rechaza los fragmentos con letras que no tengan
    ninguna minúscula (todo mayúsculas) y **no penaliza** los `w:t` sin letras
    (una coma o un espacio que Word parte en un run propio), que era el falso
    positivo que dejaba `incumplen=1` en el nombre real.
  - `descripcion` y `valor_esperado` actualizados a "altas y bajas, sin
    negrita" en `reglas_unt.yaml` y `unt_format_rules_schema.yaml`; se conserva
    el `rule_id` (identificador de máquina).
  - La comprobación de negrita (`not_exists`) queda intacta.

### 2026-10-12 — Tests y verificación

- `tests/_docx_builder.py`: el autor del doc bueno pasa a mixta
  ("Ana María Pérez García"), acorde a la regla; la mutación de la regla solo
  conmuta la negrita, así que sigue siendo efectiva.
- `tests/test_paridad_formatos.py`: el autor del doc conforme pasa a mixta
  para seguir cumpliendo la regla.
- `tests/test_tipo_documento.py`: la plantilla oficial deja de marcar autores;
  queda **1 error real** (palabras clave) en vez de 2.
- **Verificación**: suite completa **397 tests pasan**; `ruff check`,
  `ruff format --check` y `mypy` limpios; paridad legacy↔DSL verde. En la tesis
  real de Linares: `sangria_parrafo` solo marca los 3 párrafos de 567 twips
  (`incumplen=[#183=567, #196=567, #198=567]`) y `caratula_autores_...` pasa
  (`cumple`).

---

## Evidencias producidas

- Motor: `validator/checks.py` y `validator/analizadores.py` (campo
  `tolerancia` en las comparaciones de atributo, aplicado en ambos motores).
- Reglas: `reglas_unt.yaml` y `unt_format_rules_schema.yaml`
  (`tolerancia: 12` en `sangria_parrafo`; patrón "altas y bajas" en
  `caratula_autores_mayusculas_sin_negrita`; notas `EVALUADO:`).
- Tests: `tests/_docx_builder.py`, `tests/test_paridad_formatos.py`,
  `tests/test_tipo_documento.py`.
- Documentación: `docs/DSL.md` (campo `tolerancia`) y esta bitácora.
- Medición con documento real (no versionada; los DOCX/PDF de estudiantes
  quedan fuera del repo).

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: mecanismo reutilizable (tolerancia) en lugar
  de un parche puntual, con tests de paridad entre dos motores.
- **Estructura de Datos**: recorrido de nodos XML y comparación numérica de
  atributos (`firstLine` en twips) con margen de tolerancia.
- **Ingeniería de Software I**: documentación del desvío manual vs práctica
  real (`EVALUADO:`) y sincronización de la documentación del DSL.

---

## Dificultades y aprendizajes

- **La puntuación también es un run**: exigir "alguna minúscula" por `w:t`
  penalizaba la coma que Word aísla en su propio run. El patrón se ajustó para
  aceptar los `w:t` sin letras y seguir rechazando los fragmentos todo
  mayúsculas.
- **Tolerar sin aflojar**: `tolerancia: 12` deja pasar 708/709 (1.25 cm) pero
  sigue marcando 567 (1.0 cm), así que no se pierde la detección real.
- **Paridad literal**: cualquier cambio en `found` obliga a tocar los dos
  motores con el mismo formato; el test de paridad sobre documentos sintéticos
  y la medición sobre la tesis real lo confirman.

---

## Plan de la semana siguiente

1. Revisar con el usuario cualquier otro desvío menor plantilla vs manual que
   aparezca con nuevos documentos reales.
2. Validar el comportamiento con un segundo documento real cuando esté
   disponible.
