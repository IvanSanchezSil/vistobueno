# Plan de corrección — Linter del DSL (PR #72)

**Rama**: `fix/motor-linter-config-invalida`
**PR**: [#72](https://github.com/retblast/vistobueno/pull/72)
**Autor**: IvanSanchezSil (Int3 — Motor de reglas / Procesamiento)
**Fecha**: 2026-11-09

---

## Contexto

La revisión del PR #72 detectó **2 hallazgos bloqueantes, 5 medios y 5
bajos** en el linter del DSL (`validator/dsl_check.py`) y en la red de
seguridad de los analizadores (`validator/analizadores.py`).

Los dos bloqueantes permiten que una configuración inválida deje el
endpoint en **500 global** o que una regla **desaparezca del reporte en
silencio**, que es justo lo que el PR decía cerrar.

## Objetivo

Corregir todos los hallazgos de la revisión sin debilitar la suite ni el
CI, con commits atómicos y verificación en cada paso.

---

## Hallazgos y solución

| ID | Hallazgo | Solución |
|----|----------|----------|
| **B1** | `_lint_xpath` interpreta los dos puntos dentro de literales (`'Palabras clave:'`) como prefijos de namespace y puede tumbar la API con 500. | Validar con `etree.XPath(expr, namespaces=NS)` de lxml (detecta prefijos desconocidos y sintaxis inválida sin falsos positivos). Eliminar `_PREFIXOS_NAMESPACE` y `_EJES_XPATH`; importar `NS` del extractor. |
| **B2** | `_lint_secciones_desconocidas` usa `cutoff=0.75` y no detecta truncamientos (`conteo`, `patron`, `lista`, `nota`, `gramatica`): la regla se pierde en silencio. | Tratar como cerrado el conjunto de claves de nivel de regla (`_SECCIONES \| _CLAVES_REGLA`); usar `difflib` solo para sugerir la corrección. |
| **M1** | `AnalizadorPaginacion.__init__` quedó antes del docstring: `__doc__` es `None`. | Mover `__init__` debajo del docstring. |
| **M2** | `ConfigurationError(ValueError)` haría que la API culpe al documento del estudiante (422); el linter además se salta configuraciones que no son diccionario y luego revienta con `AttributeError`. | Heredar de `DSLValidationError` (la API lo mapea a 500) y validar `isinstance(config, dict)` en el linter y en `Analizador.__init__`. |
| **M3** | `_PREFIXOS_NAMESPACE` duplica `extractor.NS` con una justificación de ciclo inexistente. | Importar `NS` del extractor (absorbido por B1). |
| **M4** | `_SEVERIDADES` duplica `models.Severity`. | Derivar el catálogo de `Severity`. |
| **M5** | `_lintar_valor_tipo_documento` rechaza los centinelas documentados `sin_determinar` y `contradictorio`. | Admitir los centinelas además de los tipos declarados. |
| **N1** | Documentación desactualizada (`README.md`, `docs/DSL.md`, `docs/diseno/05_compilador_linter.md`, árbol de `AGENTS.md`). | Actualizar los cuatro documentos. |
| **N2** | Bitácora con rama/PR/conteos/commits incorrectos y sin las secciones obligatorias. | Actualizar `docs/semana9.2_trabajo_ivanSanchezSil.md`. |
| **N3** | Tres tests "antes" no ejercitan el runtime que describen. | Reescribirlos para evaluar de verdad el XPath y la severidad; renombrar el de ids duplicados. |
| **N4** | El linter cuesta ~3 ms por petición porque el DSL se recompila en cada validación. | Aceptado por la revisión; se anota como pendiente (caché del compilado por hilo). No cambia código en este PR. |
| **N5** | Rama desfasada respecto de `master`. | Fusionar `master` en la rama antes de corregir. |

---

## Commits planificados (atómicos)

1. `chore: fusionar master en la rama del linter` (N5)
2. `docs: agregar plan de corrección del linter (PR #72)`
3. `fix(dsl): validar XPath con lxml y no confundir literales` (B1 + M3)
4. `fix(dsl): detectar cualquier clave de regla desconocida` (B2)
5. `fix(motor): ConfigurationError es un error de configuración del DSL` (M2a)
6. `fix(motor): rechazar configuraciones de sección que no son diccionario` (M2b)
7. `fix(motor): restaurar el docstring de AnalizadorPaginacion` (M1)
8. `refactor(dsl): usar Severity en el catálogo de severidades` (M4)
9. `fix(dsl): admitir los centinelas de detección de tipo` (M5)
10. `test(dsl): ejercitar de verdad los controles "antes"` (N3)
11. `docs: documentar los controles nuevos del linter` (N1)
12. `docs: actualizar la bitácora de la semana 9.2` (N2)

Cada commit de código incluye sus tests y se verifica con la suite
relevante. Los mensajes van en español y **sin `Co-authored-by`**.

---

## Verificación

- [x] `pytest tests/ -v` completo, sin fallos. (799 passed, 4 skipped, 6 xfailed)
- [x] `ruff check validator/ scripts/ tests/`.
- [x] `ruff format --check validator/ scripts/ tests/`.
- [x] `mypy validator/ scripts/`.
- [ ] `git status` limpio (sin `__pycache__` ni temporales).
- [x] Caso manual: regla inválida en la API → **500** de configuración, no 422. (Orden `except DSLValidationError` antes de `except ValueError` en `api.py`.)
- [ ] Revisión del `git diff` de cada commit.

## Estado

- [x] Merge de `master`
- [x] Plan versionado
- [x] B1 + M3
- [x] B2
- [x] M2a
- [x] M2b
- [x] M1
- [x] M4
- [x] M5
- [x] N3
- [x] N1
- [x] N2
- [ ] Verificación final y push al fork
