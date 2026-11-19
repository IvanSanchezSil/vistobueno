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
