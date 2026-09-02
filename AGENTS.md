# Guía de trabajo — VistoBueno

Guía para integrantes del proyecto. Define convenciones, arquitectura y flujo de trabajo.

---

## Contexto del proyecto

**VistoBueno** es una web app para la Biblioteca de la Facultad de Educación y Ciencias de la Comunicación (FECyC) de la Universidad Nacional de Trujillo (UNT). Los estudiantes suben su tesis (DOCX) y reciben validación automática contra las reglas de formato institucionales.

**Producto final**: un semáforo verde/rojo que le dice al estudiante si puede entregar, más un reporte detallado con prompts listos para copiar y pegar en una IA y corregir los problemas.

---

## Arquitectura

```
Frontend (React)
  → POST /validar (multipart/form-data)
    → FastAPI endpoint (validator/api.py)
      → extractor DOCX (validator/extractor.py)
      → motor de reglas (validator/engine.py)
      → generador de prompts IA (validator/prompts.py)
    → respuesta JSON (ValidarResponse)
  ← semáforo + resumen + resultados + prompts IA + metadatos
```

### Componentes existentes

| Módulo | Archivo | Responsabilidad |
|--------|---------|-----------------|
| **Motor de reglas** | `validator/engine.py` | Carga YAML, ejecuta reglas, arma reporte |
| **Modelos internos** | `validator/models.py` | `RuleResult`, `Severity` (dataclass) |
| **Extractor DOCX** | `validator/extractor.py` | Abre .docx (zip OPC), extrae XML |
| **Checks** | `validator/checks.py` | Ejecuta checks individuales (xpath, atributos, regex) |
| **Prompts IA** | `validator/prompts.py` | Genera prompts template para reglas fallidas |
| **API** | `validator/api.py` | Endpoint FastAPI `POST /validar` |
| **DTOs API** | `validator/api_models.py` | Modelos Pydantic de respuesta (campos en español) |
| **CLI referencia** | `validator/cli.py` | Validador desde línea de comandos |
| **Reglas** | `unt_format_rules_schema.yaml` | 43 reglas, 31 ejecutables |

---

## Convenciones de trabajo

### Rama de trabajo

1. **Nunca trabajar directamente en `master`**.
2. Crear una rama por tarea o semana:
   ```
   git checkout -b week3-frontend-integration
   ```
3. Hacer push periódicamente a la rama.
4. Al terminar, abrir PR o hacer merge manual a `master`.

### Commits

- **Un commit por tarea lógica** (atómico).
- Mensajes en **español**, formato convencional:
  ```
  feat(api): agregar endpoint POST /validar
  docs: actualizar contrato de API
  fix: corregir nombre de paquete en flake.nix
  test(api): agregar tests de contrato
  ```
- Prefijos: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`.

### Idioma

| Capa | Idioma |
|------|--------|
| Identificadores Python (clases, funciones, variables) | **Inglés** (convención universal) |
| Comentarios en código | **Español** |
| Nombres de campo JSON en API | **Español** |
| Mensajes de error HTTP | **Español** |
| Documentación (`docs/`, `README.md`, `AGENTS.md`) | **Español** |
| Commits Git | **Español** |
| IDs de reglas YAML | **Inglés** (identificadores de máquina) |

### Documentación de trabajo (obligatorio)

Cada integrante lleva una **bitácora semanal** en `docs/semana{N}_trabajo_{username}.md` con:
- Datos generales (nombre, semana, fechas, rol)
- Objetivos de la semana
- Actividades realizadas (con fechas)
- Evidencias producidas (archivos, commits, screenshots)
- Relación con competencias curriculares
- Dificultades y aprendizajes
- Plan de la semana siguiente

---

## Cómo usar el motor de validación

### Desde Python

```python
from validator.engine import load_rules, validate_docx, build_report
from validator.prompts import build_ai_help_section

rules = load_rules("unt_format_rules_schema.yaml")
resultados = validate_docx("tesis.docx", rules)
reporte = build_report(resultados)

# Prompts IA solo para reglas fallidas
fallidos = [r for r in resultados if not r.passed]
prompts = build_ai_help_section(fallidos)
```

### Desde CLI

```bash
# Validar un DOCX
python -m validator.cli tesis.docx unt_format_rules_schema.yaml

# Solo errores
python -m validator.cli tesis.docx unt_format_rules_schema.yaml --severity error

# JSON completo
python -m validator.cli tesis.docx unt_format_rules_schema.yaml --json
```

### Desde la API

```bash
curl -X POST "http://localhost:8000/validar" \
  -F "archivo=@mi_tesis.docx"
```

---

## Estructura de datos clave

### `RuleResult` (modelo interno del motor)

```python
@dataclass
class RuleResult:
    rule_id: str      # ID de la regla (ej. "papel_tamano")
    passed: bool       # True si cumple
    severity: Severity # "error" o "warning"
    message: str       # Descripción en español
    expected: str      # Valor esperado
    found: str         # Lo que encontró ("cumple" si pasa)
    location: Optional[str]  # Referencia al reglamento
    fuente: str        # Archivo fuente
    cita: str          # Cita textual
```

### `ValidarResponse` (modelo DTO de la API)

Campos en español: `paso` (en vez de `passed`), `severidad`, `mensaje`, `esperado`, `encontrado`, `ubicacion`. Más `metadatos` (nombre archivo, tamaño, etc.) que no existe en el motor.

### `build_report()` output

```json
{
  "semaforo": "verde" | "rojo",
  "resultados": [ ...RuleResult.to_dict() ],
  "resumen": { "total": N, "fallidos_error": N, "fallidos_warning": N }
}
```

El semáforo **siempre** se calcula sobre TODOS los errores, independiente del filtro de severidad.

---

## Entorno de desarrollo

```bash
nix develop   # activa el entorno con todas las dependencias
```

Dependencias: Python 3.14, FastAPI, uvicorn, Pydantic, pyyaml, python-docx, PyMuPDF, lxml, pytest, httpx, python-multipart.

### Correr la API en desarrollo

```bash
uvicorn validator.api:app --reload
# Swagger UI: http://localhost:8000/docs
```

### Ejecutar tests

```bash
pytest tests/ -v
```

---

## Reglas de validación

- **43 reglas** definidas en `unt_format_rules_schema.yaml`.
- **31 con mecanismo verificable** (ejecutables sobre XML del DOCX).
- **12 sin mecanismo** (requieren análisis semántico, fuera del MVP).
- Las reglas cubren: papel, fuente, tamaños, interlineado, alineación, márgenes, numeración, sangría, estructura de secciones.

### Severidad

- `error`: bloquea la entrega (semáforo rojo).
- `warning`: no bloquea, pero se muestra en el reporte.

3 reglas bajadas de `error` a `warning` por desvío documentado entre manual y plantillas oficiales.

---

## Roles por integrante

| Integrante | Rol principal | Responsabilidades |
|------------|---------------|-------------------|
| Integrante 1 | Backend / API | Endpoint, Pydantic, tests, documentación API |
| Integrante 2 | Frontend / React | UI, upload, visualización de reportes |
| Integrante 3 | Motor de reglas / Procesamiento | Checks, extractor, nuevas reglas, OCR |

> Ajustar esta tabla según los roles reales del equipo.

---

## Lo que NO se hace (MVP)

- ❌ Base de datos / persistencia
- ❌ Autenticación / usuarios
- ❌ Background workers / colas
- ❌ Docker / Kubernetes
- ❌ Soporte PDF (pendiente: extractor con PyMuPDF)
- ❌ Detección automática de tipo de investigación
- ❌ OCR de reglamentos escaneados (pendiente)
- ❌ LLM en tiempo de ejecución (solo template para prompts IA)

---

## Estructura del repositorio

```
vistobueno/
├── AGENTS.md                          # Esta guía
├── README.md                          # Documentación general del proyecto
├── flake.nix                          # Entorno de desarrollo Nix
├── unt_format_rules_schema.yaml       # 43 reglas de formato (fuente de verdad)
├── validator/
│   ├── __init__.py                    # Docstring del paquete
│   ├── engine.py                      # Motor: load_rules, validate_docx, build_report
│   ├── models.py                      # RuleResult (dataclass), Severity (Enum)
│   ├── extractor.py                   # Abre .docx, extrae XML (ExtractedDocx)
│   ├── checks.py                      # Checks individuales (xpath, atributos, regex)
│   ├── prompts.py                     # Generador de prompts "cómo preguntar a una IA"
│   ├── api.py                         # FastAPI endpoint POST /validar
│   ├── api_models.py                  # Pydantic DTOs (ValidarResponse, etc.)
│   └── cli.py                         # CLI de referencia
├── tests/
│   └── test_api_contract.py           # Tests de contrato para la API
├── docs/
│   ├── CONTRATO_API.md                # Especificación del endpoint
│   ├── ejemplo_respuesta_motor.json   # Salida de referencia del motor
│   └── semana{N}_trabajo_{user}.md    # Bitácoras semanales
├── scripts/
│   └── eval_contra_plantillas.py      # Evaluación batch contra plantillas
└── recursos/                          # Plantillas oficiales y reglamentos (.docx, .pdf)
```

### Flujo de datos en detalle

1. El frontend envía un archivo `.docx` vía `POST /validar` (multipart/form-data).
2. `api.py` recibe el archivo, valida tipo y tamaño, lo guarda en un archivo temporal.
3. `engine.validate_docx()` llama a `extractor.extract()` que abre el ZIP del DOCX y extrae los XML relevantes (`document.xml`, `footer1.xml`, `header1.xml`).
4. El engine recorre cada regla del YAML que tenga `mecanismo_verificable`.
5. Para cada regla, ejecuta sus `checks` via `checks.run_check()` (xpath, atributos XML, regex, secuencia de títulos, presencia de imágenes).
6. Cada check produce un `(passed, detalle)` que se acumula en fallos.
7. El engine arma `List[RuleResult]` con el resultado de cada regla.
8. `build_report()` agrupa los resultados, calcula el semáforo y el resumen.
9. `build_ai_help_section()` genera prompts template para las reglas fallidas.
10. `api.py` mapea los resultados del motor a los DTOs Pydantic (campos en español).
11. La respuesta JSON se devuelve al frontend.

### Capa de abstracción: motor vs API

El **motor de validación** (`engine.py`, `models.py`, `extractor.py`, `checks.py`) es un módulo Python puro, sin dependencia de FastAPI. Se puede usar desde:
- La API (`api.py`)
- La CLI (`cli.py`)
- Scripts de evaluación batch (`scripts/`)

La **capa API** (`api.py`, `api_models.py`) es un adaptador delgado que:
- Recibe HTTP multipart
- Valida entrada
- Llama al motor
- Mapea `RuleResult` → `ResultadoReglaAPI` (DTO)
- Agrega metadatos (nombre de archivo, tamaño)
- Devuelve JSON con campos en español

Esto significa que **no debes mover lógica de validación a `api.py`**. Si una lógica pertenece al motor, va en `engine.py` o `checks.py`.

---

## Reglas de comportamiento del agente

### Preguntar cuando no esté claro

Si alguna instrucción, decisión de diseño, o requisito no está claro, **pregunta al usuario antes de asumir**. Es mejor hacer una pregunta rápida que implementar algo incorrecto y tener que rehacerlo. Ejemplos de cuándo preguntar:

- No está claro dónde va un cambio (¿motor? ¿API? ¿frontend?)
- Hay dos formas de hacer algo y no hay una razón obvia para elegir una
- Un requisito contradice algo existente en el código
- No estás seguro del scope de una tarea
- Algo en el AGENTS.md o el README parece desactualizado

### Este documento es vivo (pero requiere aprobación)

El `AGENTS.md` se puede actualizar conforme el proyecto evolucione:
- Nuevos componentes → agregar a la tabla de componentes
- Nuevas convenciones → agregar a la sección correspondiente
- Cambios de arquitectura → actualizar diagrama y descripciones
- Nuevos roles o responsabilidades → actualizar tabla de roles

**Restricción**: todo cambio al `AGENTS.md` debe ser **aprobado por el usuario** antes de hacerse commit. No actualices este documento unilateralmente.

---

## Evidencia para pasantía

Cada integrante debe poder demostrar:

| Competencia | Evidencia esperada |
|-------------|-------------------|
| Ingeniería de Software II | Arquitectura, diseño, manejo de errores, tests |
| Estructura de Datos | Modelos de datos, serialización, mapeo motor→API |
| Redes de Computadoras I | HTTP, REST, multipart, códigos de estado |
| Ingeniería de Software I | Documentación técnica, contratos de API |
