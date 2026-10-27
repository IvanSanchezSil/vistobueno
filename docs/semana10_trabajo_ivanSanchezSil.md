# Semana 10 — Bitácora de trabajo

**Integrante**: IvanSanchezSil ( — Motor de reglas / Procesamiento)  
**Fecha**: 2026-10-27  
**Rama**: `semana10-auditoria-motor`  
**Base**: `origin/semana8-deposito-ficha` (PR #56 ya mergeado)  
**Estado**: En progreso  
**Contexto**: Auditoría `AUDIT_COMPORTAMIENTO_VISTOBUENO_2026-10-26.md`

## Objetivo de la semana

Corregir los hallazgos de la auditoría que corresponden a  (Motor/Reglas), documentando y planificando primero, sin tocar código hasta tenerlo claro. Priorizar correctitud del motor (falsos positivos / hallazgos erróneos).

## Hallazgos asignados a 

| ID | Severidad | Archivos | Acción prevista | Estado |
|----|-----|----------|-----------------|--------|
| AUD-01 | Alta | `validator/analizadores.py` (`_norm_indice`) | Separar normalización entre títulos del cuerpo (sin recorte romano falso) e ítems del índice (mantener lógica actual). Falso positivo con "General" y títulos acabados en i/l/v/x/c. | Pendiente |
| AUD-02 | Alta | `validator/tokenizer.py`, `validator/analizadores.py`, `reglas_unt.yaml` | Arreglar `anexos_minimos_*`: permitir `seccion()` hasta final (`hasta_final: true`), incluir títulos `Anexo N.` en `_texto()`, mostrar **todos** los faltantes (eliminar `[:8]`). Sincronizar `tests/_mutations.py`. | Pendiente |
| AUD-03 | Media | `validator/analizadores.py`, `validator/compilador.py` | Hacer `encontrado` legible: culpables primero, página correcta del nodo infractor, sin anteponer valores conformes. Cuidar paridad con `tests/test_paridad_formatos.py`. | Pendiente |
| AUD-04 | Media | `reglas_unt.yaml` | Añadir notas `EVALUADO:` a `caratula_titulo_trabajo_tamano` y `caratula_optar_grado_tamano` (plantilla usa 13pt/12pt). | Pendiente |
| AUD-05 | Media | `reglas_unt.yaml` / analizadores | Decisión: endurecer selectores frágiles (`/w:r[1]`, `following-sibling::w:p[1]`) o documentar. | Pendiente (decisión) |
| AUD-06 | Baja | `validator/analizadores.py` (`_sigpalabra`) | Decisión: revisar umbral `>= 4` auto-pasa entradas cortas. | Pendiente (decisión) |
| AUD-07 | Baja | `reglas_unt.yaml` | Decisión: restringir `caratula_optar_grado_tamano` al "grado de Bachiller" o añadir `EVALUADO:`. | Pendiente (decisión) |
| AUD-20 | Media | `tests/_docx_builder.py`, `tests/_mutations.py` | Añadir fixtures que reproduzcan estructura real (anexos con Título1 + "Anexo N.") y casos para AUD-01. | Pendiente |

**Coordinar:** AUD-15 (`validator/exportador.py`) — fuera de alcance directo; AUD-21 (paridad) con AUD-03.

## Plan de trabajo

Orden propuesto:

1. **Documentación y planificación** (hecho) — crear bitácora semana 10 + plan detallado.
2. **AUD-01** — Aislado, test de regresión con "General" + entrada con página arábiga.
3. **AUD-02** — Más amplio (tokenizer + analizadores + YAML + mutations). Añadir fixture de estructura de anexos.
4. **AUD-20** — Blindar 01-02 con fixtures.
5. **AUD-03** — Cambiar formato de `encontrado`. Revisar `test_paridad_formatos.py` tras el cambio.
6. **AUD-04** — Trivial, notas `EVALUADO:`.
7. **AUD-05/AUD-06/AUD-07** — Solo con decisión de dominio.

## Criterios de aceptación

- [ ] AUD-01 corregido con test que falle antes y pase después
- [ ] AUD-02 corregido: detecta anexos con estructura Título1 "Anexos" + "Anexo N.", muestra todos los faltantes
- [ ] AUD-03: `encontrado` legible, culpables primero, página correcta
- [ ] AUD-04: notas `EVALUADO:` añadidas
- [ ] `tests/_mutations.py` sincronizado si aplica
- [ ] `pytest tests/ -v` sin regresiones
- [ ] `tests/test_paridad_formatos.py` OK (o actualizado con justificación)
- [ ] `nix flake check` OK
- [ ] `ruff check`, `ruff format --check`, `mypy validator/ scripts/` OK

## Riesgos

- Cambiar `found` puede romper paridad → revisar `test_paridad_formatos.py` siguiendo el patrón de `7ff5cd3`
- Añadir `hasta_final` a `seccion()` puede afectar otras reglas → opcional, por defecto mantener comportamiento actual
- Incluir `TITULO` en búsqueda de anexos → limitar al contexto de esa regla, no global

## Evidencia

Plan detallado en `docs/PLAN_SEMANA10_AUDITORIA_MOTOR.md`
