# Cambios al motor: enfoque en autómatas, expresiones regulares y analizadores

**Autor**: Iván Sánchez Silva
**Semana**: 3
**Rol**: Motor de reglas / Procesamiento (Integrante 3)
**Fecha**: 2026-09-07
**Contexto**: Prácticas preprofesionales — VistoBueno, Biblioteca de la FECyC (UNT)

**Cursos vinculados**: Lenguajes Formales y Autómatas (autómatas finitos,
gramáticas, lenguajes regulares) · Compiladores (análisis léxico, análisis
sintáctico, compilación de un lenguaje de descripción de reglas)

**Documentos relacionados**: [`docs/DSL.md`](DSL.md) (referencia de la
gramática del DSL) · [`docs/PLAN_DSL.md`](PLAN_DSL.md) (plan futuro con
decisiones pendientes)

---

## 1. Introducción (en lenguaje natural)

VistoBueno valida una tesis (archivo `.docx`) contra las reglas de formato de
la UNT. El motor original funcionaba, pero su código central (`checks.py`)
era una gran cadena de `if/elif`: para cada tipo de comprobación (un
atributo XML, la presencia de un nodo, un patrón de texto, una imagen…) había
una rama distinta dentro de la **misma función**. Eso convertía a `checks.py`
en una función difícil de entender, de probar y de extender.

En la **semana 3** se decidió reescribir el motor con los conceptos que se
estudian en **Lenguajes Formales y Autómatas** y **Compiladores**:

- **Analizadores** (analogía con el *análisis léxico* de un compilador):
  pequeñas piezas especializadas que "leen" el documento y extraen un hecho
  (el tamaño del papel, la fuente del cuerpo, el texto de la carátula, las
  palabras de un párrafo).
- **Expresiones regulares** (los *lenguajes regulares* de la teoría):
  definen de forma declarativa qué patrones de texto son válidos.
- **Autómatas finitos deterministas (DFA)**: tratan al documento como un
  **flujo de símbolos** (los títulos de sección) que debe ser *aceptado* por
  el autómata; si la secuencia de títulos no coincide con la esperada, el
  autómata **rechaza** y nos dice qué símbolos faltan.
- **Gramáticas BNF** (las *gramáticas libres de contexto*): describen la
  estructura completa de la tesis como un conjunto de producciones, y un
  **parseador descendente recursivo** comprueba si el documento "deriva" de
  ellas.

Todo esto se construyó **sin romper el contrato externo** (ni el de la API
ni el del motor). Es el mismo motor por fuera, reestructurado por dentro.

---

## 2. Cómo funciona un DOCX por dentro (contexto necesario)

Para entender el cambio hay que saber qué es un `.docx`:

> Un `.docx` es un **ZIP** que contiene varios archivos XML. El más
> importante es `word/document.xml`, que guarda **todos** los párrafos del
> documento con su formato. Cada párrafo es un `<w:p>`, y dentro de él cada
> "run" `<w:r>` contiene texto `<w:t>` y formato (`<w:rPr>`: fuente, tamaño,
> negrita…). Además, cada párrafo puede tener un **estilo de párrafo**
> `<w:pStyle w:val="Ttulo1"/>` que indica si es un **título** (Heading 1,
> Heading 2, Título 1…) o texto normal.

Las herramientas que ya existían en el proyecto y que se reutilizaron:

| Pieza | Dónde | Qué hace |
|---|---|---|
| `extract()` | `validator/extractor.py` | Abre el ZIP, parsea `document.xml` (y `footer1.xml`, `header1.xml`) con `lxml` y lo deja listo como árbol XML |
| `text_of(nodo)` | `validator/extractor.py` | Concatena todo el texto `<w:t>` de un nodo (para leer el texto de un párrafo completo) |
| `ExtractedDocx.part()` | `validator/extractor.py` | Devuelve el árbol de `document`, `footer` o `header` |
| `ExtractedDocx.is_cuerpo(nodo)` | `validator/extractor.py` | Dice si un párrafo pertenece al **cuerpo** (la última sección con estilo Normal) |

---

## 3. El núcleo de la respuesta a "¿cómo se toma en cuenta la estructura?"

Esta es la parte más importante de entender, así que se explica con
detenimiento.

### 3.1 El motor NO lee el contenido de las secciones: lee los TÍTULOS

Cuando el validador comprueba la estructura (por ejemplo:
"Carátula → Dedicatoria → Jurado → Índice → Presentación → Resumen → …"),
**no está leyendo el texto de cada sección ni contando su contenido**. Usa
la **estructura tipográfica que el propio Word declara en el XML**: los
**estilos de párrafo**.

Esto es lo que hace `AutomataSecuencia._headings()`:

```python
def _headings(self, extracted):
    doc = extracted.document
    textos = []
    for p in doc.xpath("//w:body//w:p", namespaces=NS):   # todos los párrafos
        pPr = p.find(W + "pPr")
        st  = pPr.find(W + "pStyle") if pPr is not None else None
        if st is not None:
            val = st.get(W + "val")
        if val and ("eading" in val or "tulo" in val):    # Heading1..3 / Ttulo1..3
            textos.append(text_of(p).strip())             # el texto del título
    return textos
```

Es decir:

- Recorre **todos los párrafos** de `document.xml`.
- Se fija en su **estilo de párrafo** (`w:pStyle`).
- Solo recolecta los que tienen un estilo con `"eading"` (encaja con
  `Heading1`, `Heading2`, `Heading3`, …) o `"tulo"` (encaja con
  `Ttulo1`, `Ttulo2`, … — así los guarda Word en español).
- Guarda el **texto** de esos títulos como el *flujo de símbolos* de entrada.

> **Consecuencia**: si un documento tiene "INTRODUCCIÓN" escrito en un
> párrafo sin estilo de título (párrafo normal), el validador **no lo
> considera** una sección. La estructura se valida sobre lo que Word "sabe"
> que es un título, no sobre lo que nosotros *creemos* que es un título.

### 3.2 La carátula es la excepción (se detecta por CONTENIDO)

La carátula en las plantillas de la UNT **no usa estilo de encabezado**: el
nombre de la universidad es un párrafo normal, centrado, con negrita. Por
eso el validador la reconoce por **contenido**, no por estilo:

```python
def _caratula_ok(self, extracted):
    doc = extracted.document
    for p in doc.xpath("//w:body/w:p", namespaces=NS):   # primeros párrafos
        t = text_of(p).strip()
        if t:                                             # el primer párrafo no vacío
            return "universidad" in t.lower()             # ¿menciona "universidad"?
    return False
```

Si el primer párrafo con texto del documento contiene "universidad", se da
por satisfecho el estado `caratula` sin necesidad de estilo de título.

### 3.3 Y el CONTENIDO de cada sección, ¿cuándo se valida?

Hay dos casos:

1. **Contenido de formato (fuente, tamaño, interlineado, alineación,
   márgenes)**: se valida SOLO sobre los párrafos del **cuerpo**, gracias a
   la noción `contexto: cuerpo` del `extractor`. "Cuerpo" se define en
   `_cuerpo_paras()` como:

   > los párrafos que están **después del último `<w:sectPr>`** (es decir,
   > después del último salto de sección real del documento) **y** cuyo
   > estilo es Normal (o no tiene estilo explícito).

   Ejemplo de regla con este contexto (`fuente_principal`):

   ```yaml
   atributo_xml:
     parte: document
     contexto: cuerpo            # OJO: solo párrafos del cuerpo
     xpath: //w:body//w:p[w:r]/w:r[1]/w:rPr/w:rFonts
     atributo: "@w:ascii"
     comparacion: all_eq
     esperado: Times New Roman
   ```

   Así comprobamos que **el texto de cuerpo** sea Times New Roman 12 pt sin
   exigírselo a los títulos ni a la carátula.

2. **Contenido "de fondo" (cuántas palabras tiene el Resumen, cuántas
   referencias hay, si hay imágenes…)**: **hoy no se valida con el DFA**.
   Son las reglas que estaban en `no_deterministas` (mínimos de palabras,
   mínimos de referencias, etc.). El plan (ver `docs/PLAN_DSL.md`, F3)
   las mecanizará con analizadores nuevos como `patron_cantidad` (contar
   palabras) y `conteo_nodos` (contar párrafos de la sección Referencias).

### 3.4 Resumen de la respuesta

| ¿Qué se valida? | ¿Cómo? | ¿Dónde? |
|---|---|---|
| **Orden de secciones** (Índice, Introducción, …) | Estilos de párrafo `Título`/`Heading` → flujo de símbolos → **DFA** | `automata_secuencia` |
| **Presencia de la carátula** | Primer párrafo contiene "universidad" | `AutomataSecuencia._caratula_ok` |
| **Formato del cuerpo** (fuente, tamaño, interl., alineación, márgenes) | XPath con `contexto: cuerpo` (párrafos tras el último sectPr, estilo Normal) | `atributo_xml` / `presencia_xml` |
| **Texto de carátula** (mayúsculas, negrita, patrón) | Regex sobre el texto del nodo | `patron_texto` |
| **Línea de investigación** | Pertenencia a catálogo | `lista_texto` |
| **Imágenes** (logotipo) | Conteo de blips por XPath | `imagen` |
| **Cantidad de palabras / referencias** | (Plan F3) `patron_cantidad`, `conteo_nodos` | Futuro |

---

## 4. Paso a paso de lo implementado (muy detallado)

### Paso 1 — `validator/automata.py` (nuevo): los objetos formales

#### 1.1 `Transicion`

```python
@dataclass
class Transicion:
    desde: str          # estado de origen
    hacia: str          # estado de destino
    patron: str         # expresión regular que el token debe matchear
    consumir: bool = True  # False = transición épsilon (no consume entrada)
```

¿Por qué existe la transición "épsilon"? En la teoría de autómatas, una
transición épsilon permite cambiar de estado **sin consumir símbolos**. Aquí
se diseñó para modelar **secciones opcionales** (por ejemplo "Dedicatoria
(opcional)"): si no aparece, se puede "saltar" el estado sin consumir
ningún título. Actualmente el DSL se implementa omitiendo por completo los
opcionales (ver Paso 3), pero la abstracción queda disponible y es la forma
"correcta" de hacerlo en la teoría.

#### 1.2 `DFA` — autómata finito determinista

El `DFA` recibe:

- `estados`: nombres de los estados.
- `transiciones`: la lista de `Transicion`.
- `inicial`: el estado de partida.
- `aceptacion`: los estados que, al alcanzar, significan "documento válido".
- `prefijos_parciales`: tolerancia a que el token y el patrón coincidan por
  prefijo y no exactamente (preserva la tolerancia del motor anterior).
- `reconocimiento_backtracking`: activa el modo con retroceso.

El método central, `reconocer(tokens)`, implementa la **búsqueda dirigida
por estados**:

```python
while True:
    progreso = False
    for desde, hacia, patron, consumir in self._trans_comp:
        if desde != estado:
            continue
        # (épsilon) saltar sin consumir
        # búsqueda greedy: escanear tokens desde `pos` hasta el primer match
        # si hay match: estado = hacia; pos = match + 1
    if not progreso:
        break
if estado in self.aceptacion:
    return True, []
return False, self._siguientes_aceptables(estado)   # qué faltó
```

Explicación en lenguaje natural:

- Se mantiene un único "puntero" `pos` en el flujo de títulos.
- En cada paso se mira la transición saliente del estado actual y se
  **busca el siguiente título** que matchee su patrón (desde `pos` en
  adelante).
- Si se encuentra: se consume (avanza `pos` y cambia de estado).
- Si no hay ninguna transición que pueda avanzar, se termina.
- Se acepta **solo si** el estado final es de aceptación.

El detalle clave del matching (`_matchea_token`):

```python
def _matchea_token(token, patron, prefijos):
    if prefijos:
        return bool(
            patron.search(token)
            or token[:25] == patron.pattern[:25]     # tolerancia de prefijo
        )
    return bool(patron.fullmatch(token))
```

Es decir: un título "Introducción y objetivos" matchea el estado
`introduccion` porque comienza por el patrón — igual que toleraba el motor
anterior.

`DFA` también tiene `reconocer_con_backtracking(tokens)`: una variante que
**no se conforma con el primer match**; prueba todas las interpretaciones
(estilo **NFA simulado**, búsqueda en profundidad) y acepta si *algún*
camino llega a un estado de aceptación. Es más lento, pero más robusto
frente a ambigüedades.

#### 1.3 `GramaticaEstructura` — gramática BNF

Recibe producciones escritas como texto, p. ej.:

```python
"TESIS → CARATULA INDICE INTRODUCCION CUERPO CONCLUSIONES REFERENCIAS"
"CUERPO → METODOLOGIA RESULTADOS"
```

Qué hace:

- `__post_init__`: parsea cada producción en el formato
  `no_terminal → símbolo símbolo … | alternativa | …`, y guarda, para cada
  no-terminal, la lista de alternativas.
- `secuencias_esperadas()`: expande `inicio` (p. ej. `TESIS`) transitivamente
  hasta obtener todas las **secuencias de terminales** posibles.
- `analizar(tokens)`: recorre las secuencias esperadas y comprueba que los
  tokens del documento las cubran **en orden**, reportando qué terminales
  faltan (con el mismo algoritmo de "puntero que no retrocede").

En la teoría de Compiladores esto es un **parseador descendente recursivo**
muy simplificado: se parte del símbolo inicial y se expande hasta los
terminales, comparando contra el flujo de entrada.

¿Por qué separar `automata.py` de todo el XML? Porque así la teoría vive en
un módulo **puro** (sin lxml, sin DOCX): se puede probar con listas de
strings y se puede **enseñar y demostrar** de forma aislada — exactamente lo
que se pide para los cursos de Lenguajes Formales y Autómatas y de
Compiladores.

---

### Paso 2 — `validator/analizadores.py` (nuevo): los analizadores de hoja

La interfaz común:

```python
class Analizador(ABC):
    def __init__(self, config: dict): self.config = config or {}
    @abstractmethod
    def analizar(self, extracted: ExtractedDocx) -> Tuple[bool, str]: ...
```

Los cuatro analizadores atómicos ("de hoja", porque no están compuestos por
otros):

| Clase | Sección DSL | Qué hace en detalle |
|---|---|---|
| `AnalizadorXML` | `atributo_xml`, `presencia_xml` | Resuelve el XPath con los namespaces del DOCX, opcionalmente filtra por `contexto: cuerpo`, y compara: `exists`/`not_exists` (cantidad de nodos), o un atributo con `eq` (primer valor), `all_eq` (todos) o `contains` (subcadena, con `ignore_case`) |
| `AnalizadorRegex` | `patron_texto` | Extrae todo el texto `<w:t>` de los nodos y aplica la regex con `coincidencia: todos / alguno / ninguno` (¿todos deben cumplir, al menos uno, o ninguno?) y `comparacion: regex` (search) / `fullmatch` (coincidencia exacta completa) |
| `AnalizadorLista` | `lista_texto` | Extrae el texto de los nodos, lo normaliza (colapsa espacios, opcional lower), y comprueba que esté en la lista permitida (por ejemplo, el catálogo de 46 líneas de investigación) |
| `AnalizadorImagen` | `imagen` | Cuenta los nodos (blips/drawings) del XPath y valida `cantidad_minima` y `cantidad_maxima` |

¿Por qué importa el `fullmatch`? Porque 5 reglas legacy de la carátula
(negrita/mayúsculas) verifican que TODO el texto del título sea
mayúsculas: el patrón `^[A-ZÁÉÍÓÚÑ0-9 .,-]+$` se aplica con **coincidencia
completa**, no con búsqueda parcial. Si el DSL no soportara `fullmatch`,
esas reglas migrarían mal (un texto con minúsculas en medio "matchearía"
por contener alguna mayúscula). Por eso `AnalizadorRegex` lo soporta y el
migrador (plan) fija `comparacion: fullmatch` en esos casos.

---

### Paso 3 — `validator/compilador.py` (nuevo): el compilador DSL

Este es el "front-end de compilador" más claro de todo el cambio. Hace de
puente entre el **lenguaje declarativo** (el YAML del DSL) y los
**analizadores ejecutables**.

#### 3.1 `AutomataSecuencia(Analizador)` — el puente DOCX → DFA

Tiene cuatro piezas:

a) `_headings(extracted)`: extrae los títulos (párrafos con estilo
   `Heading…`/`Ttulo…`) → el flujo de símbolos que alimentará el DFA.

b) `_normalizar(s)`: prepara cada texto de título para comparar:
   - `mayusculas` → `s.upper()`
   - `ignorar_indent` → quita espacios de los laterales
   - siempre: colapsa espacios múltiples, quita "(OPCIONAL)", quita puntos
     finales.

c) `_caratula_ok(extracted)`: detecta la carátula por contenido (ver 3.2).

d) `_build_dfa(estados_cfg)`: traduce la lista `estados` del YAML a un DFA
   concreto:

   ```python
   origen = "__inicio__"
   for e in estados_cfg:
       if e.get("opcional"):
           continue                      # los opcionales se omiten
       estados.append(e["nombre"])
       transiciones.append(Transicion(desde=origen, hacia=e["nombre"],
                                      patron=e.get("patron", e["nombre"])))
       origen = e["nombre"]
   aceptacion = [origen] if estados else []   # SOLO el último obligatorio
   ```

   ¿Por qué los opcionales se **omiten** y no se les hace transición
   épsilon? Para mantener la **paridad exacta** con el comportamiento del
   motor legacy `_check_secuencia`, que simplemente saltaba los ítems
   "(OPCIONAL)" y exigía solo los obligatorios.

   ¿Por qué la aceptación es **solo el último estado**? Porque "llegar al
   último estado obligatorio" implica haber pasado por todos los anteriores
   en orden. Si se marcaran como aceptación los estados intermedios, un
   documento que solo tiene "INTRODUCCIÓN" (cuando se esperan
   "INTRODUCCIÓN" y "RESULTADOS") se aceptaría indebidamente. Este fue un
   bug real que se detectó y corrigió en la semana (ver Paso 6).

e) `analizar(extracted)`: junta todo:
   - Detecta carátula (y la saca de los estados activos si se satisfizo).
   - Construye el DFA con los estados restantes.
   - Normaliza los headings y llama `dfa.reconocer(headings)`.
   - Devuelve `(True, …)` si aceptó o `(False, "faltantes=…")` con la lista
     de títulos esperados que no se encontraron.

#### 3.2 `GramaticaEstructuraAnalizador` — puente DOCX → gramática

Equivalente al anterior pero usando `GramaticaEstructura`: extrae los
headings, crea la gramática a partir del YAML y llama `gramatica.analizar()`.

#### 3.3 `ReglaCompilada` — la regla compilada

Es el par `(regla, [analizadores])`. Su método `ejecutar(extracted)`:

1. Corre **todos** los analizadores de la regla (semántica **AND**: todos
   deben cumplir).
2. Si un analizador lanza excepción, lo registra como fallo (un analizador
   roto no debe tumbar el reporte completo).
3. Recolecta los detalles de los fallos y construye el `RuleResult` con
   `severity`, `message`, `expected` (el `valor_esperado`), `found` (los
   fallos, o "cumple"), `location`, `fuente` y `cita` provenientes del YAML.

Es decir: **la salida es idéntica a la del motor legacy**, aunque por dentro
se haya usado un DFA, una regex o una gramática.

#### 3.4 `CompilerDSL` — la tabla de despacho

```python
_FABRICAS = {
    "atributo_xml":        AnalizadorXML,
    "presencia_xml":       AnalizadorXML,
    "patron_texto":        AnalizadorRegex,
    "lista_texto":         AnalizadorLista,
    "imagen":              AnalizadorImagen,
    "automata_secuencia":  AutomataSecuencia,
    "gramatica_estructura":GramaticaEstructuraAnalizador,
}
```

`CompilerDSL.compilar(rules_data)` recorre la lista `reglas` del YAML y, para
cada sección del DSL presente en la regla (`SECCIONES_ANALIZADOR`), consulta
la tabla y crea el analizador correspondiente. Esto reemplaza la cadena
`if/elif` del motor viejo por una **tabla de despacho** (patrón *Registry /
Factory*).

---

### Paso 4 — `validator/engine.py` (modificado): doble formato sin romper nada

Antes: `validate_docx` iteraba sobre `rules_data["rules"]` y ejecutaba los
`checks` legacy.

Ahora:

```python
def validate_docx(docx_path, rules_data):
    extracted = extract(docx_path)
    if "reglas" in rules_data:                    # formato DSL (nuevo)
        return CompilerDSL().ejecutar(rules_data, extracted)
    return _validate_legacy(rules_data, extracted)  # formato legacy
```

- `_validate_legacy()` contiene el código original intacto (movido a una
  función privada).
- `load_rules`, `filter_by_severity`, `build_report` **no cambiaron**.

¿Por qué mantener el formato legacy? Por tres razones:

1. **No romper nada**: la API, la CLI y los tests de contrato siguen
   funcionando sin cambios.
2. **Migración gradual**: se puede traducir regla por regla al DSL y
   comparar resultados (tests de paridad), sin un "big bang".
3. **Reversibilidad**: si una regla DSL diera un falso positivo, se puede
   volver a la versión legacy mientras se corrige.

---

### Paso 5 — `tests/test_dsl.py` (nuevo): pruebas sin plantillas externas

Las plantillas oficiales están en `.gitignore` (no se versionan), así que no
podemos depender de ellas para probar el DSL. La solución fue construir
**DOCX sintéticos en memoria**:

- `_make_docx(headings, cover)`: crea un ZIP OPC mínimo con
  `[Content_Types].xml`, `_rels/.rels` y `word/document.xml`, donde cada
  heading se emite como `<w:p><w:pPr><w:pStyle w:val="Ttulo1"/></w:pPr>…`.
- Con eso, `extract()` (el extractor real) puede abrirlo y el motor completo
  se ejecuta de verdad, sin depender de archivos externos.

Los 16 tests:

| Clase | Qué verifica |
|---|---|
| `TestDFA` | Reconocer una secuencia completa, rechazar una incompleta, greedy que no retrocede, backtracking que no se cuelga |
| `TestGramatica` | Expansión de `secuencias_esperadas`, `analizar` con doc ok y con sección faltante |
| `TestCompiladorDSL` | Compilación de reglas, `atributo_xml` que cumple, secuencia que cumple / no cumple, gramática que cumple, carátula detectada por párrafo |
| `TestContratoMotor` | `validate_docx` devuelve `RuleResult` con los mismos campos de `to_dict()`, y `build_report` mantiene `semaforo/resumen/resultados` |

---

### Paso 6 — Bug real detectado y corregido: la aceptación del DFA

**Síntoma**: el test `test_secuencia_no_cumple` fallaba: con solo
"INTRODUCCIÓN" presente y esperándose "INTRODUCCIÓN" y "RESULTADOS", el
autómata devolvía `passed=True`.

**Causa**: en la primera versión de `_build_dfa`, todos los estados
obligatorios se agregaban al conjunto `aceptacion`. Al reconocer "INTRODUCCIÓN"
el DFA quedaba en el estado `introduccion`… que era de aceptación. Por eso
"aceptaba".

**Corrección**: la aceptación pasó a ser **solo el último estado
obligatorio**. Si no se llega a ese estado, el DFA rechaza y reporta en
`faltantes` los patrones alcanzables que faltaron (por ejemplo "RESULTADOS").

**Lección de teoría aplicada**: en un DFA, un estado no es "de aceptación"
por estar en el medio; el estado de aceptación es aquel en el que el flujo
de entrada se considera **agotado y válido**. Aquí "válido" significa "la
trama de secciones llegó hasta el final esperado".

---

### Paso 7 — Modo `backtracking`

Se agregó `reconocer_con_backtracking()` al `DFA`. En lugar de quedarse con
el primer match de cada transición (greedy), explora todas las
interpretaciones con búsqueda en profundidad (estilo NFA simulado) y acepta
si **existe algún camino** a la aceptación.

Se expone en el DSL con `reconocimiento: greedy | backtracking`
(default `greedy`, para mantener el comportamiento histórico y la paridad
con el motor legacy).

¿Por qué incluir las dos? Porque **teóricamente todo NFA puede
determinizarse** (teorema del subconjunto), pero en la práctica la
determinización puede multiplicar los estados. Tener el simulador NFA a mano
es la solución pragmática que prefieren los implementadores de compiladores
cuando el DFA crece de forma explosiva.

---

### Paso 8 — Ejemplo DSL y documentación

- `reglas_dsl_ejemplo.yaml`: 8 reglas de ejemplo que cubren **los 6 tipos de
  analizador** (atributo_xml, presencia_xml, patron_texto, lista_texto,
  imagen, automata_secuencia y gramatica_estructura). Es la "plantilla" de
  referencia para la migración del YAML grande.
- `docs/DSL.md`: la referencia de la gramática del DSL (todas las secciones,
  con sus parámetros, ejemplos y cómo extender).

---

### Paso 9 — F1 cerrada: migración completa y paridad exacta (2026-09-08)

La F1 del plan ([`PLAN_DSL.md`](PLAN_DSL.md)) convirtió las **32 reglas
mecanizadas** del YAML legacy al DSL y verificó **paridad exacta** de
comportamiento entre ambos motores. Los 4 detalles que se ajustaron por paridad:

**1) Hook `matche` en el DFA** (`validator/automata.py`)

El `DFA` acepta un parámetro `matche` (callable) que decide si un token
satisface un patrón; por defecto usa `_matchea_token`. `AutomataSecuencia`
inyecta `_matchea_legacy`, que replica **exactamente** la semántica de
`checks._check_secuencia` del motor legacy:

- `token.startswith(patron)` o `patron.startswith(token[:25])` (tolerancia de
  prefijo),
- o igualdad de **token significativo** (`_sig_token`): el primer token con
  ≥ 4 caracteres alfanuméricos, sin puntuación (p. ej. "1.3. EL PROBLEMA"
  matchea "EL PROBLEMA").

Sin este hook, el DFA (greedy, 1-char) rechazaba títulos reales numerados como
"1.5 VARIABLE(S) Y OPERACIONALIZACIÓN" que el legacy sí aceptaba.

**2) `_faltantes_legacy`: el detalle de secuencia ya no usa el DFA**

> Nota: **supera** la descripción de los Pasos 6 y 7. El DFA sigue siendo quien
> decide `passed`, pero el `found` ("faltantes=…") ya no es la lista de
> transiciones alcanzables: ahora `AutomataSecuencia._faltantes_legacy()`
> reproduce el escaneo del motor legacy — recorre los estados en orden, salta
> los `opcional` y la carátula si `cover_ok`, matchea con `_matchea_legacy` y
> reporta el ítem **original** del `valor_esperado` (tope 6). Así el texto del
> reporte es idéntico al legacy incluso cuando el DFA y el escaneo discrepan.

**3) Secciones con lista de configuraciones** (`compilar()`)

El valor de una sección DSL puede ser una **lista** de configs (semántica AND).
Lo requieren 4 reglas legacy con múltiples checks del mismo tipo:
`papel_tamano`, `interlineado` (2× `atributo_xml`), `numeracion_posicion`
(2× presencia + 1 atributo) e `indice_subdivisiones` (3× presencia).

**4) Orden de secciones según la regla**

`compilar()` itera las secciones en el **orden en que aparecen en la regla**
(no la tabla fija `SECCIONES_ANALIZADOR`), para que el `found` de
`numeracion_posicion` conserve el orden "exists / nodos / atributo" del legacy.

**Verificación F1**: `tests/test_paridad_formatos.py` (3 DOCX sintéticos) +
`scripts/evaluar_paridad_plantillas.py` contra los 6 `.docx` reales de
`recursos/` (5 plantillas + manual): paridad **exacta** en `rule_id`, `passed`
y `found`. Suite completa: **37 tests**. `reglas_unt.yaml` se genera con
`scripts/migrar_legacy_a_dsl.py` y **no lo carga la API todavía** (ver
`README.md`).

---

## 5. Mapeo con los cursos (Lenguajes Formales y Autómatas · Compiladores)

| Concepto de la semana | Concepto de los cursos | Componente |
|---|---|---|
| "El documento es un flujo de símbolos" | Alfabeto / cadena de entrada | `AutomataSecuencia._headings()` → flujo de títulos |
| "El DFA acepta si la secuencia es válida" | Autómata finito determinista y lenguajes regulares | `DFA`, `reconocer()` |
| "El DFA rechaza y dice qué faltó" | Lenguaje complementario / reporte de rechazo | `_siguientes_aceptables()` |
| Transición con tolerancia de prefijo | ε-transiciones y simplificación de autómatas | `prefijos_parciales`, `consumir=False` |
| "Pruebo todos los caminos" | Simulación de NFA / determinización | `reconocer_con_backtracking()` |
| Patrones de texto | Lenguajes regulares, expresiones regulares | `AnalizadorRegex`, `patron_texto` |
| Gramática BNF de la tesis | Gramáticas libres de contexto, derivación | `GramaticaEstructura`, `gramatica_estructura` |
| Parsear del inicio y expandir | Análisis sintáctico descendente (recursive descent) | `GramaticaEstructura.analizar()` |
| YAML → analizadores ejecutables | Compilación: del lenguaje fuente al ejecutable | `CompilerDSL`, `_FABRICAS`, `ReglaCompilada` |
| Extraer títulos = tokens | Análisis léxico (tokenización) | `_headings()`, `tokenizer.py` (plan F2) |

---

## 6. Por qué Nix no necesitó cambios

Los módulos nuevos importan **únicamente librería estándar de Python** y dos
paquetes que el `flake.nix` **ya tenía**:

| Módulo | Imports externos | ¿Ya estaba en `flake.nix`? |
|---|---|---|
| `automata.py` | `re`, `dataclasses`, `typing` | — (stdlib) |
| `analizadores.py` | `re`, `abc`, `typing` + lxml | `lxml` ✅ |
| `compilador.py` | `re`, `dataclasses`, `typing` + lxml + yaml | `lxml`, `pyyaml` ✅ |
| `engine.py` | `yaml`, lxml | `pyyaml`, `lxml` ✅ |
| `tests/test_dsl.py` | `zipfile`, `tempfile`, `pathlib` | — (stdlib) |

El entorno ya era reproducible con:

```bash
nix develop
pytest tests/ -v        # suite completa (API + DSL + contrato)
```

**Regla que se respetó**: nada de `pip install`; todo lo que haga el proyecto
debe ir en `flake.nix`. Como no se introdujeron dependencias nuevas, el
`flake.nix` **quedó igual**. Si en el futuro se quiere una librería nueva
(p. ej. `hypothesis` para los tests de propiedad del plan F6), ahí sí se
edita `flake.nix` **antes** de usarla, y se hace commit de ese cambio solo.

---

### Paso 10 — F2: tokenizer, PDA y sección `automata_pila` (2026-09-09)

La F2 del plan ([`PLAN_DSL.md`](PLAN_DSL.md)) sube un nivel en la jerarquía de
Chomsky: del **lenguaje regular** (DFA) al **lenguaje libre de contexto**
(PDA), y centraliza el **análisis léxico** del documento en un tokenizer.

**1) `validator/tokenizer.py` — análisis léxico**

Convierte `<w:body>` en un flujo tipado de tokens en orden de documento:

| Tipo | Origen |
|---|---|
| `TITULO(nivel, texto)` | párrafo con pStyle que contiene "eading"/"tulo" (paridad legacy) |
| `PARRAFO(texto)` | párrafo sin estilo de encabezado |
| `TABLA` | bloque `w:tbl` (incluye los párrafos anidados de sus celdas) |
| `IMAGEN` | un blip embebido (`w:drawing//a:blip`) |
| `SALTO_SECCION` | `w:sectPr` (directo en body o anidado en pPr, emitido tras el párrafo) |

Recorre `body.iter(...)` (párrafos anidados dentro de tablas incluidos, como el
XPath `//w:body//w:p` del legacy). Expone `solo()` (filtro por `tipos`) y
`textos()` (proyección de texto para DFA/PDA/gramática).

**2) `PDA` en `validator/automata.py`**

`TransicionPDA` extiende `Transicion` con `push`/`pop`. La clase `PDA` hereda
el motor greedy del DFA y verifica anidación:

- **Aceptación**: estado final **Y pila vacía** → "estructura cerrada". Si se
  llega a un estado de aceptación con pila no vacía, reporta los símbolos sin
  cerrar (`estructura sin cerrar: falta …`).
- `pop` exige que el tope de la pila sea el símbolo pedido (tope inesperado →
  rechazo inmediato).
- Transiciones **épsilon** (`consumir: false`) para moverse sin avanzar la
  entrada.

**3) Sección DSL `automata_pila`** (`validator/compilador.py`)

Nueva sección de analizador + alta en `SECCIONES_ANALIZADOR` y `_FABRICAS`.
Configura `inicial`, `aceptacion` y `transiciones` (con `push`/`pop`), y opciones
compartidas con los otros autómatas: `tipo_flujo`, `tipos`, `normalizacion`.

**4) `tipo_flujo` y gramática con tokens**

- `AutomataSecuencia` acepta `tipo_flujo: titulos | documento`. `titulos`
  (default) usa solo los `TITULO` — reproducción exacta de la proyección
  histórica. `documento` proyecta el flujo completo filtrado por `tipos`.
- `gramatica_estructura` acepta `tipo_flujo`/`tipos`: la BNF consume el
  flujo tokenizado en lugar de la lista de headings (backward compatible).

**5) Refactor de las proyecciones históricas**

`AutomataSecuencia._headings()` y la ruta de títulos de
`GramaticaEstructuraAnalizador` ya **no recorren el XML**: consumen
`solo(tokenizar(...), [TITULO])`. Quedó duplicada la misma semántica legacy
(condición "eading"/"tulo", `text_of().strip()`, orden documental) y se eliminó
el import `W` del compilador. La paridad se re-verificó tras el refactor.

**Regla de ejemplo**: `estructura_capitulos_pila` en `reglas_dsl_ejemplo.yaml`
(abre `CAPÍTULO` con `push`, cierra con `FIN DE CAPÍTULO`/`pop` y exige
`EPÍLOGO` final con la pila vacía).

**Verificación F2**: `tests/test_f2_automatas.py` (16 tests: tokenizer, PDA
puro, `automata_pila` end-to-end y gramática con tokens) + suite completa
**53 tests** + paridad `scripts/evaluar_paridad_plantillas.py` OK en los 6
`.docx` reales. Nota de entorno: esta sesión corrió sin Nix (`/nix/store`
ausente); se usaron `pytest`, `fastapi`, `httpx` y `python-multipart` como runner
de tests sin tocar `flake.nix`.

### Paso 11 — F3: mecanización de reglas no deterministas (2026-09-09)

La F3 del plan (ver `docs/PLAN_DSL.md`) toma las **12 reglas sin mecanismo**
(aquellas cuya validación dependía del análisis semántico humano) y mecaniza
las **9 que tienen criterio verificable**, agregándolas a `reglas_unt.yaml`.
Se hizo **a mano** (el migrador `scripts/migrar_legacy_a_dsl.py` solo regen-era
las 32 legacy y las descartaría al re-ejecutar — está anotado en `_migracion`).

**Decisión de alcance** (aprobada): las 3 reglas de **referencias mínimas**
se aplican **sin detectar tipo de investigación**, con su severidad original
`warning` (no bloquean la entrega). Quedaron **documentadas como
no-automatizables**: `sistema_citas` (heurística autor-año débil),
`proyecto_formato_general` y `suficiencia_profesional_formato` (metareglas ya
cubiertas por las reglas generales de A4/TNR/1.5/márgenes).

**1) `tokenizer.seccion()` — acotar la validación por sección**

Nuevo helper del tokenizer (F2): `seccion(flujo, inicio, fin=None)` devuelve
los tokens posteriores al primer `TITULO` que matchea la regex `inicio`
(ignore case) y hasta el siguiente `TITULO`. Si `fin` es una regex, solo un
título que la matchee corta; sin más títulos, toma el final del flujo. Sin
match → lista vacía (la regla cae como fallo). Todas las secciones de F3 la
usan para no validar sobre todo el documento.

**2) Cuatro analizadores nuevos en `validator/analizadores.py`**

| Sección DSL | Analizador | Qué cuenta | Reglas que habilita |
|---|---|---|---|
| `patron_cantidad` | `AnalizadorCantidadPatron` | palabras / matches regex / entradas (`;`/`,`) | `resumen_longitud`, `palabras_clave_minimo` |
| `conteo_nodos` | `AnalizadorConteoNodos` | párrafos de una sección o nodos XPath (min/máx/múltiples) | `referencias_minimo_*` |
| `lista_obligatoria` | `AnalizadorListaObligatoria` | subcadenas normalizadas (ignore case) | `anexos_minimos_*` |
| `hipervinculo_texto` | `AnalizadorHipervinculo` | `w:hyperlink` cuyo texto matchea un patrón | `caratula_orcid` |

- `AnalizadorConteoNodos` es el **contador genérico**; `AnalizadorImagen` =
  subclase suya con etiqueta fija `imagenes` (el detalle `imagenes=N
  minimo=M` del legacy se conserva, paridad intacta).
- `AnalizadorCantidadPatron` soporta `filtro` por párrafo (`^palabras clave`)
  y `operacion: count_entries` para el texto posterior al primer `:`.
- `conteo_nodos` soporta `cantidades_multiples: [20, 30, 20]` (cumple si la
  cantidad alcanza cualquiera) — preparado para cuando se detecte el tipo de
  investigación.

**3) Registro en `validator/compilador.py`**

Alta de las 4 secciones en `SECCIONES_ANALIZADOR` y en `_FABRICAS` (mismo
patrón que F1/F2), con sus importaciones. Cada regla ejecuta todas sus
secciones (las secciones F3 coexisten con `patron_texto`/`atributo_xml` en la
misma regla, p. ej. `proyecto_caratula_texto`).

**4) Reglas agregadas a `reglas_unt.yaml` (32 → 41)**

Las 9 reglas F3 (resumen_longitud, palabras_clave_minimo,
referencias_minimo_cuantitativo/cualitativo/revision,
anexos_minimos_cuantitativo/cualitativo, caratula_orcid,
proyecto_caratula_texto) se insertan **antes de `_migracion:`**, que se anota
con `f3_reglas_agregadas_manualmente: 9` y `f3_no_automatizables: 3`. El
bloque de reglas se cierra con los 3 ids no-automatizables comentados. Las
severidades originales de cada regla **se respetan** (palabras_clave_error,
proyecto_caratula_texto error; el resto warning).

**5) Ajuste de la paridad (los motores siguen siendo equivalentes)**

El contrato de paridad exige que las 32 reglas legacy se comporten **igual**
en ambos motores — no que el DSL no tenga reglas extra. Se relajaron las
aserciones de `tests/test_paridad_formatos.py` y
`scripts/evaluar_paridad_plantillas.py`: ahora exigen `set(legacy) <=
set(dsl)` y comparan las 32 legacy una a una (`passed` y `found`).

**Verificación F3**: `tests/test_f3_mecanizacion.py` (21 tests: `seccion()`,
analizadores por regla, `cantidades_multiples`, imagen refactor, smoke de las
41 reglas en `reglas_unt.yaml`) + suite completa **74 tests** verdes +
paridad `PARIDAD: OK` (6/6 plantillas reales). Sin cambios en `flake.nix`
(solo `lxml`, `re` y stdlib). Entorno: igual que F2, sin Nix disponible.

---

1. Sintaxis de todos los módulos: `python3 -c "import ast; …"` OK.
2. Imports en cadena: `engine → compilador → analizadores/automata →
   extractor → lxml/yaml` OK.
3. Suite `tests/test_dsl.py` (16 tests): 16/16 en verde con Python 3.14 del
   sistema (solo se necesitan `pyyaml` y `lxml`).
4. Motor **legacy** re-verificado con un DOCX sintético: sigue omitiendo las
   reglas sin mecanismo y evaluando las mecanizadas.
5. `reglas_dsl_ejemplo.yaml`: compila sus 8 reglas (6 familias de analizador)
   y ejecuta de punta a punta sin excepciones.
6. La suite completa de contrato NO corrió en este entorno porque requiere
   `fastapi`/`pydantic`/`httpx` (viven dentro de `nix develop`). Pendiente:
   correr `pytest tests/ -v` dentro del entorno Nix.

**Bug detectado y corregido**: el de la aceptación del DFA (Paso 6), que
aceptaba secuencias incompletas.

---

## 8. Resumen técnico

| Archivo | Estado | Descripción |
|---|---|---|
| `validator/automata.py` | **nuevo** | `Transicion`, `DFA` (greedy + backtracking), `GramaticaEstructura` (BNF), `TransicionPDA`, `PDA` (push/pop) — teoría pura |
| `validator/tokenizer.py` | **nuevo** | Análisis léxico: flujo tipado (`TITULO`, `PARRAFO`, `TABLA`, `IMAGEN`, `SALTO_SECCION`, `nivel`), `seccion()`, `solo()`, `textos()` |
| `validator/analizadores.py` | **nuevo** | `Analizador` (ABC) + `AnalizadorXML`, `AnalizadorRegex`, `AnalizadorLista`, `AnalizadorConteoNodos` (+ `AnalizadorImagen` como subclase), `AnalizadorCantidadPatron`, `AnalizadorListaObligatoria`, `AnalizadorHipervinculo` |
| `validator/compilador.py` | **nuevo** | `CompilerDSL`, `ReglaCompilada`, `AutomataSecuencia`, `GramaticaEstructuraAnalizador`, `AutomataPila`, tabla `_FABRICAS` |
| `validator/engine.py` | **modificado** | detección de formato DSL vs legacy (`_validate_legacy`) |
| `tests/test_dsl.py` | **nuevo** | 16 tests con DOCX sintéticos en memoria |
| `tests/test_f2_automatas.py` | **nuevo** | 16 tests: tokenizer, PDA, automata_pila, gramática con tokens |
| `tests/test_f3_mecanizacion.py` | **nuevo** | 21 tests: seccion() y los 4 analizadores F3 contra reglas/41 |
| `reglas_unt.yaml` | **modificado** | 32 legacy → **41 reglas** (9 mecanizadas a mano; anotación en `_migracion`) |
| `reglas_dsl_ejemplo.yaml` | **nuevo** | 13 reglas de ejemplo (12 familias de analizador) |
| `docs/DSL.md` | **nuevo** | Referencia de la gramática del DSL (incluye tokenizer, automata_pila y F3) |
| `docs/PLAN_DSL.md` | **nuevo** | Plan futuro (migración, tokenizer, PDA, mecanizar reglas, traza, tests de propiedad) con 4 decisiones pendientes |

**Sin cambios**: `models.py`, `extractor.py`, `checks.py`, `prompts.py`,
`api.py`, `api_models.py`, `cli.py`, `flake.nix`, `unt_format_rules_schema.yaml`.

---

## 9. Postura de autoría y reflexión

Este trabajo de semana 3 demuestra, en la práctica preprofesional, la
aplicación directa de **Lenguajes Formales y Autómatas** (DFA, lenguajes
regulares, NFA simulado) y de **Compiladores** (análisis léxico de tokens del
documento, análisis sintáctico con BNF y parseo descendente, y la noción de
compilar un lenguaje declarativo —el DSL— a un ejecutable). El motor quedó
**más formal, más componible y más explicable**, sin romper ningún contrato
existente.

El camino completo (migrar las 32 reglas, tokenizar todo el documento,
autómatas de pila para estructuras anidadas, mecanizar las reglas de mínimos,
guardar la traza del autómata en el reporte y tests de propiedad) está
detallado en [`docs/PLAN_DSL.md`](PLAN_DSL.md), con 4 decisiones pendientes.