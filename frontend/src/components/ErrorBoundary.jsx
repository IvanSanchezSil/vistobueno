import { Component, Fragment } from 'react'

// Límite de error de React (React Docs: "Error Boundaries"): si el render de
// una vista falla por un bug propio, la app no se queda en pantalla blanca:
// muestra un aviso claro con dos salidas («Reintentar» y «Recargar la
// página») y el detalle técnico plegado para el reporte del fallo. Solo
// captura errores de render de los hijos; los manejadores de eventos y los
// efectos asíncronos siguen su curso.
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
  // Si el fallo ocurre en el primer render, el aviso ya está montado cuando
  // corre componentDidMount; si ocurre después, lo detecta componentDidUpdate.
  componentDidMount() {
    if (this.state.error) this.enfocarTitulo()
  }

  componentDidUpdate(prevProps, prevState) {
    if (!prevState.error && this.state.error) this.enfocarTitulo()
  }

  enfocarTitulo = () => {
    this.tituloRef?.focus({ preventScroll: true })
  }

  // «Reintentar»: se limpia el límite y el App descarta el reporte actual,
  // así el usuario retoma el flujo desde un estado conocido.
  //
  // Alcance real (verificado en la segunda revisión del PR #62, hallazgo F2):
  // React ya remonta el subárbol que falló cuando el límite renderiza el
  // aviso, así que el contador `reinicios` NO cambia la cantidad de montajes
  // de los hijos: la key del fragmento es inocua y se conserva solo para
  // dejar explícito que el límite se reinicia desde cero. Si el fallo es
  // determinista (un bug que se repite siempre), el aviso vuelve a aparecer
  // tras reintentar; por eso la segunda salida («Recargar la página») es la
  // que rompe ese bucle de verdad.
  reintentar = () => {
    this.setState((estado) => ({ error: null, reinicios: estado.reinicios + 1 }))
    this.props.onReiniciar?.()
  }

  // «Recargar la página»: recarga la aplicación y descarta todo el estado
  // en memoria. Es la salida del bucle cuando el fallo se repite siempre.
  // Se puede inyectar con `onRecargar` (lo usan los tests).
  recargar = () => {
    const accion = this.props.onRecargar ?? (() => window.location.reload())
    accion()
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
              La pantalla dejó de responder por un fallo interno. Puede reintentar para
              volver a la pantalla de carga (el reporte actual se descarta) o recargar la
              aplicación si el problema persiste. Si se repite, comparta el detalle técnico
              con el administrador.
            </p>
            <details className="error-detalle">
              <summary>Ver el detalle técnico</summary>
              <pre>{String(this.state.error?.message || this.state.error)}</pre>
            </details>
            <div className="acciones-form">
              <button type="button" className="btn-validar" onClick={this.reintentar}>
                Reintentar
              </button>
              <button type="button" className="btn-secundario" onClick={this.recargar}>
                Recargar la página
              </button>
            </div>
          </div>
        </main>
      )
    }
    // La key cambia al reiniciar el límite; es inocua (React ya remonta el
    // subárbol que falló) y se conserva por legibilidad del reinicio.
    return <Fragment key={this.state.reinicios}>{this.props.children}</Fragment>
  }
}
