// Tests unitarios de filtrarAplicables() — contrato v1.5: las reglas no
// aplicables al tipo de documento (aplicable=false, paso=true) NO deben
// mostrarse como cumplidas en el reporte.
// Runner: vitest (`npm test`).
import { describe, it, expect } from 'vitest'
import { filtrarAplicables } from './Report.jsx'

const OK = { rule_id: 'margen_derecho', paso: false, severidad: 'warning', aplicable: true }
const NO_APLICA = {
  rule_id: 'estructura_tinv_cualitativo',
  paso: true, // no falló: no se evaluó
  severidad: 'error',
  aplicable: false,
}

describe('filtrarAplicables', () => {
  it('lista vacía o inválida → []', () => {
    expect(filtrarAplicables([])).toEqual([])
    expect(filtrarAplicables(null)).toEqual([])
    expect(filtrarAplicables(undefined)).toEqual([])
    expect(filtrarAplicables('texto')).toEqual([])
  })

  it('mantiene las reglas aplicables (aplicable=true)', () => {
    expect(filtrarAplicables([OK])).toEqual([OK])
  })

  it('tolera respuestas sin el campo (contrato v1.4 / mocks viejos)', () => {
    const sinCampo = { rule_id: 'papel_tamano', paso: true, severidad: 'error' }
    expect(filtrarAplicables([sinCampo, OK])).toEqual([sinCampo, OK])
  })

  it('excluye las no aplicables (aplicable=false) aunque traigan paso=true', () => {
    const salida = filtrarAplicables([OK, NO_APLICA, null])
    expect(salida).toEqual([OK])
    expect(salida).not.toContain(NO_APLICA)
  })
})
