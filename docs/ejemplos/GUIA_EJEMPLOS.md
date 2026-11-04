# Ejemplos: documento bueno y documento malo

Par de documentos sintéticos y la respuesta real de `POST /validar` para cada
uno. Sirve para mostrar el semáforo y el reporte en los dos extremos: un
documento que cumple y uno que no.

Los documentos salen del factory determinista de los tests. No contienen
datos de estudiantes reales.

## Archivos

| Archivo | Qué es |
|---------|--------|
| `doc_bueno.docx` | Documento que cumple todas las reglas aplicables (plan cuantitativo) |
| `respuesta_doc_bueno.json` | Respuesta de la API para `doc_bueno.docx` |
| `doc_malo.docx` | El mismo documento con cinco desvíos mínimos, uno por regla |
| `respuesta_doc_malo.json` | Respuesta de la API para `doc_malo.docx` |

## Resultado

| Documento | Semáforo | Reglas evaluadas | Errores | Warnings |
|-----------|----------|------------------|---------|----------|
| `doc_bueno.docx` | **verde** | 43 de 49 | 0 | 0 |
| `doc_malo.docx` | **rojo** | 43 de 49 | 4 | 1 |

Las 6 reglas restantes no aplican al tipo de documento (plan cuantitativo).
La respuesta del documento bueno incluye la ficha de depósito, porque la API
solo la materializa con semáforo verde.

## Hallazgos del documento malo

| Regla | Severidad | Desvío aplicado | Esperado | Encontrado |
|-------|-----------|-----------------|----------|------------|
| `fuente_principal` | error | Fuente Arial | Times New Roman | Arial |
| `tamano_cuerpo` | error | Cuerpo a 15 pt | 12 pt | 15 pt |
| `interlineado` | error | Interlineado de 1.25 líneas | 1.5 líneas | 1.25 líneas |
| `margen_izquierdo` | error | Margen izquierdo de 2.3 cm | 3.0 cm | 2.3 cm |
| `sangria_parrafo` | warning | Sin sangría de primera línea | 1.27 cm | 0 cm |

El campo `encontrado` del JSON conserva el detalle técnico del motor (por
ejemplo, `@w:ascii: 3 valores evaluados, 3 incumplen: #1=Arial (pág. 4),
…`). La tabla de arriba traduce ese detalle a lenguaje legible para la
demostración.

Las dos respuestas están versionadas tal cual. Si el motor cambia el
formato del detalle, hay que regenerarlas (`python
scripts/ejemplo_bueno_malo.py`) y revisar el diff: el test
`tests/test_ejemplos_versionados.py` compara las respuestas versionadas con
las que produce el motor, así que un desfase no pasa inadvertido.

## Cómo se generó

```bash
nix develop --command python3 scripts/ejemplo_bueno_malo.py \
  --salida /ruta/a/esta/carpeta
```

El script construye los dos DOCX, los sube al endpoint real con el cliente de
prueba de FastAPI y guarda las respuestas. Es reproducible: los documentos son
deterministas y no dependen de la red.
