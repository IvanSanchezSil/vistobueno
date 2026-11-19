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

	function construirPlan(ficha, selectores) {
		// Cada operación es independiente: si falta el dato, la operación
		// se omite y queda en el resumen (el toast lo muestra; el
		// operador completa a mano — fallo visible, nunca silencioso).
		//
		// `campo` identifica el dato en el resumen: "texto" no dice qué
		// campo falló (US-15).
		const operaciones = [];
		const omitidos = [];
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

		const orcid = comoLista(valorManual(ficha, "renati.advisor.orcid"))[0];
		if (orcid) {
			operaciones.push({
				tipo: "texto",
				campo: "ORCID del asesor",
				selector: selectores.orcidAsesor,
				valor: orcid,
			});
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

		return { operaciones, omitidos: omitidos, problemas: problemas };
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
