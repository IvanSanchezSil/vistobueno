# Actividad 1 — Análisis de requisitos de interfaz

**Proyecto:** VistoBueno — Validación automática de formato de tesis
**Institución:** Universidad Nacional de Trujillo (UNT) — FECyC
**Autor:** Integrante 2 (Frontend / Experiencia de usuario)
**Fecha:** Semana 1

---

## 1. Contexto del sistema

**VistoBueno** es una aplicación web diseñada para la Biblioteca de la Facultad de Educación y Ciencias de la Comunicación (FECyC) de la Universidad Nacional de Trujillo. Su propósito es **validar automáticamente el formato de documentos de tesis** (DOCX) contra las directivas institucionales vigentes.

El sistema permite a los estudiantes obtener un reporte inmediato sobre el cumplimiento de las reglas de formato, evitando rechazos en la entrega de tesis por errores de presentación.

---

## 2. Usuarios objetivo

| Usuario | Descripción | Necesidad principal |
|---------|-------------|---------------------|
| Estudiante de pregrado | Entrega tesis como requisito de grado | Verificar que su documento cumple el formato antes de entregar |
| Estudiante de postgrado | Entrega tesis de maestría/doctorado | Validar formato extenso con múltiples secciones |
| Bibliotecario/a | Revisa documentos antes de aceptar | Herramienta auxiliar para verificar cumplimiento |

---

## 3. Objetivos de la interfaz

1. Permitir al estudiante **subir su documento de tesis** de forma rápida y sencilla
2. Mostrar el **resultado de validación** de manera clara y visual (semáforo)
3. Proporcionar un **reporte detallado** organizado por categorías de reglas
4. Ofrecer **prompts listos para copiar** que el estudiante pueda usar en una IA para corregir problemas
5. Funcionar en **dispositivos móviles, tablets y escritorios**

---

## 4. Requisitos funcionales

### 4.1 Carga de documentos

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-01 | El usuario debe poder seleccionar un archivo desde su computadora | Alta |
| RF-02 | El usuario debe poder arrastrar y soltar un archivo en la zona de carga | Alta |
| RF-03 | El sistema debe aceptar archivos en formato DOCX y PDF | Alta |
| RF-04 | El sistema debe rechazar archivos de otro formato con mensaje de error | Alta |
| RF-05 | El sistema debe rechazar archivos mayores a 25 MB con mensaje de error | Alta |
| RF-06 | El sistema debe mostrar el nombre, tamaño y extensión del archivo seleccionado | Media |
| RF-07 | El usuario debe poder cancelar la selección y elegir otro archivo | Media |

### 4.2 Validación

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-08 | El usuario debe poder iniciar la validación con un clic en "Validar" | Alta |
| RF-09 | El sistema debe mostrar un indicador de carga durante el proceso | Alta |
| RF-10 | El sistema debe enviar el archivo al endpoint POST /validar del backend | Alta |
| RF-11 | Si la API no está disponible, el sistema debe mostrar datos de ejemplo | Baja |

### 4.3 Reporte de resultados

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-12 | El sistema debe mostrar un semáforo verde (cumple) o rojo (no cumple) | Alta |
| RF-13 | El sistema debe mostrar el porcentaje de cumplimiento | Media |
| RF-14 | El sistema debe mostrar el total de reglas evaluadas, errores y advertencias | Alta |
| RF-15 | El usuario debe poder filtrar resultados por severidad (errores, advertencias) | Alta |
| RF-16 | El usuario debe poder buscar reglas por nombre o mensaje | Media |
| RF-17 | El usuario debe poder ver resultados agrupados por categoría | Alta |
| RF-18 | El usuario debe poder expandir/colapsar cada categoría | Alta |
| RF-19 | Cada regla debe mostrar el valor esperado y el valor encontrado | Alta |

### 4.4 Prompts IA

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-20 | El sistema debe generar un prompt por cada regla fallida | Alta |
| RF-21 | El usuario debe poder copiar el prompt al portapapeles con un clic | Alta |
| RF-22 | El sistema debe confirmar visualmente que el prompt fue copiado | Media |

### 4.5 Navegación

| ID | Requisito | Prioridad |
|----|-----------|-----------|
| RF-23 | El usuario debe poder volver a la pantalla de carga desde el reporte | Alta |
| RF-24 | La aplicación debe ser una sola página (SPA) con vista intercalada | Media |

---

## 5. Requisitos no funcionales

| ID | Requisito | Categoría |
|----|-----------|-----------|
| RNF-01 | La interfaz debe funcionar en dispositivos móviles (320px mínimo) | Usabilidad |
| RNF-02 | La interfaz debe adaptarse a tablets (600px+) y escritorios (900px+) | Usabilidad |
| RNF-03 | El sistema debe soportar modo oscuro | Usabilidad |
| RNF-04 | Los colores deben tener contraste suficiente (WCAG 2.1 AA) | Accesibilidad |
| RNF-05 | Los elementos interactivos deben ser navegables por teclado | Accesibilidad |
| RNF-06 | Los componentes deben tener atributos ARIA para lectores de pantalla | Accesibilidad |
| RNF-07 | La interfaz debe cargar en menos de 3 segundos en conexión normal | Rendimiento |
| RNF-08 | Los componentes React deben ser modulares y reutilizables | Mantenibilidad |

---

## 6. Restricciones técnicas

- **Frontend:** React 18 + Vite (sin TypeScript, solo JSX)
- **API:** Endpoint existente POST /validar (fastapi, por Integrante 1)
- **Formato de respuesta:** JSON con semáforo, resultados y prompts IA
- **Sin persistencia:** La app no almacena resultados (stateful en memoria)
- **Sin autenticación:** Acceso abierto sin login

---

## 7. Lista de funcionalidades principales

| # | Pantalla | Funcionalidad | Descripción |
|---|----------|---------------|-------------|
| 1 | Carga | Seleccionar archivo | Botón o drag-and-drop para elegir DOCX/PDF |
| 2 | Carga | Validar tipo y tamaño | Rechazo automático de formatos inválidos y archivos grandes |
| 3 | Carga | Iniciar validación | Botón "Validar" que envía el archivo al backend |
| 4 | Reporte | Ver semáforo | Indicador verde/rojo del resultado general |
| 5 | Reporte | Ver resumen | KPIs: total reglas, errores, advertencias |
| 6 | Reporte | Filtrar por severidad | Chips para alternar entre todos/errores/advertencias |
| 7 | Reporte | Buscar reglas | Campo de búsqueda por texto |
| 8 | Reporte | Ver por categoría | Secciones expandibles agrupadas |
| 9 | Reporte | Copiar prompts IA | Botón para copiar cada prompt al portapapeles |
| 10 | Navegación | Volver a cargar | Botón para regresar a la pantalla de carga |

---

## 8. Referencias

- **Mockup de carga:** `mockups/carga.html`
- **Mockup de reporte:** `mockups/reporte.html`
- **Contrato de API:** `docs/CONTRATO_API.md`
- **Guía del proyecto:** `AGENTS.md`

---

## 9. Evidencia de producto

| Evidencia | Descripción |
|-----------|-------------|
| Documento de requisitos | Este archivo (`01_requisitos_interfaz.md`) |
| Lista de funcionalidades | Sección 7 de este documento |
| Mockups de interfaces | `mockups/carga.html`, `mockups/reporte.html` |
