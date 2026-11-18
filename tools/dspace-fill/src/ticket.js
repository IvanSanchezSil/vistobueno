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
	};
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBTicket;
}
