# Handover: UI de la ficha de depósito (frontend, Semana 8)

**Fecha**: 2026-10-23
**De**: Integrante 1 (Backend/API)
**Para**: Integrante 2 (Frontend)
**Estado**: resuelto — el diseño de pantallas quedó implementado.
**Resuelto**: 2026-11-03 (PR #68). La pantalla quedó implementada en
`frontend/src/components/FichaDeposito.jsx` (vista) y `frontend/src/ficha.js`
(lógica de flujo pura), con cobertura en `frontend/src/ficha.test.js`.
La integración con la identidad del trámite se revisó el 2026-11-16 en el
PR #95.
**Contrato vigente**: `docs/CONTRATO_API.md` (v1.14.0). La SPA envía el token
compartido opcional (`VITE_API_TOKEN` → `X-VistoBueno-Token`) cuando está
configurado; en loopback no hace falta.
**Limitaciones conocidas del motor** (no de la UI): AUD-24 a AUD-27
quedaron cerrados en el PR #75 (autores, asesor, año de portada y palabras
clave). La pantalla permite corregir los campos a mano por si el documento
se aparta de la estructura esperada.
**Contexto de producto**: `docs/PLAN_FICHA_DEPOSITO.md` (v0.2 congelado).

---

## 1. El problema en una frase

El backend ya entrega la ficha detectada, el buzón que habla con el
userscript, la constancia y el registro descargable; falta la **pantalla
que une todo**: revisar la ficha, prepararla, esperar el handle y
descargar el papeleo.

Todo el backend está en `semana8-deposito-ficha` (PR #55) con suite
verde; el flujo completo está verificado de punta a punta con
`nix run .#test-ficha-deposito` (sin navegador: el driver corre el
userscript real contra el mock).

## 2. Qué se pide, pantalla por pantalla

### 2.1 Ficha de depósito (solo con semáforo verde)

La respuesta de `POST /validar` trae `ficha_deposito` **solo en verde**
(en rojo es `null` y la pantalla no existe). Dos grupos:

- `extraidos` (8 campos, editables — el operador corrige lo que el
  motor detectó):
  | Campo | Cómo llega | UI sugerida |
  |-------|-----------|-------------|
  | `dc.title` | texto completo (HOY llega con el prefijo "Título del trabajo de investigación:" — ver §6; el operador lo recorta) | input largo |
  | `dc.contributor.author` | lista (1-2 autores) | lista editable |
  | `dc.contributor.advisor` | texto | input |
  | `dc.description.abstract` | texto completo | textarea |
  | `dc.subject` | lista | chips/lista editable |
  | `dc.date.issued` | "2026" (solo año) | input corto |
  | `escuela` | texto | input |
  | `renati.juror` | `detectado=false` siempre (captura no confiable) | opcional, a mano |
  | Con `detectado=false` el `valor` viene `null`: campo vacío editable. |
- `manuales` (4 campos, vacíos — el operador los teclea UNA vez):
  `matricula` y `renati.author.dni` aceptan **lista alineada por
  posición con los autores** (una por estudiante; las tesis con dos
  autores generan dos constancias y dos filas), `renati.advisor.dni` y
  `renati.advisor.orcid` son únicos.

Sugerencia: resguardar la ficha editada en `localStorage` (refrescar la
página no debe perder el trabajo del operador). Sin persistencia en el
servidor: es un resguardo de cliente.

### 2.2 Botón "Preparar depósito"

`POST /ficha-pendiente` con la ficha editada (el mismo objeto
`extraidos` + `manuales`, tal cual llegó en la respuesta de /validar).
Respuesta `201` con `{tramite_id, revision, autofill_hasta,
retenido_hasta, vence_en}`. La SPA conserva el `tramite_id` y la
`revision` para identificar el trámite en vuelo. Desde ese momento el
userscript (en el navegador del operador, sobre las páginas de DSpace)
puede leer la ficha del buzón.

Nota operativa: el buzón tiene **una sola ranura** — preparar de nuevo
reemplaza la ficha anterior ("última gana"). Tiene dos ventanas: 1 hora
de **autorrelleno** (`autofill_hasta`) y 24 horas de **retención** del
trámite (`retenido_hasta`). Vencer la primera no borra la ficha: el
trámite sigue en `GET /tramite`. Si la API se reinicia, el buzón se
vacía: re-preparar.

### 2.3 Panel de espera ("Esperando el depósito…")

Sondear `GET /tramite` (estado canónico) y `GET /deposito` (confirmación)
cada ~3 s mientras el panel esté abierto:

- **404** en `GET /deposito` = aún no hay nada: seguir esperando, en
  silencio (no es error).
- **200** = el operador confirmó el depósito en la página del ítem:
  `{tramite_id, handle, titulo_observado, timestamp, revision_confirmada,
  confirmado_en, confirmado_por, confirmacion_vigente,
  titulo_verificado, autores_verificados}`. Ignorar la confirmación si su
  `tramite_id` no coincide con el trámite actual, si `confirmacion_vigente`
  es `false` o si el trámite venció. Cotejar `titulo_observado` contra la
  ficha preparada por igualdad normalizada (minúsculas, sin acentos y sin
  espacios extras). La inclusión no identifica una tesis. Si NO coincide:
  mostrar el recibido con el botón de aceptar/rechazar — nunca usarlo a
  ciegas.

Al recibir: mostrar handle, fecha y hora. El timestamp es de solo lectura:
el servidor conserva el valor reportado por el userscript.

> Con el contrato v1.14.0 el depósito **no lo reporta la SPA**: lo
> reporta el userscript después de la atestación explícita del operador.
> La SPA solo lo lee. Ver §7.1.

### 2.4 Panel de papeleo

- **Constancias**: `POST /constancia` con `{ficha, tramite_id, handle,
  timestamp, indice_autor}` — UNA DESCARGA POR AUTOR (iterar
  `indice_autor` 0..N-1).
  La respuesta es el `.docx` binario (attachment con el nombre del autor).
  Con `?formato=zip` devuelve un **paquete por autor** con la constancia
  .docx y su fila del registro como `registro.csv` — una descarga = todo
  el papeleo del estudiante (sugerido como opción "Descargar todo").
- **Registro**: `POST /fila-registro` con `{ficha, tramite_id, handle,
  timestamp}`:
  - `formato=json` (default): `{"filas": ["\tTesis…", …]}` — para el
    botón "copiar fila" al portapapeles.
  - `?formato=tsv | csv | xlsx`: **archivo descargable** directo al
    disco (Excel/LibreOffice lo abre con las columnas sanas).
  - Una fila por autor, mismo handle.
- Los errores llegan como `{"detail": "…"}` en español y nombran
  exactamente el dato faltante ("Faltan 1 matrícula(s)…"); muéstralos,
  no los tragues.

## 3. Errores que sí verás en la operación

| HTTP | Cuándo | UI |
|------|--------|-----|
| 409 | el depósito venció o la ficha, el trámite, el handle o el timestamp no coinciden | mostrar `detail`, volver a preparar y depositar |
| 422 | falta un dato de la ficha canónica / índice fuera de rango / timestamp canónico mal | mostrar `detail`, volver a la ficha |
| 500 | `VISTOBUENO_FIRMA` sin configurar, plantilla ausente | mostrar `detail` como nota de configuración |

## 4. Lo que NO se pide

- Sin CORS, sin auth, sin escribir el XLSX oficial (el operador pega la
  fila o copia del archivo descargado — decisión congelada del plan §3).
- Sin llamadas del frontend a DSpace: el mundo DSpace es del userscript
  (`tools/dspace-fill/`, ya construido y probado).
- Sin modificar el backend: si algo del contrato molesta, me lo dices y
  lo discutimos antes de tocar `api.py`.

## 5. Verificación que te pido

- ⚠️ **Proxy de Vite**: las rutas del flujo (`/ficha-pendiente`,
  `/deposito`, `/constancia`, `/fila-registro`) ya están en
  `frontend/vite.config.js` junto a `/validar`. En `npm run dev` el
  proxy las enruta al backend; en build estático o `vite preview` usa
  `VITE_API_URL` o un reverse proxy (la API no agrega CORS — solo el
  userscript lo salta con `GM_xmlhttpRequest`).
- Tests del frontend (vitest) para: ficha solo en verde, manuales por
  autor, sondeo con 404 silencioso, cotejo de título, N descargas.
- Prueba manual con la API real: `nix run .#test-ficha-deposito`
  demuestra el flujo completo sin navegador (buzón incluido); tu
  pantalla se prueba contra la misma API (`nix run .#serve`), con la
  ficha del doc bueno publicada a mano si quieres sondear el panel.
- El checklist del ensayo general manual está en
  `tools/dspace-fill/dev/mock-dspace/README.md`.

## 6. Pendiente conocido (no te frene)

El motor entrega `dc.title` con el prefijo de la etiqueta de carátula
("Título del trabajo de investigación: …"). Está pedido su pulido al
motor (nota de seguimiento en el handover de Int3); mientras tanto el
operador lo recorta en tu pantalla — es el caso `detectado=true` con
texto editable, así que no requiere nada especial de tu lado.

## 7. Después de tu parte

El piloto real con el operador (borrador descartable en la instancia,
checklist firmado) — el ensayo general local ya corre solo con
`nix run .#test-ficha-deposito`.

## 7.1 Adaptación pendiente de Int2 al contrato v1.14.0 (2026-11-16)

Int1 publicó el contrato v1.14.0. **No se tocaron archivos del frontend**:
esta lista describe lo que la SPA debe adoptar en su propia entrega.

| Cambio | Qué debe hacer la SPA |
|--------|------------------------|
| `POST /deposito` incompatible | La SPA **no** reporta el depósito: lo hace el userscript tras la atestación del operador. La SPA solo lo **lee**. |
| `GET /tramite` nuevo | Reemplaza a `GET /ficha-pendiente` como fuente del estado: trae `ficha`, `revision`, `inconsistencia`, `deposito`, `confirmacion_vigente`, `autofill_hasta` y `retenido_hasta`. |
| Dos ventanas | `autofill_hasta` (relleno, 1 h) y `retenido_hasta` (trámite, 24 h). El panel de espera debe distinguir "vencido para rellenar" de "trámite vencido". |
| Revisión | La SPA guarda la `revision` que publica la ficha y la envía en `revision_esperada` si ofrece acciones de esa clase. Una respuesta `409` obliga a releer `GET /tramite`. |
| Confirmación vigente | `GET /deposito` trae `confirmacion_vigente`, `revision_confirmada`, `confirmado_en`, `titulo_verificado` y `autores_verificados`. El panel debe mostrar "confirmado por el operador" y **no** "archivado por el servidor". |
| Autores no verificados | Si `autores_verificados=false`, la pantalla dice "autores no verificados"; nunca "coinciden". |
| Conciliación | `POST /ficha-pendiente/reconciliar` (con `revision_esperada`, `motivo` y `handle`) es la vía para corregir la ficha. Invalida la confirmación: la SPA debe pedir una reconfirmación. |
| Inconsistencia | `GET /tramite` trae `inconsistencia`; si existe, el papeleo queda bloqueado (`409`) hasta conciliar. |
| Papeleo | `POST /fila-registro` y `POST /constancia` exigen ficha exactamente igual a la canónica y un depósito confirmado y vigente. |

---

## 8. Verificación de la Actividad 15 (2026-11-04, Integrante 1)

Lote 3 del plan previo al piloto (`docs/PLAN_LOTES_PRE_PILOTO.md`). La
pantalla se verificó contra la API real, no contra mocks sueltos.

### 8.1 Qué se comprobó

| # | Paso | Resultado |
|---|------|-----------|
| 1 | Subir `docs/ejemplos/doc_bueno.docx` | HTTP 200, semáforo **verde**, 0 fallos (43 reglas evaluadas en esa corrida de 2026-11-04; el catálogo actual evalúa 44 de 54) |
| 2 | La ficha viaja solo con verde | `ficha_deposito` presente en verde y `null` en rojo |
| 3 | Editar título, autores, asesor, año y palabras clave | Los valores editados llegan tal cual en `POST /ficha-pendiente` |
| 4 | Completar los campos manuales | Matrícula y DNI del autor se alinean por posición con los autores |
| 5 | «Preparar depósito» | `POST /ficha-pendiente` → 204 (contrato v1.12.0 en esa corrida) |
| 6 | Panel de espera y viaje al buzón | `GET /ficha-pendiente` devuelve la ficha editada; `GET /deposito` responde 404 en silencio mientras no hay depósito |
| 7 | Aceptar el handle | `POST /deposito` → 204 y `GET /deposito` devuelve `handle`, `titulo` y `timestamp` |
| 8 | Constancia y fila del registro | `POST /constancia` → DOCX de 137 KB con los MERGEFIELD del Modelo B ya reemplazados; `?formato=zip` devuelve la constancia + `registro.csv`; `POST /fila-registro` responde en `tsv`, `csv`, `xlsx` y `json` |
| 9 | Cabecera de token | `cabecerasBuzon()` envía `X-VistoBueno-Token` solo si hay token configurado; el backend solo lo exige para peers remotos (`tests/test_api_acceso.py`) |
| 10 | Limpiar el resguardo | «Volver al reporte» borra la clave `vb-ficha-deposito` de `localStorage` |

Comprobaciones de seguridad del servidor en la misma corrida:

- `GET /docs` con `Host` propio → **200**; con `Host: evil.com` → **400**.
- `POST /constancia` sin `VISTOBUENO_FIRMA` → **500** con el mensaje en
  español que nombra la variable (es el comportamiento documentado en
  `docs/CONTRATO_API.md`: configuración del servidor, no un fallo del
  cliente).

### 8.2 Lo que faltaba y quedó cubierto

La pantalla **no tenía ninguna prueba de componente**: solo existían tests
de las funciones puras de `frontend/src/ficha.js`. Ahora hay
`frontend/src/components/FichaDeposito.test.jsx` con 8 casos que montan la
pantalla y recorren el flujo completo (editar, completar, publicar, esperar,
aceptar, rechazar, descargar, resguardo). Los casos se verificaron con
mutaciones: si la pantalla deja de publicar la ficha, o si desaparece el
cotejo del título (que evita usar un handle ajeno a ciegas), el test falla.

### 8.3 Lo que la verificación destapó

Las respuestas versionadas del par de ejemplo (`docs/ejemplos/`) quedaron
desfasadas cuando el PR #78 cambió el formato del detalle de las reglas
(AUD-03): 5 reglas y sus prompts de IA seguían con el texto anterior. Se
regeneraron con `python scripts/ejemplo_bueno_malo.py` y se agregó
`tests/test_ejemplos_versionados.py`, que compara las respuestas versionadas
con las que produce el motor. Sin ese test, el desfase volvería a colarse
sin que nadie lo note.

### 8.4 Límites de esta verificación

Los pasos se ejecutaron con un cliente HTTP que replica lo que hace el
navegador (mismos métodos, cabeceras y cuerpos que `frontend/src/ficha.js`),
y la parte de interfaz se cubre con los tests de componente. El clic manual
en un navegador real contra la instancia de la sede queda para el piloto:
es el paso 4 del checklist del kit del operador
(`docs/PILOTO_OPERADOR.md`, lote 4 del plan).

### 8.5 Limitaciones del motor que el operador verá

**AUD-24 a AUD-27 quedaron cerrados en el PR #75** (no eran de la UI):

- `dc.title` llega sin el prefijo «Título del trabajo de investigación:».
- Los autores se capturan uno por párrafo, sin partir «Apellido, Nombre».
- El asesor se toma del párrafo siguiente a la etiqueta o del mismo
  párrafo si van juntos.
- `dc.date.issued` es el año de portada (2026), no el del título.
- Las palabras clave llegan sin puntuación final.

El operador puede seguir corrigiendo cualquier campo a mano en la pantalla
por si el documento se aparta de la estructura esperada.
