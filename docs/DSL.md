# DSL declarativo de validación — VistoBueno

Documento de referencia del **lenguaje específico de dominio (DSL)** para
definir reglas de validación de formato de tesis. El DSL reemplaza — de
forma **opcional y gradual** — el formato legacy
(`mecanismo_verificable.checks`) por un modelo basado en **analizadores
léxicos (tokenizer), autómatas finitos (DFA), autómatas de pila (PDA),
gramáticas BNF y analizadores de conteo/presencia** (F1→F3).

La gran ventaja: **no rompe el contrato de la API ni el del motor**. El
motor interno (`engine.validate_docx`) siguió devolviendo `List[RuleResult]`.

---

## Formato del archivo

```yaml
namespaces: { w: "...", r: "...", ... }
reglas:
  - id: <string>
    tipo: <atributo_xml | presencia_xml | patron_texto | lista_texto |
           imagen | secuencia | estructura | formato_texto>
    descripcion: <string>
    valor_esperado: <string | list>
    severidad: error | warning
    fuente: <string>
    ubicacion: <string>
    cita: <string>
    # luego, UNA o VARIAS secciones de analizador (todas deben cumplirse):
    atributo_xml: { ... }
    patron_texto: { ... }
    lista_texto: { ... }
    imagen: { ... }
    automata_secuencia: { ... }
    gramatica_estructura: { ... }
    automata_pila: { ... }
    patron_cantidad: { ... }
    conteo_nodos: { ... }
    lista_obligatoria: { ... }
    hipervinculo_texto: { ... }
```

El `engine` detecta el formato por la clave `reglas` (DSL) vs `rules`
(legacy). Ambos formatos pueden coexistir en el repositorio.

---

## Secciones de analizador

> Los analizadores de F3 (`patron_cantidad`, `conteo_nodos`,
> `lista_obligatoria`) y el `automata_pila` de F2 pueden acotar su
> búsqueda a una **sección del documento** usando `seccion:` (span cortado
> entre títulos por el tokenizer — ver § 0). Sin `seccion:`, operan sobre
> todo el documento.

### 0. El tokenizer y la función `seccion()` (F2/F3)

El módulo `validator/tokenizer.py` convierte el `<w:body>` en un flujo de
tokens tipados (`TITULO`, `PARRAFO`, `TABLA`, `IMAGEN`, `SALTO_SECCION`).
Es la base de los autómatas de F2 y de las secciones de F3:

```python
from validator.extractor import extract
from validator.tokenizer import tokenizar, seccion, TITULO, PARRAFO

flujo = tokenizar(extract("tesis.docx"))
resumen = seccion(flujo, "resumen")   # tokens tras el 1er TITULO "resumen*"
referencias = seccion(flujo, "referencias", fin="anexos")  # corte opcional
```

- `seccion(flujo, inicio, fin=None)`: devuelve los tokens posteriores al
  primer TITULO que matchea la regex `inicio` (ignore case) y hasta el
  siguiente TITULO (excluido). Si `fin` es una regex, solo un TITULO que la
  matchee corta; si no hay más títulos, toma el final del flujo. Sin match
  de `inicio`, devuelve la lista vacía (la regla cae como fallo).

Todas las secciones de analizador aceptan:

```yaml
seccion:
  inicio: resumen      # regex sobre el texto del TITULO que abre la sección
  fin: anexos          # opcional: regex del TITULO que la cierra
```

### 1. `atributo_xml` / `presencia_xml` → `AnalizadorXML`

Verifica atributos de nodos o su presencia vía XPath.

```yaml
atributo_xml:
  parte: document | footer | header     # defecto: document
  contexto: todos | cuerpo              # defecto: todos
  xpath: //w:sectPr[1]/w:pgSz
  atributo: "@w:w"                      # solo para comparaciones de valor
  comparacion: eq | all_eq | contains | exists | not_exists
  esperado: "11906"
  ignore_case: false                    # opcional (contains)
```

- `exists` / `not_exists` operan solo sobre la cantidad de nodos.
- `eq` compara el primer valor del atributo; `all_eq` todos; `contains`
  subcadena (con `ignore_case`).

### 2. `patron_texto` → `AnalizadorRegex`

Aplica una expresión regular al contenido textual de los nodos.

```yaml
patron_texto:
  parte: document
  xpath: //w:body//w:p
  patron: "^\\d+$"
  coincidencia: todos | alguno | ninguno   # defecto: todos
  comparacion: regex | fullmatch           # defecto: regex (search)
  ignore_case: false
```

- `todos`: todos los nodos `w:t` deben matchear.
- `alguno` / `ninguno`: al menos uno / ninguno.

### 3. `lista_texto` → `AnalizadorLista`

Comprueba que el texto de los nodos pertenezca a una lista permitida.

```yaml
lista_texto:
  parte: document
  xpath: //w:body/w:p[contains(., 'línea')]
  lista: ["Línea: educación", "Línea: desarrollo"]
  ignore_case: true
```

### 4. `imagen` → `AnalizadorImagen`

Cuenta imágenes (blips) en los nodos que matchean el XPath y verifica
cantidades mínima y/o máxima.

```yaml
imagen:
  parte: document
  xpath: //w:drawing//a:blip
  formato: png
  cantidad_minima: 1
  cantidad_maxima: 4     # opcional
```

### 5. `automata_secuencia` → DFA (secuencia ordenada de títulos)

Modela la estructura de secciones como un **autómata finito determinista**.
Los estados son los títulos esperados; cada transición consume el próximo
título que matchea el patrón del estado. Los estados `opcional: true` se
omiten (pero no se exigen).

```yaml
automata_secuencia:
  nivel_titulo: [1, 2, 3]                 # estilos Heading/Título reconocidos
  normalizacion: [mayusculas, ignorar_indent]
  reconocimiento: greedy | backtracking   # defecto: greedy
  estados:
    - nombre: caratula
      patron: "universidad"               # regex sobre el heading normalizado
      opcional: true
    - nombre: introduccion
      patron: "introducción"
    - nombre: resultados
      patron: "resultados"
```

Reglas de reconocimiento:
- El puntero de entrada **nunca retrocede** (`greedy`) — se preserva el
  comportamiento histórico del motor legacy.
- `backtracking` explora interpretaciones alternativas (búsqueda NFA).
- La carátula se satisface si el **primer párrafo** del documento contiene
  "universidad" (no usa estilo de encabezado).

### 6. `gramatica_estructura` → BNF (estructura jerárquica)

Expresa la estructura completa como una **gramática libre de contexto**
(BNF ligera) y la evalúa con un **parseador descendente recursivo**.

```yaml
gramatica_estructura:
  reglas_sintacticas:
    - "TESIS → CARATULA INDICE INTRODUCCION CUERPO CONCLUSIONES REFERENCIAS"
    - "CUERPO → METODOLOGIA RESULTADOS"
  terminales: [CARATULA, INDICE, INTRODUCCION, METODOLOGIA, RESULTADOS, CONCLUSIONES, REFERENCIAS]
  no_terminales: [TESIS, CUERPO]
  inicio: TESIS
```

El parser expande `inicio` hasta obtener secuencias de terminales y
comprueba que los headings del documento las cubran en orden.

### 7. `automata_pila` → PDA push/pop (estructura anidada)

Expresa una sección como un **autómata de pila** (F2): los estados se
abren con `push` y se cierran con `pop`, lo que permite validar
anidamiento de sub-secciones (no expresable con un DFA plano).

```yaml
automata_pila:
  nivel_titulo: [1, 2, 3]
  estados:
    - nombre: introduccion
      patron: "introducción"
      push: desarrollo            # entrar al sub-nivel "desarrollo"
      pila: [...]
      vaciar_pila: false
    - nombre: desarrollo
      patron: "metodología"
      push: resultados
    - nombre: resultados
      patron: "resultados"
      pop: true                   # cierra el nivel "desarrollo"
    - nombre: conclusiones
      patron: "conclusiones"
      pop: true
```

Reglas de reconocimiento (compartidas con el DFA):
- El puntero de entrada no retrocede (salvo `backtracking`).
- `opcional: true` en un estado lo hace no exigible.
- El tokenizer alimenta el PDA con la proyección de texto del flujo de
  títulos (`TITULO`), igual que el DFA y la gramática.

### 8. `patron_cantidad` → `AnalizadorCantidadPatron` (F3)

Cuenta palabras, matches de regex o entradas estructuradas y verifica un
valor mínimo:

```yaml
patron_cantidad:
  seccion: { inicio: resumen }        # opcional: acota el texto contado
  operacion: count_words | count_matches | count_entries
  patron: "..."                       # solo count_matches
  filtro: "^palabras clave"           # opcional: párrafos que cuentan
  ignore_case: true
  cantidad_minima: 159
```

- `count_words`: palabras (`\w+`) del texto contado (regla *resumen
  ≥ 159 palabras*).
- `count_matches`: matches de `patron` en el texto.
- `count_entries`: entradas separadas por `,` o `;` del texto posterior al
  primer `:` (p. ej. `Palabras clave: a, b, c` → 3). Útil con `filtro`
  sobre el párrafo de etiqueta.

### 9. `conteo_nodos` → `AnalizadorConteoNodos` (F3)

Cuenta nodos XPath **o** párrafos no vacíos de una sección y verifica
cantidad mínima:

```yaml
conteo_nodos:
  seccion: { inicio: referencias }    # modo "sección": cuenta PARRAFOs
  # — o en su lugar —
  parte: document
  xpath: //w:body//w:p                # modo "nodos"
  cantidad_minima: 20
  cantidades_multiples: [20, 30, 20]  # opcional: cualquier valor cumple
```

- Sin `xpath` pero con `seccion:`, cuenta los párrafos no vacíos
  (`PARRAFO`) del slice — usado por las reglas de *referencias mínimas*
  según tipo de investigación.
- `cantidades_multiples` permite aceptar cualquiera de varios mínimos
  (cuando el mínimo depende del tipo de investigación). Si se declara,
  **no** se usa `cantidad_minima`.

### 10. `lista_obligatoria` → `AnalizadorListaObligatoria` (F3)

Verifica que cada ítem de una lista de **contenidos obligatorios** (por
subcadena normalizada) aparezca en la sección:

```yaml
lista_obligatoria:
  seccion: { inicio: anexo }
  ignore_case: true
  items:
    - Matriz de consistencia
    - Consentimiento informado
```

- Cada ítem se busca como subcadena (normalizada a minúsculas) en el texto
  de la sección. Usado por las reglas de *anexos mínimos*.

### 11. `hipervinculo_texto` → `AnalizadorHipervinculo` (F3)

Cuenta hipervínculos (`w:hyperlink`) cuyo texto matchea un patrón y
verifica un mínimo:

```yaml
hipervinculo_texto:
  parte: document
  contexto: todos
  xpath: //w:body//w:hyperlink
  patron: 'https?://orcid\.org/\d{4}-?\d{4}-?\d{4}-?\d{4}'
  cantidad_minima: 1
```

Usado por la regla *caratula_orcid* (el código ORCID debe ser un
hipervínculo de 16 dígitos, normalizado a minúsculas y entre paréntesis).

---

## Componentes de código

| Archivo | Clases | Responsabilidad |
|---------|--------|-----------------|
| `validator/automata.py` | `DFA`, `Transicion`, `GramaticaEstructura`, `PDA`, `TransicionPDA` | DFA, PDA y gramáticas puras, sin conocimiento del DOCX |
| `validator/tokenizer.py` | `Token`, `tokenizar`, `seccion`, `solo`, `textos` | Análisis léxico: flujo tipado del `<w:body>` y cortes por sección |
| `validator/analizadores.py` | `Analizador` (ABC), `AnalizadorXML`, `AnalizadorRegex`, `AnalizadorLista`, `AnalizadorConteoNodos`, `AnalizadorImagen`, `AnalizadorCantidadPatron`, `AnalizadorListaObligatoria`, `AnalizadorHipervinculo` | Analizadores de hoja sobre `ExtractedDocx` |
| `validator/compilador.py` | `CompilerDSL`, `ReglaCompilada`, `AutomataSecuencia`, `GramaticaEstructuraAnalizador`, `AutomataPila` | Compila el YAML DSL → analizadores y produce `List[RuleResult]` |
| `validator/engine.py` | `validate_docx` (modificado) | Detecta el formato (DSL vs legacy) y delega |
| `reglas_dsl_ejemplo.yaml` | — | Archivo de ejemplo completo del formato DSL |

---

## Paridad de contrato

| Contrato | Legacy | DSL | ¿Cambia? |
|----------|--------|-----|----------|
| `validate_docx() -> List[RuleResult]` | ✅ | ✅ | No |
| `build_report() -> {semaforo, resumen, resultados}` | ✅ | ✅ | No |
| `RuleResult.to_dict()` campos | ✅ | ✅ | No |
| `ValidarResponse` (API, español) | ✅ | ✅ | No |
| CLI `python -m validator.cli` | ✅ | ✅ | No |

---

## Ejecutar

```bash
# Con el motor (detecta el formato automáticamente)
python -m validator.cli tesis.docx reglas_dsl_ejemplo.yaml --json

# Tests específicos del DSL
pytest tests/test_dsl.py tests/test_f2_automatas.py tests/test_f3_mecanizacion.py -v
```

---

## Extensión

Para agregar un tipo de analizador nuevo:
1. Crear la clase que herede de `Analizador` en `validator/analizadores.py`
   (o en `automata.py` si es compuesto).
2. Registrar la sección en `SECCIONES_ANALIZADOR` y en `_FABRICAS` de
   `validator/compilador.py`.
3. Agregar un ejemplo en `reglas_dsl_ejemplo.yaml` y un test en
   `tests/test_dsl.py`.