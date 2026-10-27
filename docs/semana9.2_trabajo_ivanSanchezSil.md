# Semana 9.2 — Bitácora de trabajo

**Integrante**: IvanSanchezSil (Int3 — Motor de reglas / Procesamiento)
**Fecha**: 2026-10-21
**Rama**: `linter-config-invalida` (creada desde `origin/semana8-deposito-ficha`)
**Estado**: En progreso

## Objetivo de la semana

Arreglar falsos verdes y errores de configuración disfrazados de fallos del
estudiante. Mejorar la confianza del semáforo evitando que reglas con
configuración inválida pasen como éxitos o fallen por error del motor.

## T3 — Falsos verdes en `analizadores.py` (prioridad 1)

1. `AnalizadorListaObligatoria` con `items: []` no comprobaba nada y pasaba.
2. `AnalizadorPaginacion` sin `xpaths` (< 2) devolvía fallo del documento.

**Solución:** linter (`_lint_lista_obligatoria`, `_lint_paginacion`) detecta al cargar;
`ConfigurationError` en `__init__` como red de seguridad. `ConfigurationError` hereda
de `ValueError` y en API genera 422 confundiendo estudiante/motor, por eso la
detección se hace en el linter → `DSLValidationError` → 500 "configuración de reglas inválida".

**Archivos:** `validator/dsl_check.py`, `validator/analizadores.py`, `tests/test_f4_ingenieria.py`
**Resultado:** 8 tests, suite 499 passed, 1 skipped.

## T2 — Endurecer el linter del DSL (prioridad 2)

Cinco casos detectados al cargar el DSL:

| Caso | Antes | Ahora |
|------|-------|-------|
| Sección mal escrita (`atributo_xmls`) | Regla desaparecía del reporte en silencio | Hallazgo con sugerencia difusa |
| XPath prefijo desconocido (`//wp:ind`) | `XPathEvalError` al evaluar, mostrado al estudiante | Hallazgo al cargar; se ignoran ejes |
| Severidad inventada (`aviso`) | `ValueError` al evaluar | Hallazgo al cargar |
| `aplicar_si` valor mal escrito | La clave ya se detectaba, el valor no → regla nunca aplicaba | Hallazgo al cargar |
| `id` duplicado | Doble conteo, observaciones indistinguibles | Hallazgo al cargar |

**Archivos:** `validator/dsl_check.py`, `tests/test_t2_linter.py`
**Resultado:** 28 tests, **527 passed, 1 skipped**, ruff/mypy limpios.

## Verificación

- Guard de producción: `reglas_unt.yaml`, `reglas_unt_pendientes.yaml`,
  `reglas_ficha.yaml` pasan el linter sin hallazgos.
- No se toca `api.py`, `api_models.py`, `frontend/`, `notificacion.py`,
  `dspace.py`.
- Base: `origin/semana8-deposito-ficha` (PR #56 ya mergeado).
