// Tests de las compuertas: forma del formulario, ruta de ítem, handle y
// comparación de títulos y autores. El DOM sale del fixture (jsdom).

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const {
	esFormularioTesis,
	esPaginaItem,
	extraerHandle,
	tituloDeItem,
	autoresDeItem,
	normalizar,
	titulosCoinciden,
	autoresCoinciden,
} = require(path.join(__dirname, "..", "src", "compuertas.js"));

function domDesde(rel) {
	const html = fs.readFileSync(path.join(__dirname, "fixtures", rel), "utf8");
	return new JSDOM(html);
}

function domDesdeHtml(html) {
	return new JSDOM(html);
}

const RUTA_ITEM = "/items/1b2c3d4e";

test("esFormularioTesis: true en el fixture del formulario", () => {
	const dom = domDesde("form.html");
	assert.strictEqual(esFormularioTesis(dom.window.document), true);
});

test("esFormularioTesis: false en una página sin formulario (fail-closed)", () => {
	const dom = domDesde("item.html");
	assert.strictEqual(esFormularioTesis(dom.window.document), false);
});

test("esFormularioTesis: false sin document", () => {
	assert.strictEqual(esFormularioTesis(null), false);
});

test("esPaginaItem: true con la ruta de ítem y la meta de título", () => {
	const dom = domDesde("item.html");
	assert.strictEqual(esPaginaItem(dom.window.document, RUTA_ITEM), true);
});

test("esPaginaItem: false en el formulario", () => {
	const dom = domDesde("form.html");
	assert.strictEqual(esPaginaItem(dom.window.document, RUTA_ITEM), false);
});

test("esPaginaItem: false en MyDSpace y en el workspace", () => {
	const dom = domDesde("item.html");
	assert.strictEqual(esPaginaItem(dom.window.document, "/mydspace"), false);
	assert.strictEqual(esPaginaItem(dom.window.document, "/workspaceitems/1/edit"), false);
	assert.strictEqual(esPaginaItem(dom.window.document, "/"), false);
});

test("esPaginaItem: false si la página no publica el título", () => {
	const dom = domDesdeHtml('<html><head></head><body></body></html>');
	assert.strictEqual(esPaginaItem(dom.window.document, RUTA_ITEM), false);
});

test("extraerHandle encuentra el handle institucional del ítem", () => {
	const dom = domDesde("item.html");
	assert.strictEqual(
		extraerHandle(dom.window.document),
		"https://hdl.handle.net/20.500.14414/27871"
	);
});

test("extraerHandle ignora un handle de otro repositorio", () => {
	const dom = domDesdeHtml(
		'<html><body><a href="https://hdl.handle.net/1234/99999">otro</a></body></html>'
	);
	assert.strictEqual(extraerHandle(dom.window.document), null);
});

test("extraerHandle no toma el primer enlace si hay varios handles", () => {
	// Referencia ajena primero, después el handle del ítem en su fila.
	const dom = domDesdeHtml(
		'<html><body>' +
			'<p><a href="https://hdl.handle.net/20.500.14414/111111">Referencia</a></p>' +
			'<table><tr><th>Handle</th><td>' +
			'<a href="https://hdl.handle.net/20.500.14414/222222">https://hdl.handle.net/20.500.14414/222222</a>' +
			"</td></tr></table>" +
			"</body></html>"
	);
	assert.strictEqual(
		extraerHandle(dom.window.document),
		"https://hdl.handle.net/20.500.14414/222222"
	);
});

test("extraerHandle devuelve null si hay dos handles sin criterio", () => {
	const dom = domDesdeHtml(
		'<html><body>' +
			'<p><a href="https://hdl.handle.net/20.500.14414/111111">Referencia</a></p>' +
			'<p><a href="https://hdl.handle.net/20.500.14414/222222">Otro</a></p>' +
			"</body></html>"
	);
	assert.strictEqual(extraerHandle(dom.window.document), null);
});

test("extraerHandle devuelve null fuera de páginas de ítem", () => {
	const dom = domDesde("form.html");
	assert.strictEqual(extraerHandle(dom.window.document), null);
});

test("tituloDeItem lee el título real de la página del ítem", () => {
	const dom = domDesde("item.html");
	assert.strictEqual(tituloDeItem(dom.window.document), "Taller de dramatización de títeres");
});

test("tituloDeItem devuelve vacío fuera de páginas de ítem", () => {
	const dom = domDesde("form.html");
	assert.strictEqual(tituloDeItem(dom.window.document), "");
});

test("autoresDeItem lee las metas de cita; sin metas devuelve null", () => {
	const dom = domDesde("item.html");
	assert.deepStrictEqual(autoresDeItem(dom.window.document), [
		"Cerna Vidal Kassiel",
		"Varas Vega Cinthya",
	]);
	const sinAutores = domDesdeHtml(
		'<html><head><meta name="citation_title" content="Tesis"></head><body></body></html>'
	);
	assert.strictEqual(autoresDeItem(sinAutores.window.document), null);
});

test("normalizar quita acentos, mayúsculas y espacios extra", () => {
	assert.strictEqual(normalizar("  Título   del  ÁRBOL "), "titulo del arbol");
});

test("titulosCoinciden tolera acentos y diferencias de caja", () => {
	assert.strictEqual(titulosCoinciden("Título del Árbol", "titulo del arbol"), true);
});

test("titulosCoinciden exige igualdad: la inclusión no basta", () => {
	assert.strictEqual(titulosCoinciden("Título", "Título del trabajo"), false);
});

test("autoresCoinciden compara por conjunto normalizado", () => {
	assert.strictEqual(
		autoresCoinciden(["Cerna Vidal Kassiel", "Varas Vega Cinthya"], [
			"Varas Vega Cinthya",
			"Cerna Vidal Kassiel",
		]),
		true
	);
	assert.strictEqual(autoresCoinciden(["Ana Pérez"], ["Ana Perez"]), true);
	assert.strictEqual(autoresCoinciden(["Ana Pérez"], ["Otra Persona"]), false);
	assert.strictEqual(autoresCoinciden(["Ana Pérez"], []), false);
	assert.strictEqual(autoresCoinciden([], ["Ana Pérez"]), false);
});
