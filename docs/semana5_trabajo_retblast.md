# Semana 5 — Trabajo realizado

**Integrante**: retblast
**Rol**: Integrante 1 — Backend / API
**Semana**: 5 de 14 (28/09/2026 – 02/10/2026)
**Proyecto**: VistoBueno — Validador automático de formato de tesis (UNT FECyC)

---

## Objetivos de la semana

1. Implementar el módulo de notificación por correo (actividad 6 del plan):
   plantilla HTML, envío SMTP best-effort, cableado al flujo de `POST /validar`.
2. Blindar el repositorio contra filtración de credenciales SMTP
   (pre-commit + CI).
3. Verificar el envío de extremo a extremo con un sink SMTP local (aiosmtpd).

> Nota: la revisión v7 del plan ubica la actividad 6 en S7–S9; este trabajo
> adelanta el cronograma en ~2 semanas.

---

## Actividades realizadas

### 28/09/2026: Scaffolding de la notificación y seguridad de credenciales

Se creó la rama `semana5-notificacion-correo` y el PR #37 con la base del
módulo de notificación:

- **`validator/notificacion.py`**: plantilla HTML + texto plano del correo de
  observaciones (registro formal, `rule_id` como referencia estable, escape
  HTML del contenido dinámico) y envío SMTP con stdlib (`smtplib` +
  `EmailMessage`, con encabezados `Date`/`Message-ID` que `send_message` no
  agrega y los servidores reales exigen). Deshabilitado por defecto: se activa
  solo con `VISTOBUENO_NOTIFICACIONES=1` + `VISTOBUENO_SMTP_*`.
- **Barrera anti-filtración en tres capas**: `.gitignore` (`.env`, `*.eml`),
  hook de pre-commit (`scripts/verificar_secretos.py`, 8 tests propios) y paso
  de escaneo en la CI (cubre `git commit --no-verify`).
- **`flake.nix`**: dependencia `aiosmtpd` + apps `smtp-dev` (sink SMTP en
  127.0.0.1:8025) y `test-local`.
- **17 tests unitarios** de `ConfigSMTP`, plantilla, escape adversario y envío
  mocked.

**Commits**: 8 (de `8b2a1d6` a `57987ad`, ver PR #37).

---

### 30/09/2026: CI roja, cableado opt-in y pruebas E2E

#### Parte A — Diagnóstico y corrección de la CI roja

La CI del PR fallaba con `SyntaxError: multiple exception types must be
parenthesized` en `scripts/verificar_secretos.py`. Causa: `ruff format`, con
`target-version = py314` (pyproject.toml), produce la sintaxis sin paréntesis
del PEP 758 (`except A, B:`), válida **solo** en Python 3.14+; localmente todo
pasaba bajo el Python 3.14 de Nix, pero el paso de escaneo corría con el
python3 del runner (3.12/3.13).

Se corrigió en dos commits que muestran la evolución del diagnóstico:

1. `d53d44b`: parentizado (corrección de síntoma) — la CI avanzó hasta el paso
   `ruff format --check`, que exige la sintaxis sin paréntesis de vuelta.
2. `c11552d`: **causa raíz** — el paso usaba un intérprete que viola el propio
   `requires-python >= 3.14` del proyecto. Se ancló con `actions/setup-python`
   3.14 y se revirtió el parentizado del script. Nota: en `notificacion.py` el
   `except (OSError, smtplib.SMTPException) as e` mantiene paréntesis porque
   la forma sin paréntesis del PEP 758 no permite cláusula `as`.

#### Parte B — Cableado del envío con estado y detalle

Se cableó la notificación al flujo de `POST /validar` (commit `691a7b0`) con
un campo nuevo en la respuesta: `notificacion: {estado, detalle}`.

- `enviar_notificacion()` pasó de devolver `bool` a devolver
  `ResultadoEnvio(enviado, detalle)`, donde `detalle` lleva el motivo técnico
  del fallo (`TipoDeError: mensaje`) para el personal del repositorio.
- Estados: `enviado | fallo | sin_correo | no_solicitado |
  sin_observaciones | deshabilitado`, con prioridad
  `sin_correo > no_solicitado > sin_observaciones > deshabilitado > fallo/enviado`.
- Best-effort: un fallo SMTP jamás cambia el código HTTP.

#### Parte C — Envío opt-in (decisión de diseño)

Se detectó un problema de producto: con envío automático, cada validación
intermedia de una misma sesión de revisión le dispararía un correo al
estudiante. Se decidió hacer el envío **opt-in por solicitud** (commit
`93d1635`): campo de formulario `notificar` (default `false`), nuevo estado
`no_solicitado` y sin apertura de conexión SMTP sin consentimiento explícito
del operador. La herramienta es de uso interno: quien decide es el personal
del repositorio, y el correo va dirigido al estudiante con registro formal.

#### Parte D — Pruebas E2E contra un sink SMTP real

`tests/test_notificacion.py` ganó una clase E2E que levanta un sink real
(aiosmtpd) y prueba el flujo completo a través de la API (6 escenarios):
enviado (verifica destinatario normalizado, asunto, cuerpo texto/HTML y
`rule_id`s de las reglas fallidas), deshabilitado, fallo de conexión (200 +
`fallo` + detalle), sin correo, `notificar` sin correo y sin opt-in.

**Hallazgos técnicos durante las E2E**:

- aiosmtpd 1.4.6 no soporta `port=0`: nunca actualiza `Controller.port`
  tras el bind, así que su propio trigger de arranque conecta al puerto 0 y
  falla. El sink reserva un puerto libre manualmente antes de crear el
  controlador.
- `email-validator` normaliza solo el dominio (la parte local conserva
  mayúsculas por diseño); las pruebas lo documentan.

#### Parte E — Documentación y sincronización

- **`docs/CONTRATO_API.md` → v1.3.0**: campo `notificar`, `notificacion`
  en la respuesta, tabla de estados con sugerencias de UI, configuración
  SMTP por variables de entorno, ejemplo `curl` y changelog.
- **`docs/FLUJO_API.md` → v1.2**: rama de notificación en el diagrama de
  flujo, con nota de que nunca altera el código HTTP.
- **`docs/openapi_spec.json`** regenerado dos veces (v1.3.0 y luego con
  `notificar`); verificación de idempotencia corregida a lo largo del
  proceso (diff contra árbol limpio, no contra el índice).
- **`AGENTS.md`**: módulo de notificación en componentes, diagrama, flujo de
  datos, comandos (`smtp-dev`), árbol del repo y responsabilidades de
  Integrante 1. Conteo de suite sincronizado a 244 tests (también en
  `docs/diseno/00_indice_diseno.md`).
- Descripción del PR #37 actualizada al contrato real.

**Resultado del día**: **244/244 tests** (213 previos + 31 nuevos),
`ruff format --check`, `ruff check` y `mypy validator/` limpios, CI verde en
todos los pasos (incluido el drift-check de openapi_spec.json).

---

## Evidencias producidas

| Evidencia | Archivo | Competencia curricular |
|-----------|---------|------------------------|
| Módulo de notificación (plantilla + envío best-effort) | `validator/notificacion.py` | Ingeniería de Software II |
| Cableado opt-in con estado y detalle | `validator/api.py`, `validator/api_models.py` | Ingeniería de Software II |
| Tests unitarios del módulo (17) | `tests/test_notificacion.py` | Ingeniería de Software II |
| Tests E2E con sink SMTP real (6) | `tests/test_notificacion.py` | Ingeniería de Software II |
| Escáner de secretos SMTP (3 capas) | `scripts/verificar_secretos.py`, `.pre-commit-config.yaml`, `ci.yml` | Ingeniería de Software I |
| Apps nix smtp-dev / test-local | `flake.nix` | Ingeniería de Software I |
| Anclaje de la CI a Python 3.14 | `.github/workflows/ci.yml` | Ingeniería de Software I |
| Contrato de API v1.3.0 (notificación) | `docs/CONTRATO_API.md` | Ingeniería de Software I |
| Diagrama de flujo con notificación | `docs/FLUJO_API.md` | Redes de Computadoras I |
| Especificación OpenAPI regenerada | `docs/openapi_spec.json` | Ingeniería de Software I |
| Guía de trabajo actualizada | `AGENTS.md` | Ingeniería de Software I |

---

## Relación con competencias

| Competencia | Actividad |
|-------------|-----------|
| **Ing. de Software II** — Construcción e integración de componentes | Cableado del envío SMTP al endpoint, opt-in, estados con detalle |
| **Ing. de Software II** — Manejo de errores y robustez | Best-effort (fallo SMTP nunca rompe la respuesta HTTP), motivo técnico expuesto |
| **Ing. de Software II** — Pruebas | 31 tests nuevos: unitarios con dobles de red + E2E con servidor SMTP real |
| **Ing. de Software I** — Gestión de configuración | Diagnóstico PEP 758/ruff/CI (causa raíz vs síntoma), anclaje de intérprete |
| **Ing. de Software I** — Seguridad de credenciales | Escáner en 3 capas (gitignore + pre-commit + CI) |
| **Redes de Computadoras I** — Protocolos de aplicación | SMTP (STARTTLS, autenticación, encabezados `Date`/`Message-ID`), multipart/form-data |

---

## Pendiente

- [x] Crear rama `semana5-notificacion-correo` y PR #37
- [x] Módulo de notificación con plantilla HTML + texto plano
- [x] Barrera anti-secretos (pre-commit + CI + gitignore)
- [x] Corregir CI roja (anclaje a Python 3.14)
- [x] Cablear envío con `notificacion.estado`/`detalle`
- [x] Envío opt-in (`notificar`) con estado `no_solicitado`
- [x] E2E con sink SMTP (aiosmtpd): 6 escenarios
- [x] CONTRATO_API v1.3.0 + FLUJO_API v1.2 + openapi_spec regenerada
- [x] AGENTS.md y 00_indice_diseno.md sincronizados (suite 244)
- [x] Bitácora semana 5
- [ ] Merge del PR #37 tras revisión
- [ ] Credenciales SMTP institucionales y buzón definitivo (pendiente del
      área de Repositorio — el módulo queda deshabilitado hasta entonces)
- [ ] Coordinar con Integrante 2 el formulario con `correo` + `notificar`

---

## Plan siguiente

- **Actividad 7 (pruebas de regresión, S6–S14 en el cronograma v7)**: continuar
  la ampliación de la suite tras cada cambio significativo.
- Cierre operativo de la actividad 6 cuando el área de Repositorio entregue
  las credenciales SMTP: configurar el entorno del servidor y validar un envío
  real contra el buzón institucional.
- Soporte a Integrante 2 para la integración del formulario (`correo`,
  `notificar`, `notificacion.estado`) y del semáforo en la UI.
