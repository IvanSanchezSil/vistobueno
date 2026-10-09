# Bitácora Semana 7 — ivanSanchezSil

- **Integrante**: Iván Sánchez Silva (Integrante 3 — Motor de reglas)
- **Semana**: 7
- **Fechas**: 2026-10-01 → 2026-10-09
- **Rol**: Motor de reglas / Procesamiento (DSL, extractor, checks)

---

## Objetivos de la semana

1. **Resolver la revisión del PR #45** ("fix(reglas): correcciones de revisión
   en las tres reglas de estructura") sobre la inferencia de tipo documental:
   las firmas se comparaban sobre toda la prosa, no solo sobre títulos, con
   dos salidas peligrosas (falso rojo por prosa inocente, o verde sin
   validación estructural).
2. **Preparar la medición** que pedía el revisor contra documentos reales, no
   solo contra plantillas.
3. **Documentar** la resolución (DSL, diseño, README, conteos, bitácora).

---

## Actividades realizadas

### 2026-10-01 → 2026-10-08 — Lectura y verificación de los insumos

- Leídos y contrastados contra el código los dos documentos de transferencia
  (`INFORME_diagnostico_conversion_pdf.md` y `HANDOVER_MOTOR_TODOS_LOS_ISSUES.md`).
- Verificado que el PR #36 (aplicabilidad por `aplicar_si`) ya estaba
  mergeado y resuelve el "semáforo jamás verde" del informe PDF.
- Verificada la línea base en una plantilla oficial: 3 errores / 10 warnings,
  `reglas_no_aplicables=2`.

### 2026-10-09 — Resolución de la revisión del PR #45

- **Q1 (firmas solo sobre títulos)**: `DeteccionTipo._tipo_inferido` ahora
  recibe los textos de los párrafos con estilo de título (tokenizer), no toda
  la prosa. Medido en la tesis real de Linares: el "1/2" de
  `proyecto_cuantitativo` que la carátula regalaba por prosa desaparece y la
  TINV se sigue detectando (`inferido=tinv_cuantitativo`).
- **Q2 (Anexo 10 en tabla / content-control)**: la declaración ahora recorre
  todos los párrafos del cuerpo (incluye `w:tbl` y `w:sdt`), lee el estado de
  una casilla `w14:checkbox` y, si el Anexo 10 es una tabla, busca la etiqueta
  en la misma fila que la casilla.
- **Salida B (tipo sin estructura cargada)**: se generalizó el mecanismo de
  centinelas del compilador para emitir un **warning** `tipo_documento_sin_estructura`
  cuando el tipo detectado es proyecto/informe/TSP (sus estructuras siguen en
  `reglas_unt_pendientes.yaml`, fuera de producción). Así el semáforo no vende
  un verde que no validó el capítulo de metodología.
- **Solape retirado**: `OPERACIONALIZACIÓN DE LAS VARIABLES` en la firma de
  `informe_cuantitativo` sí aparece como título real en una TINV, pero solo
  aporta 1/2 (el umbral es 2), así que no vira la clasificación. Se documentó
  y no se modificó.

### 2026-10-09 — Evidence y tests

- Medición sobre la tesis real (Linares, DOCX): tabla de puntaje por tipo en
  prosa vs títulos (proyecto 1/2 → 0/2; TINV se mantiene 2/2).
- 13 tests nuevos:
  - `TestInferenciaSoloTitulos` (prosa no cuenta; tesis TINV que menciona
    proyecto en prosa no vira; un proyecto real sí se detecta).
  - `TestDeclaracionEnTablaYSdt` (declaración en tabla con etiqueta en otra
    celda, casilla vacía, content-control `w14` marcado y desmarcado).
  - `TestAvisoSinEstructura` (los 5 tipos sin estructura emiten warning; una
    TINV no lo emite).
- Suite completa: **381 tests pasan** (+13).

---

## Evidencias producidas

- Cambios en `validator/analizadores.py` (inferencia por títulos, declaración
  en tabla/sdt/w14), `validator/compilador.py` (centinelas con severidad por
  estado y warning de tipo sin estructura), `tests/test_tipo_documento.py`,
  `reglas_unt.yaml` (comentarios), `docs/DSL.md`, `docs/diseno/15_tipo_documento_grupos.md`,
  `README.md`, `AGENTS.md`, `docs/diseno/00_indice_diseno.md` y esta bitácora.
- Todo se agrupa en el **PR #45** (rama `semana7-fix-reglas-estructura`).
- Medición con documento real (no versionada; los DOCX/PDF de estudiantes
  quedan fuera del repo, en la raíz local y en `docs/pruebas/`).

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: manejo de la revisión de un PR (respuesta a
  los tres puntos del revisor), ajuste del diseño y validación con tests.
- **Estructura de Datos**: recorridos del árbol XML del DOCX (títulos, tablas,
  content-control) y normalización de texto para el conteo de firmas.
- **Ingeniería de Software I**: documentación precisa del cambio (DSL, diseño
  de decisiones, conteos sincronizados).

---

## Dificultades y aprendizajes

- **`find()` de lxml no baja a los nietos**: el `w14:checked` vive dentro de
  `w:sdtPr`, y la primera versión no lo encontraba (solo los tests de
  content-control lo delataron).
- **La medición no miente**: el "1/2 de proyecto" que la carátula regalaba por
  prosa se descartó como riesgo hasta que la medición sobre una tesis real lo
  confirmó. Con la tesis de Linares quedó claro que una TINV real está a un
  título ruidoso de virar.
- **Scope control**: la revisión pedía tres cosas puntuales; se resolvieron y
  se dejó explícito qué NO se tocó (el solape de informe, las 5 estructuras
  pendientes, los demás issues del handover).

---

## Plan de la semana siguiente

1. Revisar los siguientes issues del handover/INFORME (uno por uno): `_cuerpo_paras`,
   márgenes landscape, XPaths de carátula.
2. Convertir la tesis de Carrión (PDF) para poder validarla y medir la
   detección con un segundo documento real.
3. Incorporar las 5 estructuras pendientes (`reglas_unt_pendientes.yaml`) a
   producción cuando haya plantillas reales de proyecto/informe/TSP.