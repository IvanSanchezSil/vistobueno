# Semana 9.2 — Bitácora de trabajo

**Integrante**: IvanSanchezSil (Int3 — Motor de reglas / Procesamiento)
**Fecha**: 2026-10-21
**Rama**: `semana9.2` (creada desde `origin/semana8-deposito-ficha` en `cccd7a3`)
**Estado**: En progreso

---

## Objetivo de la semana

Arreglar falsos verdes y errores de configuración disfrazados de fallos del
estudiante en `validator/analizadores.py`. Mejorar la confianza del semáforo
evitando que reglas con configuración inválida pasen como éxitos o fallen
por error del motor.

## Tareas planificadas

### T3 — Falsos verdes en `analizadores.py` (prioridad 1, pequeña)

**Problema detectado:**

1. `AnalizadorListaObligatoria` con `items: []` → devuelve
   `(True, "items_obligatorios=0 completo")`. No comprueba nada y pasa como
   éxito.

2. `AnalizadorPaginacion` sin `xpaths` (o con menos de 2) → falla con
   `(False, "paginacion requiere xpaths (>=2)")`. El estudiante recibe un
   error de formato que no es suyo.

**Diagnóstico:**

- `lista_obligatoria` vacía: el analizador no detecta que la regla está
  vacía. Debería **invalidar la regla** (config error), no pasar como éxito.
- `paginacion` sin xpaths: el error de configuración se muestra como **fallo
  del documento**, no del motor. El estudiante se confunde.

**Plan de implementación:**

1. En la construcción del analizador (`__init__` o factory), validar:
   - `items` no vacío → si está vacío, lanzar `ConfigurationError`/`ValueError`
     con mensaje de config.
   - `xpaths` con al menos 2 elementos → si no, error de config.
2. Diferenciar el error de configuración del fallo del documento: un error
   de config **no** debe parecer un fallo de la regla.
3. Test: que una regla con config inválida falle al cargar/compilar, no al
   validar contra un documento.

**Archivos a tocar:**

- `validator/analizadores.py` (clases `AnalizadorListaObligatoria` y
  `AnalizadorPaginacion`)
- `validator/compilador.py` (opcional: factory de analizadores)
- `tests/test_f4_ingenieria.py` (tests del linter / analizadores)

**Criterios de aceptación:**

- Una regla `lista_obligatoria` con `items: []` lanza error de configuración
  al compilar (no pasa como verde).
- Una regla `paginacion` sin `xpaths` lanza error de configuración al
  compilar (no se muestra como fallo del documento).
- Tests existentes siguen pasando.
- Suite: `pytest tests/ -v` verde.

---

## Notas

- No se toca `api.py`, `api_models.py`, `frontend/`, `notificacion.py`,
  `dspace.py`.
- Cambios locales solamente; sin push.
- La rama `semana9.2` parte de `origin/semana8-deposito-ficha` (que ya tiene
  el PR #56 mergeado).

---

## Historial de cambios

| Fecha | Commit | Qué |
|-------|--------|-----|
| 2026-10-21 | `a3e4f2c` | T3: falsos verdes en `analizadores.py` (ConfigurationError + validación en __init__) |