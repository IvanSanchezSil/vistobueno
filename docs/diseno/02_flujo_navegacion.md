# Actividad 2 — Diagrama de flujo de navegación

**Proyecto:** VistoBueno — Validación automática de formato de tesis
**Institución:** Universidad Nacional de Trujillo (UNT) — FECyC
**Autor:** Integrante 2 (Frontend / Experiencia de usuario)
**Fecha:** Semana 2

---

## 1. Flujo principal del usuario

```
                    ┌─────────────┐
                    │   INICIO    │
                    └──────┬──────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Pantalla de Carga  │
                │  (Upload Screen)    │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌─────────────────┐      ┌─────────────────┐
    │  Seleccionar    │      │  Arrastrar y    │
    │  archivo        │      │  soltar archivo │
    │  (clic botón)   │      │  (drag & drop)  │
    └────────┬────────┘      └────────┬────────┘
              │                        │
              └────────────┬───────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │  Validar tipo y     │
                │  tamaño del archivo │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
    ┌─────────────────┐      ┌─────────────────┐
    │  Archivo válido │      │ Archivo inválido│
    │  (DOCX/PDF,     │      │ (formato o      │
    │   ≤ 25 MB)      │      │  tamaño         │
    └────────┬────────┘      │  incorrecto)    │
              │               └────────┬────────┘
              │                        │
              │                        ▼
              │             ┌─────────────────────┐
              │             │  Mostrar mensaje    │
              │             │  de error           │
              │             │  (formato o tamaño) │
              │             └──────────┬──────────┘
              │                        │
              │                        │
              │                        ▼
              │             ┌─────────────────────┐
              │             │  Volver a           │
              │             │  seleccionar        │◄──────────┐
              │             └──────────┬──────────┘           │
              │                        │                      │
              │                        └──────────────────────┘
              ▼
    ┌─────────────────────┐
    │  Mostrar info del   │
    │  archivo: nombre,   │
    │  tamaño, extensión  │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │  Clic "Validar"     │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │  Estado: Cargando   │
    │  (botón deshabil.)  │
    └──────────┬──────────┘
               │
               ▼
    ┌─────────────────────┐
    │  POST /validar      │
    │  (envío del archivo)│
    └──────────┬──────────┘
               │
      ┌────────┴────────┐
      │                 │
      ▼                 ▼
┌───────────┐    ┌────────────┐
│  Éxito    │    │  Error API │
│  (200 OK) │    │  (no 200)  │
└─────┬─────┘    └─────┬──────┘
      │                │
      │                ▼
      │      ┌─────────────────┐
      │      │  Usar datos     │
      │      │  MOCK (ejemplo) │
      │      └────────┬────────┘
      │               │
      └───────┬───────┘
              │
              ▼
   ┌─────────────────────┐
   │  Pantalla Reporte   │
   │  (Report Screen)    │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Mostrar semáforo   │
   │  (verde o rojo)     │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Mostrar resumen    │
   │  (total, errores,   │
   │   advertencias)     │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Mostrar barra de   │
   │  cumplimiento (%)   │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Controles:         │
   │  - Filtros          │
   │  - Búsqueda         │
   │  - Vista detallada/ │
   │    simple           │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Lista de reglas    │
   │  (agrupadas por     │
   │   categoría)        │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Prompts IA         │
   │  (copiar al         │
   │   portapapeles)     │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Clic "Validar      │
   │  otro archivo"      │
   └──────────┬──────────┘
              │
              ▼
   ┌─────────────────────┐
   │  Volver a pantalla  │
   │  de carga           │
   └─────────────────────┘
```

---

## 2. Diagrama de navegación entre pantallas

```
┌─────────────────────────────────────────────────────────────┐
│                     APLICACIÓN VISTOBUENO                   │
│                                                             │
│  ┌─────────────────────┐         ┌─────────────────────┐   │
│  │                     │         │                     │   │
│  │   PANTALLA CARGA    │ ──────► │   PANTALLA REPORTE  │   │
│  │                     │         │                     │   │
│  │  - Dropzone         │  datos  │  - Semáforo         │   │
│  │  - Info archivo     │  de     │  - Resumen KPIs     │   │
│  │  - Botón "Validar"  │  API    │  - Filtros          │   │
│  │                     │         │  - Resultados       │   │
│  │                     │ ◄────── │  - Prompts IA       │   │
│  │                     │  clic   │  - "Validar otro"   │   │
│  └─────────────────────┘         └─────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. Estados de cada pantalla

### 3.1 Pantalla de Carga (Upload)

| Estado | Descripción | Elemento visible |
|--------|-------------|------------------|
| **Vacío** | Sin archivo seleccionado | Dropzone con instrucciones |
| **Archivo seleccionado** | Archivo válido elegido | Panel de info + botón Validar |
| **Cargando** | Enviando a la API | Botón deshabilitado "Validando..." |
| **Error de tipo** | Archivo no es DOCX/PDF | Mensaje de error rojo |
| **Error de tamaño** | Archivo > 25 MB | Mensaje de error rojo |
| **Error de API** | Backend no disponible | Datos mock cargados silenciosamente |

### 3.2 Pantalla de Reporte (Report)

| Estado | Descripción | Elemento visible |
|--------|-------------|------------------|
| **Semáforo rojo** | Hay errores bloqueantes | Círculo rojo + "Revisa antes de entregar" |
| **Semáforo verde** | Todo cumple | Círculo verde + "¡Puedes entregar!" |
| **Filtro activo** | Solo errores o solo warnings | Chips resaltados |
| **Búsqueda activa** | Texto en campo de búsqueda | Resultados filtrados |
| **Categoría expandida** | Sección abierta | Lista de reglas visible |
| **Categoría colapsada** | Sección cerrada | Solo encabezado con contadores |
| **Prompt copiado** | Copia exitosa al portapapeles | Botón cambia a "¡Copiado!" por 1.5s |

---

## 4. Flujo de manejo de errores

```
┌──────────────────────────────────────────────────────────────┐
│                    MANEJO DE ERRORES                         │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │ Error de formato│───►│ "Formato no soportado. Debes    │  │
│  │ (no DOCX/PDF)  │    │  subir un archivo DOCX o PDF."  │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │ Error de tamaño │───►│ "El archivo excede el límite    │  │
│  │ (> 25 MB)       │    │  de 25 MB."                     │  │
│  └─────────────────┘    └─────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │ Error de API    │───►│ console.warn + usar MOCK_REPORT │  │
│  │ (no disponible) │    │ (silencioso, usuario no ve error)│  │
│  └─────────────────┘    └─────────────────────────────────┘  │
│                                                              │
│  ┌─────────────────┐    ┌─────────────────────────────────┐  │
│  │ Error HTTP      │───►│ "Error del servidor: {status}"  │  │
│  │ (respuesta      │    │ (mensaje de error visible)      │  │
│  │  ≠ 200)         │    └─────────────────────────────────┘  │
│  └─────────────────┘                                         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 5. Transiciones de estado (máquina de estados)

### Pantalla de Carga

```
                  ┌──────────────┐
                  │    VACÍO     │◄────────────────────┐
                  └──────┬───────┘                      │
                         │ archivo seleccionado         │
                         ▼                              │
                  ┌──────────────┐                      │
                  │  SELECCIONADO│                      │
                  └──────┬───────┘                      │
                         │ clic "Validar"               │
                         ▼                              │
                  ┌──────────────┐                      │
                  │  CARGANDO    │                      │
                  └──────┬───────┘                      │
                         │                              │
              ┌──────────┴──────────┐                   │
              │                     │                   │
              ▼                     ▼                   │
       ┌────────────┐       ┌────────────┐              │
       │  ÉXITO     │       │  ERROR     │              │
       │  (→Report) │       │  (mostrar) │              │
       └────────────┘       └─────┬──────┘              │
                                  │                     │
                                  └─────────────────────┘
```

### Pantalla de Reporte

```
                  ┌──────────────┐
                  │  CARGANDO    │
                  │  DATOS       │
                  └──────┬───────┘
                         │ datos recibidos
                         ▼
                  ┌──────────────┐
                  │  VISUALIZANDO│◄───┐
                  └──────┬───────┘    │
                         │            │
         ┌───────────────┼────────────┤
         │               │            │
         ▼               ▼            │
  ┌────────────┐  ┌────────────┐      │
  │  FILTRANDO │  │  BUSCANDO  │      │
  └─────┬──────┘  └─────┬──────┘      │
        │               │             │
        └───────────────┴─────────────┘
                         │
                         ▼ "Validar otro"
                  ┌──────────────┐
                  │  VOLVIENDO   │
                  │  A CARGA     │
                  └──────────────┘
```

---

## 6. Referencias

- **Mockup de carga:** `mockups/carga.html`
- **Mockup de reporte:** `mockups/reporte.html`
- **Requisitos de interfaz:** `docs/diseno/01_requisitos_interfaz.md`

---

## 7. Evidencia de producto

| Evidencia | Descripción |
|-----------|-------------|
| Diagrama de flujo principal | Sección 1 de este documento |
| Diagrama de navegación | Sección 2 de este documento |
| Estados de pantallas | Sección 3 de este documento |
| Manejo de errores | Sección 4 de este documento |
| Máquinas de estados | Sección 5 de este documento |
