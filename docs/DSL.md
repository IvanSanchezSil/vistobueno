# DSL declarativo de validación — VistoBueno

Documento de referencia del **lenguaje específico de dominio (DSL)** para
definir reglas de validación de formato de tesis. El DSL reemplaza — de
forma **opcional y gradual** — el formato legacy
(`mecanismo_verificable.checks`) por un modelo basado en **analizadores
léxicos, autómatas finitos (DFA) y gramáticas BNF**.

La gran ventaja: **no rompe el contrato de la API ni el del motor**. El
motor interno (`engine.validate_docx`) siguió devolviendo `List[RuleResult]`.

---

## Formato del archivo

```yaml
namespaces: { w: "...", r: "...", ... }
reglas:
  - id: <string>
    tipo: <atributo_xml | presencia_xml | patron_texto | lista_texto |
           imagen | secuencia | estructura>
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
```

El `engine` detecta el formato por la clave `reglas` (DSL) vs `rules`
(legacy). Ambos formatos pueden coexistir en el repositorio.

---

## Secciones de analizador

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

---

## Componentes de código

| Archivo | Clases | Responsabilidad |
|---------|--------|-----------------|
| `validator/automata.py` | `DFA`, `Transicion`, `GramaticaEstructura` | Autómatas y gramáticas puras, sin conocimiento del DOCX |
| `validator/analizadores.py` | `Analizador` (ABC), `AnalizadorXML`, `AnalizadorRegex`, `AnalizadorLista`, `AnalizadorImagen` | Analizadores de hoja sobre `ExtractedDocx` |
| `validator/compilador.py` | `CompilerDSL`, `ReglaCompilada`, `AutomataSecuencia`, `GramaticaEstructuraAnalizador` | Compila el YAML DSL → analizadores y produce `List[RuleResult]` |
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
pytest tests/test_dsl.py -v
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