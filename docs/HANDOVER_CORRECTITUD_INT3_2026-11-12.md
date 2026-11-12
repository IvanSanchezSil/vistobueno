# Handover Integrante 3 — motor — 2026-11-12

**Estado:** tareas pendientes. Implementar solo los archivos asignados a este integrante.
Ver [índice y estado común](HANDOVER_CORRECTITUD_2026-11-12.md).
Las dependencias de [Int1](HANDOVER_CORRECTITUD_INT1_2026-11-12.md),
[Int2](HANDOVER_CORRECTITUD_INT2_2026-11-12.md) e
[Int3](HANDOVER_CORRECTITUD_INT3_2026-11-12.md) no autorizan a editar sus archivos.

## 1. Tareas propias

### M0. Terminar la integración de PR #75 — VA-13 / AUD-24 a AUD-27

**Archivos:** los del PR #75 y su documentación.

- Consulta 2026-11-12: abierto, head `8c0a6c8`, checks verdes, conflictos.
  PR #73 ya está mergeado. El autor de #75 resuelve su integración.
- Conservar las correcciones actuales de índice/anexos. No reemplazar archivos
  enteros de `master` con versiones antiguas de la rama.
- Evidencia: rama exacta, 823 passed / 4 skipped; código funcional aplicado a
  la base auditada, 842 passed / 4 skipped. Esos conteos son evidencia histórica.
- **Aceptación:** ambas tesis capturan dos autoras completas, asesora, año 2026,
  resumen y palabras clave limpias. Comprobar también las cinco plantillas.
  Quitar xfail solo cuando el caso pase. Cierre tras integración, no por el body.

### M1a. Validar la entrada del extractor — VA-11

**Archivos:** `validator/extractor.py`, `tests/test_extractor_edgecases.py`.

- Definir una excepción de documento inválido para B5. Validar XML, raíz,
  namespace y cuerpo. Documentar qué partes OPC mínimas admite el motor.
- Conservar límites de descompresión y pruebas contra ZIP hostil. No usar un
  `except Exception` que convierta defectos del servidor en entradas inválidas.
- **Aceptación:** XML truncado, raíz ajena y cuerpo ausente fallan de forma
  controlada; documentos admitidos y fixtures válidos siguen extrayéndose.

### M1. Resolver formato efectivo y revisar todo el texto — VA-01, VA-02

**Archivos:** `extractor.py`, `analizadores.py`, `reglas_unt.yaml`, tests/factory.

- Leer `styles.xml`, `docDefaults`, estilos de párrafo/carácter, `basedOn` y
  propiedades directas. Definir precedencia y detectar ciclos sin bloquearse.
- Evaluar cada run con texto, incluidos hipervínculos. No usar solo `w:r[1]`.
  No seleccionar solo párrafos que ya declaran `w:jc` o `w:spacing`.
- Seleccionar primero los párrafos/runs sujetos a la regla; resolver después
  el valor efectivo. No ignorar una propiedad ausente ni suponer que cumple.
- Declarar límites para numeración, formato condicional, temas u otras fuentes
  que no se resuelvan. No prometer soporte completo por leer `basedOn`.
- Conservar exclusiones de dominio acordadas. La asignación de Heading1 no
  puede eximir texto arbitrario sin un alcance de títulos declarado y probado.
- **Aceptación:** primer run vacío; segundo run Arial 36 pt; estilo incorrecto;
  formato directo y heredado equivalentes; propiedades ausentes; estilo de
  carácter; hipervínculo; cadena de estilos; ciclo; párrafo con estilo de título.
  Una infracción local se detecta sin rechazar el documento equivalente correcto.

### M2. A4 en todas las secciones aplicables — VA-03

**Archivos:** `reglas_unt.yaml`, `analizadores.py`, pruebas de secciones.
No cambiar globalmente la semántica de `eq`: otras reglas la usan.
Comparar todas las secciones sujetas a A4 y normalizar orientación.
**Aceptación:** portada A4 + cuerpo Letter falla; A4 horizontal legítimo pasa;
señalar la sección culpable. Documentar el alcance de anexos y carátula.

### M3. Corregir paginación y su grado de certeza — VA-04

**Archivos:** `_paginacion_para` en `extractor.py`, analizador de paginación,
`tests/test_f2_paginacion.py`, documentación de la ubicación por página.

- Procesar saltos por orden y valor. `pageBreakBefore` afecta al propio párrafo;
  `w:val="0"` no crea salto. Contar varios saltos dentro del mismo párrafo.
- Corregir la prueba existente que espera el párrafo anterior para break-before.
- Distinguir página desconocida/estimada de página comprobada. No inventar
  precisión si faltan marcadores o dependen de render/caché de Word.
- **Aceptación mínima:** `[1,2]` con break-before en el segundo párrafo;
  `[1,3]` con dos saltos en el primero; `[1,1]` con break-before desactivado.
  Probar saltos de sección, marcadores ausentes y párrafo que cruza página.

### M4. Detectar declaraciones múltiples — VA-05

**Archivos:** `DeteccionTipo._tipo_declarado`, pruebas de tipo de documento.
Recoger todas las casillas marcadas antes de decidir. Dos tipos diferentes
producen contradicción; repetir el mismo tipo no cambia la decisión.
**Aceptación:** cuantitativo + cualitativo marcados no dan verde; invertir el
orden conserva el resultado; comprobar casillas en párrafos, tablas y controles.

### M5. Resumen, Abstract y palabras clave — VA-06, VA-07

**Archivos:** `reglas_unt.yaml`, analizadores de cantidad/sección, tests/factory.

- Leer el manual local. Resumen: 159–220 palabras; palabras clave: 3–5.
  Separar prosa y etiquetas antes del conteo. Probar límites exactos.
- Revisar Resumen y Abstract por separado. Un título ABSTRACT vacío no prueba
  que exista su contenido. Admitir las etiquetas de cada idioma documentadas.
- Verificar en el manual qué límites se aplican al Abstract. No copiar límites
  ni inventar severidades sin fuente. Registrar cualquier decisión pendiente.
- **Aceptación:** 158/159/220/221 palabras; 2/3/5/6 claves; Abstract vacío;
  solo un idioma correcto; palabras clave excluidas del conteo de prosa.
  Mil palabras y diez claves generan la observación correspondiente.
- Mantener `palabras_clave_minimo` en error. Si se agregan reglas, actualizar
  mutaciones, conteos, ejemplos y contrato. No debilitar las guardias existentes.

### M6. Aplicar el nombre de anexo decidido — VA-14

**Archivos:** `reglas_unt.yaml`, pruebas de anexos.
Cambiar el ítem acordado a «Base de datos» y añadir nota `EVALUADO` con la
decisión de 2026-11-08. Mantener warning. **Aceptación:** el título real se
reconoce y su ausencia se informa. Un anexo como imagen requiere revisión
manual; texto XML no encontrado no demuestra ausencia del contenido escaneado.

### M7. Comprobar lo que anuncia la regla del logo — VA-15

**Archivos:** regla `caratula_logotipo_tamano`, analizador de imagen, tests.
Delimitar carátula y medir dibujo; usar 4,84 × 6,73 cm con tolerancia justificada.
No identificar visualmente el logo si no existe ese mecanismo.
**Aceptación:** imagen solo en el cuerpo no satisface carátula; dimensiones
incorrectas generan warning. Si solo se implementa presencia, renombrar la
descripción y dejar la medición expresamente pendiente, no «cerrada».

### M8. ORCID por persona y destino — VA-16

**Archivos:** `reglas_unt.yaml`, `AnalizadorHipervinculo`, extractor de relaciones.
Delimitar carátula, asociar cada persona y resolver el destino del vínculo.
Aceptar dígito de control X y validar el identificador. No verificar identidad
por red. **Aceptación:** falta un autor, solo hay ORCID del asesor, texto
correcto con destino falso, ORCID válido terminado en X y checksum incorrecto.

### M9. Texto literal y recursos restringidos en PDF — VA-12

**Archivos:** `validator/exportador.py`, `tests/test_exportador.py`.
Escapar también sintaxis Markdown de texto no confiable. Impedir que un prompt
cierre su bloque de código. Restringir el fetcher de PDF a recursos permitidos.
**Aceptación:** imágenes Markdown, URLs locales/remotas, backticks y HTML del
documento no activan accesos a recursos. Usar un fetcher simulado; no acceder
a archivos sensibles ni hacer peticiones reales para demostrarlo.

### M10. Contadores de CLI y exportación — VA-18

**Archivos:** `validator/cli.py`, `exportador.py`, pruebas de CLI/exportación.
Usar `total_evaluadas` bajo «evaluadas». Mostrar omitidas aparte.
**Aceptación:** 49 totales, 41 evaluadas no se presentan como 49 evaluadas.

### M11. Reparar el paquete OPC del factory — VA-17

**Archivos de Int3:** `tests/_xml_constants.py`, `tests/_docx_builder.py`,
`tests/docx_factory.py`, pruebas de construcción del motor.
**Consumidor:** B6 de Int1. Int3 no modifica el contrato de API ni sus ejemplos.

- Corregir la relación interna y agregar una imagen válida en el destino
  correcto del ZIP. Verificar también tipos de contenido y relaciones.
- **Aceptación:** el documento base abre con `python-docx`; todos los destinos
  de relaciones internas existen; mutaciones y reglas mantienen su intención.
- Entregar el PR/commit y el comando de regeneración a Int1. B6 continúa
  después de esta entrega. No encargar a retblast el arreglo del builder.

### M12. Cerrar brechas normativas — NM-01 a NM-07

**Dueño exclusivo de implementación:** Int3. Leer primero
[AUDITORIA_NORMATIVA_2026-11-12.md](AUDITORIA_NORMATIVA_2026-11-12.md) y sus CSV.
Esta tarea amplía M1, M3, M5 y M6. No duplica sus arreglos. Dividir en PR por
subtarea. Retblast no implementa estas reglas ni sus fixtures.

| Orden | Archivos / tarea | Aceptación concreta |
|---|---|---|
| M12a — P1 | `reglas_unt.yaml`, `analizadores.py`, `extractor.py` si requiere contexto; ampliar M3 | Decimal explícito correcto no falla por existir. Reinicio romano 99 falla. PAGE a la izquierda no cumple por otro párrafo derecho. `titlePg=0` no significa primera página diferente. Probar continuidad y pie activo; declarar límites de página sin render. |
| M12b — P1 | `reglas_unt.yaml`, selectores de carátula; ampliar M1 | Eliminar escuela falla aunque exista facultad. Asesor 36 pt falla aunque la etiqueta esté correcta. Probar cada bloque y cada propiedad exigida, con estilos y múltiples runs. |
| M12c — P1 | Reglas de detección y estructura; `reglas_unt_pendientes.yaml`; `tests/test_tipo_documento.py` | Encargado ratifica tesis/informe/TINV. No afirmar soporte de ocho tipos. Para cualitativo, eliminar cada apartado obligatorio produce fallo. Tipos ambiguos y no soportados quedan explícitos. No activar pendientes sin documento real. |
| M12d — P2 | Reglas y pruebas de carátula | Ratificar límite inferior del título por tipo; probar 14/15/20/21 palabras según decisión. Probar dos autores en orden e invertidos. Confirmar vigencia de máximo de autores antes de bloquear. No cambiar desvío acordado de mayúsculas sin decisión. |
| M12e — P2 | Reglas de referencias y analizador de cantidad | Probar mínimos 20/30/20 TINV; 30 por proyecto/informe cuando se soporten. TSP separa mínimo 20 del informe y máximo 10 de sesión. Una entrada partida no cuenta como varias referencias; texto ajeno no suma. APA y correspondencia semántica no se declaran comprobados por conteo. |
| M12f — P2 | Reglas de anexos; ampliar M6 | Encargado ratifica contradicciones REQ-51 a REQ-55. Eliminar cada anexo requerido falla en el tipo correcto. No acreditar firma ni porcentaje real por título del anexo. |
| M12g — P2 | `fuente`, `cita`, `ubicacion` en YAML y mensajes/prompts | Cada cita literal existe en la fuente. Paráfrasis marcada como tal. Seguimiento y notas se presentan como calidad técnica; encabezados como derivados de plantilla. Corregir conteo documental 46→50 sin alterar catálogo válido. |

En cada PR: agregar regresiones antes del arreglo, sincronizar mutaciones,
verificar documentos reales aplicables y actualizar matriz REQ con prueba y
límite. Si una decisión falta, registrar el requisito como pendiente; no elegir
un estándar por intuición ni convertirlo en «cumple». No tocar API o SPA.
