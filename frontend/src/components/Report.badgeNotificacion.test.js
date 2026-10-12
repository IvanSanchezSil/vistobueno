// Tests unitarios de badgeNotificacion() — mapeo de notificacion.estado a
// badge visible (contrato v1.3.0 + deshabilitado con detalle, v1.4).
// Runner: vitest (`npm test`). Caso cubierto del comentario 4 de la revisión
// del PR #48.
import { describe, it, expect } from 'vitest'
import { badgeNotificacion } from './Report.jsx'

const DETALLE_CONFIG =
  'El servidor no tiene la notificación habilitada: configure VISTOBUENO_NOTIFICACIONES=1 y VISTOBUENO_SMTP_HOST.'

describe('badgeNotificacion', () => {
  it('payload ausente o inválido → sin badge', () => {
    expect(badgeNotificacion(null)).toBeNull()
    expect(badgeNotificacion(undefined)).toBeNull()
    expect(badgeNotificacion({})).toBeNull()
    expect(badgeNotificacion({ estado: 42 })).toBeNull()
  })

  it('enviado → badge ok avisando el envío', () => {
    const b = badgeNotificacion({ estado: 'enviado', detalle: null })
    expect(b.clase).toBe('ok')
    expect(b.texto).toContain('Enviamos las observaciones')
  })

  it('fallo → badge fail con el detalle técnico del backend', () => {
    const b = badgeNotificacion({ estado: 'fallo', detalle: 'SMTPAuthenticationError: 535' })
    expect(b.clase).toBe('fail')
    expect(b.detalle).toBe('SMTPAuthenticationError: 535')
  })

  it('fallo sin detalle → mensaje de reintento de respaldo', () => {
    const b = badgeNotificacion({ estado: 'fallo', detalle: null })
    expect(b.detalle).toContain('reintente o envíelo manualmente')
  })

  it('sin_correo → badge warn pidiendo el correo en el formulario', () => {
    const b = badgeNotificacion({ estado: 'sin_correo', detalle: null })
    expect(b.clase).toBe('warn')
    expect(b.texto).toContain('falta el correo del estudiante')
  })

  it('no_solicitado → badge info ofreciendo la casilla opt-in', () => {
    const b = badgeNotificacion({ estado: 'no_solicitado', detalle: null })
    expect(b.clase).toBe('info')
    expect(b.texto).toContain('No se solicitó el envío')
  })

  it('deshabilitado con detalle → badge info: enmarca la nota de config sin solaparla', () => {
    const b = badgeNotificacion({ estado: 'deshabilitado', detalle: DETALLE_CONFIG })
    expect(b.clase).toBe('info')
    expect(b.texto).toBe('Nota para administradores:')
    expect(b.detalle).toBe(DETALLE_CONFIG)
    // el texto principal no debe repetir lo que ya dice el detalle
    expect(b.texto).not.toContain('habilitado')
    expect(b.detalle).toContain('VISTOBUENO_NOTIFICACIONES=1')
  })

  it('deshabilitado sin detalle (backend anterior) → sin badge', () => {
    expect(badgeNotificacion({ estado: 'deshabilitado', detalle: null })).toBeNull()
    expect(badgeNotificacion({ estado: 'deshabilitado', detalle: '' })).toBeNull()
    expect(badgeNotificacion({ estado: 'deshabilitado', detalle: '   ' })).toBeNull()
  })

  it('sin_observaciones → sin badge', () => {
    expect(badgeNotificacion({ estado: 'sin_observaciones', detalle: null })).toBeNull()
  })

  it('detalle con espacios se recorta (trim)', () => {
    const b = badgeNotificacion({ estado: 'deshabilitado', detalle: `  ${DETALLE_CONFIG}  ` })
    expect(b.detalle).toBe(DETALLE_CONFIG)
  })
})
