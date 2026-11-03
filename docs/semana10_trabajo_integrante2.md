# Bitácora Semana 10 — integrante2

- **Integrante**: integrante2 (Integrante 2 — Frontend / React)
- **Semana**: 10
- **Fechas**: 2026-10-27 → 2026-10-31
- **Rol**: Frontend (React + Vite): robustez de la SPA, accesibilidad y
  pantalla de ficha de depósito
- **Ramas**: `s8-robustez-ux` (PR #62, robustez y envío del formulario),
  `auditoria-2026-10-26-int2` (PR #68, pantalla de ficha + auditoría Int2).
  Ninguna toca `master` directo; la segunda se apila sobre la primera.

> Nota de numeración: el calendario del proyecto rotula como «semana 9» a la
> ventana 2026-10-26 → 2026-10-31 (bitácora de retblast). Este archivo usa el
> nombre propuesto en la revisión del PR #62 (`semana10_trabajo_integrante2.md`)
> y deja las fechas explícitas para que no haya ambigüedad al leerlo.

---

## Objetivos de la semana

1. **Robustez de la SPA**: que un fallo de render no deje la pantalla en
   blanco, que el envío con Enter funcione y que los iconos del header no
   dependan del render de emojis del sistema.
2. **Cerrar la parte de Int2 de la auditoría de 2026-10-26**: AUD-16
   (pantalla de ficha), AUD-17 (mocks honestos) y AUD-18 (fallback sin
   backend solo en desarrollo).
3. **Dejar los cambios con cobertura automatizada**: la regla de `AGENTS.md`
   es explícita («lo probé a mano» no es verificación), así que los tres
   cambios del día 1 llevan tests de componente con jsdom y
   `@testing-library/react`.

---

## Actividades realizadas

### 2026-10-27 — Robustez, envío con Enter e iconos SVG (PR #62)

Tres arreglos de la lista de pendientes propia, todos locales al frontend:

- **Límite de error (`ErrorBoundary.jsx`)**: hasta ahora un fallo de render
  dejaba la pantalla en blanco. Ahora `App` envuelve la vista activa y el
  fallo muestra un aviso con dos salidas —**«Reintentar»** (descarta el
  reporte y retoma el flujo) y **«Recargar la página»**— y el detalle técnico
  plegado para el reporte del fallo. El alcance se describe con precisión: el reporte ya
  se defiende de un payload malformado (`Report.jsx` valida `resultados`,
  `aplicable` y `metadatos`), así que el límite es la red contra bugs propios
  del render.
- **Envío con Enter**: el card de carga pasa a ser un `<form noValidate>` con
  `onSubmit` propio y el botón «Validar documento» queda como `type="submit"`;
  los botones auxiliares (quitar archivo, cerrar aviso) pasan a
  `type="button"`. `noValidate` deja la validación en las reglas propias
  (con sus mensajes `role="alert"`) y evita duplicar la burbuja nativa del
  navegador. La dropzone conserva su Enter/Space para abrir el selector
  (`preventDefault` propio).
- **Toggle de tema con SVG inline**: fin del emoji ☀️/🌙 del header (mismo
  criterio que los iconos de la dropzone desde la v7: se renderizan igual en
  todos los sistemas y en las capturas de evidencia); sol/luna con
  `stroke="currentColor"` y `aria-hidden`, conservando `aria-label`,
  `aria-pressed` y `title`.

#### Correcciones tras la revisión de retblast (2026-10-29)

La revisión pidió cambios (2 bloqueantes y 3 hallazgos de accesibilidad) y
las observaciones se aplicaron antes de volver a pedir el merge:

| Hallazgo | Corrección |
|----------|------------|
| **B1** — PR en conflicto con `master` | Rama reconstruida sobre `master` actualizado (`80e428d`); el `README.md` se combina con el texto del equipo, sin revertir nada de lo suyo. |
| **B2** — conflicto entre el PR #62 y el #68 | El PR #68 se reapila sobre este: el `App.jsx` del #68 conserva el `ErrorBoundary` y los iconos SVG, y su diff queda reducido a la pantalla de ficha. |
| **A1** — el aviso de error no se anuncia y el foco se pierde | El aviso lleva `role="alert"` y el foco pasa al encabezado al montar (mismo patrón que el semáforo del reporte). Con teclado o lector de pantalla ya no se queda en `<body>`. |
| **A2** — el `<summary>` perdía el triángulo | `display: list-item` (valor por defecto) en vez de `display: flex`; el objetivo táctil de 44 px se resuelve con `min-height` y `padding`. |
| **A3** — la recuperación podía quedar en un bucle | Corregido en la segunda ronda (F2): la etiqueta del botón pasa a «Reintentar» y se agrega «Recargar la página», que es la salida real del bucle cuando el fallo se repite. |
| **N1** — la promesa de Enter solo se cumplía en el camino feliz | Con el formulario completo, Enter valida; si falta el archivo o el correo es inválido, el botón está deshabilitado y Enter lleva el foco al elemento pendiente (donde ya está el aviso). La redacción del PR y de esta bitácora se ajustó a ese comportamiento real. |
| **N2** — los tres cambios sin cobertura automatizada | `jsdom` + `@testing-library/react` + `jest-dom`; `environment: 'jsdom'` en la configuración de vitest y 10 tests nuevos (`ErrorBoundary.test.jsx`, `Upload.test.jsx`, `App.test.jsx`). |
| **N3** — justificación exagerada del límite de error | El alcance se describe con precisión (bug propio del render, no payload inesperado). |
| **N4** — el cierre de la semana 10 estaba en el archivo de la semana 7 | Este archivo (`semana10_trabajo_integrante2.md`); `semana7_trabajo_integrante2.md` queda con su contenido. |
| **N5** — borde invisible del detalle técnico en modo oscuro | En oscuro usa un azul grisáceo con contraste superior a 3:1 (WCAG 1.4.11). |
| **N6** — commit con tres cambios mezclados | La rama se reconstruye con un commit por tarea lógica: límite de error, envío con Enter, iconos SVG, tests y documentación. |

#### Segunda ronda de revisión de retblast (2026-11-02)

La revisión de la rama reconstruida cerró 8 de los 11 hallazgos y abrió 5
nuevos (F1 a F5). Los cinco están aplicados:

| Hallazgo | Corrección |
|----------|------------|
| **F1** — regresión de teclado: `onFormKeyDown` se comía el Enter de otros controles | La intercepción se limita al campo de correo. Con el formulario completo, Enter sigue disparando el envío implícito; con el formulario incompleto, solo el correo lleva el foco al elemento pendiente. Los botones («Quitar archivo», «Cerrar aviso») y la casilla «Enviar observaciones» conservan su Enter nativo. 3 tests de regresión. |
| **F2** — la corrección de A3 no hacía lo que decía | React ya remonta el subárbol que falló, así que la `key` no cambia el número de montajes (medido: 5 → 6 con y sin `key`): el comentario, el test y el cuerpo del PR dejan de afirmar un remontaje que no ocurre. La etiqueta pasa a **«Reintentar»** y se agrega **«Recargar la página»**, la salida real del bucle con un fallo determinista. |
| **F3** — los números de verificación mezclaban este PR con el apilado | El cuerpo del PR #62 lleva sus propias cifras (34/34 tests, 171.61 kB) y las del PR #68 aparte. |
| **F4** — la referencia al paso «8c» no correspondía al script citado | Se quitó el paréntesis: `scripts/e2e_flujo_completo.sh` no tiene paso 8c (el 8c está en `scripts/e2e_ficha_deposito.sh`, del PR #55). |
| **F5** — faltaba un test que cubriera F1 | `Upload.test.jsx` tiene tres casos nuevos (Enter sobre «Quitar archivo», sobre la casilla y sobre el correo con el formulario incompleto). Como jsdom no implementa la activación implícita de un control con Enter, el test emula lo que hace el navegador. |

**Verificación en Chrome real** (no solo en vitest): Enter sobre «Quitar
archivo» quita el archivo, Enter sobre la casilla conserva el foco en la
casilla, Enter en el correo lleva el foco a la dropzone (sin archivo) o lo
deja en el campo (con archivo); el aviso del límite ofrece las dos salidas,
mantiene `role="alert"` y el foco en el `H2`, y tras «Reintentar» con un
fallo determinista el aviso vuelve con la salida de recarga disponible.

#### Verificación (2026-10-27, repetida tras las correcciones)

- `npm run lint` → 0 errores · `npm test` → **34/34** (20 previos + 14
  nuevos de componente) · `npm run build` → 171.61 kB OK.
- E2E del flujo completo (`scripts/e2e_flujo_completo.sh`) → **11/11**.

---

## Evidencias producidas

- `frontend/src/components/ErrorBoundary.jsx` — límite de error con
  `role="alert"`, foco al encabezado y recuperación con remontaje.
- `frontend/src/components/ErrorBoundary.test.jsx`,
  `frontend/src/components/Upload.test.jsx`,
  `frontend/src/App.test.jsx` — cobertura de componente con jsdom y
  `@testing-library/react`.
- `frontend/src/components/Upload.jsx` — `<form noValidate>`, envío con
  Enter y `type` explícito en los botones.
- `frontend/src/App.jsx` — iconos SVG del toggle de tema.
- Commits: `ab7de6f` (límite de error), `f02a95f` (Enter), `5571bad`
  (SVG), `2345fd5` (tests), más el commit de documentación de esta bitácora.

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: manejo de errores (límite de error con
  salida recuperable), calidad de código (commits atómicos, lint) y pruebas
  automatizadas como criterio de aceptación.
- **Estructuras de Datos**: no aplica en este día (sin cambios de modelos).
- **Redes de Computadoras I**: el `<form>` y el contrato `POST /validar` se
  mantienen intactos; el cambio es de interacción, no de contrato.
- **Ingeniería de Software I**: documentación técnica (bitácora, README) y
  respuesta documentada a la revisión de código.

---

## Dificultades y aprendizajes

- **El feedback de jsdom sobre el foco**: en el entorno de pruebas, un
  `role="alert"` no basta — hay que comprobar además que el elemento
  anunciado recibe el foco. El test de A1 lo verifica con `toHaveFocus()`.
- **React 18 reintenta el render en desarrollo**: un hijo que falla «una
  sola vez» no reproduce el error en los tests (React vuelve a invocarlo y la
  segunda vez tiene éxito). Los tests simulan el fallo con un flag explícito.
- **Un test puede pasar sin distinguir dos implementaciones**: el test de A3
  desactivaba la bandera de fallo antes de pulsar el botón, así que pasaba
  igual con y sin `key` (lo detectó la segunda revisión). Ahora cada test
  comprueba lo que dice comprobar, y lo que se afirma en el texto está
  medido.
- **No toda verificación es manual**: la revisión señaló que «lo probé a mano»
  no es verificación (`AGENTS.md`). Los tests de componente son el paso
  intermedio entre la prueba manual y el E2E: el E2E no puede provocar un
  fallo de render de forma controlada.

---

## Plan de la semana siguiente

1. Cerrar la pantalla de ficha de depósito (AUD-16) con su E2E y sus
   capturas de evidencia.
2. Regenerar las capturas de la SPA y dejarlas versionadas como evidencia.
3. Revisar con el equipo la numeración de semanas del calendario (la
   ventana 2026-10-26 → 2026-10-31 figura como «semana 9» en la bitácora de
   retblast y como «semana 10» en este archivo) y unificar el criterio.
