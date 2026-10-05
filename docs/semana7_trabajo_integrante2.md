# Semana 7 — Pruebas de usabilidad + documentación

**Integrante**: Integrante 2 (Frontend / UX)  
**Fecha**: 2026-09-23  
**Rama**: `s7-usabilidad-ihc` (PRs: retblast#31, Rodo00#10)

---

## Objetivos

1. Ejecutar pruebas de usabilidad del flujo de carga y visualización de resultados.
2. Aplicar mejoras IHC a la interfaz.
3. Pruebas finales del flujo completo (frontend ↔ backend).
4. Corregir errores y documentar avances.

---

## Actividades realizadas

### Evaluación IHC

Se evaluaron las interfaces de **carga**, **resultados** y **desplegables** contra principios de usabilidad (visibilidad de estado, prevención de errores, affordance, contraste, redundancia). Hallazgos principales:

- Límite de archivo inconsistente (25 MB UI vs 10 MB backend).
- Falta de feedback durante la validación.
- Errores de API ocultos detrás del reporte mock.
- Click en dropzone no abría el selector.
- Badge de severidad redundante con el icono.
- Fuentes por debajo de 12 px en contadores/detalles.
- `API_BASE_URL=''` acoplada a mismo origen sin documentar.

### Correcciones aplicadas (commit `e27e683` + commit de revisión)

| Área | Cambio |
|------|--------|
| **Carga** | Límite unificado a **10 MB**; spinner + dropzone deshabilitada; click en toda la dropzone; botón ✕ para quitar archivo; aviso de error cerrable; solo `.docx`. |
| **Errores API** | HTTP con cuerpo JSON (`detail`) → mensaje real al usuario **sin** mock. Error de red o proxy sin JSON → fallback a mock **como modo demo** (avisado en Report con `__mock`). Título de aviso genérico: “No se pudo validar.” |
| **Resultados** | Scroll suave al semáforo; categorías en cards IA en vez de `rule_id`; desplegables cerrados por defecto; badge de severidad eliminado (redundante con icono); iconos compactos con `aria-label`. |
| **Layout / CSS** | Pantalla completa centrada (alto y ancho); botón “← Validar otro archivo” visible; separación intro ↔ dropzone; footer separado; fuentes mínimas 12 px; `focus-visible` en `summary`/labels; botón Copiar ≥ 44 px; contraste dark en chips/avisos; spinner. |

### Documentación de despliegue (punto 2 de `Arreglos.txt`)

- `README.md` → sección **“Despliegue del frontend (`VITE_API_URL` y proxy)”**: tabla dev / preview / build, nota de reverse proxy y modo demo.
- `frontend/src/App.jsx` y `frontend/vite.config.js` → comentarios sobre alcance del proxy (solo `vite dev`) y variables de entorno.
- `frontend/.env.example` → plantilla de `VITE_API_URL`.

### Pruebas del flujo completo

- Backend: `.venv/bin/python -m uvicorn validator.api:app` en `:8000` (PID estable con `setsid`).
- Frontend: `npm run dev` en `:5173`.
- `POST` a `http://localhost:5173/validar` (proxy) → **HTTP 200**, 41 reglas, semáforo rojo con DOCX de prueba.
- Suite de tests backend: **132 passed, 17 skipped** (verificado en iteraciones previas).

### Nueva tanda — `Arreglos.txt` v2 (posicionamiento + notificación)

Se recibió una nueva versión de `Arreglos.txt` con 3 puntos a coordinar:

#### §0 — Cambio de posicionamiento del producto (C11)

El producto ahora se orienta al **personal de la sede (Repositorio FECyC)**, no a la autogestión del estudiante. Textos reorientados de 2ª persona informal a operador:

| Archivo | Cambio |
|---------|--------|
| `Upload.jsx` | Título "Sube tu tesis" → **"Validar documento de tesis"**; intro, dropzone y textos a "Adjunte/Arrastre/selecciónelo" |
| `Report.jsx` | "¡Puedes entregar!" → **"Documento listo para entregar"**; "Tu documento" → "El documento"; "corrige" → "corregir"; "Copia y pega" → "Copie y pegue" |
| `docs/diseno/01_requisitos_interfaz.md` | Tabla de actores: operador como usuario primario, estudiante como receptor; objetivos y RF renumerados (RF-01…RF-25) |
| `docs/diseno/03_wireframes.md` | Títulos, dropzone, error copy, semáforo, prompts — todo reorientado; limitado a `.docx`, 10 MB |
| `mockups/carga.html`, `mockups/reporte.html` | Mismos cambios de copy |

#### §1 — Captura del correo del estudiante (C12/C13)

- **Nuevo campo opcional** en `Upload.jsx`: input `type="email"` con:
  - Validación de formato en cliente (`/^[^\s@]+@[^\s@]+\.[^\s@]+$/`) para evitar 422 innecesario.
  - `aria-invalid`, `aria-describedby`, mensaje de error inline.
  - Copy de privacidad: *"El correo se usará únicamente para enviar el reporte de validación al estudiante."*
- **Restricción técnica**: el correo viaja en la **misma solicitud** `POST /validar` (campo de formulario `correo`), así que se pide **antes** de validar, no después.
- En `validate()`: `if (correo && esCorreoValido(correo)) form.append('correo', correo)`.
- Si el backend responde `422` con `detail` español, el banner existente ya lo muestra (sin cambios).
- CSS nuevo: `.campo-correo`, `.campo-ayuda`, `.campo-error` + variante dark mode.

#### §2 — Respuesta aditiva `notificacion` (C14, preparado para cablear)

- `mocks.js`: `MOCK_REPORT.notificacion = { enviado: true }` (aditivo, no rompe parsing).
- `Report.jsx`: badge condicional bajo el semáforo:
  - `enviado: true` → *"📧 El reporte fue enviado al correo del estudiante."* (verde)
  - `enviado: false` → *"⚠ No se pudo enviar el correo al estudiante."* (rojo)
- CSS: `.badge-notif.ok` / `.badge-notif.fail` + dark mode.

> **Nota**: §3 confirma que el contrato API no cambia esta semana (correo sigue siendo opcional; sin él el endpoint se comporta igual). §4 indica envío real ~S6/S7 con credenciales SMTP institucionales.

### Tercera tanda — `Arreglos.txt` v3 (notificación por correo: opt-in + estados)

Se describió el contenido del **PR #37** (`semana5-notificacion-correo`, backend), que extiende la respuesta de `POST /validar` a **v1.3.0 (aditivo)** y agrega el envío opt-in de observaciones. Frontend preparado en consecuencia:

#### §1 — Respuesta `notificacion: { estado, detalle }` (C15)

El campo deja de ser `{ enviado: boolean }` y pasa a un objeto con 6 estados (contrato `NotificacionAPI` / `EstadoNotificacionAPI`):

| `estado` | Qué muestra el badge |
|----------|----------------------|
| `enviado` | 🟢 "Enviamos las observaciones al correo del estudiante." |
| `fallo` | 🔴 "No se pudieron enviar..." + **detalle técnico** (`SMTPAuthenticationError: 535 ...`) para reintentar o enviar manualmente |
| `sin_correo` | 🟠 Pide el correo del estudiante en el formulario de carga |
| `no_solicitado` | 🔵 Ofrece la casilla de envío (opt-in) en el formulario |
| `sin_observaciones` / `deshabilitado` | Sin badge (nada relevante) |

- `Report.jsx`: nueva función `badgeNotificacion(notif)` con el mapa anterior; solo se renderiza si `estado` es string (retrocompatible: backend anterior sin el campo → sin badge, sin romper).
- `mocks.js`: `notificacion: { estado: 'enviado', detalle: null }`.
- CSS: `.badge-notif.warn` (ámbar), `.badge-notif.info` (azul), `.badge-notif-detalle` (detalle técnico en bloque secundario) + variantes dark mode.

#### §2 — Casilla opt-in `notificar` (C16)

- Nuevo checkbox en `Upload.jsx` **junto al campo de correo**: *"Enviar observaciones por correo al estudiante"*.
- **Habilitada solo con correo válido** (sin correo no hay notificación posible): si el operador borra o invalida el correo, la casilla se desmarca y deshabilita.
- En `validate()`: `if (notificar && correo && esCorreoValido(correo)) form.append('notificar', 'true')` — el backend interpreta la ausencia como `false` (default).
- Envío efectivo solo si se cumplen **todas**: `notificar=true`, correo válido, semáforo rojo y SMTP habilitado en el servidor → así el estudiante no recibe correo por validaciones intermedias.
- CSS `.check-notificar` (incl. estados `disabled`, `focus-visible`, dark mode); `mockups/carga.html` sincronizado (casilla + lógica mínima que la habilita con correo válido).
- Docs actualizados: `01_requisitos_interfaz.md` (RF-26 nuevo; RF-12 y RF-20 ajustados), `03_wireframes.md` (bloque correo + casilla en escritorio ×3 y móvil), `README.md` (flujo y estado actual).

#### Verificación

- Backend del PR #37 en `:8001`: con correo → `{"estado":"deshabilitado","detalle":null}` (SMTP apagado); sin correo → `{"estado":"sin_correo"}`.
- Backend `master` en `:8000`: acepta el campo extra `notificar` sin romperse (HTTP 200, sin `notificacion` → la UI no muestra badge).
- Proxy Vite `:5173` → `:8000`: 200 (docx), 415 (.txt), 422 (correo inválido) — todos con `detail` español.
- `npm run build` OK; `pytest` 192 passed / 21 skipped.

---

## Evidencias

- Commits: `e27e683` (mejoras IHC), `7bd0be4` (Arreglos.txt v1), commit pendiente (Arreglos.txt v2).
- PRs: https://github.com/retblast/vistobueno/pull/31 · https://github.com/Rodo00/vistobueno/pull/10
- Archivos: `frontend/src/components/Upload.jsx`, `Report.jsx`, `frontend/src/index.css`, `frontend/src/mocks.js`, `frontend/src/App.jsx`, `frontend/vite.config.js`, `frontend/.env.example`, `README.md`, `docs/diseno/01_requisitos_interfaz.md`, `docs/diseno/03_wireframes.md`, `mockups/carga.html`, `mockups/reporte.html`.

---

## Relación con competencias curriculares

| Competencia | Evidencia |
|-------------|-----------|
| **Interacción Humano-Computador** | Evaluación IHC, correcciones de usabilidad, pruebas de flujo, documentación de avances. |
| **Ingeniería de Software II** | Separación de manejo de errores (red vs HTTP), documentación de configuración de despliegue. |

---

## Dificultades y aprendizajes

- Distinguir **error de red** vs **respuesta HTTP con detalle** evita ocultar fallos reales del backend detrás del modo demo.
- El proxy de Vite **no existe** en build estático: hay que documentar `VITE_API_URL` o reverse proxy desde el inicio.

---

## Plan siguiente

- Verificar build (`npm run build`) y commit de la nueva tanda.
- Integrar feedback de revisión del PR (si lo hay).
- Cerrar actividad 7 en `resultados_vistobueno/S7_pruebas_usabilidad/resumen.txt`.
