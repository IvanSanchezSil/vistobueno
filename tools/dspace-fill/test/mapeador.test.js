// Tests del mapeador: ficha → plan de relleno determinista.

const test = require("node:test");
const assert = require("node:assert");
const path = require("path");

const VBMapeador = require(path.join(__dirname, "..", "src", "mapeador.js"));
const { SELECTORES } = require(path.join(__dirname, "..", "src", "compuertas.js"));

function fichaCompleta() {
	return {
		extraidos: [
			{ campo: "dc.title", valor: "Taller de dramatización", pagina: 1, detectado: true },
			{ campo: "dc.contributor.author", valor: ["Cerna Vidal Kassiel", "Varas Vega Cinthya"], pagina: 1, detectado: true },
			{ campo: "dc.contributor.advisor", valor: "Ms. Ada Lovelace", pagina: 1, detectado: true },
			{ campo: "dc.description.abstract", valor: "Resumen del trabajo.", pagina: 3, detectado: true },
			{ campo: "dc.subject", valor: ["títeres", "lectura"], pagina: 3, detectado: true },
			{ campo: "dc.date.issued", valor: "2026", pagina: null, detectado: true },
			{ campo: "escuela", valor: "Educación Primaria", pagina: 1, detectado: true },
			{ campo: "renati.juror", valor: null, pagina: null, detectado: false },
		],
		manuales: [
			{ campo: "matricula", valor: ["15185003-20", "10130003-23"] },
			{ campo: "renati.author.dni", valor: ["12345678", "87654321"] },
			{ campo: "renati.advisor.dni", valor: "11222333" },
			{ campo: "renati.advisor.orcid", valor: "0000-0002-1825-0097" },
		],
	};
}

test("ficha completa produce el plan con todas las operaciones", () => {
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);
	const tipos = plan.operaciones.map((op) => op.tipo);
	assert.deepStrictEqual(tipos, [
		"texto", // título
		"filas", // autores
		"filas", // asesor (campo repetible del formulario)
		"filas", // resumen (campo repetible del formulario)
		"filas", // palabras clave
		"texto", // año
		"qualdrop", // DNI autor
		"qualdrop", // DNI asesor
		"texto", // ORCID
		"combobox", // fix Acceso abierto (siempre)
	]);
	assert.deepStrictEqual(plan.omitidos, []);
	assert.deepStrictEqual(plan.problemas, []);
});

test("cada operación identifica el campo para el resumen", () => {
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);
	const campos = plan.operaciones.map((op) => op.campo);
	assert.deepStrictEqual(campos, [
		"título",
		"autores",
		"asesor",
		"resumen",
		"palabras clave",
		"año de emisión",
		"DNI del autor",
		"DNI del asesor",
		"ORCID del asesor",
		"derechos de acceso",
	]);
});

test("el título viaja íntegro al selector correcto", () => {
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);
	const titulo = plan.operaciones.find((op) => op.selector === SELECTORES.titulo);
	assert.ok(titulo);
	assert.strictEqual(titulo.valor, "Taller de dramatización");
});

test("los autores y las palabras clave van como filas alineadas", () => {
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);
	const autores = plan.operaciones.find((op) => op.selector === SELECTORES.autores);
	assert.deepStrictEqual(autores.valores, ["Cerna Vidal Kassiel", "Varas Vega Cinthya"]);
	const palabras = plan.operaciones.find((op) => op.selector === SELECTORES.palabrasClave);
	assert.deepStrictEqual(palabras.valores, ["títeres", "lectura"]);
});

test("asesor y resumen se tratan como filas: una fila sobrante se puede quitar", () => {
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);
	const asesor = plan.operaciones.find((op) => op.selector === SELECTORES.asesor);
	assert.strictEqual(asesor.tipo, "filas");
	assert.deepStrictEqual(asesor.valores, ["Ms. Ada Lovelace"]);
	const resumen = plan.operaciones.find((op) => op.selector === SELECTORES.resumen);
	assert.strictEqual(resumen.tipo, "filas");
});

test("el QUALDROP del autor alinea DNI por posición y fija el sufijo", () => {
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);
	const dni = plan.operaciones.find((op) => op.tipo === "qualdrop" && op.opcionSufijo === "renati.author.dni");
	assert.deepStrictEqual(dni.valores, ["12345678", "87654321"]);
	assert.strictEqual(dni.selectorMeta, SELECTORES.dniAutorMeta);
});

test("un hueco en la lista de DNI no compacta: se reportan los autores sin DNI", () => {
	// El DNI del segundo autor no puede terminar en la fila del primero.
	const ficha = fichaCompleta();
	ficha.manuales.find((m) => m.campo === "renati.author.dni").valor = ["", "22222222"];
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);
	const dni = plan.operaciones.find((op) => op.tipo === "qualdrop" && op.opcionSufijo === "renati.author.dni");
	assert.deepStrictEqual(dni.valores, ["", "22222222"]);
	assert.strictEqual(plan.problemas.length, 1);
	assert.strictEqual(plan.problemas[0].campo, "DNI del autor");
	assert.match(plan.problemas[0].detalle, /autor 1/);
});

test("una lista de DNI de otra longitud no se empareja a mano", () => {
	const ficha = fichaCompleta();
	ficha.manuales.find((m) => m.campo === "renati.author.dni").valor = ["12345678"];
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);
	assert.ok(!plan.operaciones.some((op) => op.opcionSufijo === "renati.author.dni"));
	assert.strictEqual(plan.problemas.length, 1);
	assert.match(plan.problemas[0].detalle, /uno por autor/);
});

test("un autor sin nombre impide el relleno de la lista de autores", () => {
	const ficha = fichaCompleta();
	ficha.extraidos.find((e) => e.campo === "dc.contributor.author").valor = ["Cerna Vidal Kassiel", ""];
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);
	assert.ok(!plan.operaciones.some((op) => op.selector === SELECTORES.autores));
	assert.strictEqual(plan.problemas.length, 1);
	assert.strictEqual(plan.problemas[0].campo, "autores");
	assert.match(plan.problemas[0].detalle, /autor 2/);
});

test("campos sin detectar se omiten con nombre legible para el toast", () => {
	const ficha = fichaCompleta();
	ficha.extraidos.find((e) => e.campo === "dc.title").valor = null;
	ficha.extraidos.find((e) => e.campo === "dc.contributor.author").valor = [];
	ficha.extraidos.find((e) => e.campo === "dc.date.issued").valor = null;
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);
	assert.ok(plan.omitidos.includes("título"));
	assert.ok(plan.omitidos.includes("autores"));
	assert.ok(plan.omitidos.includes("año de emisión"));
	assert.ok(!plan.operaciones.some((op) => op.selector === SELECTORES.titulo));
	// El fix de Acceso abierto nunca se omite.
	assert.ok(plan.operaciones.some((op) => op.tipo === "combobox"));
});

test("el año puede venir como fecha completa: se extraen los 4 dígitos", () => {
	const ficha = fichaCompleta();
	ficha.extraidos.find((e) => e.campo === "dc.date.issued").valor = "2026-10-19";
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);
	const anho = plan.operaciones.find((op) => op.selector === SELECTORES.anho);
	assert.ok(anho);
	assert.strictEqual(anho.tipo, "anhoDesdeTexto");
});

test("DNI del autor acepta valor único o lista", () => {
	const ficha = fichaCompleta();
	ficha.manuales.find((m) => m.campo === "renati.author.dni").valor = "12345678";
	ficha.extraidos.find((e) => e.campo === "dc.contributor.author").valor = ["Cerna Vidal Kassiel"];
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);
	const dni = plan.operaciones.find((op) => op.tipo === "qualdrop" && op.opcionSufijo === "renati.author.dni");
	assert.deepStrictEqual(dni.valores, ["12345678"]);
});

test("sin manuales no hay QUALDROP ni ORCID, y no explota", () => {
	const ficha = fichaCompleta();
	ficha.manuales = [];
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);
	assert.ok(!plan.operaciones.some((op) => op.tipo === "qualdrop"));
	assert.ok(!plan.operaciones.some((op) => op.selector === SELECTORES.orcidAsesor));
});

test("listaPosicional conserva los huecos; comoLista los descarta", () => {
	assert.deepStrictEqual(VBMapeador.listaPosicional(["", "B", ""]), ["", "B", ""]);
	assert.deepStrictEqual(VBMapeador.listaPosicional(["", "B"]), ["", "B"]);
	assert.deepStrictEqual(VBMapeador.comoLista(["", "B"]), ["B"]);
});
