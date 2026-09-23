# Diseño — Ubicación por página física (ítem 1 de la Fase 2)

> Documento: `11_ubicacion_pagina.md`
> Estado: ✅ **IMPLEMENTADA** (2026-09-21, Semana 5, rama `semana5-motor-calidad-paginacion`)
> Autor: IvanSanchezSil (Integrante 3 — Motor de reglas / DSL)
> Alcance: cerrar el [ítem 1 del backlog](../PLAN_BACKLOG_FUTURO.md) (paginación real):
> mapa párrafo→página, sección DSL `paginacion` y **enriquecimiento de `location`**
> con el número de página físico cuando una regla falla.
> Relacionado: [`validator/extractor.py`](../../validator/extractor.py) ·
> [`validator/analizadores.py`](../../validator/analizadores.py) ·
> [`validator/compilador.py`](../../validator/compilador.py) ·
> [`tests/test_f2_paginacion.py`](../../tests/test_f2_paginacion.py)

## 1. Contexto

El reporte del motor situaba cada fallo solo con la referencia al reglamento
(campo `location`, p. ej. `"Sección "Formato general" (párr. 141)"`). El ítem 1
del backlog pedía decirle al estudiante **en qué página del documento** está el
problema: `"página 14 (párr. 124-125)"`, algo mucho más útil para un DOCX de 150
páginas.

La primera parte del ítem (mapa párrafo→página) se implementó en la Semana 5
con dos marcadores que Word persiste en el XML del DOCX:

- `w:lastRenderedPageBreak` — insertado al guardar un documento ya renderizado.
- `w:br w:type="page"` — salto de página explícito.

Este documento cubre la segunda parte: **conectar ese mapa a los analizadores**
para que el `location` de una regla fallida diga "página N".

## 2. Decisión de diseño: heurística del DOCX, sin render

Inicialmente se propuso renderizar el DOCX a PDF (LibreOffice headless +
PyMuPDF) para obtener páginas reales. **Decisión (2026-09-21): NO se agrega
LibreOffice.** Razones:

- Es una dependencia pesada en Nix (cientos de MB) solo para un enriquecimiento.
- Los DOCX que valida el motor ya están renderizados por Word (el estudiante los
  escribió y guardó en su PC), así que `w:lastRenderedPageBreak` suele estar
  presente.
- Si **no** hay marcadores en el documento, el mapa no puede calcular páginas; en
  ese caso el motor **omite el sufijo** (no inunda el reporte con
  "página no disponible").

El resultado es determinista y sin dependencias nuevas. PyMuPDF ya está en el
flake pero queda disponible para otros usos (p. ej. el ítem 13, benchmark).

## 3. Implementación

### 3.1 Extractor — `_paginacion_para()` y `ExtractedDocx.pagina_de()`

```python
def _paginacion_para(document) -> dict:
    paginacion = {}
    pagina = 1
    for p in document.xpath("//w:body//w:p", namespaces=NS):
        tiene_salto = (p.find(f".//{W}lastRenderedPageBreak", namespaces=NS) is not None
                       or p.find(f".//{W}br[@w:type='page']", namespaces=NS) is not None)
        paginacion[p] = pagina
        if tiene_salto:
            pagina += 1
    return paginacion
```

Puntos clave:

- La clave del mapa es el **elemento lxml**, no `id()` del proxy: los proxies
  lxml se liberan y recrean (su `id()` cambia) si no hay una referencia fuerte,
  lo que rompía las consultas posteriores (bug corregido en esta semana).
- El párrafo **con** el salto queda en la página actual; el contenido siguiente
  pasa a la siguiente (patrón `[1,1,2,2,3]` en los tests).
- `pagina_de(node)` sube por ancestros hasta el `w:p` y consulta el mapa; devuelve
  `None` si el nodo no es un párrafo del cuerpo (o no está en el mapa).

### 3.2 Analizadores — `Analizador.ultimo_nodo`

La clase base `Analizador` gana un atributo `ultimo_nodo`, que el helper
compartido `_nodos()` rellena con el primer nodo de cada consulta XPath:

```python
def _nodos(self, extracted, parte, contexto):
    nodos = extracted.xpath(parte, self.config.get("xpath", ""), contexto)
    self.ultimo_nodo = nodos[0] if nodos else None
    return nodos
```

Casi todos los analizadores pasan por `_nodos`, por lo que quedan cubiertos
`atributo_xml`, `presencia_xml`, `patron_texto`, `paginacion`, etc. Un nodo no
párrafo (p. ej. `w:ind`) se resuelve subiendo por ancestros a su `w:p`.

### 3.3 Compilador — `ReglaCompilada.ejecutar()`

Al producirse un fallo, se anexa la página del primer analizador que falló:

```python
if fallos and pagina is not None and ubicacion:
    ubicacion = f"{ubicacion}; página {pagina}"
```

Reglas de la convención:

- **Solo cuando falla**: una regla cumplida conserva su `location` original.
- **Solo si `ubicacion` no es vacía**: no se inventa una ubicación.
- **Formato**: el sufijo se agrega al string `location`/`ubicacion`. El DTO de la
  API mapea `location`→`ubicacion` de forma transparente, **sin cambiar el
  contrato** (`CONTRATO_API.md` no se toca).

## 4. Evidencia

### 4.1 Tests (`tests/test_f2_paginacion.py`)

- `test_paginacion_es_monotona_y_pagina_inicial`: el mapa es monótono y page 1 =
  carátula (el manual dice que no se enumera pero **sí** se cuenta).
- `test_mapa_de_saltos_renderizados_y_explicitos`: `[1,1,2,2,3]` con ambos
  marcadores.
- `test_pagina_de_no_para_es_none` → `None` para `None` y para el documento.
- `test_paginas_distintas_pasa` / `test_paginas_repetidas_falla` /
  `test_no_encontrado_falla`: end-to-end del `AnalizadorPaginacion`.
- `test_indice_paginas_separadas_*`: regla real contra `reglas_unt.yaml`
  (base pasa / mutación falla / índice renombrado falla).
- `test_regla_fallida_enriquece_location_con_pagina`: `sangria_parrafo` mutada
  (firstLine=0) termina en `"página 4"` (3 saltos previos de los índices).
- `test_regla_cumplida_no_altera_location`: la ubicación queda intacta al pasar.

### 4.2 Marco de pruebas

El `docx_factory` configura `indices_paginas_separadas: True` en la base, por lo
que el DOCX sintético incluye `w:lastRenderedPageBreak` reales y el enriquecimiento
se puede probar de manera determinista. La mutación `sangria_parrafo` sigue
emitiendo `w:ind` con `firstLine=0`, de modo que el fallo cae sobre un párrafo
real (el primero del cuerpo, página 4).

## 5. Alcance y no-alcance

Incluido:

- Enriquecimiento de `location` con página física vía heurística, sin render.
- `ultimo_nodo` en la base `Analizador` (componible, reutilizable).
- Regla `caratula_no_se_enumera` (carátula sin enumerar) **ya estaba
  mecanizada** (presencia de `w:titlePg` en `reglas_unt.yaml:366-378`); no se
  duplicó.

No incluido (documentado como pendiente):

- Los ítems 2 (encabezados/pies), 3 (notas al pie) y 11-12 (TOC y numeración
  jerárquica) del backlog — planificados para continuar esta misma Semana 5.
- El compañero de API/frontend debe exponer `formato` en `POST /validar`
  (ítem 16, bloque E).