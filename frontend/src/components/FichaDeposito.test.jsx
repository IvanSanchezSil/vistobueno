// Test de componente del flujo de la ficha de depósito (Actividad 15).
// Runner: vitest con jsdom + @testing-library/react (`npm test`).
//
// La pantalla `FichaDeposito.jsx` monta el trámite completo —editar los
// datos extraídos, completar los del operador, publicar en el buzón,
// esperar el reporte del userscript, aceptar el handle y descargar la
// constancia y la fila del registro— y no tenía ninguna prueba de
// componente: solo existían tests de las funciones puras de `ficha.js`.
//
// Estos tests fijan ese flujo con una API simulada que responde como la
// real (buzón de una ranura, 404 mientras no hay depósito, 204 al
// publicar, papeleo al final). Cada paso del checklist de la Actividad 15
// queda cubierto y reproducible en CI.
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

import FichaDeposito from './FichaDeposito.jsx'

const HANDLE = 'https://hdl.handle.net/123456/1'
const TIMESTAMP = '2026-11-04T10:30:00-05:00'

// Ficha que devuelve `POST /validar` con semáforo verde (valores ya
// corregidos por el motor; los manuales vienen vacíos).
const FICHA = {
  extraidos: [
    { campo: 'dc.title', valor: 'Estrategias ludicas para la motricidad' },
    { campo: 'dc.contributor.author', valor: ['Ana Maria Perez Garcia'] },
    { campo: 'dc.contributor.advisor', valor: 'Mag. Carlos Alberto Rodriguez Miranda' },
    { campo: 'dc.description.abstract', valor: 'Resumen de demostracion.' },
    { campo: 'dc.subject', valor: ['motricidad', 'juego'] },
    { campo: 'dc.date.issued', valor: '2026' },
    { campo: 'escuela', valor: 'ESCUELA PROFESIONAL DE EDUCACION INICIAL' },
  ],
  manuales: [
    { campo: 'matricula', valor: null },
    { campo: 'renati.author.dni', valor: null },
    { campo: 'renati.advisor.dni', valor: null },
    { campo: 'renati.advisor.orcid', valor: null },
  ],
}

const REPORTE_VERDE = {
  semaforo: 'verde',
  resumen: {
    total: 49,
    total_evaluadas: 43,
    reglas_no_aplicables: 6,
    fallidos_error: 0,
    fallidos_warning: 0,
  },
  metadatos: { archivo_nombre: 'tesis.docx', archivo_tamano_bytes: 1024 },
  resultados: [],
  ficha_deposito: FICHA,
}

// Instala una API simulada. `depósito` controla lo que responde el buzón:
// null = todavía no hay depósito (404), objeto = reporte del userscript.
function instalarApi({ deposito = null } = {}) {
  const llamadas = []
  const responder = async (res) => res
  globalThis.fetch = vi.fn(async (url, opciones = {}) => {
    llamadas.push({ url, opciones })
    const ruta = String(url)

    if (ruta.includes('/ficha-pendiente')) {
      return { ok: true, status: 204, json: async () => null, headers: new Headers() }
    }
    if (ruta.includes('/deposito')) {
      if (!deposito) {
        return { ok: false, status: 404, json: async () => null, headers: new Headers() }
      }
      return {
        ok: true,
        status: 200,
        json: async () => deposito,
        headers: new Headers(),
      }
    }
    if (ruta.includes('/constancia')) {
      return {
        ok: true,
        status: 200,
        blob: async () => new Blob(['constancia'], { type: 'application/msword' }),
        headers: new Headers({ 'Content-Disposition': 'attachment; filename="constancia.docx"' }),
      }
    }
    if (ruta.includes('/fila-registro')) {
      if (ruta.includes('formato=json')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({ filas: ['titulo\tautor\t20261234'] }),
          headers: new Headers(),
        }
      }
      return {
        ok: true,
        status: 200,
        blob: async () => new Blob(['fila'], { type: 'text/tab-separated-values' }),
        headers: new Headers(),
      }
    }
    return responder({ ok: true, status: 200, json: async () => ({}), headers: new Headers() })
  })
  return llamadas
}

// Los campos del operador alineados por autor (matrícula y DNI del autor)
// son un input por autor: la etiqueta del input es el nombre del autor y el
// id lleva el índice. Selocalizan por id, no por etiqueta.
const campoPorAutor = (container, campo, indice = 0) =>
  container.querySelector(`[id="${campo}-${indice}"]`)

// Rellena los datos del operador: un valor por autor (matrícula y DNI).
function completarDatosOperador(container) {
  fireEvent.change(campoPorAutor(container, 'matricula'), { target: { value: '20261234' } })
  fireEvent.change(campoPorAutor(container, 'renati.author.dni'), {
    target: { value: '87654321' },
  })
}

describe('FichaDeposito — flujo de la Actividad 15', () => {
  beforeEach(() => {
    window.localStorage.clear()
    // jsdom no implementa la descarga de archivos ni createObjectURL.
    globalThis.URL.createObjectURL = vi.fn(() => 'blob:mock')
    globalThis.URL.revokeObjectURL = vi.fn()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    window.localStorage.clear()
  })

  it('no muestra la ficha cuando el semáforo es rojo', () => {
    instalarApi()
    render(
      <FichaDeposito
        data={{ ...REPORTE_VERDE, semaforo: 'rojo', ficha_deposito: null }}
        apiUrl=""
        onBack={() => {}}
      />
    )
    expect(screen.getByText(/Ficha de depósito no disponible/i)).toBeTruthy()
    expect(screen.queryByRole('button', { name: /Preparar depósito/i })).toBeNull()
  })

  it('muestra los datos extraídos y los del operador', () => {
    instalarApi()
    render(<FichaDeposito data={REPORTE_VERDE} apiUrl="" onBack={() => {}} />)

    expect(screen.getByRole('heading', { name: /Ficha de depósito/i })).toBeTruthy()
    expect((screen.getByLabelText(/^Título$/i)).value).toBe(
      'Estrategias ludicas para la motricidad'
    )
    expect((screen.getByLabelText(/^Autores$/i)).value).toBe('Ana Maria Perez Garcia')
    expect(screen.getByText(/1 autor en la ficha/i)).toBeTruthy()
  })

  it('bloquea «Preparar depósito» mientras falten matrícula o DNI', async () => {
    instalarApi()
    render(<FichaDeposito data={REPORTE_VERDE} apiUrl="" onBack={() => {}} />)

    const boton = screen.getByRole('button', { name: /Preparar depósito/i })
    expect(boton).toBeDisabled()
    expect(screen.getByText(/Faltan datos para preparar el depósito/i)).toBeTruthy()
    expect(screen.getByText(/Faltan matrícula\(s\)/i)).toBeTruthy()
    expect(screen.getByText(/Faltan DNI\(s\) de autor/i)).toBeTruthy()
  })

  it('publica la ficha editada en el buzón y abre el panel de espera', async () => {
    const llamadas = instalarApi()
    const { container } = render(<FichaDeposito data={REPORTE_VERDE} apiUrl="" onBack={() => {}} />)

    // Editar un valor extraído (paso 3 del checklist).
    fireEvent.change(screen.getByLabelText(/^Título$/i), {
      target: { value: 'Estrategias ludicas revisadas' },
    })

    // Completar los datos del operador (paso 4): un valor por autor.
    completarDatosOperador(container)

    const boton = screen.getByRole('button', { name: /Preparar depósito/i })
    await waitFor(() => expect(boton).not.toBeDisabled())

    fireEvent.click(boton)

    await waitFor(() =>
      // El texto aparece dos veces: el botón cambia de etiqueta y el panel
      // de espera muestra el encabezado. Basta con que exista el panel.
      expect(screen.getAllByText(/Esperando el depósito/i).length).toBeGreaterThan(0)
    )
    expect(screen.getByText(/Ficha publicada en el buzón/i)).toBeTruthy()

    const publicacion = llamadas.find((c) => c.url.includes('/ficha-pendiente'))
    expect(publicacion).toBeTruthy()
    expect(publicacion.opciones.method).toBe('POST')
    const enviado = JSON.parse(publicacion.opciones.body)
    const titulo = enviado.extraidos.find((c) => c.campo === 'dc.title')
    expect(titulo.valor).toBe('Estrategias ludicas revisadas')
    const matriculaEnviada = enviado.manuales.find((c) => c.campo === 'matricula')
    expect(matriculaEnviada.valor).toEqual(['20261234'])
  })

  it('acepta el handle reportado y habilita el papeleo', async () => {
    instalarApi({
      deposito: { handle: HANDLE, titulo: 'Estrategias ludicas para la motricidad', timestamp: TIMESTAMP },
    })
    const { container } = render(<FichaDeposito data={REPORTE_VERDE} apiUrl="" onBack={() => {}} />)

    completarDatosOperador(container)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Preparar depósito/i })).not.toBeDisabled()
    )
    fireEvent.click(screen.getByRole('button', { name: /Preparar depósito/i }))

    // El panel de espera deja el posto al reporte del userscript.
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Aceptar depósito/i })).toBeTruthy()
    )
    expect(screen.getByText(HANDLE)).toBeTruthy()

    fireEvent.click(screen.getByRole('button', { name: /Aceptar depósito/i }))

    await waitFor(() => expect(screen.getByText(/Papeleo/i)).toBeTruthy())
    expect(screen.getByRole('button', { name: /Constancia de Ana Maria Perez Garcia/i })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Fila del registro \(\.tsv\)/i })).toBeTruthy()
  })

  it('avisa cuando el título recibido no coincide con la ficha', async () => {
    instalarApi({
      deposito: { handle: HANDLE, titulo: 'Un titulo completamente distinto', timestamp: TIMESTAMP },
    })
    const { container } = render(<FichaDeposito data={REPORTE_VERDE} apiUrl="" onBack={() => {}} />)

    completarDatosOperador(container)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Preparar depósito/i })).not.toBeDisabled()
    )
    fireEvent.click(screen.getByRole('button', { name: /Preparar depósito/i }))

    await waitFor(() =>
      expect(screen.getByText(/El título recibido no coincide con la ficha/i)).toBeTruthy()
    )
    // El handle no se usa a ciegas: sigue disponible el botón de rechazo.
    expect(screen.getByRole('button', { name: /Rechazar y volver/i })).toBeTruthy()
  })

  it('descarga la constancia del autor y la fila del registro', async () => {
    const llamadas = instalarApi({
      deposito: { handle: HANDLE, titulo: 'Estrategias ludicas para la motricidad', timestamp: TIMESTAMP },
    })
    const { container } = render(<FichaDeposito data={REPORTE_VERDE} apiUrl="" onBack={() => {}} />)

    completarDatosOperador(container)

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Preparar depósito/i })).not.toBeDisabled()
    )
    fireEvent.click(screen.getByRole('button', { name: /Preparar depósito/i }))
    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Aceptar depósito/i })).toBeTruthy()
    )
    fireEvent.click(screen.getByRole('button', { name: /Aceptar depósito/i }))

    await waitFor(() =>
      expect(screen.getByRole('button', { name: /Constancia de Ana Maria Perez Garcia/i })).toBeTruthy()
    )
    fireEvent.click(screen.getByRole('button', { name: /Constancia de Ana Maria Perez Garcia/i }))

    await waitFor(() =>
      expect(llamadas.some((c) => c.url.includes('/constancia'))).toBe(true)
    )
    const peticionConstancia = llamadas.find((c) => c.url.includes('/constancia'))
    const cuerpo = JSON.parse(peticionConstancia.opciones.body)
    expect(cuerpo.handle).toBe(HANDLE)
    expect(cuerpo.timestamp).toBe(TIMESTAMP)
    expect(cuerpo.indice_autor).toBe(0)

    // La fila en JSON se muestra en pantalla para copiar o pegar.
    fireEvent.click(screen.getByRole('button', { name: /Ver la fila \(texto\)/i }))
    await waitFor(() => expect(container.querySelector('.ficha-filas pre')).toBeTruthy())
    expect(container.querySelector('.ficha-filas pre').textContent).toContain('20261234')
  })

  it('resguarda la ficha editada y la borra al volver al reporte', async () => {
    const onBack = vi.fn()
    instalarApi()
    render(<FichaDeposito data={REPORTE_VERDE} apiUrl="" onBack={onBack} />)

    fireEvent.change(screen.getByLabelText(/^Título$/i), {
      target: { value: 'Titulo con datos del operador' },
    })

    await waitFor(() =>
      expect(window.localStorage.getItem('vb-ficha-deposito')).toContain('Titulo con datos')
    )

    fireEvent.click(screen.getAllByRole('button', { name: /Volver al reporte/i })[0])
    expect(onBack).toHaveBeenCalled()
    expect(window.localStorage.getItem('vb-ficha-deposito')).toBeNull()
  })
})
