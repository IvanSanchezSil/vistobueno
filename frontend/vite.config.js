import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    open: true,
    // Proxy SOLO existe en `vite dev`. En `vite preview` o un build estático
    // no hay proxy: usar VITE_API_URL o un reverse proxy en despliegue.
    proxy: {
      '/validar': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Ficha de depósito (v1.7.0): las 4 rutas del flujo. Sin proxy la
      // SPA las enviaría a Vite (404), y la alternativa (VITE_API_URL
      // directo) está bloqueada por CORS — la API no agrega
      // CORSMiddleware por diseño (invariante del buzón).
      '/ficha-pendiente': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/deposito': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/constancia': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/fila-registro': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})