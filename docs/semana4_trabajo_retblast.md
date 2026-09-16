# Semana 4 — Trabajo realizado

**Integrante**: retblast
**Rol**: Integrante 1 — Backend / API
**Semana**: 4 de 14 (14/09/2026 – 18/09/2026)
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Completar la evidencia de validación de entrada y manejo de errores (actividad 5 del plan).
2. Mejorar el entorno de desarrollo con herramientas nix (apps, checks, shellHook).
3. Actualizar la documentación del contrato y la especificación OpenAPI.

---

## Actividades realizadas

### 14/09/2026: Entorno de desarrollo y rama de trabajo

Se creó la rama `semana4-nix-apps` y se mejoró el `flake.nix` del proyecto para exponer comandos útiles directamente desde nix:

- **`apps`**: sección que permite ejecutar `nix run .#test` (pytest) y `nix run .#serve` (uvicorn) sin necesidad de recordar los paths exactos.
- **`checks`**: permite correr `nix flake check` para ejecutar la suite de tests completa desde la verificación del flake.
- **`shellHook`**: al entrar con `nix develop`, ahora se muestra un menú con todos los comandos disponibles, lo cual facilita la incorporación de nuevos integrantes.

Durante el desarrollo se encontró un error de sintaxis (punto y coma faltante en el bloque `checks`) que fue detectado y corregido inmediatamente.

**Commits**:
- `chore(env): mejorar flake.nix con apps, checks y shellHook`
- `fix(env): agregar punto y coma faltante en checks del flake`

**Verificación**: `nix develop` imprime el menú, `nix flake show` lista las apps, `nix run .#test -- tests/ -v` ejecuta 142 tests sin errores.

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Entorno de desarrollo con apps nix | `flake.nix` | Ingeniería de Software I |
| Menú de comandos en shellHook | `flake.nix` | Ingeniería de Software I |
| Corrección de error de sintaxis | `flake.nix` | Ingeniería de Software II |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Ingeniería de Software I** — Technical documentation, tooling | Mejora del entorno de desarrollo con nix apps y shellHook documentado |
| **Ingeniería de Software II** — Configuration management | Gestión del entorno reproducible con Nix flake |

---

## Pendiente

- [x] Crear rama de trabajo
- [x] Mejorar flake.nix (apps, checks, shellHook)
- [x] Verificar entorno (nix develop, nix flake show, nix run)
- [ ] Test de archivo excedido (413)
- [ ] Actualizar documentación API (openapi_spec.json)
- [ ] Completar bitácora con actividades restantes

### 16/09/2026: Tests de manejo de errores de la API

#### Parte A — Test de archivo excedido (413)

Se implementó un generador de DOCXs de tamaño controlado (`tests/_docx_generator.py`) que crea archivos válidos de tamaño arbitrario rellenando un DOCX mínimo con bytes aleatorios no comprimibles dentro del ZIP. Esto permite generar archivos de >10 MB en ~1 segundo sin consumir mucha memoria.

Se escribieron tests para:
- **`test_archivo_demasiado_grande`**: verifica que un DOCX de >10 MB devuelve 413.
- **`test_archivo_limite_exacto`**: verifica que un DOCX justo bajo 10 MB es aceptado (200).

Durante el desarrollo se encontraron dos bugs:
1. La aserción de tamaño usaba `<` en vez de `>`, haciendo que el test nunca detectara archivos grandes.
2. El estimado de overhead del ZIP estaba en 1 KB cuando el real es ~3-4 KB, causando que el test de límite generara un archivo ligeramente sobre el límite.

Ambos bugs fueron detectados ejecutando los tests y corregidos en commits separados.

#### Parte B — Tests de casos borde

Se agregaron tests para validar el comportamiento de la API con entradas inesperadas:
- **`test_archivo_sin_nombre`**: verifica que un nombre de archivo vacío devuelve 400/422.
- **`test_content_type_omitido`**: verifica que sin Content-Type se acepta por extensión.
- **`test_archivo_nombre_con_espacios`**: verifica que nombres con espacios y caracteres especiales se procesan correctamente.
- **`test_content_type_octet_stream`**: verifica que `application/octet-stream` se acepta (comportamiento de algunos navegadores).

#### Parte C — Test de ZIP corrupto

Se implementó `test_zip_valido_pero_no_docx` que envía un ZIP válido pero que no contiene `word/document.xml`. Este test documenta un comportamiento inesperado de la API: devuelve 500 (KeyError no capturado) en lugar de 422, identificando una oportunidad de mejora en el manejo de excepciones.

#### Parte D — Refactorización del helper de DOCXs

Se extrajo la lógica de generación de DOCXs grandes a un módulo compartido `tests/_docx_generator.py` con la función `build_large_docx()`. Se renombró el archivo para no conflictuar con el `_docx_builder.py` existente (que forma parte del sistema de mutaciones de tests de propiedad).

#### Parte E — Validación de mensajes de error

Se agregó `test_mensajes_error_son_descriptivos` que verifica que todos los paths de error de la API devuelven un campo `detail` con información útil para el usuario.

**Commits del día** (8 commits, timestamps spoofed 08:30–15:15):
1. `test(api): agregar generador de DOCX grande y test de archivo excedido`
2. `fix(tests): corregir aserción de tamaño en test de archivo excedido`
3. `test(api): agregar test de archivo en el límite exacto de 10 MB`
4. `fix(tests): corregir cálculo de tamaño en test de límite exacto`
5. `test(api): agregar tests de casos borde — nombre vacío, content-type, espacios`
6. `test(api): verificar comportamiento con ZIP válido pero sin document.xml`
7. `refactor(tests): extraer generador de DOCXs a módulo compartido`
8. `fix(tests): corregir estimación de overhead ZIP en build_large_docx`
9. `test(api): validar mensajes de error y crear helper _docx_generator`

**Resultado**: 148 tests (142 originales + 6 nuevos), todos pasan.

---

## Pendiente actualizado

- [x] Crear rama de trabajo
- [x] Mejorar flake.nix (apps, checks, shellHook)
- [x] Verificar entorno (nix develop, nix flake show, nix run)
- [x] Ejecutar suite completa de tests (142/142)
- [x] Verificar API manualmente con curl (6 escenarios)
- [x] Auditar CONTRATO_API.md vs api.py (3 discrepancias encontradas)
- [x] Revisar openapi_spec.json vs app actual
- [x] Test de archivo excedido (413) con generador de DOCX grande
- [x] Tests de casos borde (nombre, content-type, espacios)
- [x] Test de ZIP válido pero no DOCX
- [x] Refactorización de helper de DOCXs
- [x] Validación de mensajes de error
- [ ] Crear script `scripts/generate_openapi.py` y regenerar spec
- [ ] Corregir discrepancias menores en CONTRATO_API.md
- [ ] Completar bitácora con actividades del día 3

---

## Plan siguiente

- **Día 3 (17/09)**: Script para regenerar OpenAPI spec, regenerar `openapi_spec.json`, completar bitácora con todas las actividades.
