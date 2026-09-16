# Actividad 3 — Wireframes de las interfaces

**Proyecto:** VistoBueno — Validación automática de formato de tesis
**Institución:** Universidad Nacional de Trujillo (UNT) — FECyC
**Autor:** Integrante 2 (Frontend / Experiencia de usuario)
**Fecha:** Semana 3

---

## 1. Wireframe — Pantalla de carga (Escritorio)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌───────┐                                                                  │
│  │  VB   │  VistoBueno                                        [🌙] [←]    │
│  └───────┘  FECyC · Universidad Nacional de Trujillo                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Sube tu tesis                                                      │   │
│  │                                                                     │   │
│  │  Adjunta tu documento en formato DOCX o PDF y recibe un reporte    │   │
│  │  automático de cumplimiento con las directivas de formato de la UNT.│   │
│  │                                                                     │   │
│  │  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │   │
│  │                                                                 │  │   │
│  │  │                         📄                                   │  │   │
│  │                                                                 │  │   │
│  │  │            Arrastra tu archivo aquí                          │  │   │
│  │                                                                 │  │   │
│  │  │            o selecciónalo desde tu computadora               │  │   │
│  │                                                                 │  │   │
│  │  │               ┌─────────────────────┐                        │  │   │
│  │                  │ Seleccionar archivo │                        │     │
│  │  │               └─────────────────────┘                        │  │   │
│  │                                                                 │  │   │
│  │  │         Formatos permitidos: .docx, .pdf · Máx: 25 MB       │  │   │
│  │                                                                 │  │   │
│  │  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Sistema VistoBueno — Practicante · Biblioteca FECyC · UNT                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Wireframe — Pantalla de carga (Archivo seleccionado)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌───────┐                                                                  │
│  │  VB   │  VistoBueno                                        [🌙] [←]    │
│  └───────┘  FECyC · Universidad Nacional de Trujillo                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Sube tu tesis                                                      │   │
│  │                                                                     │   │
│  │  Adjunta tu documento en formato DOCX o PDF y recibe un reporte    │   │
│  │  automático de cumplimiento con las directivas de formato de la UNT.│   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │                                                             │   │   │
│  │  │  ┌──────┐                                                   │   │   │
│  │  │  │ DOCX │  mi_tesis_v2.docx                                │   │   │
│  │  │  └──────┘  2.34 MB                                         │   │   │
│  │  │                                                             │   │   │
│  │  │                            ┌─────────────────┐              │   │   │
│  │  │                            │  Validar   ✦    │              │   │   │
│  │  │                            └─────────────────┘              │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Sistema VistoBueno — Practicante · Biblioteca FECyC · UNT                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Wireframe — Pantalla de carga (Error de formato)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌───────┐                                                                  │
│  │  VB   │  VistoBueno                                        [🌙] [←]    │
│  └───────┘  FECyC · Universidad Nacional de Trujillo                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Sube tu tesis                                                      │   │
│  │                                                                     │   │
│  │  ┌ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┐  │   │
│  │                         📄                                       │  │   │
│  │            Arrastra tu archivo aquí                              │  │   │
│  │               ┌─────────────────────┐                            │  │   │
│  │               │ Seleccionar archivo │                            │     │
│  │               └─────────────────────┘                            │  │   │
│  │  └ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘  │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  ✕ No pudimos procesar tu archivo.                          │   │   │
│  │  │     Formato no soportado. Debes subir un archivo DOCX o PDF.│   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│  Sistema VistoBueno — Practicante · Biblioteca FECyC · UNT                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Wireframe — Pantalla de reporte (Semáforo + Resumen)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌───────┐                                                                  │
│  │  VB   │  VistoBueno                           [🌙]  [← Validar otro]   │
│  └───────┘  FECyC · Universidad Nacional de Trujillo                       │
│                                                                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  ┌─────┐                                                            │   │
│  │  │  ✕  │  Revisa antes de entregar                                 │   │
│  │  └─────┘  Se detectaron errores de formato que bloquean la entrega  │   │
│  │                                                                     │   │
│  │  Cumplimiento                                            76%       │   │
│  │  ████████████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░   │   │
│  │                                                                     │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                │   │
│  │  │     31      │  │      3      │  │      2      │                │   │
│  │  │   Reglas    │  │   Errores   │  │ Advertencias│                │   │
│  │  │ evaluadas   │  │             │  │             │                │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘                │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Wireframe — Pantalla de reporte (Controles + Filtros)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  (Todos)  (Errores)  (Advertencias)     [Detallada] [Simple]      │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  🔍 Buscar regla o mensaje...                          ✕   │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Wireframe — Pantalla de reporte (Vista detallada — Categorías)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  ▼ Papel                                                            │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  ✓  El tamaño del papel debe ser A4                     [ok]      │   │
│  │                                                                     │   │
│  │  ▼ Fuente y tamaño                                                  │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  ✓  La fuente del cuerpo debe ser Times New Roman        [ok]      │   │
│  │  ✓  El tamaño de letra del cuerpo debe ser 12pt          [ok]      │   │
│  │  ✓  El título del trabajo debe ser 14pt                  [ok]      │   │
│  │                                                                     │   │
│  │  ▼ Márgenes                                       1 err  0 warn   │   │
│  │  ─────────────────────────────────────────────────────────────────  │   │
│  │  ✓  El margen superior debe ser 2.5 cm                   [ok]      │   │
│  │  ✓  El margen izquierdo debe ser 3 cm                    [ok]      │   │
│  │  ✕  El margen derecho debe ser 2.5 cm                   [error]   │   │
│  │       Esperado: 2.5 cm                                           │   │
│  │       Encontrado: 2.5 cm aprox. (plantillas usan 708/709)        │   │
│  │  ✓  El margen inferior debe ser 2.5 cm                   [ok]      │   │
│  │                                                                     │   │
│  │  ▶ Interlineado                                       0 err      │   │
│  │  ▶ Alineación                                         0 err      │   │
│  │  ▶ Sangría                                            1 warn     │   │
│  │  ▶ Numeración de página                               1 err      │   │
│  │  ▶ Carátula                                           2 err      │   │
│  │  ▶ Estructura                                         0 err      │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Wireframe — Pantalla de reporte (Vista simple)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  Resumen de pendientes: corrige estos puntos para obtener          │   │
│  │  el visto bueno.                                                   │   │
│  │                                                                     │   │
│  │  ●  El margen derecho debe ser 2.5 cm                             │   │
│  │  ●  La sangría de primera línea debe ser 1.27 cm                  │   │
│  │  ●  Los preliminares deben numerarse en romanos                   │   │
│  │  ●  El título del trabajo debe ir en negrita y mixta              │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. Wireframe — Pantalla de reporte (Prompts IA)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                                                                     │   │
│  │  🤖 Cómo preguntar a una IA                                        │   │
│  │                                                                     │   │
│  │  Copia y pega estos prompts en cualquier IA (ChatGPT, Claude,      │   │
│  │  etc.) para corregir cada problema.                                │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  margen_derecho                    [Copiar]                 │   │   │
│  │  │                                                             │   │   │
│  │  │  Tengo un documento de tesis en Word (Universidad Nacional  │   │   │
│  │  │  de Trujillo). Detecté un problema de formato:              │   │   │
│  │  │                                                             │   │   │
│  │  │  - Regla incumplida: El margen derecho debe ser 2.5 cm     │   │   │
│  │  │  - Valor esperado según el reglamento: 2.5 cm              │   │   │
│  │  │  - Lo que encontró el validador: 2.5 cm aprox.             │   │   │
│  │  │                                                             │   │   │
│  │  │  ¿Puedes darme instrucciones paso a paso para corregir...? │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  │  ┌─────────────────────────────────────────────────────────────┐   │   │
│  │  │  sangria_parrafo                   [Copiar]                 │   │   │
│  │  │                                                             │   │   │
│  │  │  Tengo un documento de tesis en Word (Universidad Nacional  │   │   │
│  │  │  de Trujillo). Detecté un problema de formato:              │   │   │
│  │  │                                                             │   │   │
│  │  │  - Regla incumplida: La sangría de primera línea debe ser  │   │   │
│  │  │    1.27 cm                                                  │   │   │
│  │  │  - Lo que encontró el validador: 1.25 cm (708 twips)       │   │   │
│  │  │                                                             │   │   │
│  │  │  ¿Puedes darme instrucciones paso a paso para corregir...? │   │   │
│  │  └─────────────────────────────────────────────────────────────┘   │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    [Validar otro archivo]                           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Wireframe responsivo — Móvil (< 600px)

### Carga (móvil)

```
┌───────────────────┐
│ [VB] VistoBueno  │
│ FECyC · UNT       │
├───────────────────┤
│                   │
│  Sube tu tesis    │
│                   │
│  ┌ ─ ─ ─ ─ ─ ┐  │
│    📄            │
│  │ Arrastra    │  │
│    tu archivo    │
│  │ aquí        │  │
│                   │
│  ┌───────────┐   │
│  │ Seleccionar│   │
│  └───────────┘   │
│                   │
│  .docx,.pdf      │
│  Máx: 25 MB      │
│  └ ─ ─ ─ ─ ─ ┘  │
│                   │
└───────────────────┘
```

### Reporte (móvil)

```
┌───────────────────┐
│ [VB] VistoBueno  │
│ [🌙] [← Validar] │
├───────────────────┤
│                   │
│  ┌─────┐         │
│  │  ✕  │ Revisa  │
│  └─────┘         │
│                   │
│  ████████░░░ 76% │
│                   │
│  31    3    2    │
│  Reglas Err Warn │
│                   │
├───────────────────┤
│ [Todos][Err][Warn]│
│ [Detall][Simple]  │
│                   │
│ 🔍 Buscar...     │
│                   │
│ ▼ Márgenes 1 err │
│ ─────────────── │
│ ✓ Margen sup.    │
│ ✕ Margen der.    │
│   Esperado: 2.5  │
│   Encontrado:    │
│   2.5 aprox.     │
│                   │
└───────────────────┘
```

---

## 10. Wireframe — Modo oscuro

Los wireframes anteriores representan el modo claro. En modo oscuro:

| Elemento | Modo claro | Modo oscuro |
|----------|------------|-------------|
| Fondo | `#f4f6f8` (gris claro) | `#1a1a1a` (casi negro) |
| Tarjetas | `#ffffff` (blanco) | `#2c2c2c` (gris oscuro) |
| Texto principal | `#616161` (gris medio) | `#b0b0b0` (gris claro) |
| Texto título | `#212121` (negro) | `#e0e0e0` (blanco) |
| Bordes | `#cfd8dc` | `#2e2e2e` |
| Fondo header | Gradiente verde | Mismo gradiente verde |
| Botones primarios | Verde `#2e7d32` | Verde `#4caf50` (más brillante) |

---

## 11. Referencias a mockups

Los wireframes anteriores corresponden a los siguientes mockups HTML:

| Wireframe | Mockup HTML | Ruta |
|-----------|-------------|------|
| Pantalla de carga | `carga.html` | `mockups/carga.html` |
| Pantalla de reporte | `reporte.html` | `mockups/reporte.html` |

Los mockups HTML son la **fuente de verdad** del diseño visual. Este documento de wireframes complementa con la estructura y estados de interacción.

---

## 12. Prompts para generación automática de wireframes

### Prompt 1 — Wireframe de pantalla de carga (ASCII art)

```
Genera un wireframe en formato ASCII art para la pantalla de carga de una
aplicación web llamada "VistoBueno" (validación de formato de tesis UNT).

Requisitos:
- Header verde con logo circular "VB", título "VistoBueno", subtítulo "FECyC · Universidad Nacional de Trujillo"
- Botón de modo oscuro (🌙) y botón "← Validar otro" (oculto inicialmente)
- Tarjeta blanca redondeada con:
  - Título "Sube tu tesis"
  - Texto explicativo sobre formato DOCX/PDF
  - Dropzone con borde punteado verde:
    - Icono de documento 📄
    - Texto "Arrastra tu archivo aquí"
    - Texto "o selecciónalo desde tu computadora"
    - Botón verde "Seleccionar archivo"
    - Nota: "Formatos permitidos: .docx, .pdf · Máx: 25 MB"
  - Panel de info del archivo (después de selección):
    - Badge con extensión (DOCX)
    - Nombre del archivo
    - Tamaño en MB
    - Botón verde "Validar ✦"
  - Mensaje de error (rojo): "No pudimos procesar tu archivo"
- Footer: "Sistema VistoBueno — Practicante · Biblioteca FECyC · UNT"

Estilo: mobile-first, responsive, minimalista, colores verde (#2e7d32) y gris.
```

### Prompt 2 — Wireframe de pantalla de reporte (ASCII art)

```
Genera un wireframe en formato ASCII art para la pantalla de reporte de
una aplicación web llamada "VistoBueno" (validación de formato de tesis UNT).

Requisitos:
- Header verde con logo "VB", título, botón modo oscuro, botón "← Validar otro"
- Sección 1 - Semáforo y resumen:
  - Círculo grande verde (✓) o rojo (✕)
  - Título: "¡Puedes entregar!" o "Revisa antes de entregar"
  - Barra de progreso de cumplimiento (ej: 76%)
  - 3 KPIs: Reglas evaluadas, Errores, Advertencias
- Sección 2 - Controles:
  - Chips de filtro: Todos / Errores / Advertencias
  - Toggle: Vista detallada / Vista simple
  - Campo de búsqueda: "Buscar regla o mensaje..."
- Sección 3 - Resultados (vista detallada):
  - Categorías expandibles (Papel, Fuente, Márgenes, etc.)
  - Cada categoría muestra: nombre, contadores err/warn/ok
  - Cada regla: icono estado, mensaje, badge severidad
  - Reglas fallidas muestran: Esperado, Encontrado
- Sección 4 - Prompts IA:
  - Título "🤖 Cómo preguntar a una IA"
  - Tarjetas con prompt de texto
  - Botón "Copiar" que cambia a "¡Copiado!"
- Footer y botón "Validar otro archivo"

Estilo: card-based, responsive, mobile-first.
```

### Prompt 3 — Wireframe responsivo (carga móvil)

```
Genera un wireframe en formato ASCII art para la pantalla de carga de
VistoBueno en formato MÓVIL (320px ancho).

Debe mostrar:
- Header compacto con logo VB y título
- Tarjeta que ocupa todo el ancho
- Dropzone simplificado (sin texto largo)
- Botón "Seleccionar archivo" grande y accesible
- Nota de formatos centrada

Estilo: mobile-first, touch-friendly, botones grandes (mín 44px tap target).
```

### Prompt 4 — Wireframe responsivo (reporte móvil)

```
Genera un wireframe en formato ASCII art para la pantalla de reporte de
VistoBueno en formato MÓVIL (320px ancho).

Debe mostrar:
- Header compacto con botón volver
- Semáforo más pequeño pero visible
- KPIs en fila compacta
- Filtros en scroll horizontal
- Categorías en ancho completo
- Prompts IA en tarjetas apiladas
- Botón "Validar otro" al final

Estilo: mobile-first, scroll vertical, contenido apilado.
```

---

## 13. Evidencia de producto

| Evidencia | Descripción |
|-----------|-------------|
| Wireframes escritorio | Secciones 1-8 de este documento |
| Wireframes móviles | Sección 9 de este documento |
| Paleta de colores | Sección 10 de este documento |
| Referencia a mockups | Sección 11 de este documento |
| Prompts de generación | Sección 12 de este documento |
