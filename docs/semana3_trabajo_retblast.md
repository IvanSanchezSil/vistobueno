# Semana 3 — Trabajo realizado

**Integrante**: retblast  
**Rol**: Integrante 1 — Backend / API  
**Semana**: 3 de 14 (07/09/2026 – 11/09/2026)  
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Consolidar el endpoint `POST /validar`: documentación, tests, flujo de datos.
2. Finalizar el contrato de API (`CONTRATO_API.md`) en estado "Implementado".
3. Completar la cobertura de tests del contrato (errores 413, content-type edge case).
4. Resolver la decisión pendiente sobre `detalle_traza` (Fase F5 del plan DSL).

---

## Actividades realizadas

### Tarea 1: Diagrama de flujo del endpoint

**Fecha**: 09/09/2026  
**Acción**: Se creó `docs/FLUJO_API.md` con diagrama Mermaid del flujo completo del endpoint `/validar`: validaciones HTTP, procesamiento motor, mapeo motor→API, manejo de errores y regla de negocio del semáforo.

**Evidencia**: `docs/FLUJO_API.md`

---

### Tarea 2: Actualización del contrato API

**Fecha**: 09/09/2026  
**Acción**: Se actualizó `docs/CONTRATO_API.md` de v1.0.0 "Diseño" a v1.1.0 "Implementado". Se corrigió el ejemplo de error 500 para reflejar el comportamiento real (incluye tipo de excepción). Se agregó sección de changelog.

**Evidencia**: `docs/CONTRATO_API.md`

---

### Tarea 3: Tests de cobertura del contrato

**Fecha**: 09/09/2026  
**Acción**: Se agregaron dos nuevos tests en `tests/test_api_contract.py`:

1. `test_archivo_demasiado_grande` — Verifica que un archivo >10 MB devuelve 413.
2. `test_content_type_octet_stream` — Verifica que `application/octet-stream` se acepta (edge case de navegadores).

**Prueba**: `pytest tests/test_api_contract.py -v` — 20/20 tests pasan.

**Evidencia**: `tests/test_api_contract.py`

---

### Tarea 4: Extracción de versión del esquema

**Fecha**: 09/09/2026  
**Acción**: Se eliminó el hardcodeo de `version_esquema="2026-09-01"` en `validator/api.py`. Ahora se lee del campo `version` en `unt_format_rules_schema.yaml`. Se agregó campo `version: "2026-09-01"` al YAML.

**Evidencia**: `validator/api.py`, `unt_format_rules_schema.yaml`

---

### Tarea 5: Examples en modelos Pydantic

**Fecha**: 09/09/2026  
**Acción**: Se agregaron `json_schema_extra` con examples a `ResultadoReglaAPI` y `ValidarResponse` en `validator/api_models.py`. Esto mejora la experiencia en Swagger UI (sección "Try it out" muestra datos de ejemplo).

**Evidencia**: `validator/api_models.py`

---

### Tarea 6: Decisión sobre `detalle_traza`

**Fecha**: 09/09/2026  
**Acción**: Se resolvió la Decisión 1 del `PLAN_DSL.md` (Fase F5): por ahora, la traza del autómata se embebe en el campo `encontrado` (string plano) sin tocar el contrato API. Si el frontend necesita un campo dedicado, se implementa en semana 4 como cambio aditivo (v1.2).

**Evidencia**: Esta decisión se documenta en la bitácora.

---

## Evidencias producidas

| Archivo | Tipo | Descripción |
|---------|------|-------------|
| `docs/FLUJO_API.md` | Documentación | Diagrama Mermaid del flujo endpoint |
| `docs/CONTRATO_API.md` | Documentación | Contrato v1.1.0 "Implementado" |
| `tests/test_api_contract.py` | Tests | +2 tests (413, content-type octet-stream) |
| `validator/api.py` | Código | version_esquema desde YAML |
| `validator/api_models.py` | Código | Examples en Pydantic models |
| `unt_format_rules_schema.yaml` | Config | Campo `version` agregado |

---

## Competencias curriculares

| Competencia | Evidencia |
|-------------|-----------|
| Ingeniería de Software II | Contrato API formal, tests de contrato, separación de capas |
| Estructura de Datos | Modelos Pydantic DTO, mapeo motor→API |
| Redes de Computadoras I | HTTP status codes (200, 413, 415, 422, 500), multipart, content-type |
| Ingeniería de Software I | Documentación técnica, diagrama de flujo |

---

## Dificultades y aprendizajes

1. **Hardcoding vs YAML**: El `version_esquema` estaba hardcodeado en `api.py`. Aprender a preferir la fuente de verdad (YAML) para valores que pueden cambiar.
2. **Edge cases de content-type**: Algunos navegadores envían `application/octet-stream` para `.docx`. El endpoint debe ser tolerante.
3. **Test de tamaño grande**: No se puede crear un archivo de 11 MB en memoria eficientemente en un test unitario. Se usó `b"x" * (11 * 1024 * 1024)` que funciona pero es untrade-off entre simplicidad y eficiencia.
4. **Decisiones pendientes**: Aprender que Documentar decisiones pendientes (como `detalle_traza`) es tan importante como implementarlas.

---

## Plan de la semana siguiente

1. Coordinar con Integrante 2 (Frontend) para validar que el contrato API es suficiente para el consumo del frontend.
2. Si el frontend necesita `detalle_traza` como campo dedicado, implementar como v1.2.
3. Agregar validación de content-type más robusta (verificar magic bytes del ZIP en vez de solo extensión).
4. Explorar si el campo `version` del YAML debe incluir también la versión del motor (legacy vs DSL).
