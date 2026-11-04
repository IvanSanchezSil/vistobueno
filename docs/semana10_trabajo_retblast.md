# Bitácora Semana 10 — retblast

- **Integrante**: retblast (Integrante 1 — Backend / API)
- **Semana**: 10
- **Fechas**: 2026-11-01 → 2026-11-07 (semana en curso)
- **Rol**: Backend / API (FastAPI, contrato de la API, buzón de ficha,
  constancias y registro, escáner de secretos)
- **Ramas**: `fix/api-hardening-b0-b1` (25 commits sobre `master`; PR #71
  mergeado el 2026-11-03) y `docs/registro-documentos-sede` (cierre de la
  Actividad 14). El 2026-11-01 el trabajo siguió en la primera rama.

---

## Objetivos de la semana

1. **Actividad 14 — material de demostración**: dejar un par de documentos
   de ejemplo reproducible (uno conforme, otro no) con sus respuestas de
   `POST /validar`, una guía de lectura y la propuesta de estructura para
   registrar los documentos aportados por la sede.
2. **Informe de Avance de la semana 10**: dejar el informe en el formato
   que exige la guía de la asignatura (APA 7, carátula institucional) y
   el Portafolio Digital de Evidencias listo para subir.
3. **Cerrar la entrega del ciclo**: subir el portafolio, el plan v10 y el
   informe, y dejar la pila de commits de la rama lista para su PR.

---

## Actividades realizadas

### 2026-11-01 — Par de ejemplo de la actividad 14 (rama `fix/api-hardening-b0-b1`)

Segundo commit de la actividad 14. El primero (`7d7a26c`) agregó el
generador `scripts/ejemplo_bueno_malo.py`; este (`7c338c9`) agrega el par
de documentos y sus respuestas.

- **Generador reproducible**: `scripts/ejemplo_bueno_malo.py` construye los
  dos DOCX con la misma fábrica determinista que usa la suite de pruebas
  (`tests/docx_factory.py`). No hay datos de personas ni tesis reales: el
  par es sintético y se regenera en cualquier máquina.
- **`docs/ejemplos/doc_bueno.docx`**: cumple el formato institucional.
  `POST /validar` devuelve semáforo **verde**, 0 fallos.
- **`docs/ejemplos/doc_malo.docx`**: incumple varias reglas. `POST /validar`
  devuelve semáforo **rojo**, 4 errores y 1 warning.
- **Las dos respuestas** quedan versionadas tal cual (`respuesta_doc_bueno.json`,
  `respuesta_doc_malo.json`): son la evidencia del resultado esperado de
  cada documento.
- **`docs/ejemplos/GUIA_EJEMPLOS.md`**: explica qué se revisó en cada
  documento y qué resultado produce. Es la guía que acompaña al material
  en el portafolio (`semana 10/GUIA_EJEMPLOS.pdf`).

El par quedó en `master` con el PR #71 (mergeado el 2026-11-03). La segunda
parte de la actividad —el registro de los documentos aportados por la sede—
se cerró el 2026-11-04 con la propuesta de estructura (ver abajo); el
llenado real depende de los documentos que entregue la sede.

### 2026-11-01 — Informe de Avance y Portafolio Digital de Evidencias

- **Informe de Avance** (`Informe_Avance_S10_VistoBueno.md`, en la carpeta
  de la asignatura): 19 actividades, 16 narrativas (14 discretas y 2
  cargas transversales), 50 PRs mergeados y 696 pruebas. En ese informe, la
  actividad 14 figura como **en ejecución** desde el 01/11, con el par de
  ejemplo como evidencia parcial; el 2026-11-04 se cerró con la propuesta de
  estructura.
- **DOCX final con formato APA 7**: `generar_informe_docx.py` convierte el
  Markdown en un DOCX con carátula institucional, Times New Roman 12,
  interlineado doble, sangría de 1,25 cm, número de página arriba a la
  derecha, tablas sin bordes verticales y referencias con sangría
  francesa. El generador reemplaza al prompt externo: el contenido
  sigue teniendo una sola fuente de verdad (el Markdown) y el formato
  deja de depender de un copiado manual.
- **Correcciones de maquetación**: la nota de la Tabla 3 quedaba sola en
  una página (huérfana) y algunas filas de la Tabla 5 se partían entre
  dos páginas. Se corrigió con `keep_with_next` en el encabezado, el
  título y la última fila de cada tabla, `cantSplit` en las filas y un
  párrafo separador de 6 pt. El DOCX quedó en 43 páginas, sin páginas
  huérfanas y con las 19 filas de la Tabla 5 completas.
- **Portafolio Digital de Evidencias**: 209 archivos (14 MB), semanas 2 a
  10, con el índice de 7 páginas que mapea cada actividad con su
  evidencia. El escaneo de secretos da limpio.

---

### 2026-11-02 — Revisión del PR #71 y sus correcciones

El PR #71 recibió una revisión con 3 hallazgos bloqueantes, 5 medios y 3
bajos, más correcciones de documentación. Todo quedó corregido en seis
commits atómicos:

- `87778ab` — **cupos por CPU real**: el cupo adaptativo medía latencia
  (`perf_counter`) en vez de consumo de CPU. Con peticiones concurrentes la
  deuda se inflaba ~18× y bloqueaba la API con `429` espurios. Ahora se
  mide `time.thread_time()` dentro del hilo que valida y el papeleo se
  despacha al threadpool. Además: el modo legacy (`VISTOBUENO_RATE_LIMIT_MAX`)
  ya no cobra deuda de CPU, la ventana del entorno rige en los dos modos y
  el papeleo tiene salida de emergencia (`VISTOBUENO_RATE_LIMIT_PAPELES_CPU_SEG`,
  con `0` para desactivarlo).
- `87778ab` — **acceso remoto**: `VISTOBUENO_HOSTS` normaliza el puerto de
  cada entrada, y el peer remoto necesita **token y Host permitido**: la
  documentación prometía un `200` que nunca llegaba.
- `97081f6` — **userscript**: el botón "+" de Angular renderiza de forma
  asíncrona y el ejecutor lo contaba en el mismo tick (el segundo autor
  quedaba duplicado y vacío). Ahora espera el crecimiento de las filas. El
  re-llenado ya no pisa la edición del operador ni borra el timestamp del
  clic en Depositar, y el script sube a `@version 1.1.0` con
  `@updateURL`/`@downloadURL`.
- `97081f6` — **mock de DSpace**: el mock tenía un DOM propio que no
  ejercitaba el camino de las filas repetidas. Ahora replica la estructura
  real (`#N_array` + `ds-form-add-more`, verificada contra la captura
  oficial) y el ensayo general cubre una ficha con **dos autores**.
- `7eff923`, `320402b` — **escáner de secretos**: deja pasar valores
  formados solo por puntuación (`"..."`), expresiones que esconden un
  literal (`self.password+"extra"`) y el valor por defecto de una lectura
  del entorno (`os.environ.get("X", "secreto")`).
- `3cfd57d` y el commit siguiente — **corrección de documentación**: los
  comandos de `uvicorn` en `AGENTS.md` ahora llevan `--no-proxy-headers`
  (sin él, un `X-Forwarded-For` puede falsificar el peer y saltar el
  control de loopback). El cambio se hizo con la aprobación del
  responsable del repositorio, como exige la cláusula de `AGENTS.md`.

Al cierre del PR #71 la suite quedó con **730 tests recolectados**: en el
CI, donde `recursos/` no está, 721 pasan, 3 se omiten porque las plantillas
oficiales no se versionan y 6 quedan como `xfail(strict=True)`. Los 32
tests de node del userscript pasan, el ensayo general
`nix run .#test-ficha-deposito` pasa (incluye el flujo con dos autores) y el
CI del PR #71 queda en verde.

### 2026-11-04 — Cierre de la actividad 14 con la propuesta de registro

La actividad 14 pide una **propuesta de estructura** para registrar los
documentos que aporte la sede, no el registro lleno. Se agregó
`docs/REGISTRO_DOCUMENTOS_SEDE.md` con:

- campos de recepción, validación, devolución y cierre;
- la regla de privacidad: códigos, sin datos personales y carpeta local
  fuera del repositorio;
- el flujo de seis pasos y los estados permitidos;
- el criterio de cierre de la actividad y las preguntas abiertas.

El registro lleno se hará en el piloto (Actividad 16), cuando la sede
entregue los documentos. El archivo versionado es una plantilla y no
contiene datos de personas.

### 2026-11-04 — Verificación del frontend (actividad 15)

Lote 3 del plan previo al piloto (`docs/PLAN_LOTES_PRE_PILOTO.md`). La
pantalla de ficha de depósito se verificó contra la API real.

**Qué se comprobó:** los diez pasos del checklist —subir el documento
conforme, confirmar el semáforo verde, editar los datos extraídos,
completar los del operador, publicar en el buzón, confirmar el panel de
espera, aceptar el handle, descargar la constancia y la fila del registro,
comprobar la cabecera de token y limpiar el resguardo del navegador—. La
constancia sale del Modelo B oficial con los MERGEFIELD ya reemplazados
(137 KB) y la fila del registro responde en `tsv`, `csv`, `xlsx` y `json`.

**Hueco encontrado y cerrado:** la pantalla **no tenía ninguna prueba de
componente**; solo existían tests de las funciones puras de `ficha.js`. Se
agregó `frontend/src/components/FichaDeposito.test.jsx` con 8 casos que
montan la pantalla y recorren el flujo completo. Los casos se validaron con
mutaciones: sin publicar la ficha, o sin cotejar el título antes de usar el
handle, el test falla.

**Desfase encontrado y cerrado:** las respuestas versionadas del par de
ejemplo quedaron con el formato de detalle anterior al PR #78 (AUD-03):
5 reglas y sus prompts de IA seguían desfasados. Se regeneraron con
`scripts/ejemplo_bueno_malo.py` y se agregó
`tests/test_ejemplos_versionados.py`, que compara las respuestas versionadas
con las del motor para que el desfase no vuelva a colarse.

El detalle completo está en `docs/HANDOVER_FRONTEND_FICHA_DEPOSITO.md` §8.

---

### 2026-11-04 — Kit del piloto (lote 4)

Lote 4 del plan previo al piloto (`docs/PLAN_LOTES_PRE_PILOTO.md`). Se
escribió el kit que va a seguir el operador de la biblioteca en la
primera sesión con la instancia real de DSpace:
`docs/PILOTO_OPERADOR.md`.

**Qué lleva:** propósito y alcance; roles (operador, Integrante 1 y
contacto de la sede); estado de la entrega; nueve precondiciones con su
comprobación; el checklist de ejecución de once pasos, cada uno con su
esperado objetivo; las limitaciones que el operador va a ver (AUD-24 a
AUD-27, el prefijo de `dc.title` y el `palabras_clave_minimo`); una tabla
de hallazgos para llenar durante la sesión; las reglas de datos
personales y datos locales; la reversión; y el cierre de la sesión.

**Borrador de coordinación:** va en el Anexo B. Es neutral y trae
marcadores entre corchetes (`[FECHA]`, `[HORA]`, `[LUGAR]`,
`[NOMBRE]`). Lo revisa y lo envía el contacto de la sede; el equipo no
envía nada en su nombre.

**Decisión de diseño:** las precondiciones van en una sección aparte, antes
del checklist. Varias solo se pueden comprobar con la API levantada
(`/docs` en 200, un `Host` ajeno en 400, la plantilla del Modelo B
presente, `VISTOBUENO_FIRMA` definida), y mezclarlas con los pasos de
ejecución las convertía en pasos sin criterio de falla.

---

## Evidencias producidas

| Evidencia | Dónde |
|-----------|-------|
| Par de ejemplo (documentos) | `docs/ejemplos/doc_bueno.docx`, `docs/ejemplos/doc_malo.docx` |
| Respuestas del validador | `docs/ejemplos/respuesta_doc_bueno.json`, `docs/ejemplos/respuesta_doc_malo.json` |
| Guía de lectura del par | `docs/ejemplos/GUIA_EJEMPLOS.md` |
| Propuesta de registro de documentos de la sede | `docs/REGISTRO_DOCUMENTOS_SEDE.md` |
| Generador del par | `scripts/ejemplo_bueno_malo.py` |
| Plan de lotes previos al piloto | `docs/PLAN_LOTES_PRE_PILOTO.md` |
| Verificación de la Actividad 15 | `docs/HANDOVER_FRONTEND_FICHA_DEPOSITO.md` §8 |
| Guía de ejemplos en el portafolio | `semana 10/GUIA_EJEMPLOS.pdf` (carpeta de la asignatura) |
| Bitácora | este archivo |

- Commits de la semana: `7d7a26c` (generador del par de ejemplo),
  `7c338c9` (par de documentos, respuestas y guía), `87778ab`,
  `97081f6`, `7eff923` y `320402b` (correcciones de la revisión del
  PR #71), `931644e` y `707dc6f` (sincronización de documentación, PR #76).
- Cierre de la Actividad 14: `d06284f` en la rama
  `docs/registro-documentos-sede` (propuesta de registro), mergeado con el
  PR #77.
- Verificación de la Actividad 15: rama `feature/act15-verificacion-frontend`
  (pruebas de componente de la pantalla de ficha, regeneración de las
  respuestas de ejemplo y su test de guarda).
- Suite actual: **742 tests recolectados**: 736 pasan y **6 quedan como
  `xfail(strict=True)`** (los criterios de aceptación de AUD-24 a AUD-27 del
  motor). Los 3 tests que dependen de `recursos/` se omiten cuando esa
  carpeta no está disponible, como pasa en el CI.
- Frontend: **76 tests** en 9 archivos de prueba (`vitest` + `jsdom`).

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: la reproducibilidad del par de ejemplo
  se resolvió con un generador determinista en lugar de archivos
  editados a mano; el par se puede regenerar y volver a verificar.
- **Estructura de Datos**: el par expone la estructura de la respuesta de
  la API (semáforo, resumen y resultados) y su correspondencia con el
  contrato vigente v1.12.0.
- **Redes de Computadoras I**: las dos respuestas son el registro de dos
  llamadas reales a `POST /validar` con `multipart/form-data`.
- **Ingeniería de Software I**: el informe de avance y el portafolio
  traducen el estado técnico a un documento académico con formato APA 7.

---

## Dificultades y aprendizajes

- **Un prompt externo no es un proceso reproducible**: el DOCX del informe
  se armaba a mano con una herramienta externa. El generador en el repo
  deja la fuente de verdad en un solo archivo (el Markdown) y hace el
  formato verificable: cualquier cambio del contenido se refleja con un
  comando.
- **Una maquetación se rompe por milímetros, no por párrafos**: la nota de
  la Tabla 3 quedó sola en la página siguiente por un párrafo separador
  demasiado alto. La corrección fue de espacios, no de contenido.
- **Verificar por coordenadas en vez de por imágenes**: la revisión de las
  43 páginas por texto y coordenadas de bloque detectó los problemas de
  paginación sin revisar 43 imágenes una por una.
- **Lo que un ejemplo no cubre**: el par demuestra el validador, no la
  integración con DSpace ni con el correo institucional. Esa parte sigue
  dependiendo de las credenciales de la sede.

---

## Plan de la semana siguiente

1. Verificar el CI de `master` después del merge del PR #71 (2026-11-03).
2. Reflejar el cierre de la actividad 14 —propuesta de estructura en
   `docs/REGISTRO_DOCUMENTOS_SEDE.md`— en el informe de avance y el
   portafolio; el registro lleno se hace en el piloto.
3. Verificar los `XPASS` de los `xfail` cuando Int3 corrija AUD-24 a
   AUD-27 y quitar las marcas.
4. Coordinar con Int2 el ajuste de la pantalla de ficha a los criterios de
   Int3 para AUD-24 a AUD-27. El token compartido (`X-VistoBueno-Token`)
   ya está implementado (`cda3d56`).
5. Cerrar el resto de la auditoría cuando Int3 entregue su parte: recién
   entonces se borra el bloque de aviso de `AGENTS.md` y se deja la línea
   en `docs/cronologia_trabajo.md`. Int2 ya cerró AUD-16 a AUD-18 con el
   PR #68.
6. Cerrar con el equipo las 6 decisiones de dominio abiertas (§8 del
   handover; AUD-18 ya está decidida).
