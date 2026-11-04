// Test de render del detalle completo de una regla que falla (AUD-03).
// El backend ahora enumera TODOS los incumplimientos (posición, valor y
// página) en `encontrado`; el frontend debe mostrarlos enteros, sin
// cortarlos: el bug reportado era que solo se veían las primeras 3 líneas.
// Runner: vitest (`npm test`).
import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'

import Report from './Report.jsx'

const incumplimientos = Array.from(
  { length: 8 },
  (_, i) => `#${i + 1}=0.00 cm (pág. 3)`
).join(', ')

const DETALLE =
  `@w:firstLine=['0.00 cm', '0.00 cm', '0.00 cm'] de 8 valores; 8 incumplen: ` +
  `${incumplimientos}; tolerancia ±0.02 cm; esperado=1.27 cm`

const REPORTE = {
  semaforo: 'rojo',
  resumen: {
    total: 1,
    total_evaluadas: 1,
    reglas_no_aplicables: 0,
    fallidos_error: 1,
    fallidos_warning: 0,
  },
  metadatos: { archivo_nombre: 'tesis.docx', archivo_tamano_bytes: 1024 },
  resultados: [
    {
      rule_id: 'sangria_parrafo',
      paso: false,
      severidad: 'warning',
      aplicable: true,
      mensaje: 'La primera línea de cada párrafo debe tener sangría de 1.27 cm',
      esperado: '1.27 cm (½ pulgada)',
      encontrado: DETALLE,
      ubicacion: 'Sección "Formato general" (párr. 141); página 3',
    },
  ],
  como_preguntar_a_una_ia: [],
}

describe('Report — detalle completo de una regla fallida', () => {
  it('muestra todos los incumplimientos, no solo los primeros', () => {
    const { container } = render(<Report data={REPORTE} />)
    const texto = container.textContent
    expect(texto).toContain('8 incumplen')
    for (let i = 1; i <= 8; i++) {
      expect(texto).toContain(`#${i}=0.00 cm`)
    }
    expect(texto).toContain('esperado=1.27 cm')
  })

  it('no corta el detalle por longitud (el último incumplimiento está)', () => {
    const { container } = render(<Report data={REPORTE} />)
    expect(container.textContent).toContain('#8=0.00 cm')
  })
})
