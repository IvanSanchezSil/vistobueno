# Registro de documentos aportados por la sede

**Estado**: propuesta de estructura (Actividad 14 del PPP).
**Fecha**: 2026-11-04.
**Ámbito**: piloto del flujo de ficha de depósito (Actividad 16).
**Relacionados**: `docs/HANDOVER_DESPLIEGUE_MAQUINA_OPERADOR.md`,
`docs/PLAN_FICHA_DEPOSITO.md`, `docs/HANDOVER_AUDITORIA_2026-10-26.md`.

> **Plantilla, no registro lleno.** Este archivo define la estructura para
> registrar los documentos que la sede entregue para el piloto. No contiene
> datos de estudiantes, asesores ni documentos reales. El registro lleno se
> mantiene en una carpeta local fuera del repositorio.

---

## 1. Objetivo

La Actividad 14 del PPP pide una **propuesta de estructura** para registrar
los documentos aportados por la sede, no el registro lleno. El llenado real
se hace durante el piloto, cuando la sede entregue los documentos.

Este registro permite responder cuatro preguntas:

1. Qué documentos entregó la sede y con qué autorización.
2. Qué resultado dio el validador para cada uno.
3. Qué se devolvió a la sede y cuándo.
4. Qué evidencia anonimizada queda para el cierre del piloto.

La estructura es independiente del formato: se puede usar como tabla
Markdown, hoja de cálculo o base local. Lo importante es conservar los
mismos campos y la misma regla de privacidad.

---

## 2. Regla de privacidad

- **No versionar documentos reales.** Los DOCX, PDF, capturas y reportes con
  datos personales se guardan en una carpeta local restringida, fuera del
  repositorio.
- **Usar un código por documento.** El código (`SEDE-001`, `SEDE-002`, …) es
  el identificador que viaja en el repositorio y en las conversaciones.
- **No escribir datos personales.** Nada de nombres, DNI, correo, teléfono,
  ORCID, firmas, matrícula, dirección ni handles de DSpace en este archivo,
  en issues, en PRs o en commits.
- **No usar `docs/ejemplos/` para documentos reales.** Esa carpeta contiene
  solo el par sintético de demostración.
- **Anonimizar lo que se comparta.** Si se adjunta un reporte, quitar nombres
  y cualquier dato que permita identificar a una persona.
- **Guardar la correspondencia código → archivo en la copia local.** Esa
  correspondencia no se versiona. El repositorio solo conserva este esquema
  y, si hace falta, una tabla de resultados sin datos personales.

---

## 3. Flujo de registro

1. **Antes de recibir.** Acordar con la sede el canal de entrega, el rol
   responsable y la autorización de uso para el piloto. Definir la carpeta
   local restringida.
2. **Al recibir.** Asignar el código, registrar la fecha, el origen, el rol
   del responsable, el tipo de documento y el uso. Confirmar que la
   autorización está completa.
3. **Antes de validar.** Copiar el archivo a la carpeta local. Verificar que
   abre y que corresponde al tipo declarado. No subir el archivo al
   repositorio.
4. **Validación.** Ejecutar `POST /validar` desde la app. Registrar semáforo,
   cantidad de errores y warnings, hallazgos conocidos y observaciones.
5. **Devolución.** Entregar el reporte al contacto de la sede. Registrar la
   fecha y el estado.
6. **Cierre.** Guardar la evidencia anonimizada y cerrar la fila. No borrar
   la copia local hasta que termine el piloto.

Si la autorización no está confirmada, el documento queda en
`pendiente_autorizacion` y **no se valida**.

---

## 4. Estructura propuesta

Una fila por documento. Si un documento tiene varios autores, no se crean
filas por autor: el reporte del validador ya los contiene y el registro
trabaja con el código del documento.

### 4.1 Campos

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `codigo` | texto | sí | Identificador único, por ejemplo `SEDE-001`. |
| `fecha_recepcion` | fecha | sí | Día en que la sede entregó el documento. |
| `origen` | texto | sí | Área u oficina de origen. No usar nombres de personas. |
| `responsable_rol` | texto | sí | Rol de quien entrega o autoriza, por ejemplo «responsable de repositorio». |
| `autorizacion` | enum | sí | `confirmada`, `pendiente` o `rechazada`. |
| `tipo_documento` | enum | sí | `tinv_cuantitativo`, `tinv_cualitativo`, `tinv_revision_literatura`, `proyecto_cuantitativo`, `proyecto_cualitativo`, `informe_cuantitativo`, `informe_cualitativo`, `tsp` u `otro`. Son los valores de `deteccion_tipo_documento`. |
| `uso` | enum | sí | `piloto` (documento del piloto), `validacion` (prueba del motor) o `plantilla` (formato oficial sin datos). |
| `referencia_local` | texto | sí | Nombre o ruta relativa en la carpeta local. No se versiona. |
| `sha256` | texto | no | Huella del archivo para verificar integridad. Solo en la copia local. |
| `estado` | enum | sí | Ver tabla de estados. |
| `fecha_validacion` | fecha | no | Día en que se ejecutó el validador. |
| `semaforo` | enum | no | `verde`, `rojo` o `no_aplica`. |
| `errores` | entero | no | Cantidad de fallos con severidad `error`. |
| `warnings` | entero | no | Cantidad de fallos con severidad `warning`. |
| `hallazgos` | texto | no | Hallazgos conocidos, por ejemplo `AUD-24` o `AUD-26`. |
| `observaciones` | texto | no | Nota breve y sin datos personales. |
| `evidencia` | texto | no | Ruta de un reporte anonimizado, si se comparte. |
| `fecha_devolucion` | fecha | no | Día en que se entregó el reporte a la sede. |
| `fecha_cierre` | fecha | no | Día en que la fila queda cerrada. |

### 4.2 Ejemplo ficticio

| `codigo` | `fecha_recepcion` | `origen` | `responsable_rol` | `autorizacion` | `tipo_documento` | `uso` | `referencia_local` | `estado` | `semaforo` | `errores` | `warnings` | `hallazgos` | `observaciones` | `evidencia` |
|----------|-------------------|----------|-------------------|----------------|------------------|-------|--------------------|----------|------------|-----------|------------|-------------|-----------------|-------------|
| `SEDE-001` | `AAAA-MM-DD` | Biblioteca FECyC | responsable de repositorio | `confirmada` | `informe_cuantitativo` | `piloto` | `informe-001.docx` | `validado` | `rojo` | 2 | 1 | `AUD-24`, `AUD-26` | Título y autores corregidos a mano | `reportes/SEDE-001.json` |

La fila anterior es solo un ejemplo de forma. No corresponde a un documento
real.

---

## 5. Estados

| Estado | Significado | Siguiente paso |
|--------|-------------|----------------|
| `pendiente_autorizacion` | El documento llegó, pero falta confirmar la autorización. | No validar; pedir autorización. |
| `recibido` | Documento y autorización confirmados; aún sin validar. | Ejecutar el validador. |
| `validado` | Validación ejecutada y resultado registrado. | Entregar el reporte a la sede. |
| `devuelto` | Reporte entregado a la sede. | Esperar correcciones o cerrar. |
| `cerrado` | Sin acciones pendientes en el piloto. | Archivar la evidencia. |
| `descartado` | Documento no usable: duplicado, formato incorrecto o autorización rechazada. | Registrar el motivo y cerrar. |

---

## 6. Qué registrar en la validación

- **Semáforo y conteos.** `verde` o `rojo`, con `errores` y `warnings`.
- **Tipo detectado.** Si el motor detectó un tipo distinto al declarado,
  anotarlo en `observaciones`.
- **Hallazgos conocidos.** Registrar `AUD-24` a `AUD-27` si aparecen. El
  operador puede corregir los campos de la ficha a mano; el registro debe
  decir qué se corrigió.
- **Plantillas oficiales vacías.** Si el documento es una plantilla oficial
  sin datos y falla por `palabras_clave_minimo`, anotarlo como un caso
  conocido de la auditoría: la regla exige palabras clave que la plantilla
  vacía no tiene. No usarlo como prueba de que el flujo falla.
- **Documentos reales.** Usar un documento de tesis real o el par sintético
  de `docs/ejemplos/`. No usar una plantilla vacía para concluir que el
  flujo funciona.

---

## 7. Almacenamiento y evidencia

| Ubicación | Qué se guarda | Se versiona |
|-----------|---------------|-------------|
| Repositorio | Este esquema y, si se acuerda, una tabla de resultados sin datos personales. | Sí |
| Carpeta local restringida | DOCX/PDF originales, reportes completos y correspondencia código → archivo. | No |
| Carpeta local de evidencia | Reportes anonimizados que se compartirán con la sede o el equipo. | No |

La carpeta local debe tener acceso restringido y un rol responsable.
No se define una ruta absoluta en el repositorio porque depende de la máquina
del operador.

---

## 8. Criterio de cierre de la Actividad 14

La Actividad 14 se cumple con el par de ejemplo ya entregado y esta
propuesta de estructura. El registro lleno **no** es requisito de la
actividad: se completa durante la Actividad 16, cuando la sede entregue
los documentos.

Antes de recibir el primer documento real, el equipo debe aceptar:

1. Los campos y estados de este documento.
2. La regla de privacidad: nada de datos personales en el repositorio.
3. La carpeta local y el rol responsable del registro.
4. Que el registro lleno se hará en el piloto, no antes.

---

## 9. Preguntas abiertas para el equipo

1. ¿Quién mantiene la copia local del registro: Integrante 1 o el operador
   de la sede?
2. ¿La carpeta local vive en un disco cifrado, en una unidad de red
   restringida o en ambos?
3. ¿Cuánto tiempo se conservan los documentos y los reportes después del
   piloto?
4. ¿Quién autoriza el acceso a la copia local y quién puede modificarla?
5. ¿Se versionará una tabla anonimizada de resultados o el registro queda
   completamente fuera del repositorio?

Estas respuestas no bloquean la propuesta, pero deben quedar antes de
recibir el primer documento real.
