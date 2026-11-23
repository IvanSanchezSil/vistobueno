# Bitácora Semana 11 — retblast

- **Integrante**: retblast (Integrante 1 — Backend / API)
- **Semana**: 11
- **Fechas**: 2026-11-08 → 2026-11-22 (actualización de cierre)
- **Rol**: Backend / API (FastAPI, contrato de la API, despliegue en la
  máquina del operador, documentación de instalación y verificación)
- **Ramas**: `docs/instalacion-windows-11` (PR #87),
  `docs/arreglos-documentacion` (PR #88),
  `feat/icono-escritorio-wsl` (PR #89),
  `fix/conteos-suite-y-ci-spa`,
  `fix/b7-reglas-evaluadas` (PR #93),
  `fix/b2-tramite-deposito` (PR #95) y
  `docs/handover-auditoria-2026-11-12` (PR #96).

---

## Objetivos de la semana

1. **Actividad 4 — instalación y despliegue**: dejar el proyecto operable en
   una máquina nueva, con una guía de instalación que cubra Windows 11 y un
   acceso directo de escritorio para el operador.
2. **Cierre documental**: dejar la documentación del repositorio con
   redacción neutra y con las cifras de la suite correctas.
3. **Verificación del acceso directo**: comprobar que la SPA se sirve desde
   la API y que el flujo de Windows queda cubierto por pruebas y por un
   paso propio en el CI.
4. **Auditoría de correctitud (B1–B8)**: atender los hallazgos `VA` del
   handover del 2026-11-12 en el área de Int1: API, DTO, buzón, correo,
   constancias, userscript y pruebas de esas áreas.

---

## Actividades realizadas

### 2026-11-08 — Decisiones de dominio y estado del motor

Se aplicaron las decisiones del 2026-11-08 sobre los hallazgos de la
auditoría: sangría literal sin exención por estilo, anexos como «Base de
datos», endurecimiento de la sola regla `error` de la carátula, igualdad
normalizada del índice y `palabras_clave_minimo` mantenida en `error`. Las
cinco plantillas oficiales siguen en rojo a propósito.

### 2026-11-09 — Guía de instalación con soporte para Windows 11 (PR #87)

- **`docs/INSTALACION.md`**: guía nueva de 388 líneas. Cubre Linux y macOS
  con Nix, Windows 10/11 con WSL2 (camino soportado) y el camino nativo de
  Windows como alternativa para levantar la API y la SPA. Incluye
  requisitos, verificación, puesta en marcha, checklist y problemas
  comunes.
- **README y handover**: el README enlaza la guía y refleja la decisión
  sobre `formato` y el rojo deliberado de `palabras_clave_minimo`; el
  handover de despliegue en la máquina del operador apunta a la guía.
- **Verificación**: suite completa en verde, escaneo de secretos limpio y
  CI en verde.

### 2026-11-09 — Corrección de redacción y consistencia (PR #88)

- Se corrigieron las variantes regionales que quedaban en el aviso de
  `AGENTS.md` y en dos líneas de `docs/HANDOVER_AUDITORIA_2026-10-26.md` y
  `docs/NOTA_F5_Y_API_DSL.md`.
- Las bitácoras históricas de las semanas anteriores quedaron fuera de
  alcance: son el registro de cómo se escribió cada semana.

### 2026-11-09 — Acceso directo de escritorio para WSL (PR #89)

- **La API sirve la SPA**: `validator/api.py` monta `frontend/dist` en `/`
  cuando el build existe. El montaje va después de todas las rutas, así que
  no tapa `/validar`, `/docs` ni el resto de la API.
- **Lanzador** (`scripts/lanzar_app.py`): levanta uvicorn en `127.0.0.1`,
  espera a que la API responda y abre el navegador de Windows.
- **Acceso directo**: `tools/launcher/VistoBueno.bat` (ASCII con CRLF) entra
  a WSL y ejecuta el lanzador; `crear_acceso_directo.ps1` crea el acceso
  directo `VistoBueno` en el escritorio con el ícono `vistobueno.ico`
  (6 tamaños, generado por `scripts/generar_icono.py`).
- **Pruebas**: `tests/test_api_spa.py` y `tests/test_lanzador.py`, 13 tests
  nuevos.
- **Verificación**: `nix flake check` dio «all checks passed»; la suite con
  `frontend/dist` construido pasó; el lanzador se probó en `:8010` con `/`
  y `/docs` respondiendo `200` y apagado limpio.

### 2026-11-09 — Revisión posterior al merge y correcciones (este PR)

La revisión de los tres PRs mergeados encontró dos problemas:

1. **Cifras de la suite desactualizadas**: los documentos declaraban 742
   tests recolectados y 736 en verde, pero la suite quedó en 755
   recolectados. Se corrigieron el README, la guía de instalación, el kit
   del piloto y el plan de lotes. Las cifras se comprobaron con las cuatro
   combinaciones posibles de `recursos/` y `frontend/dist`.
2. **El CI no ejercitaba la SPA**: el test de integración solo corre si el
   build existe, así que en el job `check` quedaba en `skip`. Se agregó un
   paso propio en el job `frontend`, después del build, que corre
   `tests/test_api_spa.py` con la SPA ya construida.

### 2026-11-12 — B7: el correo cuenta las reglas evaluadas (PR #93)

- **Causa**: el correo mostraba `resumen.total` bajo la etiqueta
  «evaluadas». Con 49 reglas definidas y 41 evaluadas, el correo anunciaba
  49.
- **Corrección**: `validator/notificacion.py` usa `resumen.total_evaluadas`.
  La regresión usa un reporte con 49 totales y 41 evaluadas y comprueba el
  41 en el HTML y en el texto plano.
- **Verificación**: 27 tests del módulo en verde y suite completa en
  825 passed, 4 skipped, 6 xfailed. El mismo cambio en el CLI y el
  exportador es de Int3 (M10).

### 2026-11-12 — B2: el depósito se identifica con un trámite (PR #95)

- **Causa**: el buzón no distinguía una ficha de otra. Un handle de un
  ítem ajeno cerraba la ficha en vuelo y el papeleo salía con datos de
  otra tesis. Solo el título los separaba, y la comparación era por
  inclusión.
- **Contrato v1.13.0**: `POST /ficha-pendiente` responde `201` con
  `{tramite_id, vence_en}`; `GET /ficha-pendiente` devuelve el sobre
  `{ficha, tramite_id, vence_en}`; `POST /deposito` exige
  `{tramite_id, handle, titulo_observado, timestamp}`; `/constancia` y
  `/fila-registro` exigen el `tramite_id` y solo habilitan el papeleo con
  el depósito vigente (`409` si no hay depósito, si el trámite no
  coincide o si el handle no es el reportado). `GET /deposito` conserva
  `titulo` como alias deprecado de `titulo_observado`.
- **Userscript**: compara el título esperado con el observado por
  igualdad normalizada; no inventa la hora si no hubo clic en
  «Depositar»; reporta el handle solo tras respuesta exitosa, con
  reintento acotado; y reinicia el timestamp cuando cambia el trámite.
- **Bugs encontrados al escribir las pruebas**:
  1. El reintento del reporte era un bucle infinito: al fallar, el
     wrapper liberaba el handle y el propio toast disparaba el
     `MutationObserver` otra vez. Ahora hay enfriamiento de 30 s.
  2. El ensayo general fallaba al final: publicar la ficha de dos
     autores invalida el depósito anterior, como manda el contrato. El
     driver ahora reporta el handle para el trámite vigente.
- **Verificación**: 837 passed, 4 skipped, 6 xfailed (cobertura 93.60 %),
  `ruff check`, `ruff format --check`, `mypy`, OpenAPI en sync, 42 tests
  del userscript sin drift del `dist/`, 76 tests de frontend con lint y
  build, `nix run .#test-ficha-deposito` con «FLUJO COMPLETO OK» y
  `nix flake check` con «all checks passed».
- **Pendiente**: la SPA sigue en v1.12.0 hasta que Int2 cierre F2. El
  userscript instalado anterior falla cerrado: sin `tramite_id` no
  reporta el handle.

### 2026-11-16 — Revisión de B2 y cierre de la integración (PR #95)

La revisión del PR #95 detectó tres límites que el contrato v1.13.0 todavía
no cubría:

1. **El papeleo confiaba en la ficha del cliente**. La API comprobaba el
   `tramite_id` y el `handle`, pero renderizaba los valores enviados en la
   solicitud. Ahora toma una instantánea atómica de la ficha publicada y del
   depósito vigente. Compara también la ficha, el handle y el timestamp de
   la solicitud. Una diferencia devuelve `409`. El buzón copia los datos
   anidados para que una mutación de la solicitud no altere el estado
   canónico.
2. **El userscript podía reportar sin título esperado y releía el envío en
   cada reintento**. Ahora falla cerrado si falta el título. Congela el
   payload del reporte, conserva el mismo `tramite_id` y limita los fallos
   de red a tres intentos.
3. **La SPA no consumía la identidad del trámite**. Ahora conserva
   `tramite_id` y `vence_en`, ignora depósitos de otro trámite, rechaza
   trámites vencidos o sin timestamp válido, limpia el estado anterior al
   preparar una ficha nueva y usa igualdad normalizada para cotejar el
   título. Las solicitudes de constancia y registro incluyen el
   `tramite_id`.

También se sincronizaron el README, el contrato de API, el flujo, el kit
del operador, el handover del frontend y la especificación OpenAPI.

**Verificación**: 845 tests pasan, 3 se omiten y 6 quedan en `xfail`
estrictos. `ruff check`, `ruff format --check`, `mypy` y la comprobación de
OpenAPI pasan. Los 46 tests del userscript, los 84 tests del frontend, el
lint y el build de producción pasan. `nix run .#test-ficha-deposito` termina
con «FLUJO COMPLETO OK»; el paso de constancia oficial se omite porque el
worktree no incluye `recursos/TESIS DIGITAL MODELO B-2026.docx`.
`nix flake check` termina con «all checks passed».

### 2026-11-16 — Auditoría del userscript: protocolo 2 (confirmación del operador)

Entrega de Int1 sobre `docs/HANDOVER_USERSCRIPT_DSPACE_2026-11-16.md` (17
hallazgos). Se implementó el lote acordado y se documentó lo que queda.

**Decisión de flujo (US-08).** Rellenar, enviar y archivar son tres estados
distintos. El clic en «Depositar» solo aporta la hora del papeleo. El
estado archivado es la **atestación explícita del operador** en la página
del ítem (`/items/<uuid>`): no es un estado verificado por el servidor. La
aprobación de la colección sigue sin ratificar y no se codificó en ninguna
constante. El userscript no añadió escrituras REST a DSpace.

**Contrato v1.14.0 (incompatible).**

- `POST /deposito` exige `atestacion: "operador"` y `revision_esperada`; el
  payload automático de v1.13.0 recibe `422` y no habilita papeleo.
- Dos ventanas: 1 h de autorrelleno (`VISTOBUENO_TTL_AUTORRELLENO_SEG`) y
  24 h de retención del trámite (`VISTOBUENO_TTL_TRAMITE_SEG`). Vencer el
  autorrelleno no borra ficha, identidad, evidencia ni confirmación.
- `GET /tramite` publica la ficha canónica, la revisión, la inconsistencia y
  el depósito confirmado.
- `POST /ficha-pendiente/reconciliar` y
  `POST /ficha-pendiente/inconsistencia`, ambos con `revision_esperada`.
- Los DTO nuevos usan `extra="forbid"`: el alias `titulo` en la entrada
  recibe `422`.

**Userscript 1.2.0 (protocolo 2).** Panel de confirmación en la página del
ítem (solo `textContent`), compuertas de ruta y handle institucional
estricto, autores como evidencia opcional, filas repetibles conciliadas
con los controles del widget (agregar y quitar, nunca borrar nodos) y
mapeo que conserva posiciones. El estado de la versión 1.1.0 se descarta:
no se migra.

**Huecos cerrados de la lista.** US-03 (filas sobrantes), US-04 (desplazamiento
de autor, DNI y matrícula: se corrigió también el papeleo en
`validator/constancia.py`, que compactaba la lista de matrículas), US-08,
US-09, US-10, US-12, US-14, US-15, US-16 y US-17. US-02 y US-11 quedan
parciales; US-01, US-05, US-06 y US-07 siguen abiertos.

**Documentación.** `docs/CONTRATO_API.md` (v1.14.0), `docs/FLUJO_API.md`,
`README.md`, `docs/openapi_spec.json`, el handover del frontend con la
lista de pendientes de Int2 y el estado por hallazgo.

**Verificación.** Suite Python completa en verde, 70 pruebas de node del
userscript sin drift del `dist/`, `nix run .#test-ficha-deposito` con
«FLUJO COMPLETO OK» (el driver ahora confirma el depósito con la
atestación del operador) y `nix flake check`. **La persistencia en Angular
real sigue sin verificarse**: las pruebas de DOM prueban el núcleo, no el
modelo de la instancia.

### 2026-11-12 — B1: medición local y bloqueo declarado

La latencia de 17.99 s de la auditoría no se reproduce en este equipo: la
plantilla oficial midió 0.196 s de `thread_time`. El `Retry-After: 223`
de la auditoría apunta a ~9.4 s de CPU cobrada bajo un cupo de 2 s por
60 s, pero el equipo de la auditoría no es este. No se tocaron los
valores por defecto: falta medir en la máquina del operador y acordar el
presupuesto y la ventana. Queda pendiente también la prueba de dos
validaciones consecutivas sin limpiar el limitador.

### 2026-11-22 — B5 y B6: entradas inválidas y ejemplos versionados

- **B5 (VA-11):** la API traduce `InvalidDocumentError` a 422. Las pruebas
  cubren XML mal formado, raíz ajena y ausencia de `w:body`. Un error de
  configuración sigue devolviendo 500 y no culpa al documento del estudiante.
  La revisión final separó la comprobación de `word/document.xml` de la
  ejecución de reglas: un `KeyError` de configuración ya no se presenta como
  un DOCX dañado.
- **B6 (VA-17):** se regeneraron los dos DOCX de `docs/ejemplos/` desde el
  factory actual. La respuesta golden no cambió de contenido. La nueva
  guarda envía los bytes del archivo versionado, valida sus relaciones OPC,
  comprueba que abre con `python-docx` y compara la respuesta completa de la
  API, incluida la ficha, las reglas y los prompts.
- **Verificación:** 82 pruebas del contrato de API y 6 de la guarda de
  ejemplos pasan. `ruff check`, `ruff format --check`, `mypy`, la
  comprobación de OpenAPI y `nix flake check` pasan. La prueba manual con
  uvicorn devolvió 200 para el DOCX bueno, 422 para un XML mal formado y 422
  para un paquete sin `word/document.xml`.
- **Suite completa:** 1117 pruebas pasan y 5 fallan en el baseline de las
  cinco plantillas oficiales. El test espera 8 warnings, mientras el catálogo
  vigente de NM-05 produce 9. B5 y B6 no modifican el motor, las reglas ni
  esos fixtures; la actualización queda fuera de este lote.

---

## Evidencias producidas


| Evidencia | Dónde |
|-----------|-------|
| Guía de instalación | `docs/INSTALACION.md` |
| Lanzador de escritorio | `scripts/lanzar_app.py` |
| Acceso directo de Windows | `tools/launcher/VistoBueno.bat`, `tools/launcher/crear_acceso_directo.ps1` |
| Ícono de la aplicación | `tools/launcher/vistobueno.ico`, `scripts/generar_icono.py` |
| Montaje de la SPA en la API | `validator/api.py` (`_montar_spa`) |
| Pruebas de la SPA y del lanzador | `tests/test_api_spa.py`, `tests/test_lanzador.py` |
| Paso de CI de la SPA | `.github/workflows/ci.yml` (job `frontend`) |
| Kit del operador actualizado | `docs/PILOTO_OPERADOR.md` |
| Contrato v1.13.0 del buzón | `docs/CONTRATO_API.md`, `docs/FLUJO_API.md`, `docs/openapi_spec.json` |
| Contrato v1.14.0 (confirmación del operador) | `validator/buzon.py`, `validator/api_models.py`, `validator/api.py`, `docs/CONTRATO_API.md`, `docs/FLUJO_API.md`, `docs/openapi_spec.json` |
| Conciliación e inconsistencia | `validator/buzon.py`, `validator/api.py`, `tests/test_api_buzon.py` |
| Userscript 1.2.0 (protocolo 2) | `tools/dspace-fill/src/wrapper.js`, `src/panel.js`, `src/compuertas.js`, `src/mapeador.js`, `src/ejecutor.js` |
| Mock y ensayo con la página de ítem real | `tools/dspace-fill/dev/mock-dspace/`, `tools/dspace-fill/dev/e2e_ensayo.js`, `scripts/e2e_ficha_deposito.sh` |
| Alineación posicional en el papeleo | `validator/constancia.py`, `tests/test_constancia.py` |
| Estado por hallazgo de la auditoría | `docs/HANDOVER_USERSCRIPT_DSPACE_2026-11-16.md` §3 y §10, `docs/auditoria_userscript_2026-11-16/estado.csv` |
| Identidad de trámite del buzón | `validator/buzon.py`, `validator/api_models.py`, `validator/api.py` |
| Instantánea canónica del papeleo | `validator/buzon.py`, `validator/api.py`, `tests/test_api_buzon.py`, `tests/test_constancia.py` |
| Userscript con trámite y título observado | `tools/dspace-fill/src/wrapper.js`, `tools/dspace-fill/src/compuertas.js` |
| Integración de la SPA con la identidad del trámite | `frontend/src/ficha.js`, `frontend/src/components/FichaDeposito.jsx` |
| Pruebas del buzón, del wrapper y del frontend | `tests/test_api_buzon.py`, `tests/test_constancia.py`, `tools/dspace-fill/test/wrapper.test.js`, `frontend/src/ficha.test.js`, `frontend/src/components/FichaDeposito.test.jsx` |
| Registro de ejecución de la auditoría | `docs/HANDOVER_CORRECTITUD_2026-11-12.md` §2.1 |
| Traducción de documentos inválidos a 422 | `validator/api.py`, `tests/test_api_contract.py`, commits `d900f11` y `bc63e9e` |
| Guarda integral de ejemplos versionados | `tests/test_ejemplos_versionados.py`, `docs/ejemplos/`, commit `9149583` |
| Bitácora | este archivo |

- Commits de la semana: `1f94571` (guía de instalación), `a548e41`
  (redacción), `7f4f683` (acceso directo), `38868b9` (B7) y `d9b7e1d`
  (B2), más los commits de documentación. La revisión final de B2 quedó
  en `ee73a5e` (límite canónico del papeleo), `78d0b00` (reporte fail-closed
  del userscript) y `46efcc5` (identidad del trámite en la SPA). El cierre
  local de B5 y B6 usa `d900f11`, `bc63e9e` y `9149583`.
- Suite al cierre local de B5 y B6: **1122 tests**. En la verificación local,
  **1117 pasan y 5 fallan** en el baseline de las cinco plantillas oficiales.
  El test espera 8 warnings, mientras el catálogo vigente de NM-05 produce 9.
  B5 y B6 no cambian el motor, las reglas ni esos fixtures.
- Verificación del flujo de Windows: el `.bat` y el `.ps1` se revisaron y
  se fijó el fin de línea CRLF, pero el flujo no se ejecutó en un Windows
  real desde este entorno. Queda pendiente probarlo en la máquina del
  operador.

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: el acceso directo separa el arranque de
  la aplicación en una capa comprobable (el lanzador, con sus pruebas) y
  una capa de plataforma (el `.bat` y el `.ps1`). El paso de CI cubre la
  parte que antes no tenía verificación.
- **Estructura de Datos**: el montaje de la SPA conserva el orden de
  resolución de rutas de FastAPI: primero las rutas de la API, después el
  recurso estático. Así el contrato de la API no cambia.
- **Redes de Computadoras I**: el lanzador mantiene la API en loopback
  (`127.0.0.1`) y desactiva `proxy_headers`, igual que el resto del
  despliegue documentado.
- **Ingeniería de Software I**: la guía de instalación documenta los dos
  caminos de Windows, sus límites y el checklist de puesta en marcha; las
  cifras de la suite se corrigieron para que la documentación no contradiga
  al código.

---

## Dificultades y aprendizajes

- **Documentar el resultado de una prueba es más frágil que la prueba**:
  la guía enumeraba los conteos de la suite como texto fijo. Cada test
  nuevo los dejó obsoletos sin que nada fallara. Ahora la guía explica de
  qué depende cada cifra.
- **Una prueba que se omite no es una prueba verde**: el test de la SPA
  se saltaba en el CI porque el build no existe ahí. La cobertura real
  llegó cuando el CI construyó la SPA antes de correr la prueba.
- **Un acceso directo esconde dos sistemas**: el atajo de Windows ejecuta
  un `.bat` que entra a WSL y arranca un proceso de Python. Cada frontera
  necesita su propio punto de verificación: el `.bat` con CRLF, el
  lanzador con pruebas unitarias y el montaje de la SPA con un test de
  integración en CI.

---

## Plan de la semana siguiente

1. Coordinar el piloto con la sede: enviar el Anexo B de
   `docs/PILOTO_OPERADOR.md` y acordar la fecha de la sesión.
2. Ejecutar el piloto (Actividad 16) y registrar los hallazgos.
3. Cerrar la Actividad 17 con el registro de documentos y el informe final.
4. Verificar el clic manual contra la instancia de la sede (Actividad 15)
   y la instalación en Windows real del acceso directo.
5. Revisar los PRs abiertos de Int3 (#72, #73 y #75) y desbloquear el
   #73, que está en conflicto.
6. Quitar las marcas `xfail` cuando Int3 cierre AUD-24 a AUD-27 y
   actualizar las cifras de la suite en el mismo commit.
7. Continuar la auditoría de correctitud en el área de Int1:
   - **B3**: diagnóstico previo del formulario de Angular y lectura
     posterior al relleno, con el laboratorio local de DSpace.
   - **B4**: reconciliación de filas sobrantes con los controles del
     propio campo.
   - **B8**: detección de autofill y de formularios restaurados.
   - **B1**: medir en la máquina del operador y acordar el cupo, más la
     prueba de dos validaciones consecutivas.
8. B5 y B6 están implementados en la rama `fix/api-b5-b6-ejemplos`; falta
   integrarlos. B1 y la verificación de navegador siguen fuera de este lote.

## Actualización 2026-11-12 — Handover de correctitud

- Se creó `docs/HANDOVER_CORRECTITUD_2026-11-12.md` con tareas para los tres
  integrantes: dueño, archivos, dependencias y criterios de aceptación.
  El índice enlaza tres documentos separados, uno por integrante.
  retblast ejecuta solo las tareas B1–B8 de Int1. Los cambios de frontend
  pertenecen a Int2; extractor, motor y factory pertenecen a Int3.
- Se registraron VA-01 a VA-21 en el seguimiento de §11 del handover de la
  auditoría. Los defectos siguen pendientes; escribir el plan no los cierra.
- Se confirmó que PR #73 ya está mergeado y PR #75 sigue abierto, con
  conflictos. Se conserva el historial anterior de esta bitácora.
- Se añadió una puerta previa al piloto: diagnóstico del formulario, lectura
  posterior al relleno y persistencia en un borrador autorizado de DSpace.
  El HTML guardado declara Angular 17.3.12. Un mock DOM no demuestra que el
  formulario reactivo real conserve los datos.
- Se reprodujo que el ejecutor informa éxito con controles deshabilitados,
  readonly o con un listener que restaura el valor anterior. La restauración
  y el autofill del navegador requieren además verificación real.
- Se incluyeron el alcance de «verde» y las pruebas que faltan para declarar
  listo el producto. No se modificó código, contrato, CI ni `AGENTS.md`.
- Verificación de la base: `nix develop -c pytest tests/ -v -p no:cacheprovider`
  → 828 passed, 6 xfailed, 1 warning. Los seis xfail siguen siendo limitaciones
  conocidas, no criterios de aceptación cumplidos.
- Siguiente paso: ejecutar los lotes del handover y registrar evidencia de
  cierre. Int1 coordina el contrato del trámite y el ensayo previo de Angular.

## Actualización 2026-11-12 — Revisión normativa completa de fuentes disponibles

- Se contrastaron manual, tablas, ocho rúbricas, cinco plantillas y las dos
  RCU locales con el motor. Se conservaron SHA-256 y localizadores de fuente.
- Se entregaron auditoría normativa, matriz de 66 grupos de requisitos,
  inventario de 226 criterios y catálogo inverso de 49 reglas activas.
  No se afirma revisión visual de todas las páginas ni vigencia legal actual.
- Se ejecutaron ocho casos XML desde el factory para paginación y carátula.
  Se registraron falsos verdes y un falso rojo; el factory conserva VA-17.
- NM-01 a NM-07 se asignaron a Int3 en M12. Int2 amplía la comunicación de
  alcance en F3. Retblast mantiene únicamente B1–B8, sin implementar motor.
- El usuario confirmó que el jefe siempre elige acceso abierto. NM-08 registra
  esa política como decidida. No se pide selector ni trabajo funcional B9.
  El plan node fuerza abierto; comprobar guardado Angular sigue dentro de B3.
- Verificación actual: `nix develop -c pytest tests/ -q` → 824 passed,
  4 skipped, 6 xfailed, 1 warning. Hay recursos/build locales ausentes en este
  worktree; los omitidos no se presentan como comprobados. No cambió código.
- Validación documental: conteos e ID únicos de los CSV, correspondencia de las
  226 filas con fuente, enlaces y cercas Markdown correctos. API local:
  `/docs` y `/openapi.json` respondieron 200. Diff sin errores de espacios.


## Aclaración 2026-11-12 — Laboratorio y observación DSpace

- El usuario confirmó nombres mixtos como referencia aprobada por el jefe.
  Se actualizó REQ-20 como decisión resuelta, sin cambiar código del motor.
- Se sustituyó el ensayo en borrador institucional por un laboratorio local.
  No se permiten guardados experimentales en UNT.
- Se escribió `PLAN_LAB_DSPACE_LOCAL_2026-11-12.md`: evidencia ya disponible,
  checklist para otra observación, límites del HAR, fuentes oficiales, setup
  por fases y aceptación. No se instaló, construyó ni inició el laboratorio.
- Se comprobó que Docker y su daemon responden. No se modificaron servicios,
  NixOS, userscript, aplicación, CI ni configuración del navegador del jefe.
- Verificación de esta entrega: enlaces, matrices y Markdown correctos;
  `git diff --check` sin errores. Suite: 824 passed, 4 skipped, 6 xfailed,
  1 warning. No se presenta la suite como prueba del lab aún no implementado.


## Actualización 2026-11-16 — Auditoría offline del userscript

- Base `c9e5499`. Se contrastaron seis módulos, pruebas, mock/driver y frontera
  API con HAR, DOM, configuración y bundles capturados. No hubo acceso a UNT.
- Se registraron 17 hallazgos US, todos de Int1, con archivos y aceptación.
  Se conservaron B2/PR #95 y B7/PR #93 como entregados; no se repiten esos arreglos.
- Se entregaron matriz de 38 filas, extractos de tres métodos de widget y del
  flujo, cuatro scripts de reproducción y sus resultados con datos ficticios.
- La suite existente del userscript pasa 46/46. Los contraejemplos confirman
  21 casos Node, uno de contrato del dropdown, seis de API/flujo canónico y dos de inyección
  del mock. No equivalen a integración real con Angular o servidor DSpace.
- Se verificó main idéntico al de la captura previa, dropdown con mousedown,
  navegación a MyDSpace y timer autosave desactivado en la configuración capturada.
- No se cambiaron módulos de aplicación, motor, frontend, CI, dist ni AGENTS.
  No se instaló ni arrancó el laboratorio. HAR/DOM/bundles completos siguen
  privados bajo `recursos/`, sin versionar.
- Comprobación de la base en el worktree: 844 passed, 4 skipped, 6 xfailed,
  1 warning. Se verificó dist sin reconstruirlo; no hay cambio del instalable.
- Se comprobaron sintaxis de los scripts, enlaces, conteos de matrices y
  privacidad de fixtures. Escáner de secretos sin hallazgos. API local:
  `/docs` y `/openapi.json` respondieron 200. Diff sin errores de espacios.
