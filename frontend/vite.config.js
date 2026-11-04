import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Destino del proxy de desarrollo. Configurable para que el ensayo
// general pueda levantar la API en otro puerto sin tocar este archivo.
// El default no cambia: la API local en el 8000.
const API_URL = process.env.VISTOBUENO_API_URL || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  // Tests de componente: jsdom + @testing-library/react (ver N2 de la revisión
  // del PR #62). Los tests de funciones puras siguen funcionando igual.
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.js'],
  },
  server: {
    port: 5173,
    // El ensayo general corre en una máquina sin pantalla: con
    // VITE_DEV_OPEN=false el dev server no intenta abrir un navegador.
    open: process.env.VITE_DEV_OPEN !== 'false',
    // Proxy SOLO existe en `vite dev`. En `vite preview` o un build estático
    // no hay proxy: usar VITE_API_URL o un reverse proxy en despliegue.
    proxy: {
      '/validar': {
        target: API_URL,
        changeOrigin: true,
      },
      // Ficha de depósito (v1.7.0): las 4 rutas del flujo. Sin proxy la
      // SPA las enviaría a Vite (404), y la alternativa (VITE_API_URL
      // directo) está bloqueada por CORS — la API no agrega
      // CORSMiddleware por diseño (invariante del buzón).
      '/ficha-pendiente': {
        target: API_URL,
        changeOrigin: true,
      },
      '/deposito': {
        target: API_URL,
        changeOrigin: true,
      },
      '/constancia': {
        target: API_URL,
        changeOrigin: true,
      },
      '/fila-registro': {
        target: API_URL,
        changeOrigin: true,
      },
    },
  },
})