# Semana 2 — Trabajo realizado

**Integrante**: retblast  
**Rol**: Integrante 1 — Backend / API  
**Semana**: 2 de 14 (01/09/2026 – 05/09/2026)  
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Diseñar el contrato de la API `POST /validar`.
2. Definir los modelos Pydantic de entrada/salida basados en las estructuras existentes del motor de validación.

---

## Actividades realizadas

### Tarea 1: Inspección del motor de validación existente

**Fecha**: 02/09/2026  
**Acción**: Se ejecutó el CLI del motor (`python -m validator.cli`) contra una plantilla oficial de tesis con el flag `--json` para capturar la forma exacta de la salida del motor.

**Archivos inspeccionados**:
- `validator/engine.py` — funciones `load_rules()`, `validate_docx()`, `build_report()`
- `validator/models.py` — `RuleResult` (dataclass), `Severity` (Enum)
- `validator/extractor.py` — `extract()`, `ExtractedDocx`
- `validator/checks.py` — `run_check()` y los 5 tipos de check soportados
- `validator/prompts.py` — `build_ai_help_section()`
- `validator/cli.py` — CLI de referencia
- `unt_format_rules_schema.yaml` — 43 reglas, 31 con mecanismo verificable

**Hallazgos clave**:
- El motor devuelve `List[RuleResult]` con campos en inglés (`rule_id`, `passed`, `severity`, `message`, etc.)
- `build_report()` agrega un diccionario con `semaforo`, `resultados` y `resumen`
- `build_ai_help_section()` devuelve `List[{rule_id, prompt}]` solo para reglas fallidas
- La plantilla de prueba devolvió: semáforo rojo, 3 errores, 4 warnings

**Evidencia**: `docs/ejemplo_respuesta_motor.json` (salida JSON completa del motor)

---

### Tarea 2: Definición del contrato de API

**Fecha**: 02/09/2026  
**Acción**: Se creó `docs/CONTRATO_API.md` con la especificación completa del endpoint `POST /validar`.

**Decisiones de diseño**:
- Content-Type: `multipart/form-data` (estándar para subida de archivos)
- Campo de archivo: `archivo` (en español, coherente con el dominio)
- Tipos soportados: solo `.docx` por ahora (PDF queda para después)
- Tamaño máximo: 10 MB
- Query param: `incluir_prompts_ia` (bool, default true)
- Nombres de campos JSON en español (el producto es para una institución hispanohablante)
- Códigos de estado: 200, 400, 413, 415, 422, 500

**Archivo**: `docs/CONTRATO_API.md`

---

### Tarea 3: Modelos Pydantic DTO

**Fecha**: 02/09/2026  
**Acción**: Se creó `validator/api_models.py` con los modelos DTO que definen el contrato de respuesta de la API.

**Modelos creados**:
- `SeveridadAPI` — Enum con valores `"error"` y `"warning"`
- `ResultadoReglaAPI` — DTO para un resultado individual de regla (mapeo de `RuleResult`)
- `PromptIA` — Bloque de prompt "cómo preguntar a una IA"
- `ResumenValidacion` — Resumen cuantitativo (total, fallidos_error, fallidos_warning)
- `MetadatosValidacion` — Metadatos del procesamiento (nombre archivo, tamaño, reglas evaluadas, versión esquema)
- `ValidarResponse` — Respuesta completa del endpoint

**Razón de la separación**: El motor interno usa `RuleResult` (dataclass, campos en inglés). La API expone `ResultadoReglaAPI` (Pydantic, campos en español). Esto permite versionar el contrato externo sin tocar el motor.

**Archivo**: `validator/api_models.py`

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Shape exacto del motor de validación | `docs/ejemplo_respuesta_motor.json` | Estructura de Datos |
| Contrato de API completo | `docs/CONTRATO_API.md` | Redes de Computadoras I, Ingeniería de Software I |
| Modelos Pydantic DTO | `validator/api_models.py` | Estructura de Datos, Ingeniería de Software II |
| Corrección de typo en flake.nix | `flake.nix` (poppler_utils → poppler-utils) | — |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Ingeniería de Software II** — Software design and implementation | Diseño del contrato de API, separación motor/API, modelos DTO |
| **Estructura de Datos** — Data representation and modeling | Modelos Pydantic, mapeo RuleResult → ResultadoReglaAPI, serialización JSON |
| **Redes de Computadoras I** — HTTP, REST APIs, file transfer | Definición de endpoint, multipart upload, códigos de estado HTTP |
| **Ingeniería de Software I** — Technical documentation | Documentación del contrato en `docs/CONTRATO_API.md` |

---

## Pendiente (siguientes tareas de la semana)

- [ ] Crear endpoint FastAPI (`validator/api.py`)
- [ ] Integrar motor existente en el endpoint
- [ ] Manejo de errores del endpoint
- [ ] Tests de contrato
- [ ] Verificar paridad API = CLI
- [ ] Screenshot de Swagger UI
- [ ] Commits atómicos y push

---

## Plan semana siguiente (semana 3)

- Implementación completa del endpoint `POST /validar`
- Tests de integración con archivos DOCX reales
- Soporte para query params (`incluir_prompts_ia`, `solo_errores`)
- Conexión inicial con el frontend React
