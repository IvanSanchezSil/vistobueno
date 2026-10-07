import { useState, useCallback, useEffect, useRef } from 'react'

// Estructura base: pantalla de carga con drag & drop.
// Replica el mockup mockups/carga.html pero con interactividad real:
//  - Valida tipo (DOCX) y tamaño (≤ 10 MB, igual que el backend).
//  - Llama al endpoint POST /validar del backend (Integrante 1).
//  - Errores HTTP con detalle JSON → se muestran al usuario (sin mock).
//  - Sin conexión / proxy sin backend → mock como modo demo (avisado en Report).
// Constantes y validación de archivo a nivel de módulo (sin dependencia de
// estado): así handleFiles puede ser useCallback([]) sin violar exhaustive-deps.
const MAX_BYTES = 10 * 1024 * 1024 // 10 MB, igual que el backend
const acceptedTypes = [
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]
// Validación de formato de correo en el cliente para evitar un 422 innecesario.
// Si llega a llegarse con formato inválido, el backend responde 422 con
// detail en español que el banner actual ya muestra (sin cambios).
const esCorreoValido = (c) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(c)

// Devuelve {titulo, texto} si el archivo no es válido; null si pasa.
const validarArchivo = (selected) => {
  if (!acceptedTypes.includes(selected.type) && !selected.name?.toLowerCase().endsWith('.docx')) {
    return { titulo: 'Archivo no compatible.', texto: 'El archivo no es .docx. Selecciona un documento de Word.' }
  }
  if (selected.size > MAX_BYTES) {
    return {
      titulo: 'Archivo demasiado grande.',
      texto: `El archivo pesa ${(selected.size / 1024 / 1024).toFixed(1)} MB. El límite es de 10 MB.`,
    }
  }
  return null
}

function Upload({ onValidated, apiUrl }) {
  const [file, setFile] = useState(null)
  const [correo, setCorreo] = useState('')
  const [correoError, setCorreoError] = useState(null)
  // Opt-in de notificación (v1.3.0): solo envía `notificar=true` si el operador
  // lo pide explícitamente. Así el estudiante no recibe correo por validaciones
  // intermedias (el backend exige además correo válido, semáforo rojo y SMTP activo).
  const [notificar, setNotificar] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragActivo, setDragActivo] = useState(false)
  const inputRef = useRef(null)
  const zonaRef = useRef(null)

  // Al volver del reporte ("Validar otro archivo") Upload se remonta de cero:
  // devuelve el foco a la dropzone (no lo pierde en <body>). En la carga inicial
  // de la app NO roba el foco.
  const primeraCarga = useRef(true)
  useEffect(() => {
    if (primeraCarga.current) {
      primeraCarga.current = false
      return
    }
    zonaRef.current?.focus()
  }, [])

  const onCorreoChange = (e) => {
    const v = e.target.value
    setCorreo(v)
    const invalido = v && !esCorreoValido(v)
    setCorreoError(invalido ? 'Formato de correo inválido (ej: correo@ejemplo.com).' : null)
    // Sin correo válido no hay notificación posible: se desmarca el opt-in
    // para que la petición no quede en un estado inconsistente.
    if (!v || invalido) setNotificar(false)
  }

  // Limpia el input para que re-elegir el MISMO archivo vuelva a disparar
  // onChange (el File ya guardado en el estado sigue siendo válido).
  const handleFiles = useCallback((files) => {
    if (files && files[0]) {
      const err = validarArchivo(files[0])
      if (err) {
        setError(err)
        setFile(null)
      } else {
        setError(null)
        setFile(files[0])
      }
    }
    if (inputRef.current) inputRef.current.value = ''
  }, [])

  const onDrop = useCallback((e) => {
    e.preventDefault()
    setDragActivo(false)
    handleFiles(e.dataTransfer.files)
  }, [handleFiles])

  const onDragOver = useCallback((e) => {
    e.preventDefault()
    if (!loading) setDragActivo(true)
  }, [loading])

  const onDragLeave = useCallback(() => {
    setDragActivo(false)
  }, [])

  const openPicker = useCallback(() => {
    if (!loading) inputRef.current?.click()
  }, [loading])

  const onDropzoneClick = useCallback((e) => {
    // Solo abrir el selector si el click no fue en el label/botón (evita doble apertura)
    if (e.target.closest('label') || e.target.closest('button')) return
    openPicker()
  }, [openPicker])

  const quitarArchivo = useCallback(() => {
    setFile(null)
    setError(null)
    if (inputRef.current) inputRef.current.value = ''
  }, [])

  // Cerrar el error devuelve el foco a la dropzone (no lo pierde en <body>).
  const cerrarError = useCallback(() => {
    setError(null)
    zonaRef.current?.focus()
  }, [])

  // Fallback a reporte mock SOLO cuando no hay respuesta útil del backend
  // (error de red o proxy sin cuerpo JSON). Modo demo, siempre avisado en Report.
  const cargarMock = async (motivo) => {
    const { MOCK_REPORT } = await import('../mocks')
    onValidated({
      ...MOCK_REPORT,
      __mock: true,
      __mockMotivo: `${motivo} Este es un reporte de ejemplo; el resultado real podría diferir.`,
    })
  }

  const validate = async () => {
    if (!file || loading) return
    setLoading(true)
    setError(null)
    try {
      let res
      try {
        const form = new FormData()
        form.append('archivo', file)
        // Correo del estudiante (opcional): viaja en la MISMA solicitud POST /validar.
        if (correo && esCorreoValido(correo)) form.append('correo', correo)
        // Opt-in de envío: "true"/"1" solo si el operador marcó la casilla
        // (el backend lo interpreta como default: false).
        if (notificar && correo && esCorreoValido(correo)) form.append('notificar', 'true')
        res = await fetch(`${apiUrl}/validar`, {
          method: 'POST',
          body: form,
        })
      } catch {
        // Error de red (backend caído, sin proxy, etc.) → mock como modo demo
        await cargarMock('No se pudo conectar con el servidor de validación.')
        return
      }

      if (res.ok) {
        try {
          const data = await res.json()
          onValidated(data)
        } catch {
          await cargarMock('El servidor devolvió una respuesta inválida.')
        }
        return
      }

      // HTTP != 2xx: si hay cuerpo JSON (detail/message), mostrar el error real y NO mock
      let detail = null
      try {
        const errBody = await res.json()
        detail = errBody?.detail ?? errBody?.message ?? null
        if (Array.isArray(detail)) {
          detail = detail
            .map((d) => (typeof d === 'string' ? d : d?.msg || JSON.stringify(d)))
            .join('; ')
        }
      } catch {
        detail = null
      }

      if (detail) {
        // Respuesta HTTP con detalle del backend (413/415/422/500, etc.)
        setError({
          titulo: `El servidor rechazó la validación (HTTP ${res.status}).`,
          texto: detail,
        })
        return
      }

      // HTTP sin JSON útil (p.ej. proxy 500 con body vacío cuando el backend está caído)
      // → fallback a mock como modo demo
      await cargarMock(`El servidor respondió HTTP ${res.status} sin detalle.`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main>
      <div className="card">
        <h2>Validar documento de tesis</h2>
        <p className="intro">
          Adjunte el documento en formato <strong>DOCX</strong> para
          obtener un reporte automático de cumplimiento con las directivas de formato de la UNT.
        </p>

        <div
          ref={zonaRef}
          className={`dropzone ${dragActivo ? 'drag' : ''} ${loading ? 'loading' : ''}`}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onClick={onDropzoneClick}
          role="button"
          tabIndex={loading ? -1 : 0}
          aria-label="Seleccionar archivo DOCX: arrastre un archivo o pulse Enter para abrir el selector"
          aria-describedby="nota-formatos"
          onKeyDown={(e) => {
            if (loading) return
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault()
              openPicker()
            }
          }}
        >
          <div className="icono" aria-hidden="true">📄</div>
          {/* role=status: anuncia a lectores de pantalla el cambio a "Validando…" */}
          <div className="txt-principal" role="status">
            {loading ? 'Validando documento…' : 'Arrastre el archivo aquí'}
          </div>
          <div className="txt-sec">o selecciónelo desde la computadora</div>

          <input
            type="file"
            id="file-input"
            ref={inputRef}
            accept=".docx"
            disabled={loading}
            onChange={(e) => handleFiles(e.target.files)}
          />
          <label htmlFor="file-input" className={`btn-select ${loading ? 'disabled' : ''}`}>
            {loading ? 'Validando…' : 'Seleccionar archivo'}
          </label>

          <div className="nota-formatos" id="nota-formatos">
            Formato permitido: .docx · Tamaño máximo: 10 MB
          </div>
        </div>

        <div className="campo-correo">
          <label htmlFor="correo-estudiante">
            Correo del estudiante <span className="opcional">(opcional)</span>
          </label>
          <input
            type="email"
            id="correo-estudiante"
            placeholder="estudiante@correo.unt.edu.pe"
            value={correo}
            onChange={onCorreoChange}
            disabled={loading}
            aria-invalid={correoError ? 'true' : 'false'}
            aria-describedby={correoError ? 'correo-error' : 'correo-ayuda'}
          />
          {correoError ? (
            <div id="correo-error" className="campo-error" role="alert">{correoError}</div>
          ) : (
            <div id="correo-ayuda" className="campo-ayuda">
              El correo se usará únicamente para enviar el reporte de validación al estudiante.
            </div>
          )}
          <label
            className={`check-notificar ${!correo || correoError ? 'disabled' : ''}`}
            title={
              !correo || correoError
                ? 'Escriba un correo válido para habilitar el envío de observaciones'
                : undefined
            }
          >
            <input
              type="checkbox"
              checked={notificar}
              onChange={(e) => setNotificar(e.target.checked)}
              disabled={loading || !correo || !!correoError}
              aria-describedby="notificar-ayuda"
            />
            <span>Enviar observaciones por correo al estudiante</span>
          </label>
          <div id="notificar-ayuda" className="campo-ayuda">
            El envío solo se intenta si el documento tiene errores bloqueantes
            (semáforo rojo) y las notificaciones están habilitadas en el servidor.
          </div>
        </div>

        {file && (
          <div className="archivo">
            <div className="fila">
              <div className="meta">
                <span className="ext">{file.name.split('.').pop().toUpperCase()}</span>
                <div>
                  <div className="nombre">{file.name}</div>
                  <div className="detalle">{(file.size / 1024 / 1024).toFixed(2)} MB</div>
                </div>
              </div>
              <div className="acciones-archivo">
                <button
                  className="btn-quitar"
                  onClick={quitarArchivo}
                  disabled={loading}
                  title="Quitar archivo"
                  aria-label="Quitar archivo seleccionado"
                >
                  ✕
                </button>
                <button
                  className="btn-validar"
                  onClick={validate}
                  disabled={loading || !!(correo && correoError)}
                  title={correo && correoError ? 'Corrija el correo del estudiante o déjelo vacío' : undefined}
                >
                  {loading ? (
                    <><span className="spinner" aria-hidden="true"></span> Validando…</>
                  ) : (
                    'Validar ✦'
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="aviso error" role="alert">
            <div className="aviso-fila">
              <strong>{error.titulo}</strong>
              <button className="aviso-cerrar" onClick={cerrarError} aria-label="Cerrar aviso">✕</button>
            </div>
            <span className="ejemplos">{error.texto}</span>
          </div>
        )}
      </div>
    </main>
  )
}

export default Upload
