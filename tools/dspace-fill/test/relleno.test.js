// Estado del relleno (US-05): pendiente, parcial y verificado; reintento
// solo de los campos pendientes y protección de la edición del operador.

const test = require("node:test");
const assert = require("node:assert");
const VBRelleno = require("../src/relleno.js");

test("sin operaciones el relleno queda pendiente, no verificado", () => {
	const r = VBRelleno.evaluar([], []);
	assert.strictEqual(r.estado, "pendiente");
	assert.deepStrictEqual(r.pendientes, []);
});

test("todos los campos con dato escritos: verificado", () => {
	const r = VBRelleno.evaluar(
		[
			{ campo: "título", estado: "completo" },
			{ campo: "autores", estado: "completo" },
		],
		["asesor"]
	);
	assert.strictEqual(r.estado, "verificado");
	assert.deepStrictEqual(r.pendientes, []);
	// Un campo sin dato en la ficha no es un fallo del relleno.
	assert.strictEqual(r.campos.asesor, "sin_dato");
});

test("un campo pendiente con otros completos: parcial", () => {
	const r = VBRelleno.evaluar(
		[
			{ campo: "título", estado: "completo" },
			{ campo: "autores", estado: "pendiente" },
		],
		[]
	);
	assert.strictEqual(r.estado, "parcial");
	assert.deepStrictEqual(r.pendientes, ["autores"]);
	assert.deepStrictEqual(r.completados, ["título"]);
});

test("todos pendientes: sigue pendiente (no parcial)", () => {
	const r = VBRelleno.evaluar([{ campo: "autores", estado: "pendiente" }], []);
	assert.strictEqual(r.estado, "pendiente");
});

test("un plan con datos esenciales inválidos no se intenta", () => {
	const plan = {
		operaciones: [],
		omitidos: [],
		problemas: [{ campo: "autores", detalle: "el autor 2 no tiene nombre" }],
	};
	assert.strictEqual(VBRelleno.puedeIntentar(plan), false);
});

test("un plan sin problemas se intenta", () => {
	const plan = { operaciones: [], omitidos: [], problemas: [] };
	assert.strictEqual(VBRelleno.puedeIntentar(plan), true);
});

test("el reintento deja solo las operaciones de los campos pendientes", () => {
	const plan = {
		operaciones: [
			{ campo: "título", tipo: "texto" },
			{ campo: "autores", tipo: "filas" },
			{ campo: "asesor", tipo: "filas" },
		],
		omitidos: ["ORCID del asesor"],
		problemas: [],
	};
	const reintento = VBRelleno.planARetry(plan, ["autores"]);
	assert.strictEqual(reintento.operaciones.length, 1);
	assert.strictEqual(reintento.operaciones[0].campo, "autores");
	assert.strictEqual(reintento.soloPendientes, true);
	// Lo omitido y los problemas se conservan: el resumen sigue completo.
	assert.deepStrictEqual(reintento.omitidos, ["ORCID del asesor"]);
});

test("sin pendientes el reintento no cambia el plan", () => {
	const plan = { operaciones: [{ campo: "título", tipo: "texto" }], omitidos: [], problemas: [] };
	assert.strictEqual(VBRelleno.planARetry(plan, []), plan);
});
