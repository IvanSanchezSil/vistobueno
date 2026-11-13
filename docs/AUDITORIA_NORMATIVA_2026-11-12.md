# Auditoría normativa — manual, plantillas y reglas

Fecha: 2026-11-12. Base: `master`, `9fdfc57`. Estado: auditoría y tareas;
no se corrigió código. Complementa el [handover de correctitud](HANDOVER_CORRECTITUD_2026-11-12.md).

## Resultado

El motor no demuestra cumplimiento completo del manual. Hay falsos verdes,
falsos rojos, requisitos sin control y decisiones documentadas que se apartan
del manual. Las cinco plantillas corresponden a programas de investigación
cuantitativa. No prueban los ocho tipos del manual. Una tesis aprobada que sale
verde tampoco demuestra que se detecten sus versiones incorrectas.

Esta revisión incluye texto completo extraído del manual, tablas, ocho rúbricas,
las cinco plantillas y las dos RCU locales. Se inspeccionó XML de las plantillas
y se ejecutaron mutaciones concretas. No se hizo una inspección visual página
por página de todos los documentos. No se validó cada criterio académico ni
la vigencia legal actual de las RCU de 2022. Faltan las modificaciones posteriores
que el propio manual cita; debe ratificarlas el encargado antes de bloquear entregas.

## Fuentes y cómo localizarlas

Los archivos originales están en `recursos/`, sin versionar. No adjuntar tesis,
HAR, credenciales ni datos personales. SHA-256 identifica la versión examinada.
En el manual, `pN` es el índice **desde cero** en `Document.paragraphs` de
python-docx: solo párrafos directos del cuerpo. `aN` cuenta desde cero todos
los párrafos descendientes de `w:body`, también los de tablas, en orden XML.
No confundir estos localizadores con páginas impresas ni con índices de líneas.
Para las RCU se usa la página física del PDF desde uno.

| Fuente | SHA-256 |
|---|---|
| EDUCACION INICIAL-PLANTILLA INVESTIGACIÓN CUANTITATIVA.docx | `9cab53c0ad701009b5d99a8304c52129659fc191acf7e2ed82cf9bf95f67a1fc` |
| MANUAL REVISADO TERCERA VERSION OBSERVACIONES 11-07-2025.docx | `8ae5c5c6b1224bf76d28685cdddbfa70aafdfe0d0392f9d3a653aeca5b74a936` |
| PROGRAMA DE SEGUNDA ESPECIALIDAD EN EDUCACION TEMPRANA-PLANTILLA.docx | `a9a2bfa10289afee8c5100571a9561b1292ca9cac795ba6afd7e5274a6b304e5` |
| PROGRAMA DE SEGUNDA ESPECIALIDAD EN ESTIMULACIÓN-PLANTILLA.docx | `3e7f632725a8f379279af90bb893bd659fa76d9bcc3fb44a56a9740029ff5b3f` |
| TECNOLOGIA EDUCATIVA-ADMINISTRACION Y GERENCIA EDUCATIVA-PLANTILLA.docx | `789a10f48a84b397c6028dc1132606c4664f78340008005da4e251a304c9979f` |
| TECNOLOGIA EDUCATIVA-INFORMATICA EDUCATIVA-PLANTILLA.docx | `ccf0214948bbb68fa58cc0536f24d59a56ffb31aea5e9fcdf6a8b9898dbfedf7` |
| RCU-N-220-2022-UNT-LINEAS DE INVESTIGACION.pdf | `1666c8d2491794cdcdb24861f4d2afb41e7e4301de4c437237c446d48c4c2583` |
| RCU-N-274-2022-UNT.pdf | `7abfa5f893c0dfa0ec3e86103b9cfa2c030b16bc754aef309a97a3350954dd0d` |

El manual tiene 1.884 párrafos directos; se extrajeron 2.785 párrafos no vacíos
incluyendo tablas. Se inventariaron **226 criterios** en ocho rúbricas:
30 cuantitativo, 32 cualitativo, 18 revisión, 25 proyecto cuantitativo,
23 proyecto cualitativo, 35 informe cuantitativo, 33 informe cualitativo y 30 TSP.
Las RCU tienen 5 y 26 páginas. Sus capas de texto permiten leerlas sin OCR nuevo;
pueden conservar errores de OCR anteriores. Se comprobaron visualmente la p3
de RCU-220 y la p26 de RCU-274 para confirmar catálogo y ámbito del artículo.

## Matrices entregadas

- [66 requisitos y grupos de requisitos](MATRIZ_REQUISITOS_2026-11-12.csv).
  Separa formato, carátula, esquemas, anexos, políticas y límites.
- [226 criterios de las rúbricas](MATRIZ_RUBRICAS_2026-11-12.csv).
  Cada fila conserva el criterio completo y su localizador. Todos requieren
  revisión humana del criterio completo. Algunos permiten subcontroles mecánicos;
  una coincidencia de encabezado no acredita su calidad metodológica.
- [49 reglas activas y su fuente declarada](INVENTARIO_REGLAS_2026-11-12.csv).
  Es inventario inverso, no certificado de que las citas sean correctas.

`INCORRECTO`: contraejemplo ejecutado o requisito estructural explícito omitido.
`PARCIAL`: el control cubre solo una parte. `FALTANTE`: no se encontró control
activo completo. `CONFLICTO`: fuentes o desvíos difieren; exige decisión.
`NO_SOPORTADO_API`: la API no carga ese esquema. `POR_VERIFICAR`: hay mecanismo,
pero esta auditoría no hizo su regresión aislada. `REVISION_HUMANA`: requiere
juicio o evidencia externa. `DECIDIDO`: política confirmada por el usuario.
Ningún estado equivale a aprobación académica. Los 66 grupos no son un conteo
de todas las obligaciones atómicas: varios tienen más de una propiedad.

## Hallazgos nuevos y responsables

| ID | Prioridad | Hallazgo | Responsable / tarea |
|---|---|---|---|
| NM-01 | P1 | Paginación: decimal explícito rechazado; reinicio romano 99 y número a la izquierda aceptados | Int3 / M12, ampliar M3 |
| NM-02 | P1 | Carátula verde sin escuela y con asesor a 36 pt | Int3 / M12, ampliar M1 |
| NM-03 | P1 | Cobertura de tipos no corresponde al manual ni queda demostrada por cinco programas | Int3 / M12; Int2 comunica alcance en F3 |
| NM-04 | P2 | No hay control de longitud del título ni orden de autores; límite inferior del título requiere decisión | Int3 / M12; encargado ratifica |
| NM-05 | P2 | Referencias: mínimos por ámbito incompletos; contar párrafos no cuenta fuentes | Int3 / M12 |
| NM-06 | P2 | Anexos incompletos y contradicciones entre prosa y esquemas | Int3 / M12, ampliar M6 |
| NM-07 | P2 | Reglas de calidad presentadas con citas no localizadas en el manual | Int3 / M12, origen de reglas |
| NM-08 | Decidido | Acceso abierto fijo reproduce la instrucción del jefe, confirmada por el usuario | Int1 / B3: verificar persistencia, sin nueva selección |

Los NM no reemplazan VA ni AUD. Todos salvo NM-08 quedan pendientes. Int1
no implementa los arreglos de motor. El encargado decide diferencias normativas;
Int3 escribe sus reglas y pruebas. Int2 presenta los límites reales.

### NM-01 y NM-02: contraejemplos ejecutados

Se partió de `compilar_docx(configuracion_base())` de `tests/docx_factory.py`.
Se cargó `reglas_unt.yaml` y se llamó a `validate_docx` y `build_report`.
Cada caso parte del mismo original; no acumula cambios del caso anterior.
Son pruebas XML del motor. La limitación del paquete del factory en VA-17
sigue abierta; no se afirma que estos archivos hayan sido renderizados por Word.

| Caso | Cambio único en el paquete | Resultado actual | Lo que debe comprobarse |
|---|---|---|---|
| baseline | Ninguno | Verde | Control del experimento |
| explicit_decimal | Añadir `w:pgNumType w:fmt="decimal"` al último `sectPr` | Rojo: `numeracion_cuerpo_arabigo` | No rechazar decimal explícito por existir |
| roman_restart_99 | Poner `w:start="99"` en cada `pgNumType` preliminar | Verde | Inicio y continuidad de preliminares |
| cover_titlepg_false | Poner `w:val="0"` en `w:titlePg` | Verde | Valor booleano y pie realmente usado |
| missing_school | Eliminar el párrafo con ESCUELA PROFESIONAL | Verde | Escuela obligatoria, independiente de facultad |
| advisor_36pt | Cambiar a `w:sz w:val="72"` los runs del nombre tras Asesor | Verde | Nombre del asesor a 12 pt |
| page_number_left | Conservar párrafo derecho sin PAGE; añadir párrafo izquierdo con PAGE | Verde | Alineación del párrafo que contiene PAGE |
| authors_uppercase_manual | Convertir a mayúsculas el nombre tras Autor | Rojo: `caratula_autores_mayusculas_sin_negrita` | Desvío confirmado por el usuario: usar mixtas como la tesis aprobada por el jefe |

Para repetir, abrir el DOCX del factory como ZIP, copiar sus partes, modificar
solo el nodo descrito con lxml, reconstruir el ZIP y ejecutar el motor. Comparar
los ID fallidos, no solo el semáforo. Repetir con un fixture OPC válido cuando
Int3 entregue M11, y con documento real autorizado. Guardar pruebas con datos
ficticios en la suite de Int3. No fijar estos verdes incorrectos como golden.

### NM-03: estructura y aplicabilidad

El manual distingue TINV cuantitativo, TINV cualitativo, revisión de literatura,
proyectos cuantitativo/cualitativo, informes cuantitativo/cualitativo y TSP.
Los cinco últimos esquemas están en `reglas_unt_pendientes.yaml`; la API no los
carga. La detección y aplicación de los tres primeros no prueba soporte de ocho.

El esquema cualitativo activo omite apartados que el manual enumera: situación
problemática, enunciado, justificación, antecedentes y bases teóricas. Una lista
de encabezados tampoco acredita jerarquía, desarrollo ni correspondencia con
el índice. El motor debe informar tipo ambiguo o no soportado sin dar a entender
que su estructura fue aprobada. No activar los cinco esquemas pendientes sin
corpus real y aceptación del responsable.

### NM-04 a NM-06: contenido mecánico y revisión humana

Las rúbricas piden títulos de 15–20 palabras. La prosa de proyectos menciona
solo máximo 20: el mínimo necesita una decisión por tipo. El orden alfabético
de autores no se verifica. RCU-274 arts. 6 y 39 limita tesis/TINV a dos personas;
antes de imponerlo se debe confirmar vigencia, modalidad y modificaciones.

Los mínimos de referencias son 20/30/20 para los tres TINV. Los proyectos e
informes piden 30. TSP pide mínimo 20 en el informe y máximo 10 en su sesión
de aprendizaje: son ámbitos distintos. Contar párrafos no verifica entradas,
APA, sangría francesa ni la relación cita–referencia.

Las listas de anexos difieren en algunos puntos del propio manual. Ejemplos:
la prosa cualitativa pide reporte de similitud y su esquema no lo enumera;
proyecto cualitativo alterna categorización/consistencia; TSP difiere respecto
a autorización institucional. Revisión de literatura no tiene control propio
de anexos mínimos activo. Exigir un encabezado no acredita contenido, firma,
consentimiento, porcentaje de similitud ni autenticidad. Esos controles externos
siguen siendo humanos. No anunciar detección de IA por encontrar un título.

### NM-07: procedencia de las reglas

`track_changes_sin_resolver` atribuye al manual una oración de entrega con
cambios aceptados que no se localizó en él; su comentario reconoce ese límite.
`notas_al_pie_consistencia` cita una práctica de Word, no un mandato literal del
manual. Los IDs internos de notas no equivalen necesariamente a números visibles.
Los dos controles pueden servir como calidad técnica, pero deben identificarse
como tales y no usar una cita institucional inventada en el reporte al estudiante.
`encabezado_membrete` y `encabezado_formato` provienen de plantillas. Registrar
ese origen. Revisar también cada cita resumida: paráfrasis y cita literal son distintas.

### NM-08: acceso abierto confirmado; sin trabajo funcional nuevo

El Anexo 11 del manual permite abierto, restringido o no autorizar. El usuario
aclaró el 2026-11-12 que el jefe siempre elige abierto y pidió emularlo.
**Se conserva esa política para el piloto acordado.** No se solicita agregar
selector, autorización por ficha ni una tarea B9.

Se ejecutó `VBMapeador.construirPlan` sin metadatos de derechos y con un dato
manual ficticio restringido. Ambos planes emiten el combobox con texto
`Acceso abierto`, como está diseñado. Esa prueba acredita el plan, no que
Angular lo guarde. B3 debe comprobar el valor canónico de abierto después de
guardar y recargar. La elección fija no sustituye el documento de autorización
que el encargado revisa fuera del motor. Si cambia el flujo acordado, se vuelve
a decidir la política antes de modificar los clientes.

## Conflictos que no deben arreglarse por intuición

- Carátula general: título mixto y 14 pt; descripción de informe: mayúsculas;
  plantillas: 13 pt. Motivo: manual 13 pt y plantillas 12 pt.
- Manual: autores en mayúsculas. Plantillas y regla acordada: mixtas. El YAML
  ya registra el desvío. El usuario confirmó el 2026-11-12 que el jefe aprueba
  mixtas según la tesis buena. La decisión queda resuelta: mantener mixtas.
- Manual: año en curso. Plantillas: año de sustentación. No confundir con el
  error de capturar el año desde el título, tratado por VA-13 / PR #75.
- El manual escribe A4 como 210x297 cm: la unidad es un error de la fuente.
  Usar A4 de 210x297 mm; no crear papel de 2.10 x 2.97 m.
- RCU-274 p26 propone esquema de artículo sujeto a la revista. Su doble
  espacio no es una regla universal de tesis. Sus esquemas de proyecto no
  coinciden en todos los componentes con el manual posterior.
- El catálogo YAML tiene **50** entradas: 19 áreas estratégicas, 7 áreas
  transversales y 24 específicas, como las tablas de RCU-220. El texto antiguo
  que dice 46 debe corregirse al actualizar la documentación del motor. Esta
  cuenta no valida el selector ni la línea específica de cada documento.

## Cierre exigido

Int3 convierte cada subcontrol aceptado en pruebas que fallen antes del arreglo.
Debe completar una tabla requisito → regla → regresión → documento real → límite.
No cerrar un NM con una modificación de documentación. Los conflictos requieren
respuesta del encargado registrada con fecha. Int2 ajusta sus mensajes cuando
Int3 entregue el alcance verificado. Int1 verifica contrato y transporte de esa
información sin editar el motor. El piloto sigue bloqueado por los P1 del
handover general y por los nuevos P1 de esta revisión.

## Aclaración posterior del usuario — 2026-11-12

La persistencia Angular se ensaya en DSpace real **local**, no mediante borradores
experimentales en UNT. El [plan del laboratorio](PLAN_LAB_DSPACE_LOCAL_2026-11-12.md)
define qué capturar en otra observación y los límites de una réplica aproximada.
Mantener autores en mixtas y acceso abierto según las decisiones confirmadas.
