# Handover Integrante 2 — frontend — 2026-11-12

**Estado:** tareas pendientes. Implementar solo los archivos asignados a este integrante.
Ver [índice y estado común](HANDOVER_CORRECTITUD_2026-11-12.md).
Las dependencias de [Int1](HANDOVER_CORRECTITUD_INT1_2026-11-12.md),
[Int2](HANDOVER_CORRECTITUD_INT2_2026-11-12.md) e
[Int3](HANDOVER_CORRECTITUD_INT3_2026-11-12.md) no autorizan a editar sus archivos.

## 1. Tareas propias

### F1. Resguardo ligado al contenido — VA-10

**Archivos:** `frontend/src/components/FichaDeposito.jsx`, `ficha.js`, tests.

- No usar `archivo_nombre` como identidad. Calcular SHA-256 del archivo con
  Web Crypto y pasar esa identidad hasta la ficha, o coordinar un identificador
  equivalente con Int1. Mismo nombre no significa mismo documento.
- Agregar caducidad y descarte explícito. Conservar recuperación del mismo
  contenido. No cargar resguardos antiguos identificados solo por filename.
- **Aceptación:** dos `tesis.docx` con contenido distinto no comparten DNI ni
  matrícula; el mismo archivo recupera su edición; un resguardo vencido no se usa.

### F2. Consumir la identidad de trámite — VA-09

**Archivos:** `ficha.js`, `FichaDeposito.jsx`, tests de lógica y componente.
**Dependencia:** contrato B2 fijado por Int1. No inventar campos propios.

- Guardar el `tramite_id` devuelto al preparar. Ignorar depósitos con otro ID.
- Conservar la confirmación del título observado. No habilitar constancias
  con un depósito viejo, sin timestamp válido o de otro trámite.
- Limpiar handle, filas y estado de aceptación al preparar un trámite nuevo.
- **Aceptación:** respuestas atrasadas y dos trámites con el mismo título no
  habilitan papeleo incorrecto. Recarga, cancelación y expiración tienen salida.

### F3. Mostrar el alcance real de «verde»

**Archivos:** `Report.jsx`, `FichaDeposito.jsx`, tests; texto coordinado con Int3.

- Mostrar evaluadas, no aplicables y advertencias por separado. No presentar
  controles no ejecutados como cumplidos. Evitar «todo el formato cumple».
- Si un tipo no tiene esquema cargado o una comprobación exige revisión manual,
  mostrar esa limitación cerca del veredicto. Mantener el significado del
  semáforo vigente; no cambiar la severidad desde la UI.
- **Aceptación:** caso verde con esquema no soportado muestra revisión
  incompleta; las advertencias siguen visibles. No ocultarlas para llegar a 100 %.

### F4. Gestionar 429 y tiempos reales — VA-19

**Archivos:** `Upload.jsx`, tests. **Coordinar:** B1.

- Leer `Retry-After` y mostrar el tiempo real. No decir «unos segundos» si son
  minutos. Evitar reintentos automáticos duplicados y restablecer el formulario.
- Medir el ciclo completo antes de cambiar los 30 s actuales. Un timeout del
  navegador no demuestra que el trabajo del servidor se canceló.
- **Aceptación:** 429 con espera larga, timeout y reintento manual conservan el
  archivo y no crean solicitudes paralelas. El ciclo del piloto cabe en el plazo.

### F5. Recuperación de la SPA sin mezcla de datos — VA-21

**Archivos:** `Upload.jsx`, `FichaDeposito.jsx`, `ficha.js`, tests.
**Dependencias:** F1 y contrato B2. Coordinar el ensayo de navegador con B8.

- Al restaurar la SPA, comprobar identidad del documento, trámite y caducidad
  antes de recuperar la ficha. Un estado visual restaurado no confirma un depósito.
- Revisar los campos manuales después del autofill. Una matrícula o DNI
  insertados por el navegador no pasan a «confirmados» por aparecer en pantalla.
  Mostrar el autor asociado y exigir revisión antes de preparar el depósito.
- Explicar qué datos conserva VistoBueno y ofrecer descartar su propio
  resguardo. Usar identificadores de campo estables; no aleatorizar nombres
  para intentar engañar al autofill ni depender de esa técnica.
- **Aceptación:** recarga y restauración con documento distinto, resguardo
  vencido, perfil con autofill y valores insertados sin eventos. El trámite
  nuevo no recupera ni publica datos de otro estudiante.
