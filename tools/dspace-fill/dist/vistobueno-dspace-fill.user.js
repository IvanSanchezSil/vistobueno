// ==UserScript==
// @name         VistoBueno — rellenador del formulario de depósito UNT
// @namespace    vistobueno
// @version      1.2.3
// @description  Pre-llena el formulario oficial de depósito de DSpace (repositorio UNT) con la ficha de VistoBueno, registra el momento del clic en Depositar y pide al operador que confirme el ítem archivado. Protocolo 2: el archivo solo se registra con atestación explícita. Ver docs/CONTRATO_API.md.
// @match        https://repositorio.unitru.edu.pe/*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      localhost
// @updateURL    https://raw.githubusercontent.com/retblast/vistobueno/master/tools/dspace-fill/dist/vistobueno-dspace-fill.user.js
// @downloadURL  https://raw.githubusercontent.com/retblast/vistobueno/master/tools/dspace-fill/dist/vistobueno-dspace-fill.user.js
// ==/UserScript==


// Compuertas del rellenador: decisiones puras sobre el DOM y los textos.
// Se puede requerir en node (CommonJS) o correr en el navegador tras la
// concatenación (dist/): el archivo declara su namespace global.

const VBCompuertas = (() => {
	// Selectores estables del formulario oficial de la instancia
	// (evidencia: captura del formulario real; ver recursos/har-analisis/).
	// Se evitan los ids con prefijo numérico (7_array-0-…): ese índice
	// cambia por fila y por versión del UI; name e id fijos no.
	const SELECTORES = {
		titulo: 'input[name="dc.title"]',
		autores: 'input[name="dc.contributor.author"]',
		asesor: 'input[name="dc.contributor.advisor"]',
		resumen: 'textarea[name="dc.description.abstract"]',
		palabrasClave: 'input[name="dc.subject"]',
		anho: 'input#dc_date_issued_year',
		dniAutorMeta: 'select[name="renati.author_QUALDROP_METADATA"]',
		dniAutorValor: 'input[name="renati.author_QUALDROP_VALUE"]',
		dniAsesorMeta: 'select[name="renati.advisor_QUALDROP_METADATA"]',
		dniAsesorValor: 'input[name="renati.advisor_QUALDROP_VALUE"]',
		orcidAsesor: 'input[name="renati.advisor.orcid"]',
		derechosInput: 'input#dc_rights',
		derechosListbox: '#combobox_dc_rights_listbox',
		depositar: '#deposit',
	};

	// Página de ítem de DSpace 8: /items/<uuid>. MyDSpace, el workspace y
	// el resto de rutas NO son páginas de ítem: allí no se muestra el
	// panel de confirmación (protocolo 2, decisión de flujo).
	const RUTA_ITEM = /^\/items\/[^/]+\/?$/;

	// Handle institucional del Repositorio UNT. Solo se acepta un enlace
	// con esta forma EXACTA: un enlace a otro repositorio o una URL con
	// parámetros no identifican el ítem preparado.
	const HANDLE_ITEM = /^https?:\/\/hdl\.handle\.net\/20\.500\.14414\/\d+\/?$/;

	function esFormularioTesis(doc) {
		// Compuerta por forma (fail-closed): si la página no tiene los
		// campos de la tesis, el plan no tocaría nada — mejor no intentar.
		if (!doc) return false;
		const requeridos = [SELECTORES.titulo, SELECTORES.autores, SELECTORES.resumen];
		return requeridos.every((sel) => doc.querySelector(sel) !== null);
	}

	function esPaginaItem(doc, ruta) {
		// Compuerta por RUTA y por contenido: la URL debe ser la de un
		// ítem (`/items/<uuid>`) y la página debe publicar el título del
		// ítem como meta de cita. Con MyDSpace o el workspace, la ruta no
		// coincide y no hay panel de confirmación.
		if (!doc) return false;
		const camino = typeof ruta === "string" ? ruta : "";
		if (!RUTA_ITEM.test(camino)) return false;
		return doc.querySelector('meta[name="citation_title"]') !== null;
	}

	function normalizarHandle(href) {
		// Devuelve el handle institucional en forma canónica (https, sin
		// barra final) o null si el enlace no tiene esa forma.
		if (typeof href !== "string") return null;
		const limpio = href.trim();
		if (!HANDLE_ITEM.test(limpio)) return null;
		return limpio.replace(/^http:\/\//, "https://").replace(/\/+$/, "");
	}

	function _pareceHandleDelItem(nodo) {
		// Cuando la página muestra varios handles, solo vale el que la
		// página identifica como el handle del ítem (la fila de metadatos
		// dice "Handle" o "Identificador"). Sin ese dato, no se elige.
		if (!nodo) return false;
		const marca = nodo.getAttribute ? nodo.getAttribute("data-test") || "" : "";
		if (marca.toLowerCase().indexOf("handle") !== -1) return true;
		const fila = nodo.closest ? nodo.closest("tr") : null;
		const texto = fila ? (fila.textContent || "").toLowerCase() : "";
		return texto.indexOf("handle") !== -1 || texto.indexOf("identificador") !== -1;
	}

	function extraerHandle(doc) {
		// NO se toma el primer enlace hdl de la página: una referencia a
		// otro ítem puede aparecer antes. Solo se aceptan enlaces con la
		// forma institucional exacta y, si hay varios, el que la página
		// etiqueta como handle del ítem.
		if (!doc) return null;
		const candidatos = [];
		const enlaces = doc.querySelectorAll('a[href*="hdl.handle.net"]');
		Array.from(enlaces).forEach(function (enlace) {
			const normalizado = normalizarHandle(enlace.getAttribute("href") || "");
			if (normalizado) candidatos.push({ nodo: enlace, handle: normalizado });
		});
		if (!candidatos.length) return null;
		const distintos = new Set(candidatos.map((c) => c.handle));
		if (distintos.size === 1) return candidatos[0].handle;
		const etiquetado = candidatos.find((c) => _pareceHandleDelItem(c.nodo));
		return etiquetado ? etiquetado.handle : null;
	}

	function tituloDeItem(doc) {
		// El título REAL del ítem: lo publica DSpace como meta de cita.
		// No es el título esperado de la ficha: el userscript lo compara
		// y lo envía como `titulo_observado`.
		if (!doc) return "";
		const meta = doc.querySelector('meta[name="citation_title"]');
		return meta ? (meta.getAttribute("content") || "").trim() : "";
	}

	function autoresDeItem(doc) {
		// Los autores del ítem, si la página los publica como metas de
		// cita (`citation_author`). Si no hay metas, NO hay evidencia:
		// se devuelve null y nunca una lista vacía que parezca "coincide".
		if (!doc) return null;
		const autores = Array.from(doc.querySelectorAll('meta[name="citation_author"]'))
			.map((meta) => (meta.getAttribute("content") || "").trim())
			.filter((autor) => autor.length > 0);
		return autores.length ? autores : null;
	}

	function normalizar(texto) {
		// Minúsculas, sin acentos, espacios colapsados: para comparar
		// títulos entre la ficha y el ítem sin morir por el detalle.
		if (typeof texto !== "string") return "";
		return texto
			.normalize("NFD")
			.replace(/[\u0300-\u036f]/g, "")
			.toLowerCase()
			.replace(/\s+/g, " ")
			.trim();
	}

	function titulosCoinciden(tituloFicha, tituloItem) {
		// Igualdad NORMALIZADA, no inclusión: un título que solo contiene
		// al otro puede ser otra tesis. El flujo v1.14.0 compara el
		// título esperado de la ficha con el título real del ítem.
		const a = normalizar(tituloFicha);
		const b = normalizar(tituloItem);
		if (!a || !b) return false;
		return a === b;
	}

	function autoresCoinciden(autoresFicha, autoresItem) {
		// Mismo criterio que el servidor: conjuntos normalizados. El
		// orden no identifica a una persona y las tildes no cambian el
		// nombre. Si falta alguna de las dos listas, no hay coincidencia.
		if (!Array.isArray(autoresFicha) || !Array.isArray(autoresItem)) return false;
		const a = autoresFicha.map(normalizar).filter(Boolean).sort();
		const b = autoresItem.map(normalizar).filter(Boolean).sort();
		if (!a.length || !b.length || a.length !== b.length) return false;
		return a.every((valor, i) => valor === b[i]);
	}

	return {
		SELECTORES,
		RUTA_ITEM,
		esFormularioTesis,
		esPaginaItem,
		extraerHandle,
		normalizarHandle,
		tituloDeItem,
		autoresDeItem,
		normalizar,
		titulosCoinciden,
		autoresCoinciden,
	};
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBCompuertas;
}


// Mapeador del rellenador: ficha de VistoBueno (JSON del buzón) → plan
// de relleno determinista. Puro: ni DOM ni red; todo el comportamiento
// se prueba en node sin navegador.

const VBMapeador = (() => {
	// Valor canónico del vocabulario common_rights (la causa del bug
	// http/https documentado en DSPACE_API §11): se selecciona por el
	// TEXTO visible, que es como el combobox de Angular filtra opciones.
	const ACCESO_ABIERTO = "Acceso abierto";

	function valorExtraido(ficha, campo) {
		if (!ficha || !Array.isArray(ficha.extraidos)) return null;
		const item = ficha.extraidos.find((e) => e && e.campo === campo);
		return item ? item.valor : null;
	}

	function valorManual(ficha, campo) {
		if (!ficha || !Array.isArray(ficha.manuales)) return null;
		const item = ficha.manuales.find((m) => m && m.campo === campo);
		return item ? item.valor : null;
	}

	function comoLista(valor) {
		if (valor === null || valor === undefined) return [];
		if (Array.isArray(valor)) return valor.filter((v) => typeof v === "string" && v.trim());
		return typeof valor === "string" && valor.trim() ? [valor] : [];
	}

	function listaPosicional(valor) {
		// Conserva las posiciones: un hueco NO se compacta. El DNI del
		// autor 2 no puede terminar en la fila del autor 1 (US-04).
		if (valor === null || valor === undefined) return [];
		if (Array.isArray(valor)) {
			return valor.map((v) => (typeof v === "string" ? v.trim() : ""));
		}
		return typeof valor === "string" && valor.trim() ? [valor.trim()] : [];
	}

	function normalizarOrcid(valor) {
		if (typeof valor !== "string") return null;
		const texto = valor.trim().replace(/^https?:\/\/(?:www\.)?orcid\.org\/([^/]+)\/?$/i, "$1");
		if (!/^(?:\d{15}[\dX]|\d{4}-\d{4}-\d{4}-\d{3}[\dX])$/i.test(texto)) return null;
		return texto.replace(/-/g, "").toUpperCase().match(/.{4}/g).join("-");
	}

	function checksumOrcidValido(orcid) {
		if (!orcid) return false;
		const digitos = String(orcid).replace(/-/g, "").toUpperCase();
		if (digitos.length !== 16 || !/^\d{15}[\dX]$/.test(digitos)) return false;
		let total = 0;
		for (let i = 0; i < 15; i++) {
			total = (total + parseInt(digitos[i], 10)) * 2;
		}
		const resto = (12 - (total % 11)) % 11;
		const esperado = resto === 10 ? "X" : String(resto);
		return digitos[15] === esperado;
	}

	function construirPlan(ficha, selectores) {
		// Cada operación es independiente: si falta el dato, la operación
		// se omite y queda en el resumen (el toast lo muestra; el
		// operador completa a mano — fallo visible, nunca silencioso).
		//
		// `campo` identifica el dato en el resumen: "texto" no dice qué
		// campo falló (US-15).
		const operaciones = [];
		const omitidos = [];
		const avisos = [];
		const problemas = [];

		const titulo = valorExtraido(ficha, "dc.title");
		if (typeof titulo === "string" && titulo.trim()) {
			operaciones.push({
				tipo: "texto",
				campo: "título",
				selector: selectores.titulo,
				valor: titulo.trim(),
			});
		} else {
			omitidos.push("título");
		}

		// Autores: la lista conserva las posiciones. Un autor sin nombre
		// es un dato inválido: no se rellena la lista porque el DNI
		// quedaría pegado a la persona equivocada.
		const autores = listaPosicional(valorExtraido(ficha, "dc.contributor.author"));
		const autoresSinNombre = [];
		autores.forEach(function (autor, indice) {
			if (!autor) autoresSinNombre.push(indice + 1);
		});
		if (!autores.length) {
			omitidos.push("autores");
		} else if (autoresSinNombre.length) {
			problemas.push({
				campo: "autores",
				detalle:
					"el autor " +
					autoresSinNombre.join(", ") +
					" no tiene nombre; no se rellenó la lista para no desalinear el DNI",
			});
		} else {
			operaciones.push({
				tipo: "filas",
				campo: "autores",
				selector: selectores.autores,
				valores: autores,
			});
		}

		// Asesor y resumen son campos repetibles en el formulario
		// oficial: se tratan como filas para que una fila sobrante se
		// elimine con el control del widget.
		const asesor = valorExtraido(ficha, "dc.contributor.advisor");
		if (typeof asesor === "string" && asesor.trim()) {
			operaciones.push({
				tipo: "filas",
				campo: "asesor",
				selector: selectores.asesor,
				valores: [asesor.trim()],
			});
		} else {
			omitidos.push("asesor");
		}

		const resumen = valorExtraido(ficha, "dc.description.abstract");
		if (typeof resumen === "string" && resumen.trim()) {
			operaciones.push({
				tipo: "filas",
				campo: "resumen",
				selector: selectores.resumen,
				valores: [resumen.trim()],
			});
		} else {
			omitidos.push("resumen");
		}

		const palabras = comoLista(valorExtraido(ficha, "dc.subject"));
		if (palabras.length) {
			operaciones.push({
				tipo: "filas",
				campo: "palabras clave",
				selector: selectores.palabrasClave,
				valores: palabras,
			});
		} else {
			omitidos.push("palabras clave");
		}

		// Solo el AÑO del campo de fecha: día y mes son widgets de solo
		// lectura (picker); el operador los elige como siempre.
		const anho = valorExtraido(ficha, "dc.date.issued");
		if (typeof anho === "string" && /^\d{4}$/.test(anho.trim())) {
			operaciones.push({
				tipo: "texto",
				campo: "año de emisión",
				selector: selectores.anho,
				valor: anho.trim(),
			});
		} else if (anho) {
			operaciones.push({
				tipo: "anhoDesdeTexto",
				campo: "año de emisión",
				selector: selectores.anho,
				valor: anho,
			});
		} else {
			omitidos.push("año de emisión");
		}

		// QUALDROP de DNI del autor: filas alineadas por posición con los
		// autores; la opción se identifica por el sufijo renati.author.dni.
		const dnisAutor = listaPosicional(valorManual(ficha, "renati.author.dni"));
		if (dnisAutor.length) {
			if (!autores.length) {
				omitidos.push("DNI del autor");
			} else if (dnisAutor.length !== autores.length) {
				problemas.push({
					campo: "DNI del autor",
					detalle:
						"la ficha trae " +
						dnisAutor.length +
						" DNI para " +
						autores.length +
						" autores: se necesita uno por autor y no se adivina el emparejamiento",
				});
			} else {
				const sinDni = [];
				dnisAutor.forEach(function (dni, indice) {
					if (!dni) sinDni.push(indice + 1);
				});
				if (sinDni.length) {
					problemas.push({
						campo: "DNI del autor",
						detalle: "falta el DNI del autor " + sinDni.join(", "),
					});
				}
				operaciones.push({
					tipo: "qualdrop",
					campo: "DNI del autor",
					selectorMeta: selectores.dniAutorMeta,
					opcionSufijo: "renati.author.dni",
					selectorValor: selectores.dniAutorValor,
					valores: dnisAutor,
				});
			}
		}

		const dniAsesor = comoLista(valorManual(ficha, "renati.advisor.dni"))[0];
		if (dniAsesor) {
			operaciones.push({
				tipo: "qualdrop",
				campo: "DNI del asesor",
				selectorMeta: selectores.dniAsesorMeta,
				opcionSufijo: "renati.advisor.dni",
				selectorValor: selectores.dniAsesorValor,
				valores: [dniAsesor],
			});
		}

		// Presencia en `extraidos` manda aunque el valor sea null o cadena
		// vacía (borrado explícito del operador): en ese caso NO se consulta
		// `manuales`, para que un valor legado no reaparezca. Solo si la
		// clave no existe en `extraidos` se usa el valor legado.
		let orcidCrudo = null;
		let presenteEnExtraidos = false;
		if (ficha && Array.isArray(ficha.extraidos)) {
			const item = ficha.extraidos.find((e) => e && e.campo === "renati.advisor.orcid");
			if (item) {
				presenteEnExtraidos = true;
				orcidCrudo = item.valor;
			}
		}
		if (!presenteEnExtraidos) {
			orcidCrudo = comoLista(valorManual(ficha, "renati.advisor.orcid"))[0];
		}
		// Normalización: acepta ORCID desnudo con o sin guiones y la URL
		// oficial, y lo deja en dddd-dddd-dddd-dddd. Cadena vacía o solo
		// espacios se trata como borrado (no se rellena ni se valida).
		const orcidNormalizado = normalizarOrcid(orcidCrudo);
		if (orcidCrudo !== null && orcidCrudo !== undefined && String(orcidCrudo).trim() !== "") {
			if (orcidNormalizado && checksumOrcidValido(orcidNormalizado)) {
				operaciones.push({
					tipo: "texto",
					campo: "ORCID del asesor",
					selector: selectores.orcidAsesor,
					valor: orcidNormalizado,
				});
			} else {
				avisos.push("ORCID del asesor: formato o dígito de control inválido; se omite el relleno");
				omitidos.push("ORCID del asesor");
			}
		}

		// Fix del bug dc.rights: SIEMPRE se intenta (el default del
		// formulario es el http roto; el vocabulario solo tiene el
		// https canónico). Si el combobox no coopera, el operador lo
		// selecciona a mano como hace hoy — fallo visible en el resumen.
		operaciones.push({
			tipo: "combobox",
			campo: "derechos de acceso",
			selectorInput: selectores.derechosInput,
			selectorListbox: selectores.derechosListbox,
			texto: ACCESO_ABIERTO,
		});

		return { operaciones, omitidos: omitidos, problemas: problemas, avisos: avisos };
	}

	return {
		construirPlan,
		valorExtraido,
		valorManual,
		comoLista,
		listaPosicional,
		ACCESO_ABIERTO,
	};
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBMapeador;
}


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
					const vista = input.ownerDocument.defaultView;
					try { el.focus(); } catch (e) {}
					el.dispatchEvent(new vista.MouseEvent("mousedown", { bubbles: true }));
					el.click();
					el.dispatchEvent(new vista.MouseEvent("mouseup", { bubbles: true }));
					_evento(doc, input, "change");
					// Algunos widgets de Angular responden mejor al
					// teclado que al clic sintético: se intenta Enter
					// sobre el input como respaldo.
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


// Estado del relleno del formulario: pendiente, en curso, parcial o
// verificado.
//
// Un relleno parcial NO bloquea el formulario. Si un campo quedó a mano
// (el control no apareció, el tipo de documento no existe, el botón "+"
// no agrego la fila), el operador debe poder completarlo y el
// userscript debe poder reintentar SOLO ese campo sin pisar lo que el
// operador ya corrigió (US-05).
//
// Módulo puro: no toca el DOM ni la API. El wrapper decide cuándo
// aplicar y cuándo reintentar.

const VBRelleno = (() => {
	const ESTADOS = {
		// Nada escrito todavía.
		PENDIENTE: "pendiente",
		// El plan está corriendo: no se puede decidir todavía.
		EN_CURSO: "en_curso",
		// Parte de los campos quedó escrita y parte no.
		PARCIAL: "parcial",
		// Todos los campos con dato quedaron escritos.
		VERIFICADO: "verificado",
	};

	// Un campo con dato en la ficha que el userscript no pudo escribir
	// queda pendiente. Un campo SIN dato en la ficha no es un fallo del
	// relleno: lo completa el operador a mano y no se reintenta.
	function evaluar(detalle, omitidos) {
		const campos = {};
		const pendientes = [];
		const ejecutadas = detalle || [];
		ejecutadas.forEach(function (item) {
			const estado = item.estado === "completo" ? "completo" : "pendiente";
			campos[item.campo] = estado;
			if (estado === "pendiente") pendientes.push(item.campo);
		});
		(omitidos || []).forEach(function (campo) {
			if (!(campo in campos)) campos[campo] = "sin_dato";
		});
		const completados = Object.keys(campos).filter(function (campo) {
			return campos[campo] === "completo";
		});
		let estado;
		if (!ejecutadas.length) {
			// El plan no tenía operaciones: no se escribió nada.
			estado = ESTADOS.PENDIENTE;
		} else if (!pendientes.length) {
			estado = ESTADOS.VERIFICADO;
		} else if (completados.length) {
			estado = ESTADOS.PARCIAL;
		} else {
			estado = ESTADOS.PENDIENTE;
		}
		return {
			estado: estado,
			campos: campos,
			pendientes: pendientes,
			completados: completados,
		};
	}

	// Un plan con datos esenciales inválidos (un autor sin nombre, una
	// lista de DNI que no corresponde a los autores) NO se ejecuta: el
	// relleno dejaría los datos desalineados. El operador corrige la
	// ficha en VistoBueno y vuelve a preparar.
	function puedeIntentar(plan) {
		if (!plan) return false;
		return !plan.problemas || plan.problemas.length === 0;
	}

	// Reintento: solo las operaciones de los campos que quedaron
	// pendientes. El modo `preservarSiLleno` impide pisar lo que el
	// operador escribió a mano en el intento anterior.
	function planARetry(plan, pendientes) {
		if (!plan) return plan;
		const lista = Array.isArray(pendientes) ? pendientes : [];
		if (!lista.length) return plan;
		const operaciones = (plan.operaciones || [])
			.filter(function (op) {
				return lista.indexOf(op.campo) !== -1;
			})
			.map(function (op) {
				// En el reintento no se pisa lo que el operador ya
				// escribió a mano en el campo pendiente.
				return Object.assign({}, op, { preservarSiLleno: true });
			});
		return {
			operaciones: operaciones,
			omitidos: plan.omitidos || [],
			problemas: plan.problemas || [],
			soloPendientes: true,
		};
	}

	return {
		ESTADOS: ESTADOS,
		evaluar: evaluar,
		puedeIntentar: puedeIntentar,
		planARetry: planARetry,
	};
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBRelleno;
}


// Tickets de operación: evita que un callback antiguo reemplace el
// estado más nuevo cuando hay varias operaciones en vuelo (US-06).
//
// Cada operación async obtiene un ticket con un identificador y una
// marca de agua. Antes de guardar estado o aplicar cambios, el callback
// comprueba que su ticket siga siendo el vigente; si no, descarta su
// resultado.
//
// Módulo puro: no toca el DOM ni la API.

const VBTicket = (() => {
	let ultimoTicket = 0;

	function nuevoTicket() {
		ultimoTicket++;
		return ultimoTicket;
	}

	return {
		nuevoTicket: nuevoTicket,
		ticketActual: function () {
			return ultimoTicket;
		},
	};
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBTicket;
}


// Panel de confirmación del depósito: la ÚNICA vía para registrar el
// archivo en VistoBueno. El panel no escribe nada por su cuenta: el
// operador lee la evidencia y pulsa el botón; el wrapper hace la
// escritura con la atestación explícita.
//
// Todo el texto se inserta con textContent: el título o el handle del
// ítem son datos externos y no pueden interpretarse como HTML.

const VBPanel = (() => {
	const ID_PANEL = "vb-panel";

	function _texto(doc, etiqueta, contenido, estilos) {
		const el = doc.createElement(etiqueta);
		el.textContent = contenido;
		if (estilos) el.style.cssText = estilos;
		return el;
	}

	function quitar(doc) {
		const existente = doc.getElementById(ID_PANEL);
		if (existente && existente.parentNode) existente.parentNode.removeChild(existente);
	}

	function montar(doc, datos) {
		quitar(doc);
		const panel = doc.createElement("div");
		panel.id = ID_PANEL;
		panel.style.cssText =
			"position:fixed;top:16px;right:16px;z-index:99999;background:#fff;color:#1a1a2e;" +
			"border:1px solid #b8c4d6;border-radius:8px;padding:14px 16px;font:13px sans-serif;" +
			"max-width:440px;box-shadow:0 2px 10px rgba(0,0,0,.25);text-align:left";

		panel.appendChild(
			_texto(doc, "strong", "Confirmar el depósito archivado", "display:block;margin-bottom:8px")
		);
		panel.appendChild(_texto(doc, "p", "Ítem: " + (datos.tituloItem || "(sin título)")));
		panel.appendChild(_texto(doc, "p", "Handle: " + (datos.handle || "(sin handle)")));
		panel.appendChild(
			_texto(
				doc,
				"p",
				"Autores: " +
					(datos.autoresItem && datos.autoresItem.length
						? datos.autoresItem.join("; ")
						: "no verificados (la página no los publica)")
			)
		);
		panel.appendChild(
			_texto(
				doc,
				"p",
				"Hora del clic en Depositar: " + (datos.timestamp || "no registrada")
			)
		);
		panel.appendChild(
			_texto(
				doc,
				"p",
				"Trámite: " + (datos.tramiteId || "(sin trámite)") + " (revisión " + datos.revision + ")"
			)
		);

		(datos.avisos || []).forEach(function (aviso) {
			panel.appendChild(
				_texto(doc, "p", aviso, "margin:6px 0 0 0;color:#8a1f11;font-weight:600")
			);
		});

		const acciones = doc.createElement("div");
		acciones.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;margin-top:12px";

		const botonConfirmar = doc.createElement("button");
		botonConfirmar.id = "vb-confirmar";
		botonConfirmar.type = "button";
		botonConfirmar.textContent = "Confirmar depósito archivado";
		botonConfirmar.disabled = !datos.puedeConfirmar;
		botonConfirmar.style.cssText =
			"background:#28a745;color:#fff;border:none;padding:8px 12px;border-radius:6px;" +
			"font:13px sans-serif;cursor:pointer";
		if (!datos.puedeConfirmar) botonConfirmar.style.opacity = "0.55";
		botonConfirmar.addEventListener("click", function () {
			if (datos.alConfirmar) datos.alConfirmar();
		});
		acciones.appendChild(botonConfirmar);

		if (datos.alMarcarInconsistencia) {
			const botonInconsistencia = doc.createElement("button");
			botonInconsistencia.id = "vb-inconsistencia";
			botonInconsistencia.type = "button";
			botonInconsistencia.textContent = "Reportar inconsistencia";
			botonInconsistencia.style.cssText =
				"background:#fff;color:#8a1f11;border:1px solid #d9a6a0;padding:8px 12px;" +
				"border-radius:6px;font:13px sans-serif;cursor:pointer";
			botonInconsistencia.addEventListener("click", function () {
				if (datos.alMarcarInconsistencia) datos.alMarcarInconsistencia();
			});
			acciones.appendChild(botonInconsistencia);
		}

		const botonCerrar = doc.createElement("button");
		botonCerrar.id = "vb-cerrar";
		botonCerrar.type = "button";
		botonCerrar.textContent = "Cerrar";
		botonCerrar.style.cssText =
			"background:#fff;color:#1a1a2e;border:1px solid #b8c4d6;padding:8px 12px;" +
			"border-radius:6px;font:13px sans-serif;cursor:pointer";
		botonCerrar.addEventListener("click", function () {
			quitar(doc);
			if (datos.alCerrar) datos.alCerrar();
		});
		acciones.appendChild(botonCerrar);

		panel.appendChild(acciones);
		doc.body.appendChild(panel);
		return panel;
	}

	return { montar, quitar, ID_PANEL };
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBPanel;
}


// Reloj del userscript: fecha y hora de pared en la zona del Perú.
//
// El registro oficial y la constancia muestran la hora peruana. `Date`
// no la da directamente: `toISOString()` devuelve UTC, que en Lima va
// 5 horas adelantado y después de las 19:00 cambia el día. Este módulo
// formatea el instante en America/Lima con `Intl`, sin depender de la
// zona horaria configurada en el navegador.

const VBReloj = (() => {
	const ZONA = "America/Lima";

	// Un solo formateador: `formatToParts` entrega los campos por nombre
	// y evita depender del orden o de los separadores del locale.
	const FORMATO = new Intl.DateTimeFormat("en-CA", {
		timeZone: ZONA,
		year: "numeric",
		month: "2-digit",
		day: "2-digit",
		hour: "2-digit",
		minute: "2-digit",
		second: "2-digit",
		hourCycle: "h23",
	});

	function ahoraLima(ahora) {
		// `ahora` es inyectable para los tests; en producción es `new Date()`.
		const partes = FORMATO.formatToParts(ahora || new Date());
		const dato = (tipo) => partes.find((parte) => parte.type === tipo).value;
		// ISO 8601 sin offset: el userscript reporta hora de pared del
		// Perú y la API interpreta un timestamp sin offset como Lima.
		return (
			dato("year") +
			"-" +
			dato("month") +
			"-" +
			dato("day") +
			"T" +
			dato("hour") +
			":" +
			dato("minute") +
			":" +
			dato("second")
		);
	}

	return { ZONA, ahoraLima };
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBReloj;
}


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
				alRecibir(sobre, null, ticket);
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
				alRecibir(tramite, null, ticket);
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
					llenar(sobre, ticket, true);
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

	function llenar(sobre, ticket, forzar) {
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
		if (mismoTramite && !forzar) {
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
		//
		// US-05: si el relleno ya fue verificado pero el operador
		// pulsa explicitamente "Rellenar" (forzar), re-intentamos TODOS
		// los campos con preservarSiLleno: se llena lo que falta y se
		// conserva lo que el operador ya corrigio a mano.
		let planEfectivo;
		if (esVerificado && forzar) {
			const todosLosCampos = (plan.operaciones || []).map(function (op) {
				return op.campo;
			});
			planEfectivo = VBRelleno.planARetry(plan, todosLosCampos);
		} else if (esParcial) {
			planEfectivo = VBRelleno.planARetry(plan, previo.pendientes);
		} else {
			planEfectivo = plan;
		}

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
			partes.push(...plan.avisos);
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


// Generado por dev/build.js — editar los src/ y reconstruir.
