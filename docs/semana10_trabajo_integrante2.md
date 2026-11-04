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

### 2026-10-28 — Pantalla de ficha de depósito y cierre de la auditoría (PR #68)

El PR #63 de Int1 (auditoría de comportamiento del 2026-10-26, 27 hallazgos)
asignó a Int2 tres hallazgos: **AUD-16** (alta), **AUD-17** y **AUD-18**. Los
tres quedan cerrados en este día.

#### AUD-16 — Pantalla de ficha de depósito (la que faltaba en la SPA)

El backend, el buzón, el userscript y el ensayo general ya existían (PR #55),
pero **los operadores no podían ejecutar el flujo desde la app**: el handover
`docs/HANDOVER_FRONTEND_FICHA_DEPOSITO.md` seguía pendiente. Nueva pantalla
`frontend/src/components/FichaDeposito.jsx`, con la lógica de flujo en
`frontend/src/ficha.js` (funciones puras, sin React):

- **Ficha editable**: los 8 campos extraídos (título, autores, asesor,
  resumen, palabras clave, año, escuela, jurado) con marca de «no detectado»;
  los 4 manuales (matrícula, DNI del autor, DNI y ORCID del asesor). La
  matrícula y el DNI del autor se alinean **por posición con los autores**
  (una entrada por estudiante).
- **Resguardo en `localStorage`**: recargar la página no pierde el trabajo del
  operador; el resguardo se borra al volver al reporte (no dejar datos
  personales de más en el navegador).
- **«Preparar depósito»** → `POST /ficha-pendiente` (204). El aviso recuerda
  que **el archivo lo adjunta el encargado en el formulario oficial**: la app
  no escribe en DSpace (el camino REST `depositar=true` está deprecado por
  decisión del equipo).
- **Panel de espera** con sondeo de `GET /deposito` cada 3 s: el **404 es
  silencio** (aún no hay depósito), nunca un error en pantalla.
- **Cotejo de título**: el título que reporta el userscript se compara con el
  de la ficha (minúsculas, sin acentos, por inclusión). Si no coincide, el
  operador **acepta o rechaza**; el handle no se usa nunca a ciegas. Un
  reporte ya rechazado no se vuelve a proponer en el siguiente sondeo (el
  buzón es «última gana»).
- **Papeleo**: una constancia `.docx` por autor, el paquete `.zip` por autor
  (constancia + su `registro.csv`) y la fila del registro en
  `.tsv`/`.csv`/`.xlsx` o como texto para copiar. El XLSX oficial de la
  biblioteca no se escribe desde la app.

La pantalla **solo existe con semáforo verde** (`ficha_deposito` es `null` en
rojo, invariante v1.7); el reporte ofrece el acceso con el botón «Continuar
con el depósito».

#### AUD-17 — `mocks.js` regenerado desde una respuesta real

El mock arrastraba valores obsoletos (708/709 twips de sangría presentados
como margen derecho) y un detalle que ya no existía. Ahora se generó desde una
respuesta **real** de `POST /validar` (documento «bueno» del factory + 4
mutaciones reales del proyecto), copiando resultados, prompts, resumen y
metadatos tal cual llegaron. La procedencia queda escrita en el propio archivo
para que sea repetible.

#### AUD-18 — Fallback a `MOCK_REPORT` en producción (decisión del equipo)

La auditoría dejó la decisión abierta; se resolvió **desactivar el fallback en
el build de producción**: en desarrollo el reporte de ejemplo sigue disponible
(modo demo, con banner), pero en producción, si el backend no responde, la app
muestra el error real con la opción de reintentar. Motivo: en una herramienta
interna, un reporte de ejemplo puede confundirse con un resultado real.

#### Token del buzón en la SPA

El backend (PR #66) admite un token compartido opcional
(`VISTOBUENO_API_TOKEN` + header `X-VistoBueno-Token`) para el caso en que la
API se exponga fuera de la máquina del operador. La SPA ahora puede enviarlo
con `VITE_API_TOKEN` (ver `frontend/.env.example`): si la variable no está
definida, la SPA sigue hablando sin header (el loopback no lo exige) y el
comportamiento por defecto no cambia.

#### Verificación (2026-10-28)

- `npm run lint` → 0 errores · `npm test` → **47/47** (20 previos + 27 nuevos
  de `ficha.test.js`: ficha solo en verde, manuales por autor y su
  desalineación, sondeo con 404 silencioso, cotejo de título, plan de N
  descargas, formato de fecha/hora) · `npm run build` → 186.18 kB.
- E2E del flujo completo → **11/11** · pytest del backend → **623 passed** (los
  2 fallos iniciales eran `openpyxl` ausente en el `.venv` local; la
  dependencia sí está declarada en `flake.nix`, el CI la tiene).
- **Prueba en vivo con Playwright contra la API real (11 pasos, 0 errores de
  consola)**: documento verde → reporte → CTA → ficha → completado de
  matrícula y DNI → «Preparar depósito» → panel de espera → depósito con
  título **distinto** (aviso de discrepancia) → aceptación → **descarga real
  de la constancia** (36.9 kB, nombre saneado por el servidor) → papeleo en
  pantalla con la fila del registro.
- Capturas de evidencia en `docs/capturas/`: `27_ficha_edicion.png`,
  `28_ficha_espera.png`, `29_ficha_handle.png` (con el aviso de
  discrepancia) y `30_ficha_papeleo.png`.

#### Coordinación pendiente

- El motor sigue entregando `dc.title` con el prefijo «Título del trabajo de
  investigación:» (pendiente de Int3, handover §6): en esta pantalla el
  operador lo recorta, como estaba previsto.

---

### 2026-11-04 — El reporte mostraba solo las primeras 3 líneas de cada error

**Lo que reportó el equipo**: «el backend manda todos los errores (ejemplo:
error de sangría en todas las líneas), pero el frontend solo muestra las
primeras 3 líneas de error».

**Diagnóstico**: el truncamiento no estaba en el frontend (que renderiza
`encontrado`/`found` entero) sino en el **backend**: el detalle de cada
regla se armaba con los tres primeros valores (`vals[:3]`) y con los tres
primeros incumplimientos (`incumplen[:3]`, `fallos[:6]`). Una regla que
fallaba en todas las líneas —la sangría es el caso típico— llegaba al
frontend con 3 líneas de error de las N que había, y además mostraba primero
los valores conformes, que esconden al culpable.

**Solución (AUD-03, opción 1 acordada por el equipo el 2026-10-28)**:

- **Nuevo módulo `validator/detalle.py`**: una sola fuente de verdad del
  texto del detalle, importada por los **dos** motores (`checks.py` legacy y
  `analizadores.py` DSL). Así la paridad legacy↔DSL sigue siendo literal (el
  test de paridad compara el texto completo) y no hay dos copias del
  formateo.
- **Se listan TODOS los incumplimientos**, cada uno con su posición (`#1`,
  `#2`, …), su valor y su página. Si superan el tope (200), el detalle dice
  cuántos más hay: nunca hay pérdida silenciosa de información.
- **Unidades legibles**: la sangría y los márgenes se muestran en cm y el
  tamaño de letra en puntos (Word guarda twips y medios puntos).
- **La ubicación apunta al primer nodo culpable**, no al primero que devolvió
  el XPath (la página que se informaba era la de un párrafo que sí cumplía).
- **Frontend**: `overflow-wrap: anywhere` en la caja del detalle (el texto
  largo tiene que partirse y leerse entero) y el mock regenerado desde una
  respuesta real con el formato nuevo.

**Verificación**:

- `tests/test_detalle_incidencias.py` (7 tests): lista completa de
  incumplimientos, página de cada uno, aviso al superar el tope, paridad
  literal legacy↔DSL, detalle de lista de valores y de patrón de texto, y
  ubicación apuntando al culpable (este test **falla** si se revierte el
  cambio del nodo culpable).
- `frontend/src/components/Report.detalleCompleto.test.jsx` (2 tests): el
  frontend pinta los 8 incumplimientos, no solo los primeros.
- `pytest`: 671 passed, 3 skipped, 6 xfailed.
- `vitest`: 68 passed (8 archivos) · `eslint`: 0 · `build`: 187.45 kB ·
  `ruff format --check`: 71 archivos correctos.
- E2E `scripts/e2e_flujo_completo.sh`: ✅ todas las pruebas.
- Verificación con navegador real (Playwright) sobre un DOCX con 8 párrafos
  de sangría incorrecta: el detalle en pantalla muestra los 8 incumplimientos
  con su página, y la caja no recorta el texto
  (`capturas/07_detalle_completo.png`).

**Coordinación**: el cambio toca `validator/`, que es área de Int3, así que
va en un PR abierto contra `upstream` para que lo revise y lo mergee. El
equipo ya había acordado la forma (opción 1 de AUD-03: módulo único
`validator/detalle.py`).

**Pendiente para Int3**: `docs/ejemplo_respuesta_motor.json` es la salida de
referencia del motor contra la tesis real y quedó con el formato anterior
del detalle; hay que regenerarlo con el documento real (no está en el
repositorio).

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
- `frontend/src/components/FichaDeposito.jsx` y `frontend/src/ficha.js` —
  pantalla de ficha y lógica pura del flujo (AUD-16).
- `frontend/src/ficha.test.js` — 27 tests de la lógica de ficha.
- `frontend/src/mocks.js` — regenerado desde una respuesta real (AUD-17).
- `frontend/.env.example` — `VITE_API_TOKEN` documentado.
- `docs/capturas/` — capturas de la pantalla de ficha (espera, handle y
  papeleo).
- `docs/HANDOVER_AUDITORIA_2026-10-26.md` (tabla §11) y `AGENTS.md` (bloque
  de aviso) — cierre administrativo de AUD-16, AUD-17 y AUD-18.
- `validator/detalle.py` — módulo único del texto de detalle (AUD-03), usado
  por los dos motores.
- `tests/test_detalle_incidencias.py` — 7 tests del detalle completo
  (incumplimientos, páginas, tope, paridad legacy↔DSL).
- `frontend/src/components/Report.detalleCompleto.test.jsx` — 2 tests de
  render del detalle completo.
- `capturas/07_detalle_completo.png` — captura de la verificación con
  navegador real (8 incumplimientos visibles).

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
- **Ingeniería de Software II** (día 2): la pantalla de ficha separa la
  lógica de flujo (funciones puras testeables) de la presentación, y el
  sondeo del buzón se modela como una máquina de estados explícita.
- **Redes de Computadoras I** (día 2): uso del contrato HTTP del buzón
  (`POST /ficha-pendiente`, `GET /deposito`), del código 404 como respuesta
  normal del sondeo y del header de token compartido.

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
- **El 404 del buzón no es un error**: al implementar el sondeo de
  `GET /deposito` hay que tratar el 404 como «todavía no hay depósito»; si se
  trata como error, la pantalla ensucia al operador con avisos falsos.
- **El cotejo del título**: el userscript puede informar un título
  levemente distinto al de la ficha (prefijos, acentos). Cotejar por
  inclusión y sin acentos evita el falso positivo, y aceptar o rechazar
  explícito evita usar un handle a ciegas.

---

## Plan de la semana siguiente

1. ~~Mergear el PR #62 y después el #68~~ → **hecho**: los dos quedaron
   mergeados (`30ac699` y `2d2f0ac`).
2. Ajustar la pantalla de ficha a los cambios de Int1 en el contrato
   (`X-VistoBueno-Token`, ya aplicado) y a los criterios de Int3 para
   AUD-24 a AUD-27 (siguen abiertos: dependen del motor).
3. Revisar con el equipo la numeración de semanas del calendario (la
   ventana 2026-10-26 → 2026-10-31 figura como «semana 9» en la bitácora de
   retblast y como «semana 10» en este archivo) y unificar el criterio.
4. Cerrar la semana con la actualización del Plan PPP (evidencia de las
   horas ejecutadas) y el informe de avance.
5. Revisar con Int3 el PR del detalle completo (AUD-03) y regenerar
   `docs/ejemplo_respuesta_motor.json` con la tesis real.
