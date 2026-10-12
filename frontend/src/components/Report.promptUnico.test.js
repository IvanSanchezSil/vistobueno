// Tests unitarios de construirPromptUnico() — une todos los prompts de la
// sección "Cómo preguntar a una IA" en UNO solo, listo para copiar y pegar.
// Runner: vitest (`npm test`).
import { describe, it, expect } from 'vitest'
import { construirPromptUnico } from './Report.jsx'

const P_MARGEN = {
  rule_id: 'margen_derecho',
  prompt:
    'Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:\n\n- Regla incumplida: El margen derecho debe ser 2.5 cm\n\n¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?',
}
const P_SANGRIA = {
  rule_id: 'sangria_parrafo',
  prompt:
    'Tengo un documento de tesis en Word (Universidad Nacional de Trujillo). Detecté un problema de formato:\n\n- Regla incumplida: La sangría de primera línea debe ser 1.27 cm\n\n¿Puedes darme instrucciones paso a paso para corregir esto en Microsoft Word, sin afectar el resto del formato del documento?',
}
const P_DESCONOCIDA = {
  rule_id: 'regla_inexistente_en_el_mapa',
  prompt: 'Prompt de una regla sin categoría mapeada.',
}

describe('construirPromptUnico', () => {
  it('lista vacía o inválida → prompt vacío', () => {
    expect(construirPromptUnico([])).toBe('')
    expect(construirPromptUnico(null)).toBe('')
    expect(construirPromptUnico(undefined)).toBe('')
    expect(construirPromptUnico('texto')).toBe('')
  })

  it('entradas sin texto de prompt se ignoran (y no cuentan en el total)', () => {
    const salida = construirPromptUnico([
      P_MARGEN,
      { rule_id: 'x' },
      { prompt: '   ' },
      null,
      undefined,
      P_SANGRIA,
    ])
    expect(salida).toContain('2 problemas de formato')
    expect(salida).toContain('Problema 2 de 2')
    expect(salida).not.toContain('Problema 3')
  })

  it('un solo prompt → marco singular ("un problema") y sin numeración redundante', () => {
    const salida = construirPromptUnico([P_MARGEN])
    expect(salida).toContain('un problema de formato')
    expect(salida).toContain('Corrige este problema en Microsoft Word')
    expect(salida).toContain('Problema 1 de 1 · Márgenes')
    expect(salida).toContain(P_MARGEN.prompt)
  })

  it('varios prompts → marco plural, numerados y con la categoría de cada uno', () => {
    const salida = construirPromptUnico([P_MARGEN, P_SANGRIA])
    expect(salida).toContain('2 problemas de formato')
    expect(salida).toContain('Corrige todos los siguientes problemas')
    expect(salida).toContain('Problema 1 de 2 · Márgenes')
    expect(salida).toContain('Problema 2 de 2 · Sangría')
    expect(salida.indexOf('Problema 1 de 2')).toBeLessThan(salida.indexOf('Problema 2 de 2'))
  })

  it('cada prompt individual queda íntegro y en su bloque (sin recortes)', () => {
    const salida = construirPromptUnico([P_MARGEN, P_SANGRIA])
    expect(salida).toContain(P_MARGEN.prompt)
    expect(salida).toContain(P_SANGRIA.prompt)
    // el bloque 2 no puede empezar antes de que termine el texto del prompt 1
    expect(salida.indexOf(P_SANGRIA.prompt)).toBeGreaterThan(salida.indexOf(P_MARGEN.prompt))
  })

  it('regla sin categoría mapeada → "Otros" (igual que las tarjetas individuales)', () => {
    const salida = construirPromptUnico([P_DESCONOCIDA])
    expect(salida).toContain('Problema 1 de 1 · Otros')
  })
})
