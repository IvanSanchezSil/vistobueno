import React from 'react'
import ReactDOM from 'react-dom/client'
import App, { temaOscuroInicial } from './App'
import './index.css'

// Aplicar el tema antes del primer render (evita destello claro en SO oscuro).
document.documentElement.classList.toggle('dark', temaOscuroInicial())

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
