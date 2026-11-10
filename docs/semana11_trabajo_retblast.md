# Bitácora Semana 11 — retblast

- **Integrante**: retblast (Integrante 1 — Backend / API)
- **Semana**: 11
- **Fechas**: 2026-11-08 → 2026-11-14 (semana en curso)
- **Rol**: Backend / API (FastAPI, contrato de la API, despliegue en la
  máquina del operador, documentación de instalación y verificación)
- **Ramas**: `docs/instalacion-windows-11` (PR #87),
  `docs/arreglos-documentacion` (PR #88),
  `feat/icono-escritorio-wsl` (PR #89) y
  `fix/conteos-suite-y-ci-spa` (este PR).

---

## Objetivos de la semana

1. **Actividad 4 — instalación y despliegue**: dejar el proyecto operable en
   una máquina nueva, con una guía de instalación que cubra Windows 11 y un
   acceso directo de escritorio para el operador.
2. **Cierre documental**: dejar la documentación del repositorio con
   redacción neutra y con las cifras de la suite correctas.
3. **Verificación del acceso directo**: comprobar que la SPA se sirve desde
   la API y que el flujo de Windows queda cubierto por pruebas y por un
   paso propio en el CI.

---

## Actividades realizadas

### 2026-11-08 — Decisiones de dominio y estado del motor

Se aplicaron las decisiones del 2026-11-08 sobre los hallazgos de la
auditoría: sangría literal sin exención por estilo, anexos como «Base de
datos», endurecimiento de la sola regla `error` de la carátula, igualdad
normalizada del índice y `palabras_clave_minimo` mantenida en `error`. Las
cinco plantillas oficiales siguen en rojo a propósito.

### 2026-11-09 — Guía de instalación con soporte para Windows 11 (PR #87)

- **`docs/INSTALACION.md`**: guía nueva de 388 líneas. Cubre Linux y macOS
  con Nix, Windows 10/11 con WSL2 (camino soportado) y el camino nativo de
  Windows como alternativa para levantar la API y la SPA. Incluye
  requisitos, verificación, puesta en marcha, checklist y problemas
  comunes.
- **README y handover**: el README enlaza la guía y refleja la decisión
  sobre `formato` y el rojo deliberado de `palabras_clave_minimo`; el
  handover de despliegue en la máquina del operador apunta a la guía.
- **Verificación**: suite completa en verde, escaneo de secretos limpio y
  CI en verde.

### 2026-11-09 — Corrección de redacción y consistencia (PR #88)

- Se corrigieron las variantes regionales que quedaban en el aviso de
  `AGENTS.md` y en dos líneas de `docs/HANDOVER_AUDITORIA_2026-10-26.md` y
  `docs/NOTA_F5_Y_API_DSL.md`.
- Las bitácoras históricas de las semanas anteriores quedaron fuera de
  alcance: son el registro de cómo se escribió cada semana.

### 2026-11-09 — Acceso directo de escritorio para WSL (PR #89)

- **La API sirve la SPA**: `validator/api.py` monta `frontend/dist` en `/`
  cuando el build existe. El montaje va después de todas las rutas, así que
  no tapa `/validar`, `/docs` ni el resto de la API.
- **Lanzador** (`scripts/lanzar_app.py`): levanta uvicorn en `127.0.0.1`,
  espera a que la API responda y abre el navegador de Windows.
- **Acceso directo**: `tools/launcher/VistoBueno.bat` (ASCII con CRLF) entra
  a WSL y ejecuta el lanzador; `crear_acceso_directo.ps1` crea el acceso
  directo `VistoBueno` en el escritorio con el ícono `vistobueno.ico`
  (6 tamaños, generado por `scripts/generar_icono.py`).
- **Pruebas**: `tests/test_api_spa.py` y `tests/test_lanzador.py`, 13 tests
  nuevos.
- **Verificación**: `nix flake check` dio «all checks passed»; la suite con
  `frontend/dist` construido pasó; el lanzador se probó en `:8010` con `/`
  y `/docs` respondiendo `200` y apagado limpio.

### 2026-11-09 — Revisión posterior al merge y correcciones (este PR)

La revisión de los tres PRs mergeados encontró dos problemas:

1. **Cifras de la suite desactualizadas**: los documentos declaraban 742
   tests recolectados y 736 en verde, pero la suite quedó en 755
   recolectados. Se corrigieron el README, la guía de instalación, el kit
   del piloto y el plan de lotes. Las cifras se comprobaron con las cuatro
   combinaciones posibles de `recursos/` y `frontend/dist`.
2. **El CI no ejercitaba la SPA**: el test de integración solo corre si el
   build existe, así que en el job `check` quedaba en `skip`. Se agregó un
   paso propio en el job `frontend`, después del build, que corre
   `tests/test_api_spa.py` con la SPA ya construida.

---

## Evidencias producidas

| Evidencia | Dónde |
|-----------|-------|
| Guía de instalación | `docs/INSTALACION.md` |
| Lanzador de escritorio | `scripts/lanzar_app.py` |
| Acceso directo de Windows | `tools/launcher/VistoBueno.bat`, `tools/launcher/crear_acceso_directo.ps1` |
| Ícono de la aplicación | `tools/launcher/vistobueno.ico`, `scripts/generar_icono.py` |
| Montaje de la SPA en la API | `validator/api.py` (`_montar_spa`) |
| Pruebas de la SPA y del lanzador | `tests/test_api_spa.py`, `tests/test_lanzador.py` |
| Paso de CI de la SPA | `.github/workflows/ci.yml` (job `frontend`) |
| Kit del operador actualizado | `docs/PILOTO_OPERADOR.md` |
| Bitácora | este archivo |

- Commits de la semana: `1f94571` (guía de instalación), `a548e41`
  (redacción), `7f4f683` (acceso directo) y los commits de este PR.
- Suite actual: **755 tests recolectados**. Con `recursos/` y
  `frontend/dist`: **749 pasan y 6 quedan como `xfail(strict=True)`** (los
  criterios de aceptación de AUD-24 a AUD-27 del motor). En un clon limpio
  pasan 745 y se omiten 4, porque `recursos/` y el build del frontend no
  están versionados.
- Verificación del flujo de Windows: el `.bat` y el `.ps1` se revisaron y
  se fijó el fin de línea CRLF, pero el flujo no se ejecutó en un Windows
  real desde este entorno. Queda pendiente probarlo en la máquina del
  operador.

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: el acceso directo separa el arranque de
  la aplicación en una capa comprobable (el lanzador, con sus pruebas) y
  una capa de plataforma (el `.bat` y el `.ps1`). El paso de CI cubre la
  parte que antes no tenía verificación.
- **Estructura de Datos**: el montaje de la SPA conserva el orden de
  resolución de rutas de FastAPI: primero las rutas de la API, después el
  recurso estático. Así el contrato de la API no cambia.
- **Redes de Computadoras I**: el lanzador mantiene la API en loopback
  (`127.0.0.1`) y desactiva `proxy_headers`, igual que el resto del
  despliegue documentado.
- **Ingeniería de Software I**: la guía de instalación documenta los dos
  caminos de Windows, sus límites y el checklist de puesta en marcha; las
  cifras de la suite se corrigieron para que la documentación no contradiga
  al código.

---

## Dificultades y aprendizajes

- **Documentar el resultado de una prueba es más frágil que la prueba**:
  la guía enumeraba los conteos de la suite como texto fijo. Cada test
  nuevo los dejó obsoletos sin que nada fallara. Ahora la guía explica de
  qué depende cada cifra.
- **Una prueba que se omite no es una prueba verde**: el test de la SPA
  se saltaba en el CI porque el build no existe ahí. La cobertura real
  llegó cuando el CI construyó la SPA antes de correr la prueba.
- **Un acceso directo esconde dos sistemas**: el atajo de Windows ejecuta
  un `.bat` que entra a WSL y arranca un proceso de Python. Cada frontera
  necesita su propio punto de verificación: el `.bat` con CRLF, el
  lanzador con pruebas unitarias y el montaje de la SPA con un test de
  integración en CI.

---

## Plan de la semana siguiente

1. Coordinar el piloto con la sede: enviar el Anexo B de
   `docs/PILOTO_OPERADOR.md` y acordar la fecha de la sesión.
2. Ejecutar el piloto (Actividad 16) y registrar los hallazgos.
3. Cerrar la Actividad 17 con el registro de documentos y el informe final.
4. Verificar el clic manual contra la instancia de la sede (Actividad 15)
   y la instalación en Windows real del acceso directo.
5. Revisar los PRs abiertos de Int3 (#72, #73 y #75) y desbloquear el
   #73, que está en conflicto.
6. Quitar las marcas `xfail` cuando Int3 cierre AUD-24 a AUD-27 y
   actualizar las cifras de la suite en el mismo commit.
