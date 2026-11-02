import { Component, Fragment } from 'react'

// Límite de error de React (React Docs: "Error Boundaries"): si el render de
// una vista falla por un bug propio, la app no se queda en pantalla blanca:
// muestra un aviso claro con una salida real («Volver a la pantalla de carga»)
// y el detalle técnico plegado para el reporte del fallo. Solo captura
// errores de render de los hijos; los manejadores de eventos y los efectos
// asíncronos siguen su curso.
//
// Nota de alcance: el reporte ya se defiende de un payload malformado del
// servidor (`Report.jsx` valida `resultados`, `aplicable` y `metadatos`), así
// que el límite de error es la red contra bugs propios del render, no contra
// respuestas raras del backend.
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null, reinicios: 0 }
    this.tituloRef = null
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Solo consola: el MVP no tiene servicio de telemetría.
    console.error('ErrorBoundary capturó un fallo de render:', error, info?.componentStack)
  }

  // Al aparecer el aviso, el foco pasa al encabezado: sin esto, quien navega
  // con teclado o con lector de pantalla se queda en <body> sin enterarse del
  // fallo (mismo patrón que el semáforo del reporte).
  componentDidUpdate(prevProps, prevState) {
    if (!prevState.error && this.state.error && this.tituloRef) {
      this.tituloRef.focus({ preventScroll: true })
    }
  }

  // «Volver a la pantalla de carga»: se limpia el límite y el App descarta el
  // reporte actual, así el usuario retoma el flujo desde un estado conocido.
  // El contador `reinicios` cambia la key del fragmento: los hijos se vuelven
  // a montar desde cero. Sin esto, un fallo en la pantalla de carga (donde no
  // hay reporte que descartar) se repetiría en el mismo tick y el usuario
  // quedaría en un bucle sin salida.
  volverACarga = () => {
    this.setState((estado) => ({ error: null, reinicios: estado.reinicios + 1 }))
    this.props.onReiniciar?.()
  }

  render() {
    if (this.state.error) {
      return (
        <main>
          {/* role="alert": el lector de pantalla anuncia el fallo al aparecer
              (el resto de superficies de error de la app usa el mismo patrón). */}
          <div className="card" role="alert">
            <h2 ref={(nodo) => { this.tituloRef = nodo }} tabIndex={-1}>
              Ocurrió un error inesperado
            </h2>
            <p className="intro">
              La pantalla dejó de responder por un fallo interno. Vuelva a la pantalla de
              carga e intente nuevamente; si el problema persiste, comparta el detalle
              técnico con el administrador.
            </p>
            <details className="error-detalle">
              <summary>Ver el detalle técnico</summary>
              <pre>{String(this.state.error?.message || this.state.error)}</pre>
            </details>
            <div className="acciones-form">
              <button type="button" className="btn-validar" onClick={this.volverACarga}>
                Volver a la pantalla de carga
              </button>
            </div>
          </div>
        </main>
      )
    }
    // La key remonta los hijos al reiniciar (ver `volverACarga`).
    return <Fragment key={this.state.reinicios}>{this.props.children}</Fragment>
  }
}
