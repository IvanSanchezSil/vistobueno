// Tests de componente del límite de error (ErrorBoundary).
// Runner: vitest con jsdom + @testing-library/react (`npm test`).
// Cubren los hallazgos A1 (anuncio y foco) y F2 (reinicio del límite y salida
// del bucle) de la revisión del PR #62.
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

  it('F2: al reintentar, el aviso se limpia y los hijos vuelven a renderizar', () => {
    const consola = silenciarConsola()
    // El hijo falla mientras el flag está activo; el test lo desactiva antes
    // de reintentar para simular que el problema ya no se reproduce.
    //
    // Lo que este test comprueba es que el límite se reinicia (el aviso
    // desaparece y el contenido vuelve a pintarse). NO comprueba un
    // remontaje atribuible a la key del fragmento: React ya remonta el
    // subárbol que falló al entrar en el estado de error, así que el número
    // de montajes es el mismo con y sin key (medido en la segunda revisión
    // del PR #62, hallazgo F2). El caso del fallo que se repite siempre es
    // el siguiente test.
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
    fireEvent.click(screen.getByRole('button', { name: /^Reintentar$/ }))

    expect(onReiniciar).toHaveBeenCalledTimes(1)
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(screen.getByText('Pantalla recuperada')).toBeInTheDocument()

    consola.mockRestore()
  })

  it('F2: si el fallo se repite, el aviso vuelve y queda la salida de recargar', () => {
    const consola = silenciarConsola()
    // Fallo determinista: el hijo siempre falla. Reintentar no lo arregla
    // (por eso el aviso vuelve), pero la aplicación ofrece la salida real
    // del bucle: recargar la página.
    const HijoConFallo = () => {
      throw new Error('fallo determinista')
    }
    const onRecargar = vi.fn()

    render(
      <ErrorBoundary onRecargar={onRecargar}>
        <HijoConFallo />
      </ErrorBoundary>
    )

    fireEvent.click(screen.getByRole('button', { name: /^Reintentar$/ }))
    expect(screen.getByRole('alert')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /Recargar la página/ }))
    expect(onRecargar).toHaveBeenCalledTimes(1)

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
