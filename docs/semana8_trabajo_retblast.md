# Semana 8 — Trabajo realizado

**Integrante**: retblast
**Rol**: Integrante 1 — Backend / API
**Semana**: 8 de 14 (19/10/2026 – 24/10/2026) — **en curso (parcial al 19/10)**
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Analizar el formulario real de depósito de DSpace (captura del
   navegador del operador) y congelar el plan de la ficha de depósito.
2. Implementar el contrato v1.7.0: ficha solo con semáforo verde, buzón
   de una ranura, constancia del Modelo B y fila del registro.
3. Construir el userscript que pre-llena el formulario oficial, con su
   ensayo general local.
4. Agregar la licencia MIT (el proyecto pasa a OSS).

---

## Actividades realizadas

### Tarea 1: análisis del formulario real y plan congelado (19/10)

- Captura del flujo "Nuevo envío" (HAR del navegador del operador,
  destruido tras la extracción): sección `traditionalPeruOne` confirmada
  (el típico `traditionalpageone` no aplica), creación del workspaceitem
  con JSON vacío, 16 campos pre-llenados por el servidor según la
  colección, vocabularios controlados con valores URI, QUALDROP de DNIs
  y bug de `dc.rights` (default `http` vs vocabulario `https`: el
  operador debía re-seleccionar "Acceso abierto" en cada envío).
  Hallazgos en `docs/DSPACE_API.md` §11.
- Hallazgo de seguridad operativa: el export "sanitized" de Chrome NO
  elimina los cuerpos POST (el HAR traía el login en claro). Regla
  establecida: todo `.har` se maneja como secreto; `*.har` quedó en
  `.gitignore` y se pidió la rotación de la contraseña al operador.
- `docs/PLAN_FICHA_DEPOSITO.md` v0.2 congelado: flujo aprobado, registro
  de 15 decisiones (login propio rechazado por la barrera BunkerWeb;
  excepción IP cancelada; userscript sobre la sesión del operador),
  mapa de campos, estrategia de pruebas de 4 niveles y rutas aparcadas
  (navegador automatizado; condición de activación de la ruta REST).
- Handover del motor actualizado: 7 extracciones + viabilidad de jurado;
  grado y línea de investigación descartados (pre-llenos del servidor).

### Tarea 2: contrato v1.7.0 — ficha, buzón, constancia y fila (19/10)

- `ficha_deposito` en `POST /validar` SOLO con semáforo verde (invariante
  con test). 24 tests nuevos entre buzón, contrato y guardas
  reforzadas: los guard tests existentes detectaron el drift del
  contrato y se actualizaron en la misma dirección del cambio.
- Buzón de una ranura (`validator/buzon.py`): TTL de 1 h, "última gana",
  ranuras independientes para ficha y depósito, sin cabeceras CORS
  (invariante con test: una página web cualquiera del navegador no puede
  leer los datos personales del estudiante).
- Constancia (`validator/constancia.py` + `POST /constancia`): Modelo B
  lleno por autor (evidencia del registro: una fila por estudiante, la
  misma handle para tesis con dos autores), 11 MERGEFIELD reemplazados
  por texto plano — incluida `ESCUELAS`, que el análisis inicial no
  había visto y la encontró el test de fidelidad contra la plantilla
  oficial. Fila TSV en el orden exacto de columnas del XLSX oficial
  (`POST /fila-registro`); el registro oficial jamás se escribe desde
  la app. 25 tests: golden files, multi-autor, 422/500 con detalle en
  español.
- Suite: 429 → 478.

### Tarea 3: userscript del formulario + ensayo general (19/10)

- `tools/dspace-fill/`: núcleo puro testeable (compuertas, mapeador
  ficha→plan, ejecutor DOM con setter nativo + eventos Angular) +
  wrapper delgado (buzón por `GM_xmlhttpRequest` con `@connect
  localhost`, MutationObserver para la navegación SPA, timestamp del
  clic en Depositar, watcher del handle, toast con resumen lleno/a
  mano/sin dato) + `dist/` instalable (commiteado, el CI verifica el
  drift) + `shim-gm.js` para correr sin Tampermonkey. 24 tests en
  node con jsdom.
- Un test del ejecutor detectó un fallo invisible propio: las filas
  incompletas (botón "+" no encontrado) se reportaban como éxito. Se
  corrigió la implementación hacia fallo visible — el resumen del toast
  nombra lo que quedó pendiente.
- Selectores verificados contra el DOM real capturado: `dc.rights` es un
  combobox (fix por texto + clic en la opción renderizada, con fallback
  manual visible); el botón "+" de filas solo existe en vivo
  (selectores candidatos + fallback).
- `nix run .#mock-dspace`: mock de las páginas de DSpace con proxy
  same-origin al buzón de la API real (la invariante sin-CORS queda
  intacta; el shim habla por el proxy). Checklist de 10 pasos en
  `dev/mock-dspace/README.md`. Verificado en vivo: ficha publicada en
  la API real y leída íntegra por el proxy.
- CI: paso aditivo en el job del frontend (`npm ci && npm test` del
  userscript + drift del dist), justificado en el PR #55 según la regla
  "toda área con verificación propia debe tener su paso en CI".

### Tarea 4: integración de la entrega del motor (diseño 17) (19/10)

- Rebase del PR #56 de Int3 (extracción de la ficha, sección DSL
  `extraccion` sobre `reglas_ficha.yaml`): sin conflictos de archivos.
- Activación de las capturas en la API (`load_ficha_rules` en
  `POST /validar`). Hallazgo y corrección de un leak propio: las reglas
  de captura llegaban a `resultados` porque el mapeo usaba la lista
  cruda del motor; ahora se excluyen (`captura=True`). Sondas de
  concurrencia actualizadas a la firma nueva de `validate_docx`. La
  ficha viaja con valores reales de extremo a extremo; el test
  transitorio se invirtió para afirmar la entrega real (con el doc
  bueno del factory). Suite: 493.
- Nota pendiente de relay a Int3: `dc.title` llega con el prefijo
  "Título del trabajo de investigación:" de la carátula — candidato a
  pulir en la captura; hoy el operador lo recorta en la pantalla.

### Tarea 5: OSS y verificación de la advertencia de secretos (19/10)

- LICENSE MIT (línea de copyright "VistoBueno contributors"), `*.har`
  en `.gitignore`, README sincronizado (regla de mantenimiento del
  AGENTS.md en cada commit que toca el contrato).

---

## Evidencias producidas

- Commits de la rama `semana8-deposito-ficha` (PR #55): `bc81822`
  (LICENSE + .har), `5039795` (plan v0.2), `3411a33` (DSPACE_API §11),
  `8bfb595` (handover), `9abf8ec` (buzón + ficha v1.7.0), `2d0f0f8`
  (contrato), `a134ae9` (constancia), `24cfbd7` (contrato constancia),
  `f85922b` (userscript), `bbcdbdf` (activación del diseño 17),
  `9914090` (contrato: ficha poblada), `e671fea` (mock-dspace),
  `9d56148` (CI del userscript).
- Documentos: `docs/PLAN_FICHA_DEPOSITO.md` v0.2, `docs/DSPACE_API.md`
  §11, `docs/CONTRATO_API.md` v1.7.0,
  `docs/HANDOVER_MOTOR_FICHA_DEPOSITO.md`, `docs/FLUJO_API.md` (buzón),
  README (sección de operación).
- Artefactos: `tools/dspace-fill/dist/vistobueno-dspace-fill.user.js`
  (instalable), `nix run .#mock-dspace` (ensayo general), paso de CI del
  userscript.
- Análisis local (no versionado, `recursos/`): `recursos/har-analisis/`
  con los cuerpos extraídos de la captura y los extractores.

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: arquitectura del buzón (estado mínimo,
  invariante sin-CORS con test de regresión), manejo del drift de
  contrato vía guard tests, estrategia de pruebas de 4 niveles, ensayo
  general previo al piloto.
- **Estructuras de Datos**: DTOs de la ficha (extraídos/manuales,
  alineación por autor), serialización motor→API, colapso de capturas
  por campo en `build_report`.
- **Redes de Computadoras I**: análisis del contrato HAL de DSpace desde
  el HAR, CORS vs contexto de extensión (`GM_xmlhttpRequest`), proxy
  same-origin del mock, multipart y códigos de estado del contrato.
- **Ingeniería de Software I**: contrato v1.7.0 documentado, plan
  congelado con registro de decisiones, handover al motor, README de
  operación.

---

## Dificultades y aprendizajes

- El export "sanitized" de Chrome NO sanea los cuerpos POST: los `.har`
  se manejan como credenciales y se destruyen tras la extracción.
- Los guard tests existentes cumplieron su función: detectaron el drift
  del contrato y obligaron a que el cambio llegara con dirección
  declarada (tests actualizados, no eliminados).
- Un test propio del ejecutor cazó un fallo invisible mío antes de que
  existiera: filas incompletas reportadas como éxito. La suite gana al
  orgullo.
- El DOM real tiene piezas que la captura estática no muestra (el
  combobox renderiza opciones en vivo; el botón "+" solo existe
  hidratado). La respuesta correcta no es adivinar: selectores
  candidatos + fallo visible con instrucción para el operador.
- La captura del jefe trajo más de lo pedido: al exportar "sanitized"
  pero no guardar, se preservó la evidencia estructural sin riesgo de
  estado en la instancia; el borrador sobrante quedó como víctima del
  piloto.

---

## Plan de la semana siguiente

1. Piloto real con el operador (borrador descartable, checklist firmado)
   sobre la rama ya integrada.
2. UI de la ficha (Int2): pantalla de revisión, manuales, "Preparar
   depósito", panel de espera con auto-completado del handle, botón de
   copia de la fila TSV, resguardo en localStorage.
3. Relay a Int3: prefijo de `dc.title` en la captura (pulió el diseño
   17).
4. Merge del PR #55 con el CI en verde.
