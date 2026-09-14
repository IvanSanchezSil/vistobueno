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

---

## Plan siguiente

- Implementar test de archivo excedido (413) con generador de DOCX grande usando lorem ipsum.
- Crear script para regenerar la especificación OpenAPI.
