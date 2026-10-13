# Semana 6 — Trabajo realizado

**Integrante**: retblast
**Rol**: Integrante 1 — Backend / API
**Semana**: 6 de 14 (05/10/2026 – 10/10/2026)
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Ensamblar la carpeta de evidencias por semanas exigida por el docente.
2. Cerrar la actividad 9 (análisis de la API de DSpace) con el merge de su PR.
3. Implementar el paso 7 del plan de tipo de documento: exponer en el
   contrato de la API los cambios del motor (`aplicable`, resumen ampliado,
   metadatos de tipo de documento).
4. Revisar e integrar los PRs del equipo de la semana (actividad 1).
5. Validar el motor contra tesis reales y transferir los hallazgos al
   Integrante 3; aplicar la revisión integrada del backend tras la auditoría
   de UX (hallazgos B3–B5).

---

## Actividades realizadas

### Tarea 1: Carpeta de evidencias por semanas (05/10)

El docente pidió organizar las evidencias por semanas universitarias
(`semana X/`). Se reestructuró la carpeta de evidencias y su generador:

- Cada carpeta `semana N` contiene la bitácora de esa semana y los artefactos
  del área Backend/API que cambiaron durante ella, en el estado del último
  commit de la semana (verificado contra el historial de git).
- La regla de verdad se mantiene: solo lo commiteado es evidencia; el
  generador lee refs fijas, nunca el árbol de trabajo.
- Se corrigió la detección de cambios (hash de blob mal parseado) y el
  recorte de imágenes en PDF (DPI inyectado en el PNG para que un diagrama
  alto quepa entero en su propia página).

> Esta tarea vive fuera del repositorio (carpeta personal de evidencias);
> por diseño no genera commits.

---

### Tarea 2: Cierre del análisis de DSpace — PR #40 mergeado (07/10, actividad 9)

El registro técnico de la API de DSpace 8.1 (`docs/DSPACE_API.md`,
commiteado originalmente el 30/09) entró a `master` con el merge del
PR #40 (`e98ea7a`). La actividad 9 queda cerrada sobre `master`; los
puntos **PENDIENTE** del documento (cuenta de depósito, permisos sobre la
colección, metadatos) siguen siendo gestión ante la sede y condicionan la
actividad 10.

---

### Tarea 3: Contrato de la API para tipo de documento (07–09/10)

> Paso 7 de `docs/PLAN_TIPO_DOCUMENTO.md`; implementa la opción A
> recomendada en `docs/HANDOVER_API_TIPO_DOCUMENTO.md`. El motor ya exponía
> `RuleResult.aplicable` y el resumen ampliado (pasos 1–6 y 8, PR #36); la
> API no los reflejaba hasta ahora.

Rama `semana7-api-contract-tipo-documento`, 6 commits (36d7ae4..604279d),
PR #44 abierto y mergeado el 09/10 (10:55, `81590d1`), contrato v1.4.0:

- **`ResultadoReglaAPI.aplicable`** (bool, default `true`): distingue las
  reglas que no aplican al tipo de documento detectado.
- **`ResumenValidacion`**: campos nuevos `total_evaluadas` y
  `reglas_no_aplicables` junto a los existentes.
- **`MetadatosValidacion`**: `reglas_evaluadas` pasa de 48 (nominal) a 46
  (realmente evaluadas para el tipo detectado), se agrega `reglas_totales`
  y los metadatos de tipo (`tipo_documento_declarado`, `_inferido`,
  `_estado`) con el helper `_extraer_metadata_tipo_documento`.
- **`docs/openapi_spec.json`** regenerado para el contrato.
- Tests de contrato y fixtures de notificación actualizados
  (`tests/conftest.py`, `test_api_contract.py`, `test_notificacion.py`).

**Verificación**: suite completa **371/371 en verde** en el tip de la rama
(commits probados en un worktree limpio, sin el árbol de trabajo local).

---

### Tarea 4: Revisión e integración de PRs del equipo (07/10, actividad 1)

Tres PRs del equipo integrados, todos con la suite en verde antes del
merge:

- **PR #36** (`IvanSanchezSil`, semana 6 del motor): las 5 estructuras
  pendientes en archivo aparte (`reglas_unt_pendientes.yaml`), lectura del
  vocabulario del formulario del Anexo 10, y tests de que cada tipo aplica
  solo su estructura (incluye un ajuste al fixture rojo de notificación,
  `281c2d0`).
- **PR #41** (`renzo`): auditoría UX integral del frontend (C17–C29), con
  un comentario de revisión previo al merge.
- **PR #43** (`renzo`): paso de `npm run lint` en la CI del frontend.

Antes de cada merge se sincronizó `master` en la rama correspondiente
(`cdeb958`, `dd76185`, `6febe7d`) para que la integración quede limpia.

---

### Tarea 5: Campaña de validación con tesis reales y handover al motor (07/10)

Se validó el motor contra documentos reales para medir su comportamiento
fuera de las plantillas: dos versiones de una tesis cuantitativa ("tesis
A"), dos de otra tesis ("tesis B"), las 5 plantillas oficiales y el manual
(norma de referencia, no banco de pruebas).

Hallazgos principales:

- El extractor definía mal el "cuerpo" del documento: 6 reglas de formato
  evaluaban contra párrafos vacíos.
- Las reglas de márgenes con `all_eq` fallaban en tesis con secciones
  landscape legítimas (los márgenes rotan con la página).
- Los XPaths de carátula buscaban placeholders de plantilla, no el
  contenido real de una tesis llenada.
- 6 reglas tipo-específicas no tenían `aplicar_si` y corrían para todos
  los tipos de documento.
- Bug de reporte: al fallar `all_eq` se mostraban solo los primeros 3
  valores (los conformes), lo que disfrazaba la causa.
- Fix local de `_norm_indice` (romanos en el índice), verificado con la
  suite en verde.

**Producto**: handover técnico interno al Integrante 3 con 7 issues
priorizados, evidencia regla por regla y criterios de aceptación
(documento de trabajo entre integrantes; no se publica en el repositorio
por contener referencias a documentos de estudiantes).

---

### Tarea 6: Revisión del PR #45 del motor (08–09/10, actividad 1)

Revisión del PR con los fixes del motor sobre los issues del handover,
con comentarios; el Integrante 3 respondió el 09 con las correcciones
(`8f0a900`, "firmas solo a títulos y declaración en tabla"). La
integración final quedó agendada para el lunes 12, ya con la rama
actualizada contra `master`.

---

### Tarea 7: Revisión integrada del backend — contrato v1.5.0 (09/10)

Rama `semana7-backend-revision-integrada`, 10 commits, PR #46 mergeado
(12:38, `737ec4e`), contrato v1.5.0. Aplica los hallazgos de la auditoría
de UX del frontend:

- **B3**: `notificacion.detalle` ahora también se llena en el estado
  `deshabilitado`, con nota de cómo habilitar el servidor. Antes,
  "casilla marcada → 200 OK → nada" era indistinguible de un envío
  silencioso.
- **B4**: `VISTOBUENO_NOTIFICACIONES` acepta `1`/`true`/`yes` (antes solo
  el literal `1` encendía el envío, y `true` lo dejaba apagado sin error
  visible).
- **B5**: best-effort total — la plantilla y las cabeceras del correo se
  arman dentro del manejo de errores; ningún fallo del armado rompe la
  respuesta HTTP. El nombre del archivo se sanitiza en el Subject contra
  inyección de cabeceras.
- **API**: el `422` queda acotado a errores del archivo del usuario; la
  validación y el envío SMTP salen del event loop de FastAPI (validación
  es síncrona y bloqueaba el loop); el estado `deshabilitado` expone el
  detalle de configuración.
- **Pruebas**: nuevo `tests/test_api_concurrencia.py`; el factory actúa
  como DOCX de prueba cuando falta la plantilla en el runner.
- **Infra**: CI con grupo de concurrencia, triggers sin duplicar y
  acciones pineadas; piso de cobertura en `pyproject.toml` (sin `--cov`
  en `addopts`); `test-local` apunta al E2E real.

**Verificación**: suite **377/377 en verde**.

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Carpeta de evidencias por semanas | `semana 2/` … `semana 7/` (Drive institucional) | Ing. de Software I |
| Cierre de la actividad 9 sobre master | `docs/DSPACE_API.md` (merge `e98ea7a`) | Ing. de Software I |
| Contrato v1.4.0: `aplicable` y metadatos de tipo | `validator/api_models.py`, `validator/api.py` (PR #44) | Ing. de Software II, Estructura de Datos |
| Contrato v1.5.0: revisión integrada B3/B4/B5 | `validator/notificacion.py`, `validator/api.py` (PR #46) | Ing. de Software II |
| OpenAPI regenerado | `docs/openapi_spec.json` | Ing. de Software II |
| Tests de contrato actualizados | `tests/test_api_contract.py`, `tests/conftest.py`, `tests/test_notificacion.py` | Ing. de Software II |
| Tests de concurrencia de la API | `tests/test_api_concurrencia.py` | Ing. de Software II |
| Campaña de validación y handover interno | 7 issues con criterios de aceptación (documento de trabajo) | Ing. de Software I |
| Integración de PRs #36, #40, #41, #43, #44, #46 | `04_Reportes/registro_prs.pdf` | Ing. de Software I |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Ing. de Software II** — Diseño y evolución de contratos | Cambio controlado del contrato: aditivo en lo posible, `reglas_evaluadas` corregido con `reglas_totales` para no perder el dato |
| **Ing. de Software II** — Robustez | Best-effort total en el envío, `422` acotado, operación fuera del event loop |
| **Estructura de Datos** — Modelado y serialización | Mapeo `RuleResult.aplicable` → DTO, resumen ampliado, metadatos de tipo |
| **Ing. de Software I** — Gestión de la integración de cambios | Merge de #36/#40/#41/#43/#44/#46 con suite verde previa; revisión del PR #45 con comentarios |
| **Ing. de Software II** — Verificación | 371/371 en el tip de la rama; 377/377 tras la revisión integrada; campaña contra tesis reales |

---

## Pendiente

- [x] Carpeta de evidencias por semanas (reestructuración)
- [x] PR #40 (DSpace) mergeado a master
- [x] Contrato tipo_documento implementado y mergeado (PR #44, v1.4.0)
- [x] Revisión integrada B3/B4/B5 mergeada (PR #46, v1.5.0)
- [x] PRs #36, #41, #43 revisados e integrados
- [x] Campaña de validación con tesis reales y handover interno al motor
- [ ] Integrar el PR #45 (fixes del motor) y verificar los criterios de aceptación
- [ ] Gestión ante la sede: cuenta de depósito y permisos (bloquea actividad 10)
- [ ] Cierre operativo de la actividad 6: credenciales SMTP institucionales

---

## Plan siguiente

- Integrar el PR #45 y correr la batería de aceptación del handover
  (plantillas y tesis reales).
- **Actividad 10 (módulo de depósito en DSpace)**: diseño a partir del
  análisis de la actividad 9, contra un stub local; la validación con la
  instancia real sigue condicionada a la gestión ante la sede.
- **Actividad 7 (regresión, continua)**: mantener la suite en verde tras
  cada cambio significativo.
- Higiene del árbol: retirar documentos locales de estudiantes del
  repositorio (hecho el 13/10).
