// Tickets de operación: evita que un callback antiguo reemplace el
// estado más nuevo cuando hay varias operaciones en vuelo (US-06).

const test = require("node:test");
const assert = require("node:assert");
const VBTicket = require("../src/ticket.js");

test("cada ticket es mayor que el anterior", () => {
	const a = VBTicket.nuevoTicket();
	const b = VBTicket.nuevoTicket();
	assert.ok(b > a, "los tickets aumentan");
});

test("ticket vigente se valida correctamente", () => {
	const t1 = VBTicket.nuevoTicket();
	const t2 = VBTicket.nuevoTicket();
	assert.strictEqual(t1, t1);
	assert.notStrictEqual(t1, t2);
});
