// Tests del ejecutor: aplicar un plan sobre el fixture del DOM real.
// El combobox de derechos se prueba en su modo de fallo visible (el
// listbox vacío → fallo; el operador selecciona a mano como hoy).
//
// Las filas repetibles se concilian con los controles del widget: el
// botón "+" agrega y el botón de quitar elimina. Nunca se borran nodos
// del DOM.

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const VBEjecutor = require(path.join(__dirname, "..", "src", "ejecutor.js"));
const VBMapeador = require(path.join(__dirname, "..", "src", "mapeador.js"));
const { SELECTORES } = require(path.join(__dirname, "..", "src", "compuertas.js"));

function domFormulario() {
	const html = fs.readFileSync(path.join(__dirname, "fixtures", "form.html"), "utf8");
	return new JSDOM(html);
}

function fichaCompleta() {
	return {
		extraidos: [
			{ campo: "dc.title", valor: "Taller de dramatización de títeres", pagina: 1, detectado: true },
			{ campo: "dc.contributor.author", valor: ["Cerna Vidal Kassiel", "Varas Vega Cinthya"], pagina: 1, detectado: true },
			{ campo: "dc.contributor.advisor", valor: "Ms. Ada Lovelace", pagina: 1, detectado: true },
			{ campo: "dc.description.abstract", valor: "Resumen del trabajo.", pagina: 3, detectado: true },
			{ campo: "dc.subject", valor: ["títeres", "lectura"], pagina: 3, detectado: true },
			{ campo: "dc.date.issued", valor: "2026", pagina: null, detectado: true },
		],
		manuales: [
			{ campo: "matricula", valor: ["15185003-20", "10130003-23"] },
			{ campo: "renati.author.dni", valor: ["12345678", "87654321"] },
			{ campo: "renati.advisor.dni", valor: "11222333" },
			{ campo: "renati.advisor.orcid", valor: "0000-0002-1825-0097" },
		],
	};
}

// Dormir inmediato: el combobox no renderiza opciones en el fixture, así
// que el reintento no necesita esperar de verdad.
const dormirRapido = async () => {};

test("el plan llena los campos de texto del formulario", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);

	await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	assert.strictEqual(doc.querySelector(SELECTORES.titulo).value, "Taller de dramatización de títeres");
	assert.strictEqual(doc.querySelector(SELECTORES.asesor).value, "Ms. Ada Lovelace");
	assert.strictEqual(doc.querySelector(SELECTORES.resumen).value, "Resumen del trabajo.");
	assert.strictEqual(doc.querySelector(SELECTORES.anho).value, "2026");
	assert.strictEqual(doc.querySelector(SELECTORES.orcidAsesor).value, "0000-0002-1825-0097");
});

test("las filas repetidas se llenan por índice (autores y palabras)", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);

	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	// El fixture trae UNA fila por campo y sin botón "+": los valores
	// extra quedan pendientes y el resumen lo reporta (fallo visible).
	assert.strictEqual(doc.querySelector(SELECTORES.autores).value, "Cerna Vidal Kassiel");
	assert.ok(resumen.fallidos.includes("autores"));
	assert.ok(resumen.fallidos.includes("palabras clave"));
	assert.ok(resumen.fallidos.includes("derechos de acceso"));
});

test("el QUALDROP elige la opción DNI por sufijo y llena el número", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	const ficha = fichaCompleta();
	ficha.extraidos.find((e) => e.campo === "dc.contributor.author").valor = ["Cerna Vidal Kassiel"];
	ficha.manuales.find((m) => m.campo === "renati.author.dni").valor = ["12345678"];
	ficha.manuales.find((m) => m.campo === "renati.advisor.dni").valor = "11222333";
	const plan = VBMapeador.construirPlan(ficha, SELECTORES);

	await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	const metaAutor = doc.querySelector(SELECTORES.dniAutorMeta);
	assert.strictEqual(metaAutor.value, "0: renati.author.dni");
	assert.strictEqual(doc.querySelector(SELECTORES.dniAutorValor).value, "12345678");
	const metaAsesor = doc.querySelector(SELECTORES.dniAsesorMeta);
	assert.strictEqual(metaAsesor.value, "0: renati.advisor.dni");
	assert.strictEqual(doc.querySelector(SELECTORES.dniAsesorValor).value, "11222333");
});

test("el combobox sin opciones falla visible y RESTAURA el valor anterior", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	doc.querySelector(SELECTORES.derechosInput).value = "Acceso restringido";
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);

	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	assert.ok(resumen.fallidos.includes("derechos de acceso"));
	assert.strictEqual(
		doc.querySelector(SELECTORES.derechosInput).value,
		"Acceso restringido",
		"el fallo del combobox borró el dato anterior del operador"
	);
});

test("el combobox coopera cuando el listbox renderiza la opción", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	// Simular el render de Angular: la opción aparece tras el primer reintento.
	let renderizado = false;
	setTimeout(() => {
		const listbox = doc.querySelector(SELECTORES.derechosListbox);
		const opcion = doc.createElement("button");
		opcion.type = "button"; // dentro del form: sin type sería submit
		opcion.textContent = "Acceso abierto";
		listbox.appendChild(opcion);
		renderizado = true;
	}, 50);

	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, {
		dormir: (ms) => new Promise((r) => setTimeout(r, ms)),
	});

	assert.ok(renderizado);
	assert.ok(resumen.exitosos.includes("derechos de acceso"));
	assert.strictEqual(doc.querySelector(SELECTORES.derechosInput).value, "Acceso abierto");
});

test("operación sobre selector ausente queda como fallida, no explota", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	const plan = {
		operaciones: [
			{ tipo: "texto", campo: "ausente", selector: "input[name=\"no.existe\"]", valor: "x" },
			{ tipo: "filas", campo: "filas ausentes", selector: "input[name=\"tampoco\"]", valores: ["x"] },
			{ tipo: "qualdrop", campo: "qualdrop ausente", selectorMeta: "select[name=\"cero\"]", opcionSufijo: "x", selectorValor: "input[name=\"cero\"]", valores: ["x"] },
		],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });
	assert.deepStrictEqual(resumen.fallidos, ["ausente", "filas ausentes", "qualdrop ausente"]);
});

test("un control deshabilitado no se informa como relleno", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	const input = doc.querySelector(SELECTORES.titulo);
	input.disabled = true;
	const plan = {
		operaciones: [{ tipo: "texto", campo: "título", selector: SELECTORES.titulo, valor: "x" }],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });
	assert.deepStrictEqual(resumen.exitosos, []);
	assert.deepStrictEqual(resumen.fallidos, ["título"]);
});

test("un valor que el control revierte no se informa como relleno", async () => {
	const dom = domFormulario();
	const doc = dom.window.document;
	const input = doc.querySelector(SELECTORES.titulo);
	input.addEventListener("input", () => {
		input.value = "anterior";
	});
	const plan = {
		operaciones: [{ tipo: "texto", campo: "título", selector: SELECTORES.titulo, valor: "nuevo" }],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });
	assert.deepStrictEqual(resumen.fallidos, ["título"]);
});

// ---------------------------------------------------------------------------
// Filas repetibles: el botón "+" real (ds-form-add-more) dentro de #N_array
// ---------------------------------------------------------------------------

function domConFilasRepetibles() {
	// Estructura mínima equivalente al DOM real de "Editar envío":
	// cada campo repetible tiene su contenedor #N_array con la lista de
	// filas y su botón "+".
	const dom = new JSDOM(`<!doctype html><html><body>
		<div id="11_array">
			<div class="cdk-drop-list">
				<div class="cdk-drag form-row"><input type="text" name="dc.contributor.author"></div>
			</div>
			<div class="cdk-drag form-row"><div class="btn-group"><button type="button" class="ds-form-add-more"></button></div></div>
		</div>
		<div id="13_array">
			<div class="cdk-drop-list">
				<div class="cdk-drag form-row">
					<select name="renati.author_QUALDROP_METADATA">
						<option value="0: renati.author.dni">DNI</option>
					</select>
					<input type="text" name="renati.author_QUALDROP_VALUE">
				</div>
			</div>
			<div class="cdk-drag form-row"><div class="btn-group"><button type="button" class="ds-form-add-more"></button></div></div>
		</div>
		<div id="99_array"><button type="button" class="ds-form-add-more" id="ajeno"></button></div>
	</body></html>`);
	const doc = dom.window.document;
	let ajeno = 0;
	doc.getElementById("ajeno").addEventListener("click", () => ajeno++);
	// Los ids reales empiezan con dígito (#11_array): no son válidos como
	// selector CSS, se buscan por atributo.
	doc.querySelectorAll('[id="11_array"], [id="13_array"]').forEach((array) => {
		const lista = array.querySelector(".cdk-drop-list");
		const fila = lista.querySelector(".cdk-drag.form-row");
		array.querySelector(".ds-form-add-more").addEventListener("click", () => {
			lista.appendChild(fila.cloneNode(true));
		});
	});
	return { doc, ajeno: () => ajeno };
}

test("el botón + real agrega filas dentro de su propia array", async () => {
	const { doc, ajeno } = domConFilasRepetibles();
	const plan = {
		operaciones: [
			{ tipo: "filas", campo: "autores", selector: 'input[name="dc.contributor.author"]', valores: ["A", "B", "C"] },
		],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	assert.deepStrictEqual(resumen.exitosos, ["autores"]);
	const valores = Array.from(doc.querySelectorAll('input[name="dc.contributor.author"]')).map(
		(el) => el.value
	);
	assert.deepStrictEqual(valores, ["A", "B", "C"]);
	// El "+" de otro contenedor no se pulsó (scope por #N_array).
	assert.strictEqual(ajeno(), 0);
});

test("autores y DNI crecen en arrays distintas y quedan alineados", async () => {
	const { doc } = domConFilasRepetibles();
	const plan = {
		operaciones: [
			{ tipo: "filas", campo: "autores", selector: 'input[name="dc.contributor.author"]', valores: ["A", "B"] },
			{
				tipo: "qualdrop",
				campo: "DNI del autor",
				selectorMeta: 'select[name="renati.author_QUALDROP_METADATA"]',
				opcionSufijo: "renati.author.dni",
				selectorValor: 'input[name="renati.author_QUALDROP_VALUE"]',
				valores: ["11111111", "22222222"],
			},
		],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	assert.deepStrictEqual(resumen.fallidos, []);
	const metas = Array.from(
		doc.querySelectorAll('select[name="renati.author_QUALDROP_METADATA"]')
	).map((el) => el.value);
	const valores = Array.from(doc.querySelectorAll('input[name="renati.author_QUALDROP_VALUE"]')).map(
		(el) => el.value
	);
	assert.deepStrictEqual(metas, ["0: renati.author.dni", "0: renati.author.dni"]);
	assert.deepStrictEqual(valores, ["11111111", "22222222"]);
});

// ---------------------------------------------------------------------------
// El DOM real: render asíncrono de Angular (revisión PR #71, M4)
// ---------------------------------------------------------------------------

function domFormularioReal() {
	// Fixture con la estructura real (#N_array + ds-form-add-more + botón
	// de quitar) y el render asíncrono de Angular: la fila aparece o se
	// quita DESPUÉS del clic.
	const html = fs.readFileSync(path.join(__dirname, "fixtures", "form-array.html"), "utf8");
	return new JSDOM(html, { runScripts: "dangerously" });
}

const dormirReal = (ms) => new Promise((r) => setTimeout(r, ms));

test("el + que renderiza de forma asíncrona igual agrega la fila", async () => {
	const dom = domFormularioReal();
	const doc = dom.window.document;
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);

	// El render del fixture tarda 50 ms: el ejecutor debe esperarlo.
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirReal });

	assert.ok(resumen.exitosos.includes("autores"), "las filas repetidas no se llenaron");
	const autores = Array.from(doc.querySelectorAll('input[name="dc.contributor.author"]')).map(
		(el) => el.value
	);
	assert.deepStrictEqual(autores, ["Cerna Vidal Kassiel", "Varas Vega Cinthya"]);
	const palabras = Array.from(doc.querySelectorAll('input[name="dc.subject"]')).map(
		(el) => el.value
	);
	assert.deepStrictEqual(palabras, ["títeres", "lectura"]);
});

test("con render asíncrono los DNI de los dos autores quedan alineados", async () => {
	const dom = domFormularioReal();
	const doc = dom.window.document;
	const plan = VBMapeador.construirPlan(fichaCompleta(), SELECTORES);

	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirReal });

	assert.ok(resumen.exitosos.includes("DNI del autor"), "el QUALDROP no se llenó");
	const valores = Array.from(doc.querySelectorAll('input[name="renati.author_QUALDROP_VALUE"]')).map(
		(el) => el.value
	);
	assert.deepStrictEqual(valores, ["12345678", "87654321"]);
	const metas = Array.from(
		doc.querySelectorAll('select[name="renati.author_QUALDROP_METADATA"]')
	).map((el) => el.value);
	assert.deepStrictEqual(metas, ["0: renati.author.dni", "0: renati.author.dni"]);
});

// ---------------------------------------------------------------------------
// Filas sobrantes: se quitan con el control del widget, no borrando nodos
// ---------------------------------------------------------------------------

test("2→1 autores: la fila sobrante se quita con el botón de quitar", async () => {
	const dom = domFormularioReal();
	const doc = dom.window.document;
	// Dos autores de entrada (como un borrador ya iniciado).
	const plan = {
		operaciones: [
			{
				tipo: "filas",
				campo: "autores",
				selector: 'input[name="dc.contributor.author"]',
				valores: ["Cerna Vidal Kassiel"],
			},
		],
		omitidos: [],
	};
	// Se agrega una segunda fila con el control del widget.
	// Los ids reales empiezan con dígito (#11_array): no son válidos como
	// selector CSS, se buscan por atributo.
	const array = doc.querySelector('[id="11_array"]');
	const lista = array.querySelector(".cdk-drop-list");
	const clon = lista.querySelector(".cdk-drag.form-row").cloneNode(true);
	clon.querySelectorAll("[data-vb-agregar],[data-vb-quitar]").forEach((el) => el.remove());
	clon.querySelectorAll("input").forEach((el) => {
		el.value = "Persona Anterior";
	});
	lista.appendChild(clon);
	// El fixture solo agrega filas con su propio botón: se re-renderiza
	// el control de quitar simulando el ngIf del bundle.
	const grupo = lista.querySelectorAll(".cdk-drag.form-row")[1];
	const quitar = doc.createElement("div");
	const botonQuitar = doc.createElement("button");
	botonQuitar.type = "button";
	botonQuitar.setAttribute("aria-label", "Remove");
	quitar.appendChild(botonQuitar);
	grupo.appendChild(quitar);
	botonQuitar.addEventListener("click", () => {
		setTimeout(() => grupo.remove(), 10);
	});

	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirReal });

	assert.deepStrictEqual(resumen.fallidos, [], "no se quitó la fila sobrante");
	const autores = Array.from(doc.querySelectorAll('input[name="dc.contributor.author"]'));
	assert.strictEqual(autores.length, 1, "quedó la fila sobrante en el formulario");
	assert.strictEqual(autores[0].value, "Cerna Vidal Kassiel");
});

test("sin control de quitar la operación falla visible: no se borra el nodo", async () => {
	// Estructura sin el botón de quitar (fila única o versión de UI
	// distinta): el ejecutor no puede conciliar y lo dice.
	const dom = new JSDOM(`<!doctype html><html><body>
		<div id="11_array">
			<div class="cdk-drop-list">
				<div role="group" cdkdrag class="cdk-drag form-row">
					<input type="text" name="dc.contributor.author" value="A">
				</div>
				<div role="group" cdkdrag class="cdk-drag form-row">
					<input type="text" name="dc.contributor.author" value="Persona Anterior">
				</div>
			</div>
		</div>
	</body></html>`);
	const doc = dom.window.document;
	const plan = {
		operaciones: [
			{
				tipo: "filas",
				campo: "autores",
				selector: 'input[name="dc.contributor.author"]',
				valores: ["Cerna Vidal Kassiel"],
			},
		],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	assert.deepStrictEqual(resumen.fallidos, ["autores"]);
	assert.strictEqual(
		doc.querySelectorAll('input[name="dc.contributor.author"]').length,
		2,
		"el ejecutor borró el nodo en vez de usar el control del widget"
	);
});

test("el DNI no se escribe si el tipo de documento no existe", async () => {
	// Sin la opción DNI, el número anterior (pasaporte) queda intacto.
	const dom = new JSDOM(`<!doctype html><html><body>
		<select name="renati.author_QUALDROP_METADATA">
			<option value="1: renati.author.pasaporte">Pasaporte</option>
		</select>
		<input type="text" name="renati.author_QUALDROP_VALUE" value="PASAPORTE-ANTERIOR">
	</body></html>`);
	const doc = dom.window.document;
	const plan = {
		operaciones: [
			{
				tipo: "qualdrop",
				campo: "DNI del autor",
				selectorMeta: 'select[name="renati.author_QUALDROP_METADATA"]',
				opcionSufijo: "renati.author.dni",
				selectorValor: 'input[name="renati.author_QUALDROP_VALUE"]',
				valores: ["11111111"],
			},
		],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	assert.deepStrictEqual(resumen.fallidos, ["DNI del autor"]);
	assert.strictEqual(
		doc.querySelector('input[name="renati.author_QUALDROP_VALUE"]').value,
		"PASAPORTE-ANTERIOR",
		"el número se escribió bajo un tipo que no es DNI"
	);
});

test("un hueco en la lista deja su fila vacía y no desplaza el resto", async () => {
	const dom = new JSDOM(`<!doctype html><html><body>
		<div id="13_array">
			<div class="cdk-drop-list">
				<div role="group" cdkdrag class="cdk-drag form-row">
					<select name="renati.author_QUALDROP_METADATA">
						<option value="0: renati.author.dni">DNI</option>
					</select>
					<input type="text" name="renati.author_QUALDROP_VALUE">
				</div>
				<div role="group" cdkdrag class="cdk-drag form-row">
					<select name="renati.author_QUALDROP_METADATA">
						<option value="0: renati.author.dni">DNI</option>
					</select>
					<input type="text" name="renati.author_QUALDROP_VALUE">
				</div>
			</div>
		</div>
	</body></html>`);
	const doc = dom.window.document;
	const plan = {
		operaciones: [
			{
				tipo: "qualdrop",
				campo: "DNI del autor",
				selectorMeta: 'select[name="renati.author_QUALDROP_METADATA"]',
				opcionSufijo: "renati.author.dni",
				selectorValor: 'input[name="renati.author_QUALDROP_VALUE"]',
				valores: ["", "22222222"],
			},
		],
		omitidos: [],
	};
	const resumen = await VBEjecutor.aplicarPlan(doc, plan, { dormir: dormirRapido });

	assert.deepStrictEqual(resumen.fallidos, []);
	const valores = Array.from(doc.querySelectorAll('input[name="renati.author_QUALDROP_VALUE"]')).map(
		(el) => el.value
	);
	assert.deepStrictEqual(valores, ["", "22222222"]);
});
