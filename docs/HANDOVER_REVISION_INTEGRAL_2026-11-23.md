# Handoff de revisión integral de VistoBueno

Revisión del 23 de noviembre de 2026 en `fix/api-b5-b6-ejemplos`, commit `71bdba84463c52e7507393a246458a41a03d16d3`. Este documento complementa el [handover de correctitud](HANDOVER_CORRECTITUD_2026-11-12.md). Los IDs RI identifican observaciones de esta revisión. Se conserva el ID anterior cuando ya existe.

## Prueba en DSpace institucional

**Resultado comunicado por el operador.** El flujo funcionó en la instancia institucional con una sesión autorizada. El único fallo observado fue que el selector de tipo de acceso quedó sin seleccionar la opción **Acceso abierto**.

**NM-08 sigue abierto · Int1, userscript.** El mapeador ya planifica la selección de `Acceso abierto` y la prueba con un formulario simulado verifica que el texto aparece en el campo. En la instancia institucional falta comprobar qué opción selecciona el widget y qué valor conserva el formulario al guardar y volver a abrir el ítem. La causa precisa queda por confirmar. La prueba comunicada cubre el flujo observado, sin certificar por separado VA-08, VA-20 y VA-21. [Mapeador](../tools/dspace-fill/src/mapeador.js#L209) · [Prueba local](../tools/dspace-fill/test/ejecutor.test.js#L120)

Actualización 2026-11-25: se corrigió el ejecutor para no contar como éxito la mera escritura del texto en el input; solo cuenta si el widget acepta la opción real (clic). Si la selección falla, el resumen marca el campo como pendiente y restaura el valor anterior. Pruebas locales (npm test, ensayo de ficha) en verde. Pendiente de verificación institucional: seleccionar «Acceso abierto», guardar y volver a abrir el ítem.

## Seguimiento del 25 de noviembre de 2026

Base de la verificación: `master` en `72b6a4b`, sincronizado con `origin/master` al consultar los PR. La evidencia del 23 de noviembre se conserva debajo como línea base.

| ID | Responsable | Estado actual y evidencia |
|---|---|---|
| RI-01 / VA-19 | Int1 | **Corregido y verificado en local.** PR #127 elevó el presupuesto de CPU de 2 a 5 s por ventana y alinea el mensaje con `Retry-After`. Con valores predeterminados, A → B y B → A devolvieron 200/200 sin limpiar el estado entre ambas cargas. En una ejecución aparte, la tercera carga recibió 429 con `Retry-After: 26` y el mismo tiempo en el mensaje. |
| RI-02 | Int1 | **Cerrado.** PR #127 conectó `GET /asistente/estado` y `POST /asistente/explicar`, y actualizó el README y OpenAPI. Se verificaron los contratos con stub, servicio no disponible y validación sin cambios en su veredicto. |
| RI-03 / VA-19 | Int2 | **Síntoma original resuelto.** Firefox mostró el reporte de A en 4.38 s y el de B en 3.94 s, en una misma instancia de la API. El plazo de 30 s sigue vigente. La SPA muestra el mensaje de error del servidor, que ahora incluye la espera. Sigue sin leer directamente la cabecera `Retry-After`. |
| RI-04 / VA-10, VA-21 | Int2 | **Abierto y reproducido de nuevo.** Tras recargar, un segundo reporte verde simulado con el mismo nombre de archivo recuperó el título y el autor del primer reporte. |
| RI-05 | Int2 con Int1 | **Abierto y reproducido de nuevo.** Con el plazo de autorrelleno vencido, el sondeo devuelve `expirado` pese al HTTP 200 del depósito. Con el plazo abierto y `confirmacion_vigente: false`, devuelve `recibido`. |
| RI-06 | Int2 | **Abierto.** Una nueva ejecución de `npm audit` dio 7 entradas en el frontend: 2 críticas, 2 altas y 3 moderadas. |
| RI-07 | Int3 | **Cerrado.** PR #126 acotó el XPath antes de evaluarlo. Su comparación de referencia obtuvo reportes idénticos para ambas tesis y las cinco plantillas. La API actual respondió en 3.64–3.93 s en las pruebas consecutivas y conservó A verde con 0 errores/5 avisos y B roja con 4 errores/5 avisos. |
| RI-08 | Int3 | **Fix en el PR #128, abierto al revisar.** Probé la punta `7d2e1d6` en una copia temporal: A y B conservaron sus veredictos y conteos. El PR cubre tamaño de línea, ciudad y año, y requisitos adicionales de línea y ciudad. REQ-27 sigue abierto por el significado normativo del año. |
| RI-09 | Int3 | **Cerrado.** PR #125 corrigió los ejemplos de CLI, el conteo de `reglas_activas.py`, el conteo de catálogo en la guía y el destino del enlace de Semana 12. Pasó la regresión que compara el script con el resumen del motor. |

**Otros avances.** PR #124 añadió la captura del ORCID del asesor cuando hay evidencia suficiente en la carátula. Los registros de integración cierran NM-02, NM-05 y NM-07. Quedan abiertos NM-03, NM-04 y NM-06. El ensayo local de depósito volvió a pasar. La verificación del widget Angular en DSpace institucional queda pendiente para el piloto. [Estado normativo](HANDOVER_AUDITORIA_2026-10-26.md#11-estado-de-los-hallazgos) · [Comparación del XPath](HANDOVER_MOTOR_FICHA_DEPOSITO.md#9-seguimiento-ri-07--ri-08-2026-11-24)

**Desfase de documentación tras RI-01.** El contrato de API aún indica 2.0 s de CPU por ventana para validación. El valor de `PRESUPUESTO_CPU_DEFAULT` en el código es 5.0 s. Int1 debe actualizar la tabla, la tasa descrita y los ejemplos de capacidad. El presupuesto de papeleo es independiente. [Contrato](CONTRATO_API.md#límite-de-peticiones-aud-12) · [Implementación](../validator/api.py#L363)

**Trabajo pendiente por integrante.** Int2 prioriza RI-04 y RI-05 con apoyo de Int1 para el contrato de depósito, y mantiene RI-06 en un PR aparte. Int3 integra RI-08 y documenta el criterio pendiente del año. Int1 conserva la verificación del cupo en la máquina del operador y el ensayo institucional del userscript como parte del piloto.

**Verificación local.** Pasaron 1 242 pruebas de Python en el árbol de trabajo, que incluía una prueba local de cupo con las tesis reales. Pasaron también Ruff y mypy en código y scripts, la comprobación de OpenAPI y el ensayo de depósito con mock. En la copia temporal del PR #128 pasaron las 11 pruebas específicas de tamaño, letras mixtas y centrado. La IA se verificó con stub y sin servicio configurado. No se ejecutaron Ollama real ni DSpace institucional.

## Línea base del 23 de noviembre

La API distinguió las dos versiones de la tesis. La versión aprobada obtuvo verde en 44.26 s. Firefox mostró un error de tiempo a los 30.2 s con esa misma versión. Después de una validación de la versión no aprobada, la siguiente carga recibió HTTP 429 con una espera de 196 s. Los dos síntomas hacen que el flujo diario falle aunque el semáforo del motor sea correcto.

## Resultados del corpus

**A** es la copia aprobada (con `(1)`). **B** es la copia no aprobada. Se usaron los originales locales. Aquí solo se publican conteos, IDs de reglas y diagnósticos de formato.

| Entrada | HTTP / semáforo | Evaluadas / total | Errores | Advertencias | Ficha |
|---|---|---:|---:|---:|---|
| A | 200 / verde | 42 / 54 | 0 | 5 | Disponible |
| B | 200 / rojo | 42 / 54 | 4 | 5 | Ausente |
| Plantilla Educación Inicial | 200 / rojo | 40 / 54 | 2 | 9 | Ausente |
| Cuatro plantillas de Segunda Especialidad y Tecnología Educativa | 200 / rojo en cada una | 40 / 54 | 4 cada una | 9 cada una | Ausente |

Se midieron A y B con un cliente ASGI local. Una segunda medición de B con el límite por cantidad dio 44.29 s. B también dio 200/rojo en un proceso con el cupo predeterminado y sin deuda previa, en 44.46 s. Se usó el límite por cantidad para completar el lote de plantillas. El ensayo en Firefox usó el build de producción, Uvicorn y el formulario real de carga.

- B tiene ocho runs de 11 pt en el cuerpo, cinco párrafos con interlineado de 276 en vez de 360, dos párrafos sin justificación efectiva y tres títulos de metodología que el motor no reconoce. Los IDs son `tamano_cuerpo`, `interlineado`, `alineacion_cuerpo` y `estructura_tinv_cuantitativo`.
- A y B comparten cinco advertencias. Son tamaño del título, tamaño de la línea de grado, tamaño del logo, sangría y anexos mínimos. Los cinco avisos son compatibles con la aprobación observada de A. En sangría, el motor encontró 4 valores fuera de tolerancia en A y 16 en B.
- En A se detectaron los siete campos de captura. La ficha trajo dos autores, asesora, año, escuela, título, resumen y tres palabras clave. La prueba no verificó identidad ni completó los campos manuales.
- Todas las plantillas fallaron por título de relleno con negrita mixta y palabras clave. Las cuatro de especialidad también fallaron las dos reglas de facultad/escuela. El test actual fija esas diferencias y nueve avisos por plantilla. La advertencia adicional respecto de la medición histórica corresponde al ORCID de relleno. Véase [el test del corpus](../tests/test_tipo_documento.py#L522).
- La CLI con el YAML histórico dio rojo para las dos versiones. A obtuvo 6 errores y 3 advertencias, B obtuvo 7 errores y 3 advertencias. La CLI con el DSL de producción dio verde para A. Véase RI-09.

## Integrante 1 · API, operación y userscript

### RI-01 / VA-19 · P1 · El cupo bloquea la carga siguiente durante varios minutos

**Reproducido.** En el mismo proceso y con el cupo predeterminado, enviar B desde loopback y, al completar, enviar A de inmediato. B devolvió 200 en 44.46 s. A devolvió 429 en aproximadamente 0.01 s con `Retry-After: 196`. El cuerpo pedía esperar «unos segundos». En otro lote, una ejecución previa de A también dejó las cargas siguientes bloqueadas. [Limitador](../validator/api.py#L396) · [Dependencia de validación](../validator/api.py#L642) · [Contrato](CONTRATO_API.md#límite-de-peticiones-aud-12)

**Cierre.** Medir CPU de hilo y latencia en la máquina del operador antes y después de RI-07. Acordar una política que permita dos tesis normales seguidas y conserve el límite para ráfagas. Probar ambos órdenes sin limpiar el estado del proceso. Verificar que `Retry-After` y el mensaje indiquen una espera coherente. Int2 usa ese dato en RI-03.

### RI-02 · P2 · La guía activa anuncia rutas de IA ausentes

**Verificado.** La arquitectura de `AGENTS.md` presenta `GET /asistente/estado` y `POST /asistente/explicar` como rutas de la API. El OpenAPI servido por Uvicorn enumera ocho rutas y no contiene ninguna de IA. El README sí indica que falta conectarlas. `OLLAMA_URL` por sí solo no hace accesible el asistente desde la web. [Guía](../AGENTS.md#L120) · [README](../README.md#L542) · [Handoff de IA](HANDOVER_API_IA.md)

**Cierre.** Alinear arquitectura, configuración y estado de entrega. Identificar los módulos disponibles en Python y marcar las rutas y controles de interfaz como pendientes. Cualquier cambio a `AGENTS.md` requiere la aprobación prevista en la guía.

**Pruebas de depósito pendientes.** El ensayo local confirmó dos autores, alineación de DNI, relleno en otra página, conservación de edición, handle, constancia y registro. VA-08, VA-20 y VA-21 conservan la prueba pendiente contra el widget Angular y el navegador del operador. El ensayo usa el mock y jsdom. Véase [el handover del userscript](HANDOVER_USERSCRIPT_DSPACE_2026-11-16.md).

## Integrante 2 · Interfaz y experiencia de operación

### RI-03 / VA-19 · P1 · La pantalla pierde el resultado de una tesis válida

**Reproducido en Firefox 153.7.0.** Cargar A en la SPA de producción. A los 30.2 s, la pantalla mostró «El servidor tardó demasiado». La API pudo terminar A en 44.26 s mediante el cliente local. El temporizador de la SPA tiene un límite fijo de 30 s. La rama de errores HTTP tampoco lee `Retry-After` para explicar el 429 de RI-01. [Carga](../frontend/src/components/Upload.jsx#L195)

**Cierre.** Coordinar RI-01 y RI-07. Hacer que las dos cargas lleguen a su reporte con el plazo acordado. Probar respuesta lenta, aborto real, error de red, 429 y reintento permitido. Mostrar la espera que indique la API. Mantener el manejo de un servicio caído.

### RI-04 / VA-10, VA-21 · P1 · El borrador se recupera por nombre de archivo

**Reproducido en Firefox con respuestas sintéticas.** Abrir la ficha de un reporte verde, recargar la página y abrir la ficha de otro reporte verde con el mismo `archivo_nombre` y otro título y autor. La segunda ficha mostró el título y el autor del primer reporte. La única clave de identidad es `metadatos.archivo_nombre` y el borrador guarda toda la ficha en `localStorage`, incluidas las listas de DNI y matrícula. A y B tienen nombres distintos en disco y B no genera ficha. [Persistencia de la ficha](../frontend/src/components/FichaDeposito.jsx#L25)

**Cierre.** Usar identidad de contenido o de validación, con caducidad y restauración explícita. Probar dos DOCX verdes con igual nombre y contenido distinto, recarga de la misma tesis y salida del trámite. Definir el tratamiento de borradores guardados por versiones anteriores.

### RI-05 · P1 · La SPA confunde caducidad de autorrelleno con caducidad del trámite

**Reproducido en la función de sondeo.** La API devuelve `vence_en = autofill_hasta` y un `retenido_hasta` independiente. La SPA usa `vence_en` para decidir cuándo descartar el trámite. Con un depósito HTTP 200 válido y `venceEn` ya vencido, `interpretarSondeo` devuelve `expirado` antes de leer la confirmación. Con plazo vigente, también da `recibido` a un depósito con `confirmacion_vigente: false`. Al pedir el papeleo en ese estado, la API comprueba la revisión y devuelve 409. [Consumidor](../frontend/src/ficha.js#L144) · [Ventanas del servidor](../validator/api.py#L1368) · [Guardia de papeleo](../validator/api.py#L1652)

**Cierre.** Usar el plazo de retención para esperar la confirmación y el de autorrelleno para el aviso correspondiente. Reconocer confirmaciones de revisiones anteriores, recuperar el estado por `GET /tramite` y guiar la reconfirmación. Probar una confirmación posterior al fin de autorrelleno pero dentro de retención, una revisión conciliada y el vencimiento definitivo. Coordina Int1.

### RI-06 · P2 · El lockfile del frontend acumula avisos de dependencias

**Confirmado por el registro de npm.** `npm audit --json` contó 7 entradas de paquetes en el frontend (2 críticas, 2 altas y 3 moderadas). Las directas son `vite` y `vitest`. Las restantes son transitivas de herramientas de desarrollo y prueba. El lockfile del userscript dio 0. Los recuentos describen el árbol instalado y cambian con el registro. No se comprobó exposición de la SPA publicada.

**Cierre.** Revisar los avisos del lockfile y actualizar las herramientas en un PR aislado. Verificar `npm ci`, `npm audit`, build, lint, Vitest y API con la SPA empaquetada. Coordinar el cambio de versión mayor con quien mantiene el entorno de CI.

## Integrante 3 · Motor, reglas y evidencia normativa

### RI-07 · P1 · XPath de autores recorre el documento completo antes de acotar la carátula

**Reproducido.** Al medir cada regla en B, `caratula_autores_tamano` tomó 14.33 s y `ficha_autores` 26.41 s. Juntas consumieron 40.74 de 44.29 s de tiempo de pared, cerca del 92 %. Las consultas combinan `following-sibling::` y `preceding-sibling::` con normalización de texto. `ExtractedDocx.xpath` ejecuta la consulta sobre el árbol entero y aplica el filtro `caratula` después. Las plantillas pequeñas tardaron entre 0.20 y 0.35 s. [Selector de formato](../reglas_unt.yaml#L321) · [Selector de captura](../reglas_ficha.yaml#L39) · [Filtro tardío](../validator/extractor.py#L981)

**Cierre.** Acotar primero los párrafos de carátula y seleccionar el bloque de autores sin reevaluar los hermanos previos de cada párrafo del cuerpo. Preservar orden, autor múltiple, cortes por asesor y línea, y separación de ORCID del nombre. Añadir una regresión sintética larga y medir A, B y cinco plantillas antes y después. Conservar semáforo, advertencias y capturas. Int1 e Int2 repiten RI-01 y RI-03 después del cambio.

### RI-08 · P2 · La regla de tamaño promete comprobar bloques que omite

**Reproducido con el factory.** En `configuracion_base()`, fijar `portada.ciudad.sz = 72` y `portada.linea.sz = 72` (36 pt). Compilar y validar con `reglas_unt.yaml`. El semáforo queda verde y `caratula_autores_tamano` responde `cumple`. Su descripción incluye línea de investigación, ciudad y año. Los selectores vigentes cubren autores y asesor. [Regla](../reglas_unt.yaml#L321) · [Factory](../tests/_docx_builder.py#L393)

**Cierre.** Cotejar alcance, fuente y severidad con el manual. Probar el tamaño de línea y el bloque de ciudad/año por separado, con estilo directo y heredado. Si la regla debe cubrir un alcance menor, ajustar descripción y matriz normativa.

### RI-09 · P2 · Los comandos y los conteos de apoyo inducen a un diagnóstico distinto

- El ejemplo principal de la CLI en el README usa el esquema histórico. Con ese comando, A sale rojo, mientras la API y el DSL vigente dan verde. Hacer de `reglas_unt.yaml` el ejemplo principal para reproducir la API. Mantener el histórico etiquetado como tal. [Ejemplos](../README.md#L214)
- `scripts/reglas_activas.py` cuenta `len(resultados)` como evaluadas y todo `passed=True` como aprobado. Con el DOCX sintético del ensayo S7 imprimió 55 «evaluadas» y 22 «aprobadas». Para esa misma entrada la CLI dio 38 evaluadas, 17 no aplicables, 25 errores y 8 advertencias. Quedaron 5 evaluadas que pasaron. Reusar el resumen del motor y distinguir las no aplicables. [Script](../scripts/reglas_activas.py#L39)
- El bloque activo de `AGENTS.md` cita 50 reglas y no recoge varios cierres del handover. Hay 54 reglas de catálogo en esta revisión. En el ensayo S7 el resultado llegó a 55 por la fila centinela de tipo. El handover previo mezcla mediciones de 49, 50 y 54. Etiquetar cifras por revisión, separar catálogo de resultado y enlazar la tabla vigente. Corregir también el enlace a `PLAN_SEMANA12_MOTOR_CORRECTITUD.md`, cuyo destino no existe. [Guía](../AGENTS.md#L412) · [Bitácora](semana12_trabajo_ivanSanchezSil.md#L10) · [Handoff anterior](HANDOVER_AUDITORIA_2026-10-26.md)

**Cobertura normativa pendiente.** Conservar NM-03 a NM-07 en el handover de correctitud. Las cinco plantillas y las dos versiones de una tesis aportan evidencia cuantitativa. Los demás tipos de documento requieren ejemplos y las decisiones normativas registradas. Verde confirma el conjunto de reglas aplicadas a ese archivo.

## Verificaciones y orden de trabajo registrados el 23 de noviembre

| Verificación | Resultado |
|---|---|
| Suite Python local con recursos y SPA compilada | 1 170 pasaron. Un aviso de deprecación de Starlette TestClient |
| Ruff lint y formato, mypy | Correctos. 90 archivos formateados y 34 fuentes revisadas por mypy |
| OpenAPI generado y escáner de secretos | OpenAPI sincronizado. El escaneo terminó correctamente |
| `nix flake check` en x86_64-linux | Correcto. Nix reutilizó outputs locales |
| Frontend: `npm ci`, build, ESLint, Vitest | Correctos. 84 tests |
| API sirviendo el build de la SPA | 3 tests pasaron |
| Userscript: `npm ci`, `npm test`, drift del archivo distribuido | 85 tests pasaron. Sin cambios en el archivo distribuido |
| `nix run .#test-local` | Correcto. Usa API y proxy locales con DOCX sintético |
| `nix run .#test-ficha-deposito` | Correcto en puertos alternos. Confirmación y descargas verificadas en mock/jsdom |
| Firefox con build de producción | Error de tiempo reproducido con A a los 30.2 s. Restauración cruzada reproducida con dos respuestas sintéticas |
| Auditoría de lockfiles en npm | Frontend 7 entradas. Userscript 0 |

1. **Int3** corrige RI-07 y registra una medición de regresión con el corpus. Puede desarrollar RI-08 en paralelo con un fixture pequeño.
2. **Int1 e Int2** validan juntos RI-01 y RI-03 con dos cargas reales consecutivas, en ambos órdenes. Registran latencia, estado del navegador, HTTP y `Retry-After`. Usan los valores predeterminados en esta verificación.
3. **Int2 con Int1** cierra RI-04 y RI-05. Repite el flujo con dos borradores de igual nombre, expiración de autorrelleno y reconfirmación tras conciliación.
4. **Cada integrante** actualiza su documentación y el estado del handover anterior cuando exista evidencia de cierre. Mantener la prueba institucional del widget Angular dentro del piloto autorizado.

La revisión ejecutó la SPA en Firefox y los dos ensayos locales. Quedaron fuera de la ejecución DSpace institucional, Word, SMTP externo, Ollama real y las arquitecturas distintas de x86_64-linux. No se publicó ni se envió ningún documento.
