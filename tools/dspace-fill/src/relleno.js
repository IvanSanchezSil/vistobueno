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
