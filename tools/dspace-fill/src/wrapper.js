// Wrapper del rellenador: pegamento delgado entre el entorno (Tampermonkey
// o el shim de desarrollo) y los módulos puros. Sin lógica de dominio:
// la viven compuertas.js, mapeador.js, ejecutor.js y panel.js.
//
// Protocolo 2 (2026-11-16): el depósito NO se reporta solo. Rellenar,
// enviar y archivar son tres estados distintos:
//
//   1. Rellenar: la ficha del buzón se copia al formulario.
//   2. Enviar: el clic en "Depositar" queda registrado como hora (HORA
//      del papeleo). No prueba que el ítem exista.
//   3. Archivar: el operador CONFIRMA en la página del ítem. Solo esa
//      atestación explícita habilita el papeleo en VistoBueno.
//
// La confirmación usa la revisión vigente que publica la API (GET
// /tramite): un panel viejo no confirma una ficha corregida.

(function () {
	"use strict";

	const doc = document;
	const esShim = !!(window.__VISTOBUENO_SHIM__);
	// En Tampermonkey el buzón es la API local directa (GM_xmlhttpRequest
	// corre en el contexto de la extensión: sin CORS, sin mixed content).
	// Bajo el shim (ensayo general con mock-dspace) se usa el proxy del
	// mock: same-origin, la API real sigue sin CORS.
	const BASE = esShim ? "/api-proxy" : "http://localhost:8000";
	const CLAVE_ENVIO = "vb_envio";
	const PROTOCOLO = 2;

	// US-06: ticket de operación para evitar que un callback antiguo
	// reemplace el estado más nuevo cuando hay varias operaciones en vuelo.
	// Se usa VBTicket (módulo puro, src/ticket.js).

	// US-11: plazo de recuperación de conexión. Tras LIMITE_REINTENTOS
	// fallos consecutivos se deja de reintentar automáticamente y se le
	// dice al operador exactamente qué hacer (pulsar "Rellenar" de nuevo
	// cuando VistoBueno vuelva a estar disponible).
	const LIMITE_REINTENTOS = 5;
	let _intentosConexion = 0;
	let _enRecuperacion = false;

	function _reiniciarIntentos() {
		_intentosConexion = 0;
		_enRecuperacion = false;
	}

	function _registrarFalloConexion() {
		_intentosConexion++;
		if (_intentosConexion >= LIMITE_REINTENTOS && !_enRecuperacion) {
			_enRecuperacion = true;
			mostrarToast(
				"VistoBueno no responde tras " + LIMITE_REINTENTOS + " intentos. " +
				"Cuando la app esté disponible, vuelve a pulsar \"Rellenar\" para reintentar.",
				15000
			);
		}
	}

	function pedir(ruta, metodo, cuerpo, alResponder, alFallar) {
		const opciones = {
			method: metodo,
			url: BASE + ruta,
			onload: alResponder,
			onerror: function (error) {
				// US-11: registro el fallo y, si se agotan los intentos,
				// muestro un mensaje de recuperación explícito.
				_registrarFalloConexion();
				if (alFallar) {
					// Si ya estamos en recuperación, no volvemos a mostrar
					// el toast genérico: el de recuperación sigue visible.
					if (!_enRecuperacion) {
						alFallar(error);
					}
					return;
				}
				if (!_enRecuperacion) {
					mostrarToast("VistoBueno no responde en " + BASE + " — ¿está corriendo la app?");
				}
			},
		};
		if (cuerpo !== undefined) {
			opciones.data = JSON.stringify(cuerpo);
			opciones.headers = { "Content-Type": "application/json" };
		}
		GM_xmlhttpRequest(opciones);
	}

	function _analizar(respuesta) {
		try {
			return JSON.parse(respuesta.responseText);
		} catch (e) {
			return null;
		}
	}

	function obtenerFicha(alRecibir) {
		// US-06: cada solicitud obtiene su propio ticket. Un callback
		// antiguo no puede reemplazar el estado de una solicitud nueva.
		const ticket = VBTicket.nuevoTicket();
		pedir(
			"/ficha-pendiente",
			"GET",
			undefined,
			function (respuesta) {
				if (ticket !== VBTicket.ticketActual()) return;
				// US-11: solo resetear el contador si el ticket sigue vigente.
				_reiniciarIntentos();
				if (respuesta.status !== 200) {
					alRecibir(null, "sin_ficha", ticket); // vacía o fuera de la ventana
					return;
				}
				const sobre = _analizar(respuesta);
				if (!sobre || !sobre.ficha || !sobre.tramite_id) {
					// La API anterior a v1.13.0 devolvía la ficha pelada. Sin
					// `tramite_id` no se puede atar el depósito: fail-closed.
					alRecibir(null, "contrato_desactualizado", ticket);
					return;
				}
				alRecibir(sobre, ticket);
			},
			function () {
				if (ticket !== VBTicket.ticketActual()) return;
				alRecibir(null, "sin_conexion", ticket);
			}
		);
	}

	function obtenerTramite(alRecibir) {
		// El trámite retenido sigue disponible aunque la ventana de
		// autorelleno haya vencido: el panel se arma con la revisión
		// vigente, no con un dato guardado en el navegador.
		// US-06: ticket para evitar que una respuesta antigua reemplace el estado nuevo.
		const ticket = VBTicket.nuevoTicket();
		pedir(
			"/tramite",
			"GET",
			undefined,
			function (respuesta) {
				if (ticket !== VBTicket.ticketActual()) return;
				// US-11: solo resetear el contador si el ticket sigue vigente.
				_reiniciarIntentos();
				if (respuesta.status === 404) {
					alRecibir(null, "sin_tramite", ticket);
					return;
				}
				if (respuesta.status !== 200) {
					alRecibir(null, "error_" + respuesta.status, ticket);
					return;
				}
				const tramite = _analizar(respuesta);
				if (!tramite || !tramite.tramite_id) {
					alRecibir(null, "contrato_desactualizado", ticket);
					return;
				}
				alRecibir(tramite, ticket);
			},
			function () {
				if (ticket !== VBTicket.ticketActual()) return;
				alRecibir(null, "sin_conexion", ticket);
			}
		);
	}

	function _tituloEsperadoDeFicha(sobre) {
		return (VBMapeador.valorExtraido(sobre.ficha, "dc.title") || "").trim();
	}

	function _leerEnvio() {
		// El estado del protocolo 1 no se migra: el contrato de
		// confirmación cambió y un atestado viejo no identifica la
		// revisión que el operador revisó. Se descarta (US-14).
		const actual = GM_getValue(CLAVE_ENVIO, null);
		if (!actual || typeof actual !== "object") return null;
		if (actual.protocolo !== PROTOCOLO) {
			GM_setValue(CLAVE_ENVIO, null);
			return null;
		}
		return actual;
	}

	function _guardarEnvio(cambios) {
		const previo = _leerEnvio() || {};
		GM_setValue(
			CLAVE_ENVIO,
			Object.assign({}, previo, cambios, { protocolo: PROTOCOLO })
		);
	}

	function _limpiarEnvioSiPertenece(tramiteId) {
		const actual = _leerEnvio();
		if (actual && actual.tramite_id === tramiteId) {
			GM_setValue(CLAVE_ENVIO, null);
		}
	}

	// --- UI mínima: toast y botón flotante ---

	function mostrarToast(texto, ms) {
		let toast = doc.getElementById("vb-toast");
		if (!toast) {
			toast = doc.createElement("div");
			toast.id = "vb-toast";
			toast.style.cssText =
				"position:fixed;bottom:16px;right:16px;z-index:99999;background:#1a1a2e;" +
				"color:#eee;padding:10px 14px;border-radius:8px;font:13px sans-serif;" +
				"max-width:420px;box-shadow:0 2px 8px rgba(0,0,0,.4)";
			doc.body.appendChild(toast);
		}
		toast.textContent = texto;
		toast.style.display = "block";
		clearTimeout(toast.__vbTimer);
		toast.__vbTimer = setTimeout(function () {
			toast.style.display = "none";
		}, ms || 6000);
	}

	function mostrarBoton(tituloFicha) {
		if (doc.getElementById("vb-boton")) return;
		const boton = doc.createElement("button");
		boton.id = "vb-boton";
		boton.type = "button";
		// Sin ficha en el buzón: texto genérico (el click consulta de
		// nuevo; si la ficha llegó mientras tanto, rellena).
		boton.textContent = tituloFicha
			? "Rellenar con ficha de VistoBueno: «" + tituloFicha + "»"
			: "Rellenar con ficha de VistoBueno (consultar buzón)";
		boton.style.cssText =
			"position:fixed;top:16px;right:16px;z-index:99999;background:#28a745;color:#fff;" +
			"border:none;padding:10px 14px;border-radius:8px;font:13px sans-serif;cursor:pointer;" +
			"max-width:420px;text-overflow:ellipsis;overflow:hidden;white-space:nowrap";
		boton.addEventListener("click", function () {
			obtenerFicha(function (sobre, motivo, ticket) {
				if (sobre) {
					llenar(sobre, ticket);
					return;
				}
				if (motivo === "contrato_desactualizado") {
					mostrarToast(
						"La API de VistoBueno no devuelve tramite_id: actualiza la app y el userscript."
					);
					return;
				}
				// US-11: si estamos en recuperación, no sobrescribir el
				// toast de recuperación con uno genérico.
				if (!_enRecuperacion) {
					mostrarToast("Sin ficha pendiente: expiró o no se preparó en VistoBueno.");
				}
			});
		});
		doc.body.appendChild(boton);
	}

	// --- Flujo principal ---

	function _tituloDelFormulario() {
		const el = doc.querySelector(VBCompuertas.SELECTORES.titulo);
		return el ? (el.value || "").trim() : "";
	}

	const RELLENO = {
		GUARDADO: "relleno",
	};

	function _rellenoPrevio(envio, tramiteId, revision) {
		// El resultado del último relleno de ESTE trámite y ESTA revisión.
		// Una revisión nueva invalida el resultado anterior: la ficha
		// cambió y hay que rellenar de nuevo.
		if (!envio || envio.tramite_id !== tramiteId) return null;
		const relleno = envio[RELLENO.GUARDADO];
		if (!relleno || typeof relleno !== "object") return null;
		if (relleno.revision !== revision) return null;
		return relleno;
	}

	function llenar(sobre, ticket) {
		// US-06: si el ticket ya no es vigente, ignorar (callback antiguo).
		if (ticket !== undefined && ticket !== VBTicket.ticketActual()) return;
		const ficha = sobre.ficha;
		const tramiteId = sobre.tramite_id;
		const revision = typeof sobre.revision === "number" ? sobre.revision : 0;
		const tituloFicha = (VBMapeador.valorExtraido(ficha, "dc.title") || "").trim();
		const tituloActual = _tituloDelFormulario();
		const envio = _leerEnvio();
		const plan = VBMapeador.construirPlan(ficha, VBCompuertas.SELECTORES);

		// US-07: recordar el tramite del formulario actual para validar
		// clics en Depositar de otras pestañas.
		tramiteIdActual = tramiteId;

		// US-05: datos esenciales inválidos (un autor sin nombre, una
		// lista de DNI que no corresponde a los autores) NO inician el
		// plan: el relleno dejaría los datos desalineados. No se registra
		// ningun envio: el operador corrige la ficha y vuelve a preparar.
		if (!VBRelleno.puedeIntentar(plan)) {
			const problemas = (plan.problemas || [])
				.map(function (problema) {
					return problema.campo + ": " + problema.detalle;
				})
				.join(" ");
			mostrarToast(
				"La ficha tiene datos que no se pueden rellenar (" +
					problemas +
					"). Corrigela en VistoBueno y vuelve a preparar el deposito.",
				12000
			);
			return;
		}

		// Si el userscript YA lleno ESTE tramite y el formulario sigue
		// mostrando su titulo, NO se vuelve a llenar: el operador ya
		// corrigio lo que quiso y un segundo relleno pisaria sus
		// cambios (PR #71, M4).
		const previo = _rellenoPrevio(envio, tramiteId, revision);
		const esParcial = previo && previo.estado === VBRelleno.ESTADOS.PARCIAL;
		const esVerificado = previo && previo.estado === VBRelleno.ESTADOS.VERIFICADO;
		const mismoTramite =
			envio &&
			envio.tramite_id === tramiteId &&
			envio.titulo &&
			tituloFicha &&
			VBCompuertas.titulosCoinciden(envio.titulo, tituloFicha);
		if (mismoTramite) {
			// US-05: un relleno PARCIAL no bloquea. Solo un relleno
			// verificado (todos los campos con dato quedaron escritos) cierra
			// el formulario; un parcial se reintenta solo con los campos que
			// quedaron pendientes.
			if (esVerificado) {
				mostrarToast("El formulario ya tiene esta tesis: no se volvio a rellenar.");
				return;
			}
			if (!previo && tituloActual && VBCompuertas.titulosCoinciden(tituloActual, tituloFicha)) {
				mostrarToast("El formulario ya tiene esta tesis: no se volvio a rellenar.");
				return;
			}
		}

		// Reintento: solo los campos pendientes del ultimo intento, y
		// sin pisar lo que el operador escribio a mano.
		const planEfectivo = esParcial
			? VBRelleno.planARetry(plan, previo.pendientes)
			: plan;

		VBEjecutor.aplicarPlan(doc, planEfectivo).then(function (resumen) {
			const estado = VBRelleno.evaluar(resumen.detalle, resumen.omitidos);
			const partes = ["Rellenado de VistoBueno - revisa antes de continuar."];
			if (resumen.exitosos.length) partes.push("Lleno: " + resumen.exitosos.join(", ") + ".");
			if (resumen.fallidos.length) partes.push("A mano: " + resumen.fallidos.join(", ") + ".");
			if (resumen.omitidos.length) partes.push("Sin dato: " + resumen.omitidos.join(", ") + ".");
			(resumen.problemas || []).forEach(function (problema) {
				partes.push("Problema: " + problema.campo + ": " + problema.detalle + ".");
			});
			if (estado.estado === VBRelleno.ESTADOS.PARCIAL) {
				partes.push(
					"Relleno parcial: vuelve a pulsar Rellenar para completar solo lo que quedo a mano."
				);
			}
			mostrarToast(partes.join(" "), 12000);
			// El timestamp del clic en "Depositar" se conserva solo si es
			// el MISMO tramite: un tramite nuevo empieza sin hora (PR #71).
			const anterior = _leerEnvio();
			_guardarEnvio({
				tramite_id: tramiteId,
				revision: revision,
				titulo: VBMapeador.valorExtraido(ficha, "dc.title") || null,
				timestamp:
					anterior && anterior.tramite_id === tramiteId ? anterior.timestamp || null : null,
				[RELLENO.GUARDADO]: {
					estado: estado.estado,
					revision: revision,
					campos: estado.campos,
					pendientes: estado.pendientes,
				},
			});
		});
	}

	function alAbrirFormulario() {
		obtenerFicha(function (sobre, motivo, ticket) {
			if (sobre) {
				mostrarBoton(_tituloEsperadoDeFicha(sobre));
				llenar(sobre, ticket);
				return;
			}
			if (motivo === "contrato_desactualizado") {
				mostrarToast(
					"La API de VistoBueno no devuelve tramite_id: actualiza la app y el userscript."
				);
				return;
			}
			// Sin ficha: el botón aparece igual (texto genérico) para
			// que el operador pueda pulsarlo tras publicar la ficha
			// desde VistoBueno con la página ya cargada (hallazgo 12:
			// el auto-relleno solo ocurre si la ficha ya estaba; el
			// botón manual rescate el caso de publicar después).
			mostrarBoton(null);
		});
	}

	// --- Panel de confirmación del archivo (protocolo 2) ---

	function _candidatoItem() {
		const ruta = window.location && window.location.pathname ? window.location.pathname : "";
		if (!VBCompuertas.esPaginaItem(doc, ruta)) return null;
		const handle = VBCompuertas.extraerHandle(doc);
		const titulo = VBCompuertas.tituloDeItem(doc);
		if (!handle || !titulo) return null;
		return { handle: handle, titulo: titulo, autores: VBCompuertas.autoresDeItem(doc) };
	}

	function _avisosDePanel(candidato, tramite, envio) {
		// Devuelve {avisos, motivos, puedeConfirmar}: los avisos son
		// texto para el operador; los motivos alimentan el reporte de
		// inconsistencia.
		const avisos = [];
		const motivos = [];
		const ficha = tramite.ficha || {};
		const tituloCanonico = (VBMapeador.valorExtraido(ficha, "dc.title") || "").trim();
		const autoresCanonicos = VBMapeador.comoLista(
			VBMapeador.valorExtraido(ficha, "dc.contributor.author")
		);

		if (!tituloCanonico) {
			avisos.push(
				"La ficha no trae título: no se puede comprobar la identidad del ítem. Corrige la ficha en VistoBueno."
			);
			motivos.push("La ficha canónica no tiene título");
		} else if (!VBCompuertas.titulosCoinciden(tituloCanonico, candidato.titulo)) {
			avisos.push(
				"El título del ítem no coincide con la ficha: concilia la ficha en VistoBueno antes de confirmar."
			);
			motivos.push("El título del ítem no coincide con la ficha");
		}
		if (
			candidato.autores &&
			candidato.autores.length &&
			autoresCanonicos.length &&
			!VBCompuertas.autoresCoinciden(autoresCanonicos, candidato.autores)
		) {
			avisos.push(
				"Los autores del ítem no coinciden con la ficha: concilia la ficha en VistoBueno antes de confirmar."
			);
			motivos.push("Los autores del ítem no coinciden con la ficha");
		}
		if (!envio || envio.tramite_id !== tramite.tramite_id) {
			avisos.push(
				"No se registró el clic en Depositar de esta ficha: la hora del papeleo no se puede fijar."
			);
		} else if (envio.revision !== tramite.revision) {
			avisos.push(
				"La ficha cambió en VistoBueno (revisión " +
					tramite.revision +
					"): vuelve a preparar el depósito."
			);
		}
		const puedeConfirmar =
			!avisos.length &&
			!!envio &&
			envio.tramite_id === tramite.tramite_id &&
			envio.revision === tramite.revision &&
			!!envio.timestamp;
		return { avisos: avisos, motivos: motivos, puedeConfirmar: puedeConfirmar };
	}

	function _pintarPanel(candidato, tramite, envio) {
		const revision = envio && envio.tramite_id === tramite.tramite_id ? envio.revision : null;
		const evaluacion = _avisosDePanel(candidato, tramite, envio);
		VBPanel.montar(doc, {
			tituloItem: candidato.titulo,
			handle: candidato.handle,
			autoresItem: candidato.autores,
			timestamp: envio ? envio.timestamp : null,
			tramiteId: tramite.tramite_id,
			revision: revision === null ? tramite.revision : revision,
			avisos: evaluacion.avisos,
			puedeConfirmar: evaluacion.puedeConfirmar,
			alConfirmar: function () {
				_confirmar(candidato, tramite, envio);
			},
			alMarcarInconsistencia: evaluacion.motivos.length
				? function () {
						_reportarInconsistencia(candidato, tramite, evaluacion.motivos);
					}
				: null,
		});
	}

	function _confirmar(candidato, tramite, envio) {
		const cuerpo = {
			tramite_id: tramite.tramite_id,
			handle: candidato.handle,
			titulo_observado: candidato.titulo,
			timestamp: envio.timestamp,
			revision_esperada: envio.revision,
			atestacion: "operador",
		};
		// Los autores son evidencia opcional: si la página no los
		// publica, no se envían y el servidor registra que NO se
		// verificaron (nunca "coinciden").
		if (candidato.autores && candidato.autores.length) {
			cuerpo.autores_observados = candidato.autores;
		}
		pedir(
			"/deposito",
			"POST",
			cuerpo,
			function (respuesta) {
				if (respuesta.status === 204 || respuesta.status === 200) {
					_limpiarEnvioSiPertenece(tramite.tramite_id);
					VBPanel.quitar(doc);
					mostrarToast(
						"Depósito confirmado por el operador ✓ (" + candidato.handle + ")"
					);
					return;
				}
				if (respuesta.status === 409) {
					// La revisión, el título o los autores no coinciden:
					// no se reintenta. Se relee el trámite y se muestra
					// el estado nuevo.
					mostrarToast(
						"VistoBueno rechazó la confirmación (409): la ficha cambió o no coincide con el ítem."
					);
					_actualizarPanel(candidato);
					return;
				}
				if (respuesta.status === 422) {
					mostrarToast(
						"El contrato de VistoBueno cambió (422): actualiza la app y el userscript."
					);
					return;
				}
				if (respuesta.status === 404) {
					mostrarToast(
						"No hay un trámite vigente en VistoBueno (404): vuelve a preparar la ficha."
					);
					VBPanel.quitar(doc);
					return;
				}
				mostrarToast(
					"No se pudo confirmar el depósito (HTTP " + respuesta.status + ")."
				);
			},
			function () {
				mostrarToast("No se pudo contactar con VistoBueno para confirmar el depósito.");
			}
		);
	}

	function _reportarInconsistencia(candidato, tramite, motivos) {
		pedir(
			"/ficha-pendiente/inconsistencia",
			"POST",
			{
				tramite_id: tramite.tramite_id,
				handle: candidato.handle,
				motivos: motivos,
				revision_esperada: tramite.revision,
			},
			function (respuesta) {
				if (respuesta.status === 204 || respuesta.status === 200) {
					VBPanel.quitar(doc);
					mostrarToast(
						"Inconsistencia reportada: concilia la ficha en VistoBueno antes del papeleo."
					);
					return;
				}
				if (respuesta.status === 409) {
					mostrarToast(
						"La revisión del trámite cambió (409): vuelve a leer el trámite y revisa la diferencia."
					);
					_actualizarPanel(candidato);
					return;
				}
				if (respuesta.status === 422) {
					mostrarToast(
						"El contrato de VistoBueno cambió (422): actualiza la app y el userscript."
					);
					return;
				}
				mostrarToast(
					"No se pudo reportar la inconsistencia (HTTP " + respuesta.status + ")."
				);
			},
			function () {
				mostrarToast("No se pudo contactar con VistoBueno para reportar la inconsistencia.");
			}
		);
	}

	function _actualizarPanel(candidato) {
		obtenerTramite(function (tramite, motivo) {
			if (!tramite) {
				VBPanel.quitar(doc);
				mostrarToast(
					motivo === "sin_tramite"
						? "No hay un trámite vigente en VistoBueno: prepara la ficha otra vez."
						: "VistoBueno no responde: no se puede confirmar el depósito."
				);
				return;
			}
			_pintarPanel(candidato, tramite, _leerEnvio());
		});
	}

	function _abrirPanel(candidato) {
		obtenerTramite(function (tramite, motivo) {
			if (!tramite) {
				VBPanel.quitar(doc);
				mostrarToast(
					motivo === "sin_tramite"
						? "No hay un trámite vigente en VistoBueno: prepara la ficha otra vez."
						: "VistoBueno no responde: no se puede confirmar el depósito."
				);
				return;
			}
			_pintarPanel(candidato, tramite, _leerEnvio());
		});
	}

	// El SPA de DSpace navega sin recargar: un observador detecta tanto la
	// aparición del formulario como la página del ítem con el handle. El
	// estado se recalcula en cada pasada para que una SEGUNDA tesis (u otro
	// ítem abierto después) no quede bloqueada por la anterior.
	const visto = { formulario: false, panel: null };

	// US-07: el tramite_id del formulario actualmente visible. Se usa para
	// evitar que un clic en Depositar de otro borrador ponga hora al trámite
	// equivocado.
	let tramiteIdActual = null;

	function revisar() {
		// US-11: mientras estamos en recuperación, no reintentar
		// automáticamente. El operador debe pulsar "Rellenar" de nuevo.
		if (_enRecuperacion) return;

		const hayFormulario = VBCompuertas.esFormularioTesis(doc);
		if (hayFormulario && !visto.formulario) {
			alAbrirFormulario();
		}
		// US-07: al salir del formulario, invalidar el tramite actual para
		// que un clic en Depositar de otra pestaña no ponga hora al trámite
		// equivocado.
		if (!hayFormulario && visto.formulario) {
			tramiteIdActual = null;
			VBPanel.quitar(doc);
			visto.panel = null;
			const boton = doc.getElementById("vb-boton");
			if (boton) boton.remove();
		}
		visto.formulario = hayFormulario;

		const candidato = _candidatoItem();
		if (!candidato) {
			// MyDSpace, el workspace o cualquier otra ruta: no hay panel.
			if (visto.panel) {
				VBPanel.quitar(doc);
				visto.panel = null;
			}
			return;
		}
		// La firma incluye los autores: la página puede publicarlos más
		// tarde (metas de cita) y el panel debe reevaluarse cuando la
		// evidencia cambia.
		const firma =
			candidato.handle +
			"|" +
			candidato.titulo +
			"|" +
			(candidato.autores || []).join("; ");
		if (visto.panel === firma) return; // el panel de este ítem ya está
		visto.panel = firma;
		_abrirPanel(candidato);
	}

	let temporizador = null;
	function revisarConCalma() {
		clearTimeout(temporizador);
		temporizador = setTimeout(revisar, 300);
	}

	// Se observa el documento entero: `citation_title` vive en <head> y el
	// cuerpo del ítem se renderiza por separado; con solo <body> la
	// compuerta podía ver el handle antes que el meta y no reintentar.
	// También se observan los cambios del atributo `content`: una meta
	// creada vacía y completada después no dispara una mutación de
	// estructura (US-10).
	new MutationObserver(revisarConCalma).observe(doc.documentElement, {
		childList: true,
		subtree: true,
		attributes: true,
		attributeFilter: ["content"],
	});

	// Momento del envío: el clic en "Depositar" queda registrado como
	// timestamp (alimenta HORA del registro y de la constancia). NO prueba
	// que el ítem esté archivado: eso lo confirma el operador.
	doc.addEventListener(
		"click",
		function (evento) {
			if (!evento.target) return;
			const boton = evento.target.closest
				? evento.target.closest(VBCompuertas.SELECTORES.depositar)
				: null;
			if (boton) {
				const envio = _leerEnvio();
				// US-07: solo poner hora si el tramite del envío es el del
				// formulario actual. Evita que un clic en otra pestaña ponga
				// hora al trámite equivocado.
				if (envio && envio.tramite_id && envio.tramite_id === tramiteIdActual) {
					envio.timestamp = VBReloj.ahoraLima();
					GM_setValue(CLAVE_ENVIO, envio);
				}
			}
		},
		true
	);

	revisar();
})();
