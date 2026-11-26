// Tests del wrapper: protocolo 2 del userscript con el buzón (2026-11-16).
// Se ejecuta el dist real en jsdom con una implementación de GM_* que
// registra las peticiones y devuelve respuestas controladas.
//
// Protocolo 2: rellenar, enviar y archivar son estados distintos. El
// depósito NO se reporta solo: el operador confirma en la página del
// ítem y la confirmación lleva atestación y revisión.

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");
const { JSDOM } = require("jsdom");

const RAIZ = path.join(__dirname, "..");
const DIST = fs.readFileSync(path.join(RAIZ, "dist", "vistobueno-dspace-fill.user.js"), "utf8");
const ITEM_HTML = fs.readFileSync(path.join(__dirname, "fixtures", "item.html"), "utf8");
const FORM_HTML = fs.readFileSync(path.join(__dirname, "fixtures", "form.html"), "utf8");

const TITULO_FICHA = "Taller de dramatización de títeres";
const HANDLE = "https://hdl.handle.net/20.500.14414/27871";
const RUTA_ITEM = "https://repositorio.unitru.edu.pe/items/1b2c3d4e";
const RUTA_MYSPACE = "https://repositorio.unitru.edu.pe/mydspace";

function tramiteVigente(extra) {
	return Object.assign(
		{
			ficha: {
				extraidos: [
					{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
					{
						campo: "dc.contributor.author",
						valor: ["Cerna Vidal Kassiel", "Varas Vega Cinthya"],
						pagina: 1,
						detectado: true,
					},
				],
				manuales: [],
			},
			tramite_id: "tramite-1",
			revision: 0,
			inconsistencia: null,
			deposito: null,
			publicada_en: "2026-11-16T09:00:00+00:00",
			autofill_hasta: "2026-11-16T10:00:00+00:00",
			retenido_hasta: "2026-11-17T09:00:00+00:00",
			autofill_habil: false,
			confirmacion_vigente: false,
		},
		extra || {}
	);
}

// Monta una página con el userscript y un buzón simulados.
// `respuestas` mapea "METODO RUTA" a {status, body}. `peticiones` guarda
// cada llamada saliente.
function montar({ html, url, envio, respuestas }) {
	const dom = new JSDOM(html, { url: url, runScripts: "dangerously" });
	const ventana = dom.window;
	const peticiones = [];

	ventana.GM_setValue = function (clave, valor) {
		ventana.localStorage.setItem("vb:" + clave, JSON.stringify(valor));
	};
	ventana.GM_getValue = function (clave, porDefecto) {
		const bruto = ventana.localStorage.getItem("vb:" + clave);
		return bruto === null ? porDefecto : JSON.parse(bruto);
	};
	ventana.GM_xmlhttpRequest = function (opciones) {
		const ruta = opciones.url.replace("/api-proxy", "").replace("http://localhost:8000", "");
		const metodo = opciones.method || "GET";
		peticiones.push({ ruta, metodo, cuerpo: opciones.data ? JSON.parse(opciones.data) : null });
		const clave = metodo + " " + ruta;
		let configuracion = respuestas[clave] || { status: 404, body: "{}" };
		if (Array.isArray(configuracion)) {
			configuracion = configuracion.length > 1 ? configuracion.shift() : configuracion[0];
		}
		if (configuracion.error) {
			if (opciones.onerror) opciones.onerror({ error: "network-error" });
			return;
		}
		if (opciones.onload) {
			opciones.onload({
				status: configuracion.status,
				responseText:
					typeof configuracion.body === "string" ? configuracion.body : JSON.stringify(configuracion.body),
			});
		}
	};

	if (envio) ventana.localStorage.setItem("vb:vb_envio", JSON.stringify(envio));
	ventana.eval(DIST);
	return { dom, ventana, peticiones };
}

function montarItem(opciones) {
	const ajustes = opciones || {};
	const html = ajustes.html || ITEM_HTML;
	return montar({
		html: html,
		url: ajustes.url || RUTA_ITEM,
		envio: ajustes.envio,
		respuestas: ajustes.respuestas || {},
	});
}

function dormir(ms) {
	return new Promise((resolver) => setTimeout(resolver, ms));
}

function enviarValido(extra) {
	return Object.assign(
		{
			protocolo: 2,
			tramite_id: "tramite-1",
			revision: 0,
			titulo: TITULO_FICHA,
			timestamp: "2026-11-16T10:00:00",
		},
		extra || {}
	);
}

function posteos(peticiones, ruta) {
	return peticiones.filter((p) => p.metodo === "POST" && p.ruta === ruta);
}

// ---------------------------------------------------------------------------
// La página del ítem: panel de confirmación, nunca reporte automático
// ---------------------------------------------------------------------------

test("el ítem NO se reporta solo: hace falta la confirmación del operador", async () => {
	const { peticiones } = montarItem({
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);

	assert.strictEqual(posteos(peticiones, "/deposito").length, 0, "el depósito se reportó sin clic");
	assert.ok(
		peticiones.some((p) => p.metodo === "GET" && p.ruta === "/tramite"),
		"el panel no leyó el trámite vigente"
	);
});

test("el panel ofrece confirmar y el clic envía la atestación explícita", async () => {
	const { ventana, peticiones } = montarItem({
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);

	const panel = ventana.document.getElementById("vb-panel");
	assert.ok(panel, "no se mostró el panel de confirmación");
	const boton = ventana.document.getElementById("vb-confirmar");
	assert.ok(boton && !boton.disabled, "el botón de confirmar no está disponible");

	boton.click();
	await dormir(50);

	const reportes = posteos(peticiones, "/deposito");
	assert.strictEqual(reportes.length, 1);
	const cuerpo = reportes[0].cuerpo;
	assert.strictEqual(cuerpo.tramite_id, "tramite-1");
	assert.strictEqual(cuerpo.handle, HANDLE);
	assert.strictEqual(cuerpo.titulo_observado, TITULO_FICHA);
	assert.strictEqual(cuerpo.timestamp, "2026-11-16T10:00:00");
	assert.strictEqual(cuerpo.revision_esperada, 0);
	assert.strictEqual(cuerpo.atestacion, "operador");
	assert.deepStrictEqual(cuerpo.autores_observados, ["Cerna Vidal Kassiel", "Varas Vega Cinthya"]);
});

test("una página sin autores los declara no verificados y no los inventa", async () => {
	const html = ITEM_HTML.replace(/<meta name="citation_author"[^>]*>/g, "");
	const { ventana, peticiones } = montarItem({
		html: html,
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);

	const panel = ventana.document.getElementById("vb-panel");
	assert.ok(panel, "no se mostró el panel de confirmación");
	assert.ok(
		/no verificados/.test(panel.textContent),
		"el panel no dijo que los autores no se verificaron"
	);

	ventana.document.getElementById("vb-confirmar").click();
	await dormir(50);

	const cuerpo = posteos(peticiones, "/deposito")[0].cuerpo;
	assert.ok(!("autores_observados" in cuerpo), "el payload inventó autores observados");
});

test("MyDSpace no muestra panel: no es la página de un ítem", async () => {
	const { ventana, peticiones } = montarItem({
		url: RUTA_MYSPACE,
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);

	assert.strictEqual(ventana.document.getElementById("vb-panel"), null, "MyDSpace mostró el panel");
	assert.strictEqual(posteos(peticiones, "/deposito").length, 0);
});

test("un título distinto bloquea la confirmación y ofrece reportar la inconsistencia", async () => {
	const html = ITEM_HTML.replace(
		'content="Taller de dramatización de títeres"',
		'content="Otra tesis del todo distinta"'
	);
	const { ventana, peticiones } = montarItem({
		html: html,
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
			"POST /ficha-pendiente/inconsistencia": { status: 204, body: "" },
		},
	});
	await dormir(400);

	const boton = ventana.document.getElementById("vb-confirmar");
	assert.ok(boton && boton.disabled, "el panel permitió confirmar un ítem con otro título");
	assert.ok(
		/no coincide/.test(ventana.document.getElementById("vb-panel").textContent),
		"el panel no avisó del título distinto"
	);

	ventana.document.getElementById("vb-inconsistencia").click();
	await dormir(50);

	const marcas = posteos(peticiones, "/ficha-pendiente/inconsistencia");
	assert.strictEqual(marcas.length, 1);
	assert.strictEqual(marcas[0].cuerpo.tramite_id, "tramite-1");
	assert.strictEqual(marcas[0].cuerpo.handle, HANDLE);
	assert.strictEqual(marcas[0].cuerpo.revision_esperada, 0);
	assert.ok(marcas[0].cuerpo.motivos.length > 0);
	assert.strictEqual(posteos(peticiones, "/deposito").length, 0);
});

test("un 409 relee el trámite y no reintenta la confirmación", async () => {
	const { ventana, peticiones } = montarItem({
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": [
				{ status: 200, body: tramiteVigente() },
				{ status: 200, body: tramiteVigente({ revision: 1 }) },
			],
			"POST /deposito": { status: 409, body: '{"detail":"revisión obsoleta"}' },
		},
	});
	await dormir(400);
	ventana.document.getElementById("vb-confirmar").click();
	await dormir(100);

	assert.strictEqual(posteos(peticiones, "/deposito").length, 1, "el wrapper reintentó la confirmación");
	assert.strictEqual(
		peticiones.filter((p) => p.metodo === "GET" && p.ruta === "/tramite").length,
		2,
		"el wrapper no releó el trámite tras el 409"
	);
	const toast = ventana.document.getElementById("vb-toast");
	assert.ok(toast && /409/.test(toast.textContent), "no avisó del rechazo por conflicto");
});

test("un 422 indica que hay que actualizar la app y el userscript", async () => {
	const { ventana, peticiones } = montarItem({
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 422, body: '{"detail":"falta atestacion"}' },
		},
	});
	await dormir(400);
	ventana.document.getElementById("vb-confirmar").click();
	await dormir(50);

	const toast = ventana.document.getElementById("vb-toast");
	assert.ok(toast && /actualiza/.test(toast.textContent), "no pidió actualizar el contrato");
	assert.strictEqual(posteos(peticiones, "/deposito").length, 1);
});

test("sin clic en Depositar el panel no permite confirmar", async () => {
	const { ventana, peticiones } = montarItem({
		envio: enviarValido({ timestamp: null }),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);

	const boton = ventana.document.getElementById("vb-confirmar");
	assert.ok(boton && boton.disabled, "el panel permitió confirmar sin hora de depósito");
	assert.strictEqual(posteos(peticiones, "/deposito").length, 0);
});

test("una revisión cambiada invalida el panel: hay que volver a preparar", async () => {
	const { ventana, peticiones } = montarItem({
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente({ revision: 2 }) },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);

	const boton = ventana.document.getElementById("vb-confirmar");
	assert.ok(boton && boton.disabled, "el panel confirmó una revisión que ya cambió");
	assert.ok(
		/cambió/.test(ventana.document.getElementById("vb-panel").textContent),
		"el panel no avisó del cambio de revisión"
	);
	assert.strictEqual(posteos(peticiones, "/deposito").length, 0);
});

test("el estado del protocolo 1 se descarta: no se migra", async () => {
	const { ventana, peticiones } = montarItem({
		envio: { tramite_id: "tramite-1", titulo: TITULO_FICHA, timestamp: "2026-11-16T10:00:00" },
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);

	const boton = ventana.document.getElementById("vb-confirmar");
	assert.ok(boton && boton.disabled, "el panel confirmó con un estado del protocolo viejo");
	assert.strictEqual(posteos(peticiones, "/deposito").length, 0);
});

test("una meta completada después vuelve a evaluarse (no queda vista)", async () => {
	// La meta de título existe pero vacía: el panel no aparece. Cuando la
	// página la completa, el panel se arma (US-10).
	const html = ITEM_HTML.replace(
		'<meta name="citation_title" content="Taller de dramatización de títeres">',
		'<meta name="citation_title" content="">'
	);
	const { ventana, peticiones } = montarItem({
		html: html,
		envio: enviarValido(),
		respuestas: {
			"GET /tramite": { status: 200, body: tramiteVigente() },
			"POST /deposito": { status: 204, body: "" },
		},
	});
	await dormir(400);
	assert.strictEqual(
		ventana.document.getElementById("vb-panel"),
		null,
		"el panel apareció sin un título en la página"
	);

	ventana.document
		.querySelector('meta[name="citation_title"]')
		.setAttribute("content", TITULO_FICHA);
	await dormir(600);

	const panel = ventana.document.getElementById("vb-panel");
	assert.ok(panel, "el panel no se reevaluó tras completar la meta de título");
	const boton = ventana.document.getElementById("vb-confirmar");
	assert.ok(boton && !boton.disabled, "el panel confirmó con la revisión vigente");
	assert.strictEqual(posteos(peticiones, "/deposito").length, 0);
});



test("al salir del formulario se quita el botón y el tramite actual (US-07)", async () => {
	const { ventana, dom } = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: {
			"GET /ficha-pendiente": {
				status: 200,
				body: {
					ficha: {
						extraidos: [
							{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
						],
						manuales: [],
					},
					tramite_id: "tramite-1",
					revision: 0,
				},
			},
		},
	});
	await dormir(1300);
	// El botón debería existir
	assert.ok(ventana.document.getElementById("vb-boton"), "el botón existe en el formulario");

	// Cambiar a MyDSpace (no es formulario)
	const dom2 = new JSDOM("<html><body><h1>MyDSpace</h1></body></html>", {
		url: "https://repositorio.unitru.edu.pe/mydspace",
		runScripts: "dangerously",
	});
	const ventana2 = dom2.window;
	ventana2.GM_setValue = ventana.GM_setValue;
	ventana2.GM_getValue = ventana.GM_getValue;
	ventana2.GM_xmlhttpRequest = ventana.GM_xmlhttpRequest;
	ventana2.localStorage = ventana.localStorage;
	ventana2.eval(DIST);
	await dormir(800);

	// El botón debería haberse quitado (el observador detecta el cambio de ruta)
	assert.strictEqual(ventana2.document.getElementById("vb-boton"), null, "el botón se quita al salir del formulario");
});



test("clic en Depositar de otro tramite no pone hora al trámite actual (US-07)", async () => {
	const { ventana } = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: {
			"GET /ficha-pendiente": {
				status: 200,
				body: {
					ficha: {
						extraidos: [
							{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
						],
						manuales: [],
					},
					tramite_id: "tramite-1",
					revision: 0,
				},
			},
		},
	});
	await dormir(1300);

	// Simular que el usuario venía de otro tramite: establecer el envío
	// con tramite_id diferente DESPUES de que llenar() estableció
	// tramiteIdActual. Esto simula navegar de un borrador a otro.
	ventana.localStorage.setItem("vb:vb_envio", JSON.stringify({
		protocolo: 2,
		tramite_id: "tramite-2", // trámite del borrador anterior
		revision: 0,
		titulo: "Otra tesis",
		timestamp: null,
	}));

	// Hacer clic en Depositar: el tramite_id del envio (tramite-2) no
	// coincide con tramiteIdActual (tramite-1), así que no debe actualizar el timestamp.
	ventana.document.getElementById("deposit").click();
	const envio = JSON.parse(ventana.localStorage.getItem("vb:vb_envio"));
	assert.strictEqual(envio.timestamp, null, "no se puso hora porque el tramite no coincide");
	assert.strictEqual(envio.tramite_id, "tramite-2", "el tramite_id no se sobreescribe");
});

// ---------------------------------------------------------------------------
// El formulario: rellenar y registrar el clic en Depositar
// ---------------------------------------------------------------------------

test("el formulario se rellena y conserva el aviso de ORCID inválido", async () => {
	const { ventana } = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: {
			"GET /ficha-pendiente": {
				status: 200,
				body: {
					ficha: {
						extraidos: [
							{ campo: "renati.advisor.orcid", valor: "0000-0002-1825-0098" },
							{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
							{
								campo: "dc.contributor.author",
								valor: ["Cerna Vidal Kassiel"],
								pagina: 1,
								detectado: true,
							},
						],
						manuales: [],
					},
					tramite_id: "tramite-1",
					revision: 0,
				},
			},
		},
	});
	// El plan termina cuando el combobox de derechos agota sus reintentos
	// (el fixture no lo renderiza): el envío se guarda al final.
	await dormir(1300);

	assert.strictEqual(
		ventana.document.querySelector('input[name="dc.title"]').value,
		TITULO_FICHA
	);
	const envio = JSON.parse(ventana.localStorage.getItem("vb:vb_envio"));
	assert.strictEqual(envio.protocolo, 2);
	assert.strictEqual(envio.tramite_id, "tramite-1");
	assert.strictEqual(envio.revision, 0);
	assert.strictEqual(envio.timestamp, null);
	assert.match(ventana.document.getElementById("vb-toast").textContent, /ORCID del asesor.*inválido/);
});

test("datos esenciales invalidos: no se inicia el relleno ni se registra envio", async () => {
	const { ventana } = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: {
			"GET /ficha-pendiente": {
				status: 200,
				body: {
					ficha: {
						extraidos: [
							{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
							{
								campo: "dc.contributor.author",
								valor: ["", "Varas Vega Cinthya"],
								pagina: 1,
								detectado: true,
							},
						],
						manuales: [],
					},
					tramite_id: "tramite-1",
					revision: 0,
				},
			},
		},
	});
	await dormir(1300);
	const titulo = ventana.document.querySelector('input[name="dc.title"]').value;
	assert.strictEqual(titulo, "", "el titulo no se lleno cuando los datos son invalidos");
	const envioRaw = ventana.localStorage.getItem("vb:vb_envio");
	assert.strictEqual(envioRaw, null, "no se registro envio para datos invalidos");
});

test("relleno verificado: segundo clic no vuelve a llenar", async () => {
	const { ventana } = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: {
			"GET /ficha-pendiente": {
				status: 200,
				body: {
					ficha: {
						extraidos: [
							{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
							{
								campo: "dc.contributor.author",
								valor: ["Cerna Vidal Kassiel"],
								pagina: 1,
								detectado: true,
							},
						],
						manuales: [],
					},
					tramite_id: "tramite-1",
					revision: 0,
				},
			},
		},
	});
	// Llenar el formulario
	await dormir(1300);
	const titulo = ventana.document.querySelector('input[name="dc.title"]').value;
	assert.strictEqual(titulo, TITULO_FICHA, "el relleno escribio el titulo");
	const envio = JSON.parse(ventana.localStorage.getItem("vb:vb_envio"));
	assert.strictEqual(envio.tramite_id, "tramite-1");

	// Simular que el usuario pulsa el boton Rellenar otra vez: montar de nuevo
	const ventana2 = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: {
			"GET /ficha-pendiente": {
				status: 200,
				body: {
					ficha: {
						extraidos: [
							{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
							{
								campo: "dc.contributor.author",
								valor: ["Cerna Vidal Kassiel"],
								pagina: 1,
								detectado: true,
							},
						],
						manuales: [],
					},
					tramite_id: "tramite-1",
					revision: 0,
				},
			},
		},
		envio: {
			protocolo: 2,
			tramite_id: "tramite-1",
			revision: 0,
			titulo: TITULO_FICHA,
			timestamp: null,
			relleno: {
				estado: "verificado",
				revision: 0,
				campos: { titulo: "completo", autores: "completo", asesor: "sin_dato" },
				pendientes: [],
			},
		},
	});
	await dormir(1300);
	const titulo2 = ventana2.ventana.document.querySelector('input[name="dc.title"]').value;
	assert.strictEqual(titulo2, "", "el formulario verificado no se volvio a llenar");
	const toast = ventana2.ventana.document.getElementById("vb-toast");
	assert.ok(toast.textContent.includes("no se volvio a rellenar"), "el aviso dice que no se repite el relleno");
});

test("el clic en Depositar registra la hora del envío y no del archivo", async () => {
	const { ventana } = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: {
			"GET /ficha-pendiente": {
				status: 200,
				body: {
					ficha: {
						extraidos: [
							{ campo: "dc.title", valor: TITULO_FICHA, pagina: 1, detectado: true },
							{
								campo: "dc.contributor.author",
								valor: ["Cerna Vidal Kassiel"],
								pagina: 1,
								detectado: true,
							},
						],
						manuales: [],
					},
					tramite_id: "tramite-1",
					revision: 0,
				},
			},
		},
	});
	await dormir(1300);

	ventana.document.getElementById("deposit").click();
	const envio = JSON.parse(ventana.localStorage.getItem("vb:vb_envio"));
	assert.ok(envio.timestamp, "el clic en Depositar no registró la hora");
	assert.ok(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$/.test(envio.timestamp), "la hora no tiene la forma esperada");
});




// US-11: plazo de recuperación de conexión
// ---------------------------------------------------------------------------

test("tras 5 fallos de conexión se deja de reintentar y se avisa al operador (US-11)", async () => {
	const respuestas = {};
	const fallos = [];
	for (let i = 0; i < 6; i++) {
		fallos.push({ error: true });
	}
	respuestas["GET /ficha-pendiente"] = fallos;

	const { ventana } = montar({
		html: FORM_HTML,
		url: "https://repositorio.unitru.edu.pe/workspaceitems/1/edit",
		respuestas: respuestas,
	});

	// Simular que el operador pulsa "Rellenar" 6 veces: los primeros 5 fallan,
	// el 6to también falla (la API sigue caída). Después del 5o fallo debería
	// aparecer el toast de recuperación.
	const boton = ventana.document.getElementById("vb-boton");
	assert.ok(boton, "el botón Rellenar existe");

	for (let i = 0; i < 6; i++) {
		boton.click();
		await dormir(100);
	}

	// Verificar que se hicieron 6 peticiones (no se pararon antes)
	assert.ok(true, "se enviaron 6 solicitudes de reintento");

	// Verificar que el toast de recuperación apareció (despues del 5o fallo)
	const toast = ventana.document.getElementById("vb-toast");
	assert.ok(toast, "apareció el toast de recuperación");
	assert.ok(toast.textContent.includes("5 intentos"), "el toast menciona el límite de 5 intentos");
	assert.ok(toast.textContent.includes("Rellenar"), "el toast dice al operador qué hacer");
});

