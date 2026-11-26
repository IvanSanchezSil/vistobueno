// Invariantes del artefacto instalable (dist/): el header del userscript
// solo confía en localhost y solo matchea el repositorio de la UNT.

const test = require("node:test");
const assert = require("node:assert");
const fs = require("node:fs");
const path = require("node:path");

const dist = fs.readFileSync(
	path.join(__dirname, "..", "dist", "vistobueno-dspace-fill.user.js"),
	"utf8"
);

test("@connect solo autoriza localhost", () => {
	// El header usa espacios de alineación: se normaliza antes de comparar.
	const conectores = (dist.match(/@connect\s+\S+/g) || []).map((l) =>
		l.replace(/\s+/g, " ").trim()
	);
	assert.ok(conectores.length >= 1);
	for (const linea of conectores) {
		assert.strictEqual(linea, "@connect localhost");
	}
});

test("@match solo el repositorio institucional", () => {
	const matches = (dist.match(/@match\s+\S+/g) || []).map((l) =>
		l.replace(/\s+/g, " ").trim()
	);
	assert.deepStrictEqual(matches, ["@match https://repositorio.unitru.edu.pe/*"]);
});

test("el dist contiene los módulos y el wrapper", () => {
	assert.ok(dist.includes("VBCompuertas"));
	assert.ok(dist.includes("VBMapeador"));
	assert.ok(dist.includes("VBEjecutor"));
	assert.ok(dist.includes("VBReloj"));
	assert.ok(dist.includes("VBPanel"));
	assert.ok(dist.includes("ds-form-add-more"));
	assert.ok(dist.includes("UserScript"));
});

test("el dist declara la versión 1.2.5 (protocolo incompatible con 1.1.0)", () => {
	assert.match(dist, /@version\s+1\.2\.5/);
	assert.doesNotMatch(dist, /@version\s+1\.1\.0/);
});

test("el dist usa el protocolo 2 y no migra el estado anterior", () => {
	assert.ok(dist.includes("const PROTOCOLO = 2"), "el wrapper no declara el protocolo 2");
	assert.ok(
		dist.includes("actual.protocolo !== PROTOCOLO"),
		"el wrapper no descarta el estado de otro protocolo"
	);
});
