// Tests de componente del límite de error (ErrorBoundary).
// Runner: vitest con jsdom + @testing-library/react (`npm test`).
// Cubren los hallazgos A1 (anuncio y foco) y A3 (recuperación sin bucle) de
// la revisión del PR #62.
import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ErrorBoundary from './ErrorBoundary'

// React registra el fallo capturado por el límite en console.error; se silencia
// para que la salida de los tests quede limpia.
function silenciarConsola() {
  return vi.spyOn(console, 'error').mockImplementation(() => {})
}

describe('ErrorBoundary', () => {
  it('muestra los hijos mientras no hay fallo', () => {
    render(
      <ErrorBoundary>
        <p>Contenido normal</p>
      </ErrorBoundary>
    )
    expect(screen.getByText('Contenido normal')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('A1: anuncia el fallo con role="alert" y lleva el foco al encabezado', () => {
    const consola = silenciarConsola()
    const HijoConFallo = () => {
      throw new Error('fallo de render simulado')
    }

    render(
      <ErrorBoundary>
        <HijoConFallo />
      </ErrorBoundary>
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: /Ocurrió un error inesperado/ })
    ).toHaveFocus()
    // El detalle técnico queda plegado, no desplegado a la fuerza.
    expect(screen.getByText('Ver el detalle técnico')).toBeInTheDocument()

    consola.mockRestore()
  })

  it('A3: al recuperar, los hijos se vuelven a montar (sin bucle de error)', () => {
    const consola = silenciarConsola()
    // El hijo falla mientras el flag está activo; el test lo desactiva para
    // simificar que el problema ya no se reproduce. Con el estado anterior
    // (sin key) el hijo se volvería a renderizar con el mismo error y el
    // usuario quedaría en un bucle sin salida.
    const estado = { fallar: true }
    const Hijo = () => {
      if (estado.fallar) throw new Error('fallo de render simulado')
      return <p>Pantalla recuperada</p>
    }
    const onReiniciar = vi.fn()

    render(
      <ErrorBoundary onReiniciar={onReiniciar}>
        <Hijo />
      </ErrorBoundary>
    )

    expect(screen.getByRole('alert')).toBeInTheDocument()

    estado.fallar = false
    fireEvent.click(screen.getByRole('button', { name: /Volver a la pantalla de carga/ }))

    expect(onReiniciar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('Pantalla recuperada')).toBeInTheDocument()

    consola.mockRestore()
  })

  it('deja el detalle técnico disponible para el reporte del fallo', () => {
    const consola = silenciarConsola()
    const HijoConFallo = () => {
      throw new Error('mensaje técnico del fallo')
    }

    render(
      <ErrorBoundary>
        <HijoConFallo />
      </ErrorBoundary>
    )

    expect(screen.getByText('mensaje técnico del fallo')).toBeInTheDocument()

    consola.mockRestore()
  })
})
