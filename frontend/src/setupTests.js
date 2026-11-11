import '@testing-library/jest-dom/vitest'
import { afterEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'

// Vitest corre con `globals: false`, así que la limpieza automática de
// Testing Library no se registra sola: se hace explícita para que cada test
// parta de un DOM vacío.
afterEach(() => cleanup())

// jsdom no implementa matchMedia: App lo usa para el tema inicial.
if (!window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
}

// jsdom tampoco implementa scrollIntoView: Report lo llama al montar para
// llevar el foco al semáforo.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn()
}
