# Handover: exponer los valores detectados por el motor (ficha de depósito)

**Fecha**: 2026-10-19 (actualiza la versión del 2026-10-14)
**De**: Integrante 1 (Backend/API)
**Para**: Integrante 3 (Motor de reglas)
**Estado**: pedido con especificación — el diseño del mecanismo es tuyo
**Contexto de producto**: `docs/PLAN_FICHA_DEPOSITO.md` (leer primero)

---

## 1. El problema en una frase

Los analizadores de carátula y cuerpo **ya localizan** título, autores,
asesor, resumen y palabras clave — pero hoy solo publican pass/fail y un
`found` resumido; el flujo de depósito en DSpace necesita **el texto
completo que encontraron**, con su página.

## 2. Qué se pide, campo por campo

> **Actualización 2026-10-19**: la captura real del formulario de la
> instancia congeló el mapa de campos (PLAN_FICHA §4). El servidor de
> DSpace pre-llena 16 campos según la colección (grado, disciplina, OCDE,
> tipo, idioma, derechos, etc.), así que el motor solo necesita exponer
> los datos que el operador realmente completa.

| Dato | Destino | Regla/analizador que hoy lo localiza | Estado |
|------|---------|--------------------------------------|--------|
| Título | `dc.title` | `caratula_titulo_trabajo_*` | Sin cambio: texto completo, sin truncar |
| Autores | `dc.contributor.author` | `caratula_autores_*` | Sin cambio: lista de nombres |
| Asesor | `dc.contributor.advisor` | regla de asesor en carátula | Sin cambio, salvo el recorte del ORCID pegado (2026-11-23) |
| ORCID del asesor | `renati.advisor.orcid` | carátula, etiqueta del asesor | **Detectado desde 2026-11-23** (PR 1); checksum y publicación en la API en el PR 2 de Int1 |
| Resumen | `dc.description.abstract` | `resumen_longitud` | Sin cambio: texto completo |
| Palabras clave | `dc.subject` | `palabras_clave_minimo` | Sin cambio: lista de entradas |
| Año de emisión | `dc.date.issued` | — (sin regla hoy) | Detección nueva: año en carátula |
| Escuela | columna ESCUELAS del registro (no es campo del formulario) | línea "ESCUELA ACADÉMICO PROFESIONAL DE…" de la carátula | La regla de carátula que la localiza (o detección trivial si no hay): texto igual que título |
| Jurado | `renati.juror` (opcional) | firmas / anexo | **Pedido de viabilidad**: ¿los nombres del jurado salen de forma confiable de la sección de firmas, en plantillas y tesis reales? Si sí, campo opcional; si no, `detectado=false` y el operador lo teclea |

**Descartados del pedido original** (el servidor ya los pre-llena por
colección; la ficha no los necesita):

- Grado/título al que opta → `thesis.degree.name` pre-lleno.
- Línea de investigación → `dc.subject.ocde` pre-lleno. El mapeo
  línea→OCDE queda cancelado para el depósito.

Los demás campos del formulario (DNI del autor y del asesor, DOI, ISBN) no
salen del DOCX: los teclea el operador en la pantalla. El motor no los busca
y la ficha no los publica.

> **Nota de cambio (2026-11-23, PR 1 del reparto ORCID):** el ORCID del
> **asesor** deja de ser manual. La regla `ficha_orcid_asesor` lo captura de
> la carátula, y `ficha_asesor`/`ficha_autores` dejan de excluir párrafos por
> contener `orcid.org`: separan la línea pura con `filtro` y recortan el
> sufijo con `quitar_sufijo`. `reporte["ficha"]` pasa de 7 a 8 claves. La
> validación de checksum y la publicación en `ficha_deposito` corresponden al
> PR 2 (Int1): aquí **no cambia el contrato de la API** (`api.py` y
> `api_models.py` intactos; `renati.advisor.orcid` sigue en
> `CAMPOS_MANUALES_FICHA`). Si el documento no trae ORCID, el motor omite la
> clave y la API publica `detectado=false` desde su lista acordada.

> **Ajustes de la revisión (2026-11-24, PR #124):** retblast reprodujo dos
> casos límite y se corrigieron en el mismo PR antes de la fusión:
> 1. El predicado que cortaba en «Línea de investigación:» era absoluto: si
>    esa línea aparecía **antes** del bloque «ASESOR(A):», el asesor dejaba
>    de detectarse. Ahora solo corta en una línea que tenga un párrafo de
>    asesor precedente. El mismo problema se acotó en `ficha_autores` (la
>    línea previa a «AUTORES:» borraba todos los nombres).
> 2. `quitar_sufijo` no recortaba la etiqueta cuando el ORCID iba sin URL:
>    «Dra. Nombre ORCID: 0000-…» publicaba «Dra. Nombre ORCID:». El patrón
>    acepta ahora el prefijo opcional «(Código) ORCID:» en asesor y autores.
>
> Se agregaron casos para ORCID desnudo bajo la etiqueta, ORCID con etiqueta
> y línea de investigación previa (37 pruebas de ficha en verde). Retblast
> confirmó que la clave **ausente** cuando no hay ORCID es la forma correcta:
> la estabilidad del contrato la garantiza la API en el PR 2.

Requisitos comunes:

- **Texto completo, no resumen**: `found` trunca (`vals[:3]`, conteos);
  la ficha necesita el valor íntegro.
- **Página de origen**: el mapa párrafo→página ya existe
  (`ultimo_nodo` + enriquecimiento de `location`, F2 ítem 1). Reusarlo.
- **Solo lectura**: esto no cambia el semáforo ni ninguna regla. Es
  captura de datos, no validación nueva.

## 3. Mecanismos posibles (a tu criterio)

Presento dos opciones; la decisión de diseño es del área motor.

**(a) Campo `valores` en `RuleResult`**: el analizador que ya localiza el
elemento llena un campo opcional (p. ej. `valores: dict | None`) con los
textos; `to_dict()` lo expone y la API lo mapea a la ficha.
- Pros: cambio local, regla por regla.
- Contras: `RuleResult` crece para un caso de uso específico; cada regla
  decide su formato a mano.

**(b) Sección DSL `extraccion`**: la regla declara en el YAML qué capturar
(p. ej. `extraccion: {campo: dc.title, del_nodo: texto}`); el analizador,
al encontrar el nodo, además de validar lo publica en un dict del
contexto (p. ej. `contexto["ficha"]`).
- Pros: declarativo, consistente con la filosofía del DSL; el formato es
  uniforme y la API no parsea texto libre por regla.
- Contras: toca compilador/analizadores y el linter (`SECCIONES_ANALIZADOR`,
  `_FABRICAS`, `_SECCIONES`).

Mi recomendación no vinculante: **(b)**, por la misma razón que el DSL
existe — pero si prefieres (a) por velocidad, funciona igual para la API:
lo único que contrato es "el valor viaja en algún campo estructurado de
la salida del motor, con la página".

## 4. Forma que espera la API (el contrato entre nosotros)

Cualquiera de las dos opciones debe permitir que `build_report()` (o el
`RuleResult` correspondiente) entregue, por dato:

```
{
  "campo": "dc.title",          # clave acordada (tabla de la §2)
  "valor": "Taller de ...",     # texto completo o lista de textos
  "pagina": 1,                  # página de origen (si hay mapa)
  "detectado": true             # false si la regla no encontró el elemento
}
```

Claves acordadas (actualizado 2026-11-24): `dc.title`,
`dc.contributor.author`, `dc.contributor.advisor`, `renati.advisor.orcid`,
`dc.description.abstract`, `dc.subject`, `dc.date.issued`, `escuela` y
`renati.juror` (opcional; hoy no se captura). Con eso, la API arma
`ficha_deposito.extraidos[]` (PLAN_FICHA §5) sin parsear `found` ni inventar
heurísticas por regla. Si un dato no aplica, `detectado: false`.

## 5. Verificación que te pido

- Tests de que cada campo de la §2 expone su valor con el factory
  determinista (carátula con contenido conocido).
- Paridad en las 5 plantillas: la ficha extrae los placeholders (es
  esperable; el operador los corrige en la pantalla).
- La suite completa en verde y las mutaciones de `tests/_mutations.py`
  sincronizadas si agregas sección DSL nueva (regla de AGENTS.md).

## 6. Lo que NO se pide

- No reglas nuevas de validación ni cambios de semáforo.
- No tocar `validator/dspace.py` ni la API: el mapeo a la ficha y el
  contrato v1.7.0 son míos.
- El mapeo línea→OCDE queda **cancelado**: `dc.subject.ocde` viene
  pre-lleno por colección en la instancia.

## 7. Después de tu parte

1. Yo publico `ficha_deposito` en el contrato (v1.7.0) y regenero
   OpenAPI.
2. Integrante 2 arma la pantalla de la ficha (extraídos + manuales,
   botón "Preparar depósito", panel de espera) sobre el flujo existente.
3. El depósito contra la instancia real no requiere gestión ante la
   sede: se hace con el userscript sobre la sesión del operador
   (PLAN_FICHA §2).

---

## 8. Nota de seguimiento (2026-10-23, tras la entrega del diseño 17)

La entrega está integrada y funcionando de punta a punta (la API activa
`reglas_ficha.yaml` en `POST /validar`; la ficha viaja con valores
reales). Un solo pulido quedó en el tintero, sin urgencia:

- **`dc.title` llega con el prefijo de la etiqueta**: la captura trae el
  párrafo completo ("Título del trabajo de investigación: Estrategias
  lúdicas…"). Hoy el operador lo recorta en la pantalla de revisión
  (Int2) y el userscript lo escribe tal cual. Si la captura puede
  dejar solo el título, mejor — es limpiar el dato en la fuente y no en
  cada uso. Tu llamada el mecanismo; las reglas de validación no se
  tocan (la captura es solo lectura, como la firmamos en el §6).

Referencia viva: el ensayo general (`nix run .#test-ficha-deposito`)
usa tu captura en el flujo completo — cualquier cambio tuyo queda
verificado ahí de gratis.

### 8.1 Hallazgos verificados contra la plantilla oficial (2026-10-23, revisión del PR #55)

Verificados con `validate_docx` + `load_ficha_rules()` sobre la
plantilla real de Educación Inicial (reproducción: ver `recursos/`).
Ambos son de `reglas_ficha.yaml` — área tuya, mecanismo a tu criterio:
solo los documento para tu cola.

- **`dc.contributor.advisor` viaja `detectado=true` con `valor=""`**:
  contradictorio para el contrato (la ficha dice "detectado" cuando no
  hay nada). Sospecha: el `quitar_prefijo` de la regla deja la cadena
  vacía cuando la línea de la plantilla no tiene el asesor real, y la
  captura la publica igual. Normalizar a `detectado=false, valor=null`
  cuando el resultado queda vacío.
- **`dc.date.issued` captura la línea de lugar** (`"Trujillo - Perú"`),
  no un año: en la carátula de la plantilla la línea "TRUJILLO –
  PERÚ … 2026" se captura parcialmente. Hoy el userscript lo resuelve
  por su cuenta (extrae 4 dígitos; sin año → queda "a mano", fallo
  visible), pero la captura debería traer el año directo.

Nota menor (ítem 4 de la misma revisión): documentar en el diseño 17
que el XPath de autores espera **párrafos hermanos** (funciona con
párrafos separados y con "Autor1, Autor2" en una línea vía separador,
pero vale dejarlo escrito).

---

## 9. Seguimiento RI-07 / RI-08 (2026-11-24/25)

### RI-07 — rendimiento de los XPath de carátula

Implementado en `validator/extractor.py`: las consultas con contexto
`caratula`/`caratula_ficha` se evalúan en un árbol reducido a la carátula y
los nodos se traducen de vuelta a los originales. Detalle, invariantes y
mediciones en `docs/diseno/17_extraccion_ficha.md` §9.

Regresión: `tests/test_caratula_xpath.py` (35 pruebas) compara todas las
expresiones del catálogo contra el comportamiento anterior y verifica que el
reporte completo —semáforo, resumen, resultados y ficha— sea idéntico con un
cuerpo de 200 párrafos que incluye etiquetas engañosas de asesor y línea.

**Verificación con el corpus real (2026-11-24):** las dos versiones de la
tesis y las cinco plantillas oficiales están disponibles localmente. Con
`python scripts/medir_caratula.py <docx...>` se comparó el motor actual contra
la implementación anterior: 37,65 s → 2,63 s en la tesis aprobada y 37,20 s →
2,22 s en la no aprobada; 0,26 s → 0,11–0,17 s en las plantillas. En los
siete documentos el reporte completo fue idéntico: verde 0/5 y rojo 4/5 con
42/54 reglas evaluadas en las tesis; 2 y 4 errores con 9 advertencias en las
plantillas. Las capturas de la ficha y los cuatro errores de la tesis no
aprobada no cambiaron. Detalle y tabla en `docs/diseno/17_extraccion_ficha.md` §9.

**Falta para cerrar RI-07:** solo la repetición de las dos cargas
consecutivas en la API de retblast y la comprobación en Firefox del límite
de 30 s (acá se midió el motor, no el navegador).

### RI-08 — alcance de `caratula_autores_tamano` (cerrado 2026-11-25)

Retblast puso `ciudad.sz` y `linea.sz` en 36 pt en el doc bueno y la regla
siguió en verde. El manual oficial sí estaba disponible en el ZIP de recursos
que aportó el usuario (`MANUAL REVISADO TERCERA VERSION OBSERVACIONES
11-07-2025.docx`, no copiado al repo) y resuelve la duda: los párr. 179-183
fijan **12 pt** para autores, asesor, línea de investigación, ciudad/país y
año en curso. Se amplía la regla existente, que mantiene `severidad: error`,
en vez de recortar su descripción:

- nueva comprobación para la línea: etiqueta y párrafo siguiente (si el texto
  va junto en un solo párrafo, el XPath devuelve solo ese nodo);
- nueva comprobación para ciudad/país: el **último** párrafo con «Trujillo»
  de la carátula, para no medir la Universidad a 18 pt;
- nueva comprobación para el año: el párrafo de cierre de sección
  (`contexto: caratula_ficha`), donde las tesis reales ponen el año separado;
  cuando el año va dentro de la línea de ciudad, ese mismo párrafo ya queda
  cubierto.

Las cinco comprobaciones usan `all_eq` sobre todos los runs con texto.
`caratula_ciudad_pais_negrita` y `caratula_linea_investigacion` siguen
midiendo negrita/contenido, respectivamente: no se duplica su propiedad.
En la matriz REQ-24 y REQ-26 siguen `PARCIAL` por las propiedades que aún no
se demuestran (mixtas, centrado), pero su evidencia de 12 pt ya está cubierta;
REQ-27 mantiene `CONFLICTO` por año en curso frente a año de sustentación,
aunque el tamaño del año ya se valide.

**Regresión:** `tests/test_ri08_caratula_tamano.py` verifica que el documento
bueno siga en verde y que 36 pt en línea, ciudad o año separado pongan la
regla en rojo. Se ajustó `test_aud05_ignora_runs_sin_texto_y_no_mira_al_asesor`
para incluir esos tres bloques a 12 pt, y se regeneraron los dos JSON golden
de `docs/ejemplos/` (solo cambian `ubicacion` y `cita`).

**Corpus real:** la regla sigue en verde en la tesis aprobada, en la no
aprobada y en las cinco plantillas; no cambia semáforo, resumen, capturas ni
los cuatro errores de la tesis no aprobada. Entregado en el PR #128, abierto y
sin merge de mi parte; CI verde en https://github.com/retblast/vistobueno/actions/runs/45615829450.
