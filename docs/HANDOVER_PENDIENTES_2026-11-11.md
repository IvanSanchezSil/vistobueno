# Handover de pendientes — 2026-11-11

**Estado:** abierto.
**Alcance:** estado real de los PRs abiertos, pendientes del motor de ficha,
pendientes de la auditoría y trabajo de API, frontend y despliegue.
**Regla principal:** el autor de cada PR corrige su PR. Este documento no
autoriza a otra persona a reemplazar, mergear ni cerrar #73/#75/#91.

**Verificación base:** `master` limpio; última suite medida:
**806 passed, 6 xfailed**. La suite no cubre la estructura real de todas las
plantillas; un verde no demuestra que el motor acierte (AUD-20).

---

## 1. Resumen ejecutivo

| PR | Head revisado | Mergeable | Autor | Decisión |
|----|---------------|-----------|-------|----------|
| #73 | `8c847a8` | **CONFLICTING** | Iván Sánchez | El autor corrige. **No mergear ni abrir rama de rescate.** |
| #75 | `f6d3810` | **MERGEABLE** | Iván Sánchez | Tiene código real; el body está desactualizado. El autor completa lo que falta. |
| #91 | `d1d8485` | **MERGEABLE** | Iván Sánchez | Solo tests/docs; rebasear y mergear si CI sigue verde. |

Puntos que no cambian:

- AUD-07 sigue la decisión del 2026-11-08: **no acotar la regla a “bachiller”**.
- `palabras_clave_minimo` sigue en `error`; las 5 plantillas en rojo son
  intencionales.
- No se agrega `formato` a `POST /validar`.
- No se escribe en la API de DSpace.
- No se usa el mock de reporte en producción.

---

## 2. PR #73 — auditoría del motor

### 2.1 Estado del hilo

- Revisión inicial: `2026-11-04`, contra `72e7e38`. Solicitaba cambios en
  AUD-01, AUD-02, AUD-03, AUD-04, AUD-07, AUD-15, AUD-20 y documentación.
- Respuesta del autor: `2026-11-11 01:01`, con el head `8c847a8`.
- Ampliación de la revisión: `2026-11-11 04:49`, sobre AUD-07. Es posterior
  a la respuesta del autor y **todavía no está aplicada**.
- El PR sigue **CONFLICTING** y sin aprobación formal. No mergear.

### 2.2 Lo que ya está encaminado

| Tema | Estado en `8c847a8` | Acción |
|------|---------------------|--------|
| AUD-01 | Incluye `_texto_con_tabs`, el híbrido de `_norm_indice` y tests del índice real. Los tests dirigidos pasan. | Mantener. El autor debe adjuntar evidencia sobre la tesis real y no reabrir el endurecimiento. |
| AUD-02 | `hasta_final` en código, `docs/DSL.md`, linter y conteo `encontrados=N/M`. | Mantener. Verificar con anexos reales. |
| AUD-03 | Adoptó el módulo de `master` (`validator/detalle.py`, PR #78). No duplica el formato. | No reimplementar. |
| AUD-04 | Notas `EVALUADO` con fecha y decisión. | Mantener; al ajustar AUD-07, corregir la nota para que no justifique el filtro “bachiller”. |
| AUD-15 | Adoptó el escape de `master` (PR #78). | No reimplementar. |
| AUD-20 | Hay fixtures nuevos y tests de índice con tabuladores. | Parcial: documentar que son opt-in y que la estructura plana del factory no representa la plantilla real. |

### 2.3 Lo que el autor todavía debe arreglar

#### AUD-07 — bloqueante de política

**Problema actual:** el YAML sigue con:

```yaml
xpath: //w:body/w:p[contains(..., 'para optar')]
  [contains(..., 'bachiller')][1]/...
n_a_si_sin_nodos: true
```

y el test `test_aud07_otras_titulaciones_son_no_aplicables` espera
`aplicable=False` para la línea de Licenciado.

**Corrección requerida:**

1. Quitar el filtro `bachiller` del XPath. La regla debe seguir usando el
   XPath amplio de `para optar`.
2. El caso “Para Optar el Título Profesional de Licenciado…” debe dar
   `aplicable=True` y `passed=False` (warning por 12 pt frente a 13 pt).
3. `n_a_si_sin_nodos` se conserva solo para documentos que **no tengan
   ninguna** línea `para optar`. No se usa para convertir Licenciado en n/a.
4. Cambiar el test de “otras titulaciones” para que espere evaluación, no
   n/a. Mantener un test separado para un documento sin la línea.
5. Actualizar la nota `EVALUADO` de `caratula_optar_grado_tamano`: el manual
   exige 13 pt también para Licenciado; el desvío de la plantilla se
   documenta, no se oculta.

#### AUD-05 — solo documentación

El autor dejó la decisión documentada, pero no implementó el cambio.

**Corrección requerida:** endurecer solo la regla `error`
`caratula_autores_tamano`:

- todos los runs con texto;
- todos los párrafos de autores hasta `ASESOR`/`ORCID`;
- mantener los selectores actuales de las reglas `warning`, con la limitación
  documentada.

No endurecer las reglas `warning` en este PR.

#### AUD-06 — solo documentación

**Corrección requerida:** implementar la igualdad del título normalizado y
dejar `_sigpalabra` como respaldo cuando el título normalizado tenga menos de
4 caracteres. Depende de AUD-01; no hacerlo antes de que AUD-01 quede estable.

#### AUD-02 y AUD-20 — verificación pendiente

- AUD-02: verificar que los anexos reales se reconocen y que `faltan` incluye
  todos los faltantes, no un corte de 8.
- AUD-20: dejar escrito que los fixtures nuevos son opt-in. Si
  `configuracion_base()` sigue plana, no afirmar que el factory replica la
  plantilla real.

#### Cierre documental y de conteos

- Corregir el body: no puede decir 757/4/6 si el estado real es otro.
- Actualizar la tabla §11 de `docs/HANDOVER_AUDITORIA_2026-10-26.md` con el
  estado real de cada AUD.
- Actualizar `AGENTS.md` solo cuando el autor haya cerrado el PR y con la
  aprobación del usuario. No reescribir el aviso para justificar AUD-07.
- Actualizar `docs/CONTRATO_API.md` si cambia el ejemplo de `found`; el
  ejemplo actual todavía muestra `@w:val=['26']`.
- No afirmar que `_mutations.py` está sincronizado si no hay reglas nuevas;
  el autor ya corrigió esa afirmación.

### 2.4 Borrador de comentario para el autor

No publicado. Usarlo solo si hace falta un recordatorio; el comentario de
revisión del 2026-11-11 ya contiene la decisión.

> El head `8c847a8` todavía restringe `caratula_optar_grado_tamano` a
> `bachiller` y devuelve `aplicable=False` para Licenciado. Eso contradice la
> decisión del 2026-11-08: el XPath debe quedar amplio (`para optar`) y el
> caso Licenciado debe evaluarse con warning por 12 pt frente a 13 pt.
> `n_a_si_sin_nodos` solo aplica cuando no existe ninguna línea `para optar`.
>
> Por favor:
>
> 1. quitar el filtro `bachiller` del YAML;
> 2. cambiar el test de Licenciado para esperar `aplicable=True` y
>    `passed=False`;
> 3. mantener un test separado para un documento sin la línea;
> 4. implementar AUD-05 y AUD-06, que hoy siguen solo documentados;
> 5. actualizar la nota `EVALUADO`, la tabla §11, el body y el conflicto con
>    `master`.
>
> No mergear hasta que la suite y la revisión de AUD-07 estén verdes.

---

## 3. PR #75 — motor de ficha de depósito

### 3.1 Qué contiene realmente

El body dice “sin código de motor todavía”. Es falso: el diff contiene
extractor, analizadores, reglas de ficha, compilador y tests.

- `0447530` → contexto `caratula_ficha` y `is_caratula_ficha`.
- `21b08f2` → `seleccion` y `quitar_sufijo` en `AnalizadorExtraccion`.
- `833ec39` → reglas de ficha.
- `f6d3810` → `detectado=false` para valores vacíos y quita el xfail de
  AUD-25.
- Medición dirigida: **9 passed, 4 xfailed** en
  `tests/test_captura_ficha.py` y `tests/test_extractor_edgecases.py`.

### 3.2 Lo que falta

| Tema | Estado | Criterio de aceptación |
|------|--------|------------------------|
| F-1, `caratula_ficha` | Hecho | Incluye el párrafo con `w:pPr/w:sectPr`; no cambia el contexto `caratula` de las 49 reglas. |
| F-2, selección | Hecho | `seleccion: primero/ultimo` se aplica después de `filtro` y conserva nodo/página. |
| F-3, título | Parcial | El prefijo `Título del trabajo de investigación:` se quita. Falta un test explícito. La decisión de conservar `, Trujillo 2024` sigue abierta; no activar `quitar_sufijo` sin decidirla. |
| F-3, autores | **Falla** | `ficha_autores` usa `[1]/following-sibling::w:p[1]` y captura un solo autor. Debe iterar todos los párrafos después de `AUTORES:`/`AUTORA:`, saltar ORCID y parar en `ASESOR`, `Línea` u otra etiqueta. No partir por la coma interna de “Apellidos, Nombres”. |
| F-3, asesor | **Falla** | El XPath selecciona el párrafo de la etiqueta `ASESORA:`. Debe preferir el párrafo siguiente; si la etiqueta y el nombre están en el mismo párrafo, usar el fallback de prefijo. |
| F-3, año | **Falla** | `ficha_anio` usa `[1]` y `contexto: caratula_ficha`; el `[1]` hace que `seleccion: ultimo` no vea la línea de portada. Debe seleccionar todos los candidatos, filtrar el año y quedarse con el de portada (2026), no con el del título (2024). |
| F-3, resumen | Sin prueba real | `ficha_resumen` usa `seccion: {inicio: ^RESUMEN$}`. El fixture arma `RESUMEN` como párrafo normal; el tokenizer no lo reconoce como título. Corregir el fixture con estilo de título o dar un fallback explícito al analizador. Agregar test del texto completo. |
| F-3, palabras clave | **Falla** | El mismo problema de `RESUMEN` deja `dc.subject` vacío. Después de corregir la sección, `quitar_sufijo` debe quitar el punto final de la última clave y no dejar entradas vacías. |
| F-4, `detectado` | Parcial | `valor != ""` corrige el asesor vacío, pero una lista vacía `[]` sigue contando como detectada. Usar una comprobación de valor utilizable (no vacío y, si es lista, con elementos). |
| F-5, tests | Parcial | Quitar los 4 `xfail(strict=True)` cuando pasen: autores, asesor, año y palabras clave. Agregar regresión del año 2024 vs 2026 y de dos autores. |
| F-5, constancia | Pendiente | `tests/test_constancia.py` debe probar 2 autores reales → 2 constancias y 2 filas, cada una con su matrícula. |
| F-6, evaluación | Pendiente | `scripts/eval_contra_plantillas.py` debe aceptar `reglas` y `rules`; test con `reglas_unt.yaml`. |
| F-7, dominio | Resuelto | `palabras_clave_minimo` se mantiene `error`; no reabrir. |
| Paridad | Pendiente | Agregar el caso real a `tests/test_paridad_formatos.py`; no dejar aserciones vacías. |
| Body/bitácora | Desactualizado | Corregir la afirmación “sin código” y los estados de F-1 a F-7. |

### 3.3 Borrador de comentario para el autor

No publicado.

> El PR ya tiene código real, aunque el body diga lo contrario. La medición
> dirigida da 9 passed y 4 xfailed. Para cerrar F-3 faltan cuatro capturas:
>
> - autores: todos los párrafos después de `AUTORES:`/`AUTORA:`, saltando
>   ORCID y parando en `ASESOR`/`Línea`; una persona por párrafo, sin partir
>   por la coma interna;
> - asesor: el párrafo siguiente a `ASESORA:` (con fallback si está en el
>   mismo párrafo);
> - año: el 2026 de la línea de portada, no el 2024 del título; el `[1]` del
>   XPath actual impide que `seleccion: ultimo` funcione;
> - palabras clave: corregir la sección `RESUMEN` del fixture o el fallback
>   del analizador, y quitar el punto final.
>
> Además, `detectado` debe ser falso para listas vacías, y hay que agregar
> los tests de resumen, título, constancia de 2 autores y F-6. Cuando pasen,
> quitar los 4 `xfail`.
>
> No mergear hasta que la suite completa y el flujo
> `nix run .#test-ficha-deposito` estén verdes.

---

## 4. PR #91 — seguimiento del linter

- Solo toca `tests/test_t2_linter.py`, `docs/PLAN_SEMANA9.2_LINTER.md` y
  `docs/semana9.2_trabajo_ivanSanchezSil.md`.
- No toca código de producción.
- El body reporta 805/4/6; la base actual es 806/6.
- Acción: rebasear sobre `master`, ejecutar `tests/test_t2_linter.py` y la
  suite completa, corregir conteos y mergear solo con CI verde.
- No requiere cambios de motor.

---

## 5. Pendientes de Int1 — API y contrato

1. Agregar `ficha_deposito` a `tests/test_ejemplos_versionados.py`. Hoy el
   golden compara semáforo, resumen, resultados y prompts, pero no la ficha.
2. Corregir `docs/ejemplos/doc_bueno.docx` y `doc_malo.docx`: `_rels/.rels`
   referencia `media/logo.png` y esa parte no existe. El extractor los lee,
   pero `python-docx` falla con `KeyError`; Word puede repararlos o
   rechazarlos.
3. Mantener el contrato v1.12.0. No cambiar `/validar` ni el formato de la
   ficha.
4. Actualizar `docs/HANDOVER_API_IA.md`: la versión real es v1.12.0; la
   1.6.0 del documento es vieja.
5. Verificar `tests/test_constancia.py`, `tests/test_api_buzon.py` y
   `scripts/e2e_ficha_deposito.sh`.
6. Mantener el token `X-VistoBueno-Token` solo para peers remotos; el
   loopback no lo exige. No exponer el buzón fuera de loopback.
7. Completar el papeleo del piloto: Actividad 15, Actividad 16 y Actividad
   17. No cambiar la app para subir el `.docx`: el archivo lo adjunta el
   encargado.

---

## 6. Pendientes de Int2 — frontend y piloto

1. No cambiar la UI por la forma del JSON; la pantalla de ficha ya existe.
2. Verificar `frontend/src/components/FichaDeposito.jsx`, la lógica de
   `frontend/src/ficha.js`, el timeout de 30 s y el foco del dropzone.
3. Corregir `docs/semana10_trabajo_integrante2.md`: el PR #78 ya está
   mergeado.
4. Agregar la bitácora S11 de Int2; falta.
5. Ejecutar el clic manual real y el piloto en la sede. No usar el mock de
   reporte en producción.
6. Revisar el aviso de Windows/WSL y el token del buzón antes de la
   instalación en la máquina del operador.

---

## 7. Documentación y decisiones

### 7.1 Documentos que deben actualizarse al cerrar los PRs

- `AGENTS.md`: aviso de auditoría y tabla de pendientes. **Requiere
  aprobación del usuario antes del commit.**
- `docs/HANDOVER_AUDITORIA_2026-10-26.md`: §11 y §13.
- `README.md`: estado de los PRs, reglas y flujo de ficha.
- `docs/PILOTO_OPERADOR.md`, `docs/PLAN_LOTES_PRE_PILOTO.md` y
  `docs/INSTALACION.md`: conteos, comandos y referencias al PR #78.
- `docs/diseno/16_modulo_ia.md`: estado real del módulo de IA y su versión
  de contrato.
- `~/Documents/University/2026-II/PRAPRE/build_evidencias.py`: agregar
  `FINES_SEMANA[12] = "2026-11-14"`.

### 7.2 Decisiones cerradas que no se reabren

- Sangría literal; sin exención por estilo de cita.
- Anexos: el ítem 5 se llama «Base de datos».
- AUD-05: endurecer solo la regla `error`.
- AUD-06: igualdad normalizada después de AUD-01.
- AUD-07: no acotar a “bachiller”; el XPath amplio se mantiene.
- `palabras_clave_minimo`: `error` intencional.
- Cache compilado por hilo: no se implementa.
- `formato` en `/validar`: no se agrega.
- DSpace REST: deprecado.
- Mock de reporte: solo en desarrollo.

---

## 8. Verificación

```bash
# Suite completa (requiere el entorno de nix)
nix run .#test -- tests/ -q

# PR #75: captura de ficha y extractor
nix run .#test -- tests/test_captura_ficha.py tests/test_extractor_edgecases.py -q

# PR #73: auditoría del motor (solo en la rama del PR)
nix run .#test -- tests/test_auditoria_motor.py -q

# Flujo completo de ficha
nix run .#test-ficha-deposito

# Flake y linter
nix flake check
```

La tesis real de la auditoría **no se versiona**: contiene datos personales.
La verificación sobre ella se hace en una copia local fuera del repo y se
reporta con placeholders.

---

## 9. Lo que no se hace

- No mergear #73 tal como está.
- No abrir una rama de rescate de #73: el autor corrige en su PR.
- No cerrar #73, #75 ni #91 sin que el autor haya terminado y sin revisión.
- No debilitar el CI ni saltar checks.
- No cambiar `palabras_clave_minimo` a `warning` para “arreglar” las
  plantillas.
- No agregar `formato` a `/validar`.
- No escribir en la API de DSpace.
- No subir PII, tesis reales, ORCID, DNI ni credenciales.
- No modificar `AGENTS.md` sin aprobación explícita del usuario.

---

## 10. Próximos pasos

1. El autor corrige #73 y #75; no se abre otra rama para esas tareas.
2. Revisar #73 cuando el head nuevo resuelva AUD-05, AUD-06, AUD-07 y el
   conflicto. Cerrar como superseded solo si el autor decide no continuar.
3. Revisar #75 cuando los 4 xfail pasen, el resumen y el título tengan test y
   el body refleje el estado real.
4. Rebasear y mergear #91 con CI verde.
5. Int1 agrega la ficha al golden y corrige los DOCX de ejemplo.
6. Int2 cierra bitácoras y ejecuta el piloto.
7. Actualizar la documentación y el aviso de auditoría solo después de los
   cierres.
