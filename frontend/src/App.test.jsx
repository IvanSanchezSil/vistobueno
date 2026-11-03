// Test de componente del toggle de tema (App).
// Runner: vitest con jsdom + @testing-library/react (`npm test`).
// Cubre el cambio del PR #62: iconos SVG inline en vez de emojis.
import { describe, it, expect, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import App from './App.jsx'

describe('App — toggle de tema', () => {
  beforeEach(() => {
    window.localStorage.clear()
    document.documentElement.classList.remove('dark')
  })

  it('muestra iconos SVG (no emojis) y conserva el nombre accesible', () => {
    render(<App />)
    const boton = screen.getByRole('button', { name: /Cambiar a modo oscuro/i })

    expect(boton.querySelector('svg')).toBeInTheDocument()
    expect(boton.textContent).not.toMatch(/[\u2600-\u27BF]/)
    expect(boton).toHaveAttribute('aria-pressed', 'false')
  })

  it('al alternar, cambia el icono, el nombre accesible y guarda la preferencia', () => {
    render(<App />)
    const boton = screen.getByRole('button', { name: /Cambiar a modo oscuro/i })

    fireEvent.click(boton)

    const botonOscuro = screen.getByRole('button', { name: /Cambiar a modo claro/i })
    expect(botonOscuro).toHaveAttribute('aria-pressed', 'true')
    expect(botonOscuro.querySelector('svg')).toBeInTheDocument()
    expect(document.documentElement.classList.contains('dark')).toBe(true)
    expect(window.localStorage.getItem('vb-tema')).toBe('oscuro')

    fireEvent.click(botonOscuro)
    expect(screen.getByRole('button', { name: /Cambiar a modo oscuro/i })).toHaveAttribute('aria-pressed', 'false')
    expect(window.localStorage.getItem('vb-tema')).toBe('claro')
  })
})
