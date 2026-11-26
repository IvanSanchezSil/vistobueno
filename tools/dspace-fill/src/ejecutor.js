// Ejecutor del rellenador: aplica un plan de relleno sobre el DOM del
// formulario oficial. Toma el document por parámetro (no globals) para
// que node + jsdom puedan probarlo contra el fixture del DOM real.
//
// Mecánica Angular: los reactive forms escuchan eventos, no asignaciones
// directas — se usa el setter nativo del prototipo del elemento y se
// despachan input/change (el patrón estándar de los autocompletadores).
//
// Las filas repetibles se concilian con los controles del propio widget:
// se agregan con el botón "+" y se QUITAN con el botón de quitar de la
// fila, nunca borrando nodos del DOM (la fila borrada a mano deja el
// modelo de Angular con un valor que ya no existe).

const VBEjecutor = (() => {
	// Cada fila repetible del formulario oficial (DSpace 8.1) vive en un
	// contenedor `#N_array` (evidencia: DOM real de "Editar envío"), y el
	// botón "+" de ESA fila es `button.ds-form-add-more`, dentro del mismo
	// contenedor. Los selectores adivinados de la versión anterior no
	// existían en la página: se llenaban las filas visibles y las demás
	// quedaban a mano sin avisar.
	const SELECTOR_ARRAY = '[id$="_array"]';
	const SELECTOR_AGREGAR = "button.ds-form-add-more";

	// Fila repetible del array: el bundle capturado la marca como
	// `role="group"` con el atributo `cdkdrag` (el contenedor del botón
	// "+" también es `role="group"`, pero no es ancestro del input).
	const SELECTOR_GRUPO = '[role="group"][cdkdrag]';

	// El botón de quitar fila no tiene clase propia: se distingue por su
	// etiqueta accesible (`form.remove` / `form.discard` traducidos) y por
	// no ser el botón "+" ni el botón de búsqueda de una relación.
	const ETIQUETA_ELIMINAR = /remove|eliminar|quitar|discard|descartar/;

	// Al pulsar "+", Angular re-renderiza el formulario de forma
	// asíncrona: la fila no existe en el mismo tick del clic. Se espera
	// a que el conteo crezca antes de seguir (revisión PR #71, M4).
	const INTENTOS_AGREGAR = 8;
	const ESPERA_AGREGAR_MS = 120;

	function _evento(doc, el, tipo) {
		const vista = el.ownerDocument.defaultView;
		el.dispatchEvent(new vista.Event(tipo, { bubbles: true }));
	}

	function _ponerTexto(doc, el, valor) {
		const prototipo = Object.getPrototypeOf(el);
		const descriptor = Object.getOwnPropertyDescriptor(prototipo, "value");
		if (descriptor && descriptor.set) {
			descriptor.set.call(el, valor);
		} else {
			el.value = valor; // respaldo: DOM sin setter nativo (fixture mínimo)
		}
		_evento(doc, el, "input");
		_evento(doc, el, "change");
		return true;
	}

	function _valorDe(el) {
		return el && typeof el.value === "string" ? el.value : "";
	}

	function _elegirOpcion(doc, select, sufijo) {
		// Los QUALDROP del formulario real usan valores "N: campo" (p. ej.
		// "0: renati.author.dni"): basta con el sufijo exacto. El
		// `includes()` anterior podía elegir una opción de otro campo cuyo
		// nombre contuviera el sufijo.
		const opcion = Array.from(select.options || []).find((o) =>
			(o.value || "").endsWith(sufijo)
		);
		if (!opcion) return false;
		select.value = opcion.value;
		_evento(doc, select, "change");
		return true;
	}

	function _aplicarTexto(doc, op) {
		const el = doc.querySelector(op.selector);
		if (!el) return { ok: false, detalle: "no se encontró el campo" };
		if (el.disabled || el.readOnly) {
			return { ok: false, detalle: "el control no admite edición" };
		}
		// US-05: corrección del operador → no se pisa.
		if (_conservarSiHayValor(doc, op, el, op.valor)) {
			return { ok: true, detalle: "se conservó el valor escrito por el operador" };
		}
		_ponerTexto(doc, el, op.valor);
		// Se relee el valor: un control que revierte lo escrito (listener
		// de Angular, render posterior) NO cuenta como relleno.
		if (_valorDe(el) !== op.valor) {
			return { ok: false, detalle: "el control no conservó el valor escrito" };
		}
		return { ok: true, detalle: "" };
	}

	function _aplicarAnhoDesdeTexto(doc, op) {
		// El valor puede venir como "2026", "2026-10-19" o similar: el
		// campo del formulario espera solo el año (maxlength=4).
		const anho = String(op.valor).match(/\d{4}/);
		if (!anho) return { ok: false, detalle: "no se encontró un año" };
		return _aplicarTexto(doc, { selector: op.selector, valor: anho[0] });
	}

	function _grupoDeFila(fila) {
		if (!fila || !fila.closest) return null;
		return fila.closest(SELECTOR_GRUPO) || fila.closest('[role="group"]');
	}

	function _botonEliminar(grupo) {
		// El control de quitar fila de DSpace 8.1 es un `<button>` con la
		// etiqueta traducida de `form.remove` (o `form.discard`). No se
		// borra el nodo: se pulsa el control para que Angular actualice el
		// FormArray.
		if (!grupo) return null;
		const botones = Array.from(grupo.querySelectorAll("button"));
		for (const boton of botones) {
			if (boton.classList && boton.classList.contains("ds-form-add-more")) continue;
			const marca = (boton.getAttribute("data-test") || "").toLowerCase();
			if (marca.indexOf("lookup") !== -1) continue;
			const etiqueta = (
				(boton.getAttribute("aria-label") || "") +
				" " +
				(boton.getAttribute("title") || "")
			).toLowerCase();
			if (ETIQUETA_ELIMINAR.test(etiqueta)) return boton;
		}
		return null;
	}

	async function _agregarFila(doc, selectorCercano, dormir) {
		// El botón se busca SOLO dentro del contenedor del campo: pulsar
		// un "+" global agregaría la fila de otro campo y desalinearía los
		// índices. Si el campo no existe o no hay botón, no se insiste: el
		// resumen reporta el faltante y el operador agrega a mano.
		const campo = doc.querySelector(selectorCercano);
		const contenedor = campo ? campo.closest(SELECTOR_ARRAY) : null;
		const boton = contenedor ? contenedor.querySelector(SELECTOR_AGREGAR) : null;
		if (!boton) return false;
		const antes = doc.querySelectorAll(selectorCercano).length;
		boton.click();
		// El render de Angular es asíncrono: se espera a que la fila
		// exista. Antes se contaba en el mismo tick y la fila nunca
		// alcanzaba a crearse (revisión PR #71, M4).
		for (let i = 0; i < INTENTOS_AGREGAR; i++) {
			if (doc.querySelectorAll(selectorCercano).length > antes) return true;
			await dormir(ESPERA_AGREGAR_MS);
		}
		return doc.querySelectorAll(selectorCercano).length > antes;
	}

	async function _eliminarFila(doc, selectorCercano, dormir) {
		// Quita la ÚLTIMA fila sobrante con el control de la propia fila.
		// Si el control no existe (fila única, campo de solo lectura o
		// versión de UI distinta), no se borra el nodo: la operación
		// falla y el operador la resuelve a mano.
		const filas = Array.from(doc.querySelectorAll(selectorCercano));
		if (filas.length <= 1) return false;
		const fila = filas[filas.length - 1];
		const boton = _botonEliminar(_grupoDeFila(fila));
		if (!boton) return false;
		const antes = doc.querySelectorAll(selectorCercano).length;
		boton.click();
		for (let i = 0; i < INTENTOS_AGREGAR; i++) {
			if (doc.querySelectorAll(selectorCercano).length < antes) return true;
			await dormir(ESPERA_AGREGAR_MS);
		}
		return doc.querySelectorAll(selectorCercano).length < antes;
	}

	async function _aplicarFilas(doc, op, dormir) {
		const existentes = Array.from(doc.querySelectorAll(op.selector));
		if (!existentes.length) return { ok: false, detalle: "no se encontró el campo" };
		const valores = op.valores || [];
		const necesarios = valores.length;
		// Si el botón "+" no agrega la fila, NO se aborta: las filas que
		// sí existen se llenan y las que faltan se reportan. Perder el
		// dato ya escrito sería peor que dejar un pendiente visible.
		for (let i = existentes.length; i < necesarios; i++) {
			const agregada = await _agregarFila(doc, op.selector, dormir);
			if (!agregada) break;
		}
		// Filas sobrantes: se quitan con el control del widget.
		while (doc.querySelectorAll(op.selector).length > necesarios) {
			const eliminada = await _eliminarFila(doc, op.selector, dormir);
			if (!eliminada) {
				return {
					ok: false,
					detalle: "no se pudo quitar una fila sobrante con el control del formulario",
				};
			}
		}
		const filas = Array.from(doc.querySelectorAll(op.selector));
		let aplicadas = 0;
		const sinDato = [];
		const sinFila = [];
		for (let i = 0; i < necesarios; i++) {
			const valor = valores[i];
			if (valor === null || valor === undefined || valor === "") {
				// Hueco real del dato: no se inventa un valor ni se
				// desplaza el de otra persona.
				sinDato.push(i + 1);
				continue;
			}
			if (!filas[i]) {
				// La fila no existe en el formulario (no se pudo
				// agregar): el dato queda pendiente, sin invadir otra
				// fila.
				sinFila.push(i + 1);
				continue;
			}
			// US-05: corrección del operador → no se pisa.
			if (_conservarSiHayValor(doc, op, filas[i], valor)) {
				aplicadas++;
				continue;
			}
			_ponerTexto(doc, filas[i], valor);
			if (_valorDe(filas[i]) === valor) aplicadas++;
		}
		if (aplicadas !== necesarios - sinDato.length - sinFila.length) {
			return { ok: false, detalle: "una fila no conservó el valor escrito" };
		}
		if (sinFila.length) {
			return {
				ok: false,
				detalle: "no se pudo agregar la fila " + sinFila.join(", "),
			};
		}
		return {
			ok: true,
			detalle: sinDato.length ? "filas sin dato: " + sinDato.join(", ") : "",
		};
	}

	async function _aplicarQualdrop(doc, op, dormir) {
		const metas = Array.from(doc.querySelectorAll(op.selectorMeta));
		const valores = op.valores || [];
		const necesarios = valores.length;
		if (!metas.length) return { ok: false, detalle: "no se encontró el campo" };
		for (let i = metas.length; i < necesarios; i++) {
			const agregada = await _agregarFila(doc, op.selectorMeta, dormir);
			if (!agregada) break;
		}
		while (doc.querySelectorAll(op.selectorMeta).length > necesarios) {
			const eliminada = await _eliminarFila(doc, op.selectorMeta, dormir);
			if (!eliminada) {
				return {
					ok: false,
					detalle: "no se pudo quitar una fila sobrante con el control del formulario",
				};
			}
		}
		const metasFinal = Array.from(doc.querySelectorAll(op.selectorMeta));
		const valoresFinal = Array.from(doc.querySelectorAll(op.selectorValor));
		let aplicadas = 0;
		const sinDato = [];
		const sinTipo = [];
		const sinFila = [];
		for (let i = 0; i < necesarios; i++) {
			const valor = valores[i];
			if (valor === null || valor === undefined || valor === "") {
				sinDato.push(i + 1);
				continue;
			}
			if (!metasFinal[i] || !valoresFinal[i]) {
				// No hay fila para este dato: no se escribe en otra.
				sinFila.push(i + 1);
				continue;
			}
			// US-05: corrección del operador → no se pisa ni el tipo.
			if (_conservarSiHayValor(doc, op, valoresFinal[i], valor)) {
				aplicadas++;
				continue;
			}
			// El tipo se elige ANTES de escribir el número: si la opción
			// no existe, el valor anterior (por ejemplo, un pasaporte)
			// queda intacto y la operación se reporta como fallida.
			if (!_elegirOpcion(doc, metasFinal[i], op.opcionSufijo)) {
				sinTipo.push(i + 1);
				continue;
			}
			_ponerTexto(doc, valoresFinal[i], valor);
			if (_valorDe(valoresFinal[i]) === valor) aplicadas++;
		}
		if (sinTipo.length) {
			return {
				ok: false,
				detalle: "el tipo de documento no existe para la fila " + sinTipo.join(", "),
			};
		}
		if (sinFila.length) {
			return {
				ok: false,
				detalle: "no se pudo agregar la fila " + sinFila.join(", "),
			};
		}
		if (aplicadas !== necesarios - sinDato.length) {
			return { ok: false, detalle: "una fila no conservó el valor escrito" };
		}
		return {
			ok: true,
			detalle: sinDato.length ? "filas sin dato: " + sinDato.join(", ") : "",
		};
	}

	async function _aplicarCombobox(doc, op, dormir) {
		// El combobox de Angular (ng-bootstrap) filtra opciones al
		// tipear y las renderiza en el listbox. Se escribe el texto
		// canónico y se reintenta la opción unas pocas veces (Angular
		// renderiza async); si nunca aparece → false (el resumen avisa
		// y el operador selecciona a mano, como hace hoy).
		const input = doc.querySelector(op.selectorInput);
		if (!input) return { ok: false, detalle: "no se encontró el campo" };
		// US-02: validar estado efectivo del control antes de escribir
		if (input.disabled || input.readOnly) {
			return { ok: false, detalle: "el control no admite edición" };
		}
		const previo = _valorDe(input);
		_ponerTexto(doc, input, op.texto);
		const intentos = 8;
		for (let i = 0; i < intentos; i++) {
			await dormir(120);
			const listbox = doc.querySelector(op.selectorListbox);
			if (!listbox) continue;
			const opciones = listbox.querySelectorAll(
				'option, [role="option"], .dropdown-item, button, a'
			);
			for (const el of opciones) {
				const texto = (el.textContent || "").replace(/\s+/g, " ").trim();
				if (texto === op.texto) {
					el.click();
					_evento(doc, input, "change");
					// Algunos widgets de Angular responden mejor al
					// teclado que al clic sintético: se intenta Enter
					// sobre el input como respaldo.
					const vista = input.ownerDocument.defaultView;
					input.dispatchEvent(
						new vista.KeyboardEvent("keydown", { key: "Enter", bubbles: true })
					);
					// US-02 / US-01: releer el valor - un control que
					// revierte lo escrito (listener de Angular, render
					// posterior) NO cuenta como relleno.
					const actual = _valorDe(input);
					const seleccionada =
						el.getAttribute("aria-selected") === "true" ||
						(el.classList && (el.classList.contains("active") || el.classList.contains("selected")));
					if (actual === op.texto || seleccionada) {
						return { ok: true, detalle: "" };
					}
					// El widget no aceptó la selección: se restaura el
					// valor anterior y se reporta pendiente. NO se
					// reescribe el texto, porque eso enmascararía el
					// fallo (parecería relleno sin haber seleccionado).
					_ponerTexto(doc, input, previo);
					return {
						ok: false,
						detalle:
							"el widget no aceptó la opción " +
							op.texto +
							" (no quedó seleccionada)",
					};
				}
			}
		}
		// Sin opciones renderizadas: se devuelve el control al valor
		// anterior. Borrarlo dejaría el formulario sin el dato que el
		// operador había escrito (US-03).
		_ponerTexto(doc, input, previo);
		return { ok: false, detalle: "no se encontró la opción " + op.texto + " (agotados " + intentos + " intentos)" };
	}

	function _selectoresDe(op) {
		// Selectores que la operación necesita en el DOM.
		const salida = [];
		if (op.selector) salida.push(op.selector);
		if (op.selectorMeta) salida.push(op.selectorMeta);
		if (op.selectorValor) salida.push(op.selectorValor);
		if (op.selectorInput) salida.push(op.selectorInput);
		return salida;
	}

	async function _esperarControles(doc, plan, dormir, intentos) {
		// US-05: esperar a que los controles del plan existan. Un campo
		// que renderiza tarde no debe quedar "a mano" para siempre. Si
		// después del margen no aparece, el plan sigue: la operación
		// correspondiente se reportará pendiente (fallo visible).
		const pendientes = new Set();
		(plan.operaciones || []).forEach(function (op) {
			_selectoresDe(op).forEach(function (sel) {
				if (!doc.querySelector(sel)) pendientes.add(sel);
			});
		});
		for (let i = 0; i < intentos && pendientes.size; i++) {
			await dormir(120);
			pendientes.forEach(function (sel) {
				if (doc.querySelector(sel)) pendientes.delete(sel);
			});
		}
	}

	function _conservarSiHayValor(doc, op, el, esperado) {
		// US-05: en un reintento, un campo que ya tiene un valor
		// distinto del esperado es una corrección del operador: no se
		// pisa. El campo cuenta como completo porque ya tiene contenido.
		if (!op.preservarSiLleno || !el) return false;
		const actual = _valorDe(el).trim();
		return !!actual && actual !== esperado;
	}

	async function aplicarPlan(doc, plan, opciones) {
		const config = opciones || {};
		const dormir = config.dormir || ((ms) => new Promise((r) => setTimeout(r, ms)));
		const exitosos = [];
		const fallidos = [];
		const detalle = [];
		// US-05: esperar los controles del plan antes de empezar. Un
		// campo que renderiza tarde (asesor, resumen) no debe quedar
		// "a mano" para siempre: se le da un margen y, si no aparece, la
		// operación se reporta pendiente (fallo visible, no silencio).
		await _esperarControles(doc, plan, dormir, config.intentosEspera || 8);
		for (const op of plan.operaciones) {
			const etiqueta = op.campo || op.tipo;
			let resultado = { ok: false, detalle: "operación desconocida" };
			if (op.tipo === "texto") resultado = _aplicarTexto(doc, op);
			else if (op.tipo === "anhoDesdeTexto") resultado = _aplicarAnhoDesdeTexto(doc, op);
			else if (op.tipo === "filas") resultado = await _aplicarFilas(doc, op, dormir);
			else if (op.tipo === "qualdrop") resultado = await _aplicarQualdrop(doc, op, dormir);
			else if (op.tipo === "combobox") resultado = await _aplicarCombobox(doc, op, dormir);
			if (resultado.ok) exitosos.push(etiqueta);
			else fallidos.push(etiqueta);
			detalle.push({
				campo: etiqueta,
				tipo: op.tipo,
				estado: resultado.ok ? "completo" : "pendiente",
				detalle: resultado.detalle || "",
			});
		}
		return {
			exitosos,
			fallidos,
			omitidos: plan.omitidos || [],
			problemas: plan.problemas || [],
			detalle,
		};
	}

	return { aplicarPlan, SELECTOR_ARRAY, SELECTOR_AGREGAR, SELECTOR_GRUPO };
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBEjecutor;
}
