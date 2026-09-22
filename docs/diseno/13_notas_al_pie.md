# 13. Notas al pie (F2 ítem 3)

- **Fecha**: 2026-09-21
- **Estado**: implementado
- **Commits**: `(Bloque C)`

## Problema

El manual no regula la numeración de las notas al pie, pero un documento con
notas mal numeradas (saltos, repeticiones o referencias a ids inexistentes) es
una señal inequívoca de edición descuidada. El territorio estaba sin validar:
el extractor ignoraba `word/footnotes.xml` y no se detectaba ningún desvío.

## Decisiones

1. **Regla nueva en el DSL**: `notas_al_pie_consistencia` (severidad
   `warning`, con nota `EVALUADO:` en el YAML porque el manual no la define).

2. **Semántica "sin notas pasa"**: un documento sin `w:footnoteReference` en el
   cuerpo es la norma (la mayoría de tesis no usa notas al pie). La ausencia NO
   es un desvío → la regla pasa (n/a). El desvío solo se detecta cuando las
   notas existen y su numeración está rota.

3. **Nueva sección DSL `nota_pie`** con `operacion: numeracion_consistente`,
   despachada por el compilador a `AnalizadorNotaPie` (registrada en
   `SECCIONES_ANALIZADOR`, `_FABRICAS` y `dsl_check._SECCIONES`).

## Criterio de `AnalizadorNotaPie`

Dados los ids de `//w:footnoteReference/@w:id` en el cuerpo:

1. Si no hay ninguno → pasa, detalle `sin_notas_al_pie (n/a)`.
2. Si hay ids repetidos → falla (`duplicadas=True`).
3. Ordenados ascendentemente deben ser exactamente `1..N` (consecutivas).
4. Si la parte `word/footnotes.xml` existe, cada id referenciado debe estar
   definido ahí (reservó `-1` y `0`; las notas reales van de `1` en adelante).

Diseño deliberado: el salto con `[1,2,4]` falla, al igual que `[1,1,2]`
(duplicado) y `[1,2,3]` con la parte footnotes ausente queda en pase por
numeración (la existencia no es verificable sin el archivo; el estándar de
Word siempre lo escribe).

## Invariante de propiedad (factory)

Aunque la base no lleva notas (n/a), la **cadena de mutación** exige que exista
una mutación que haga fallar la regla. Se agrega `notas_pie_ids=[1,2,4]` en
`tests/_mutations.py`; la factory emite el párrafo con las referencias y la
parte `footnotes.xml` solo cuando la lista no está vacía (`_notas_pie_para`,
`_footnotes_xml`). Con esto `test_doc_bueno_pasa_43/45` y
`test_mutaciones_cubren_las_45_reglas` se mantienen automáticos.

## Conteos tras el cambio

| Concepto | Antes | Ahora |
|----------|-------|-------|
| Reglas en `reglas_unt.yaml` | 44 | **45** |
| `_migracion.total_reglas_con_f3` | 44 | 45 |
| Doc bueno | 42/44 | **43/45** |
| Mutaciones | 44 | 45 |
| Tests | 176 | **187** |

## End-to-end

`curl -F "archivo=mi_tesis.docx" localhost:8000/validar` devuelve la regla
`notas_al_pie_consistencia` en `resultados`. Si la tesis no usa notas al pie,
aparece como **cumple** (n/a); si las usa con numeración rota, falla como
`warning` y su `ubicacion` se enriquece con `; página N` (ítem 1 de la F2).