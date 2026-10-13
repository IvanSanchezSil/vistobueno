# Semana 7 — Trabajo realizado

**Integrante**: retblast
**Rol**: Integrante 1 — Backend / API
**Semana**: 7 de 14 (12/10/2026 – 17/10/2026) — **en curso (parcial al 13/10)**
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Integrar el PR #45 (fixes del motor) y verificar los criterios de
   aceptación del handover de la semana 6 con una batería sobre plantillas
   y tesis reales.
2. Iniciar la actividad 10 (módulo de depósito en DSpace) contra un stub
   local.
3. Revisar e integrar los PRs del equipo (actividad 1).

---

## Actividades realizadas

### Tarea 1: Integración del motor y batería de aceptación (12/10, PR #45)

Merge del PR #45 (`IvanSanchezSil`) con los fixes de los 7 issues del
handover de la semana 6:

- **#1** cuerpo semántico del extractor (Introducción → Referencias)
  (`ce5ba30`).
- **#2** márgenes en secciones landscape (`fbe0bc3`), con detección por
  geometría (w > h) además del atributo (`ef88116`).
- **#3/#4** carátula con contexto propio y título posicional (`71b51f0`).
- **#5** `aplicar_si` en las 6 reglas tipo-específicas (`ea7fe3b`).
- **#7** reporte de los valores no conformes al fallar `all_eq`
  (`82fd8f2`).
- Además: unificación de la detección de títulos en `es_heading`
  (`9b6295a`), sangría tolerante a 1.25 cm y autores en altas y bajas
  (`7ff5cd3`), centinelas fuera de los prompts IA (`7546948`).

**Batería de aceptación** (criterios del handover, corrida sobre
`master` tras el merge):

| Documento | Meta del handover | Resultado |
|-----------|-------------------|-----------|
| Suite de tests | 371 en verde | ✅ 401 passed |
| 5 plantillas oficiales | de 3 errores a 2 | ✅ 1 error / 6 warnings |
| Tesis A (1) | 1 error + 4 warnings | ✅ **0 errores / 5 warnings, semáforo verde** |
| Tesis A (original) | 2 errores | ✅ 1 error (estructura, real) + 5 warnings |
| Tesis B (stress) | falsos positivos fuera, errores reales quedan | ✅ 18 errores reales, sin crashes |

Primera tesis real de un estudiante con semáforo verde. La regla
`proyecto_caratula_texto` y las reglas de otros tipos quedaron no
aplicables (6 reglas omitidas por tipo), como preveía el handover.

**Delta abierto para el motor**: `indice_apunta_secciones` falla como
warning en la tesis A (el handover lo esperaba resuelto; posible efecto
del refactor de `es_heading`). Consultado con el Integrante 3.

---

### Tarea 2: Revisión e integración de PRs del frontend (12–13/10, actividad 1)

- **PR #48** (`renzo`, merge 11:11): badge de deshabilitado con nota de
  configuración. Revisión formal con **APPROVED**; el autor aplicó 4
  comentarios de revisión (`0c823be`) antes del merge.
- **PR #50** (`renzo`, merge 08:45 del 13): dropzone con estados y botón
  Validar prominente, prompt único que junta los prompts IA de la
  respuesta, vitest en el job del frontend del CI, y aserción E2E
  `total==47` → `>=47` (los conteos son dinámicos desde el cambio de tipo
  de documento). Sin cambios de contrato.

---

### Tarea 3: Higiene del árbol de trabajo (13/10)

Los documentos de estudiantes (4 DOCX de tesis, sus PDF y un reporte de
validación) y el handover interno se retiraron del árbol del repositorio
hacia el archivo local de evidencias. Ninguno estuvo nunca commiteado;
el movimiento elimina el riesgo de un `git add .` descuidado.

---

### (en progreso) Tarea 4: Módulo de depósito en DSpace — actividad 10

Diseño ya registrado en `docs/DSPACE_API.md` §8. Implementación prevista
contra un stub local del contrato HAL (autenticación JWT + CSRF,
workspaceitems, JSON Patch de metadatos, licencia, depósito), con
validación contra la instancia real pendiente de la gestión ante la sede.

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Batería de aceptación del handover | 401 tests + tabla de resultados | Ing. de Software II |
| Integración de los fixes del motor | PR #45 (7 issues resueltos) | Ing. de Software I |
| Primera tesis real con semáforo verde | corrida del 12/10 | Ing. de Software II |
| PRs #48 y #50 integrados | revisión APPROVED + merge | Ing. de Software I |
| Higiene del árbol | movimiento documentado, sin commits | Ing. de Software I |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Ing. de Software II** — Verificación | Batería de aceptación contra criterios definidos a priori |
| **Ing. de Software I** — Gestión de la integración | Revisión con comentarios (PR #45, #48), merges con suite verde |
| **Ing. de Software I** — Seguridad | Retiro de datos personales del árbol de trabajo |

---

## Pendiente

- [x] PR #45 integrado y verificado con batería
- [x] PRs #48 y #50 integrados
- [x] Higiene del árbol de trabajo
- [ ] Módulo de depósito DSpace (`validator/dspace.py`) + contrato v1.6.0
- [ ] Cierre operativo de la actividad 6: credenciales SMTP (sede)
- [ ] Gestión ante la sede: cuenta de depósito DSpace y excepción de la
      barrera antibot para `/server/api`
- [ ] Cierre de la bitácora al final de la semana

---

## Plan siguiente

- Actividad 8: consolidación de la documentación OpenAPI.
- Validación real del depósito cuando la sede entregue la cuenta de
  servicio y la excepción de la barrera.
- Actividad 11 (S13–S14): E2E de los flujos de notificación y depósito
  integrados.
