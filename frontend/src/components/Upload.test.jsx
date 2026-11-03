// Tests de componente del envío con Enter (Upload).
// Runner: vitest con jsdom + @testing-library/react (`npm test`).
// Cubren la observación N1 de la revisión del PR #62: la promesa de Enter
// tiene que ser precisa según el estado del formulario.
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import Upload from './Upload.jsx'

const ARCHIVO_DOCX = new File(
  ['contenido'],
  'tesis.docx',
  { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }
)

function seleccionarArchivo(container) {
  const input = container.querySelector('#file-input')
  fireEvent.change(input, { target: { files: [ARCHIVO_DOCX] } })
}

describe('Upload — envío con Enter', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        semaforo: 'verde',
        resultados: [],
        resumen: { total: 0, fallidos_error: 0, fallidos_warning: 0 },
        notificado: false,
        deposito: { estado: 'no_solicitado' },
      }),
    })
  })

  it('envía la validación al pulsar Enter con el formulario completo', async () => {
    const { container } = render(<Upload onValidated={() => {}} apiUrl="" />)
    seleccionarArchivo(container)

    const correo = screen.getByLabelText(/Correo del estudiante/i)
    fireEvent.change(correo, { target: { value: 'estudiante@correo.unt.edu.pe' } })

    // jsdom no implementa el envío implícito del navegador (Enter en un
    // <form>); se dispara el evento submit, que es lo que el navegador
    // genera en ese caso.
    fireEvent.submit(container.querySelector('form'))

    await waitFor(() => expect(globalThis.fetch).toHaveBeenCalledTimes(1))
    expect(globalThis.fetch.mock.calls[0][0]).toContain('/validar')
    expect(globalThis.fetch.mock.calls[0][1].method).toBe('POST')
  })

  it('sin archivo, Enter lleva el foco a la dropzone (botón deshabilitado)', () => {
    const { container } = render(<Upload onValidated={() => {}} apiUrl="" />)
    const correo = screen.getByLabelText(/Correo del estudiante/i)

    fireEvent.keyDown(correo, { key: 'Enter' })

    const dropzone = container.querySelector('.dropzone')
    expect(dropzone).toHaveFocus()
    expect(screen.getByRole('button', { name: /Validar documento/i })).toBeDisabled()
    expect(globalThis.fetch).not.toHaveBeenCalled()
  })

  it('con correo inválido, Enter lleva el foco al campo de correo', () => {
    const { container } = render(<Upload onValidated={() => {}} apiUrl="" />)
    seleccionarArchivo(container)

    const correo = screen.getByLabelText(/Correo del estudiante/i)
    fireEvent.change(correo, { target: { value: 'correo-invalido' } })
    fireEvent.keyDown(correo, { key: 'Enter' })

    expect(correo).toHaveFocus()
    expect(screen.getByRole('button', { name: /Validar documento/i })).toBeDisabled()
    expect(globalThis.fetch).not.toHaveBeenCalled()
  })

  it('el botón de validar es type="submit" y el de quitar archivo es type="button"', () => {
    const { container } = render(<Upload onValidated={() => {}} apiUrl="" />)
    seleccionarArchivo(container)

    expect(screen.getByRole('button', { name: /Validar documento/i })).toHaveAttribute('type', 'submit')
    expect(screen.getByRole('button', { name: /Quitar archivo/i })).toHaveAttribute('type', 'button')
  })

  // Regresión F1 (segunda revisión del PR #62): el manejador de Enter del
  // formulario interceptaba cualquier Enter, y con `preventDefault()` anulaba
  // la activación por defecto de los botones y de la casilla.
  //
  // jsdom no implementa la activación implícita de un control con Enter, así
  // que el helper emula lo que hace el navegador: si la aplicación cancela
  // el evento, el control NO se activa; si no lo cancela, se activa.
  const pulsarEnterComoElNavegador = (elemento) => {
    const evento = new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })
    elemento.dispatchEvent(evento)
    const cancelado = evento.defaultPrevented
    if (!cancelado && elemento.tagName === 'BUTTON') fireEvent.click(elemento)
    return cancelado
  }

  it('F1: Enter sobre «Quitar archivo» quita el archivo (no se intercepta)', () => {
    const { container } = render(<Upload onValidated={() => {}} apiUrl="" />)
    seleccionarArchivo(container)

    const correo = screen.getByLabelText(/Correo del estudiante/i)
    fireEvent.change(correo, { target: { value: 'correo-invalido' } })

    const quitar = screen.getByRole('button', { name: /Quitar archivo/i })
    const cancelado = pulsarEnterComoElNavegador(quitar)

    expect(cancelado).toBe(false)
    // El archivo se quitó: vuelve a la zona de carga en estado vacío.
    expect(screen.getByText('Arrastre aquí su documento .docx')).toBeInTheDocument()
  })

  it('F1: Enter sobre la casilla «Enviar observaciones» no se intercepta', () => {
    render(<Upload onValidated={() => {}} apiUrl="" />)
    const casilla = screen.getByRole('checkbox', { name: /Enviar observaciones por correo/i })

    const cancelado = pulsarEnterComoElNavegador(casilla)

    expect(cancelado).toBe(false)
  })

  it('F1: Enter sobre el campo de correo con el formulario incompleto sí se intercepta', () => {
    const { container } = render(<Upload onValidated={() => {}} apiUrl="" />)
    const correo = screen.getByLabelText(/Correo del estudiante/i)

    const cancelado = pulsarEnterComoElNavegador(correo)

    expect(cancelado).toBe(true)
    expect(container.querySelector('.dropzone')).toHaveFocus()
  })
})
