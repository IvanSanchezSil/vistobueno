# Bitácora Semana 6 — ivanSanchezSil

- **Integrante**: Iván Sánchez Silva (Integrante 3 — Motor de reglas)
- **Semana**: 6
- **Fechas**: 2026-09-23 → 2026-09-30
- **Rol**: Motor de reglas / Procesamiento (DSL, extractor, checks)

---

## Objetivos de la semana

1. **Analizar el MANUAL REVISADO TERCERA VERSION OBSERVACIONES 11-07-2025.docx** para identificar qué reglas de formato aún no están implementadas en el motor DSL (`reglas_unt.yaml`).
2. **Documentar el análisis comparativo** entre los requisitos del manual y las reglas actualmente implementadas (48 reglas).
3. **Establecer un plan de trabajo** para implementar las reglas faltantes en una fase futura, manteniendo el estado actual de la rama listo para posteriores desarrollos.

---

## Análisis comparativo: Manual vs Reglas DSL actuales

### Reglas actualmente implementadas (48 en `reglas_unt.yaml`)

El motor DSL actualmente implementa reglas que cubren:

**Formato general:**
- Tamaño de papel (A4, 210x297 mm)
- Fuente y tamaño del cuerpo (Times New Roman, 12 pt)
- Interlineado (1.5 líneas)
- Alineación del cuerpo (justificada)
- Márgenes (superior, inferior, derecho, izquierdo)
- Sangría de párrafo (1.27 cm / 0.5 pulgadas)

**Carátula:**
- Nombre de la Universidad: tamaño, negrita, mayúsculas, centrado
- Facultad y Escuela Profesional: tamaño, negrita, mayúsculas, centrado
- Título del trabajo: tamaño, negrita, mayúsculas/minúsculas, centrado
- Autor(es): tamaño, mayúsculas, orden alfabético, centrado
- Grado académico y código ORCID: hipervínculo entre paréntesis
- Asesor(a): tamaño, negrita, mayúsculas/minúsculas, centrado
- Línea de investigación: tamaño, orden alfabético
- Ciudad y país: tamaño, negrita, mayúsculas/minúsculas, centrado
- Logotipo de la Universidad: centrado, dimensiones 4.84 cm alto × 6.73 cm ancho
- Año en curso: tamaño
- Numeración de carátula: no se enumera pero se cuenta

**Estructura de documentos:**
- Índice: subdivisión (contenidos, tablas, figuras), páginas separadas, numeración, apuntado a secciones reales
- Resumen: extensión mínima 159 palabras
- Palabras clave: mínimo 3
- Referencias: cantidad mínima por tipo de investigación (cuantitativo, cualitativo, revisión, proyecto, informe, TSP)
- Sangría francesa en referencias: 1.27 cm (720 twips)
- Anexos: listas obligatorias por tipo de investigación
- Encabezados: membrete (logo UNT), formato (Times New Roman)
- Notas al pie: consistencia en numeración y estilo

**Estructuras formales ya implementadas (3 reglas de secuencia):**
- Estructura formal del Trabajo de Investigación Cuantitativo
- Estructura formal del Trabajo de Investigación Cualitativo
- Estructura formal del Trabajo de Revisión de la Literatura

### Reglas pendientes de implementación (brechas identificadas)

Tras el análisis detallado del MANUAL REVISADO TERCERA VERSION OBSERVACIONES 11-07-2025.docx, se identifican las siguientes reglas que **no están aún implementadas** en el motor DSL:

> Esta sección deja registrado el estado **en el momento del análisis**. Las 5
> estructuras del punto 1 se implementaron después en `reglas_unt_pendientes.yaml`
> (Paso 8 del plan), a propósito en un archivo aparte: la facultad no tiene
> plantillas oficiales de esos 5 tipos, así que no hay documento contra el que
> verificar el comportamiento. El punto 2 sigue pendiente.

#### 1. Estructuras formales de tipos adicionales de investigación (5 reglas)
Estas corresponden a los esquemas formales definidos en el Capítulo II del manual para títulos profesionales:

a) **Estructura formal del Proyecto de Investigación Cuantitativo**  
   - Carátula, Índice, I. Aspectos Generales, 1.4. Tipo de Investigación, 1.5. Línea de Investigación, 1.9. Recursos, II. Plan de Investigación, Problema de Investigación, Descripción de la realidad problemática, Formulación del problema, Justificación de la investigación, Limitaciones, Objetivos de la investigación, Marco Teórico, Antecedentes, Bases teóricas, Metodología, Población, Muestra y Muestreo, Diseño de Investigación, Métodos de Investigación, Instrumentos de Recolección de Datos, Técnicas de Procesamiento de Datos, Referencias, Anexos.

b) **Estructura formal del Proyecto de Investigación Cualitativo**  
   - Igual a la anterior hasta Bases Teóricas, luego: Definición de Términos, Matriz de Categorización y Unidad de Análisis, Metodología, Tipo de Estudio, Escenario, Selección de Participantes, Técnicas de Análisis e Interpretación de Datos, Referencias, Anexos.

c) **Estructura formal del Informe de Investigación Cuantitativo**  
   - Cubierta, Carátula, Dedicatory (opcional), Jurado Evaluador, Agradecimiento (opcional), Índice, Presentación, Resumen, Abstract, I. Introducción, El Problema, Situación Problematizada, Enunciado del Problema, Antecedentes, Justificación o Importancia, Limitaciones, Objetivos, Hipótesis, Operacionalización de las Variables, II. Marco Teórico (Estado del Arte), III. Metodología (Material y Métodos), Población, Muestra y Muestreo, Diseño de Contrastación, Instrumentos Usados en la Recolección de Datos, Métodos, Técnicas y Procedimientos…, IV. Análisis y Discusión de Resultados, V. Conclusiones y Recomendaciones, Referencias, Anexos.

d) **Estructura formal del Informe de Investigación Cualitativo**  
   - Cubierta, Carátula, Dedicatory (opcional), Jurado Evaluador, Agradecimiento (opcional), Índice, Presentación, Resumen, Abstract, I. Introducción, El Problema, Situación Problematizada, Enunciado del Problema, Antecedentes, Justificación o Importancia, Limitaciones, Objetivos, Matriz de Categorización y Unidad de Análisis, II. Marco Teórico, III. Metodología, Participantes, Diseño, Instrumentos Usados en la Recolección de Información, Métodos, Técnicas, Procedimientos y Estrategias Usados en el Análisis e Interpretación de Datos, IV. Análisis y Discusión de Resultados, V. Conclusiones y Recomendaciones, Referencias, Anexos.

e) **Estructura formal del Trabajo de Suficiencia Profesional**  
   - Cubierta, Carátula, Dedicatory (opcional), Jurado Evaluador, Agradecimiento (opcional), Índice, Presentación, Resumen, Abstract, Introducción, Problema, Situación o Realidad Problematizada, Enunciado del Problema, Justificación, Limitaciones, Objetivos (General, Específicos), Diseño de Sesión de Aprendizaje, Datos Informativos, Propósitos y Evidencias de Aprendizaje, Secuencia Didáctica, Recursos y Materiales Educativos, Referencias Bibliográficas, Anexos, Sustento Teórico Científico (Introducción, Desarrollo), Sustento Psicopedagógico (Introducción, Desarrollo), Conclusions, Referencias Bibliográficas, Anexos.

#### 2. Posibles mejoras en reglas existentes (pendientes de validación adicional)
Algunas reglas ya implementadas podrían requerir ajustes adicionales para cumplir con especificidades del manual:
- Verificación más detallada de dimensiones del logotipo (ya implementada con tolerancia)
- Validaciones adicionales en sangría francesa (ya implementada)
- Especificaciones más detalladas en referencias y anexos (ya implementadas con listas y conteos)

---

## Evidencias del análisis

| Tipo | Detalle |
|------|---------|
| Documento fuente | `recursos/MANUAL REVISADO TERCERA VERSION OBSERVACIONES 11-07-2025.docx` (1884 párrafos analizados) |
| Reglas actuales | 48 reglas en `reglas_unt.yaml` |
| Reglas pendientes | 5 estructuras formales adicionales (ver lista arriba) |
| Cobertura estimada | ~90% de reglas de formato básico implementadas, ~10% pendientes (estructuras de tipos adicionales) |

---

## Plan de trabajo (para fase futura)

Este análisis establece el punto de partida para un trabajo futuro de implementación. El plan recomendado sería:

1. **Implementación de las 5 estructuras formales faltantes**
   - Crear reglas DSL de tipo `secuencia` (autómata DFA greedy)
   - Definir estados obligatorios y opcionales según el manual
   - Configurar normalización (`[mayusculas, ignorar_indent]`) y reconocimiento (`greedy`)

2. **Actualización de tests y factory**
   - `tests/_mutations.py`: añadir las 5 nuevas reglas a `REGLAS` (47→52), definir mutaciones mínimas, actualizar `REGLAS_ACOPLADAS` y `EXCLUIDAS_BASE`
   - `tests/test_propiedad.py`: actualizar conteos esperados y conjunto `ESTRUCTURA`
   - `tests/test_f3_mecanizacion.py`: actualizar contadores y documentación
   - `tests/test_paridad_formatos.py`: ajustar pruebas de paridad
   - `tests/test_f4_ingenieria.py`: actualizar aserciones de conteo

3. **Validación y documentación**
   - Ejecutar `pytest tests/ -v` para verificar que todos los tests pasen
   - Verificar con `ruff check`, `ruff format --check` y `mypy`
   - Validar contra plantilla oficial: `python -m validator.cli plantilla.docx reglas_unt.yaml`
   - Actualizar documentación: `AGENTS.md`, `README.md`, `docs/diseno/00_indice_diseno.md`

4. **Entrega**
   - Trabajar en rama dedicada (ej: `semana6-estructuras-adicionales`)
   - Commits atómicos con mensajes en español y prefijos convencionales
   - Abrir PR a `master` para revisión y fusión

---

## Relación con competencias curriculares

- **Ingeniería de Software II**: Análisis de brechas, diseño incremental, planificación de trabajo futuro basado en especificaciones.
- **Estructura de Datos**: Modelado de estructuras secuenciales mediante autómatas finitos deterministas (DFA).
- **Redes de Computadoras I**: Comprensión de que los cambios en el motor DSL no afectan el contrato de la API (se mantiene independiente).

---

## Dificultades y aprendizajes del análisis

- **Amplitud del manual**: El documento normativo contiene especificidades detalladas que requieren interpretación cuidadosa para traducirlas a reglas automatizables.
- **Diferencia entre norma y plantilla**: Algunas especificidades del manual pueden no reflejarse exactamente en las plantillas oficiales utilizadas para testing.
- **Enfoque por capas**: El análisis reveló que la mayor parte del formato básico ya estaba cubierto, quedando pendientes principalmente las estructuras formales de los diferentes tipos de documentos.

---

## Estado actual y próximos pasos

**Estado actual de la rama `semana6`:**
- 48 reglas implementadas en `reglas_unt.yaml`, incluida la regla discriminadora
  `deteccion_tipo_documento`
- 5 estructuras adicionales implementadas en `reglas_unt_pendientes.yaml`, en un
  archivo aparte: la API no las carga porque no hay plantillas oficiales de esos
  5 tipos contra las que verificarlas
- 368 tests pasan (`nix flake check` → "all checks passed!")
- Trabajo publicado en el PR #36 con el CI en verde

**Cómo se ejecutó finalmente:** el trabajo se hizo sobre la rama `semana6`,
siguiendo los 9 pasos de `docs/PLAN_TIPO_DOCUMENTO.md`:
1. Los pasos 1 a 6 (andamiaje de dos fases, detección de tipo, la regla
   discriminadora, `aplicar_si` en las 3 estructuras, conteos dinámicos y
   centinelas de tipo sin determinar) quedaron en `reglas_unt.yaml`.
2. El paso 7 (contrato de API) se entregó como documento para el Integrante 1,
   en `docs/HANDOVER_API_TIPO_DOCUMENTO.md`, sin tocar la API.
3. El paso 8 (las 5 estructuras) quedó en `reglas_unt_pendientes.yaml`.
4. El paso 9 cerró la documentación (`docs/DSL.md`, README, AGENTS,
   índice de diseño).

**Aprendizaje sobre el manual:** dos rangos de párrafos del plan apuntaban a
párrafos de formato y no a los esquemas. Los rangos reales se localizaron por el
encabezado `ESQUEMA ...` de cada uno. Un punto del plan (el 4 del paso 8) se
descartó al cotejarlo: citaba una regla que no existe en el repositorio.

El análisis queda documentado como base para un trabajo futuro, listo para ser retomado cuando se disponga de tiempo y recursos para su implementación.