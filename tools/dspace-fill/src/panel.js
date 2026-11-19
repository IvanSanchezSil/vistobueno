// Panel de confirmación del depósito: la ÚNICA vía para registrar el
// archivo en VistoBueno. El panel no escribe nada por su cuenta: el
// operador lee la evidencia y pulsa el botón; el wrapper hace la
// escritura con la atestación explícita.
//
// Todo el texto se inserta con textContent: el título o el handle del
// ítem son datos externos y no pueden interpretarse como HTML.

const VBPanel = (() => {
	const ID_PANEL = "vb-panel";

	function _texto(doc, etiqueta, contenido, estilos) {
		const el = doc.createElement(etiqueta);
		el.textContent = contenido;
		if (estilos) el.style.cssText = estilos;
		return el;
	}

	function quitar(doc) {
		const existente = doc.getElementById(ID_PANEL);
		if (existente && existente.parentNode) existente.parentNode.removeChild(existente);
	}

	function montar(doc, datos) {
		quitar(doc);
		const panel = doc.createElement("div");
		panel.id = ID_PANEL;
		panel.style.cssText =
			"position:fixed;top:16px;right:16px;z-index:99999;background:#fff;color:#1a1a2e;" +
			"border:1px solid #b8c4d6;border-radius:8px;padding:14px 16px;font:13px sans-serif;" +
			"max-width:440px;box-shadow:0 2px 10px rgba(0,0,0,.25);text-align:left";

		panel.appendChild(
			_texto(doc, "strong", "Confirmar el depósito archivado", "display:block;margin-bottom:8px")
		);
		panel.appendChild(_texto(doc, "p", "Ítem: " + (datos.tituloItem || "(sin título)")));
		panel.appendChild(_texto(doc, "p", "Handle: " + (datos.handle || "(sin handle)")));
		panel.appendChild(
			_texto(
				doc,
				"p",
				"Autores: " +
					(datos.autoresItem && datos.autoresItem.length
						? datos.autoresItem.join("; ")
						: "no verificados (la página no los publica)")
			)
		);
		panel.appendChild(
			_texto(
				doc,
				"p",
				"Hora del clic en Depositar: " + (datos.timestamp || "no registrada")
			)
		);
		panel.appendChild(
			_texto(
				doc,
				"p",
				"Trámite: " + (datos.tramiteId || "(sin trámite)") + " (revisión " + datos.revision + ")"
			)
		);

		(datos.avisos || []).forEach(function (aviso) {
			panel.appendChild(
				_texto(doc, "p", aviso, "margin:6px 0 0 0;color:#8a1f11;font-weight:600")
			);
		});

		const acciones = doc.createElement("div");
		acciones.style.cssText = "display:flex;gap:8px;flex-wrap:wrap;margin-top:12px";

		const botonConfirmar = doc.createElement("button");
		botonConfirmar.id = "vb-confirmar";
		botonConfirmar.type = "button";
		botonConfirmar.textContent = "Confirmar depósito archivado";
		botonConfirmar.disabled = !datos.puedeConfirmar;
		botonConfirmar.style.cssText =
			"background:#28a745;color:#fff;border:none;padding:8px 12px;border-radius:6px;" +
			"font:13px sans-serif;cursor:pointer";
		if (!datos.puedeConfirmar) botonConfirmar.style.opacity = "0.55";
		botonConfirmar.addEventListener("click", function () {
			if (datos.alConfirmar) datos.alConfirmar();
		});
		acciones.appendChild(botonConfirmar);

		if (datos.alMarcarInconsistencia) {
			const botonInconsistencia = doc.createElement("button");
			botonInconsistencia.id = "vb-inconsistencia";
			botonInconsistencia.type = "button";
			botonInconsistencia.textContent = "Reportar inconsistencia";
			botonInconsistencia.style.cssText =
				"background:#fff;color:#8a1f11;border:1px solid #d9a6a0;padding:8px 12px;" +
				"border-radius:6px;font:13px sans-serif;cursor:pointer";
			botonInconsistencia.addEventListener("click", function () {
				if (datos.alMarcarInconsistencia) datos.alMarcarInconsistencia();
			});
			acciones.appendChild(botonInconsistencia);
		}

		const botonCerrar = doc.createElement("button");
		botonCerrar.id = "vb-cerrar";
		botonCerrar.type = "button";
		botonCerrar.textContent = "Cerrar";
		botonCerrar.style.cssText =
			"background:#fff;color:#1a1a2e;border:1px solid #b8c4d6;padding:8px 12px;" +
			"border-radius:6px;font:13px sans-serif;cursor:pointer";
		botonCerrar.addEventListener("click", function () {
			quitar(doc);
			if (datos.alCerrar) datos.alCerrar();
		});
		acciones.appendChild(botonCerrar);

		panel.appendChild(acciones);
		doc.body.appendChild(panel);
		return panel;
	}

	return { montar, quitar, ID_PANEL };
})();

if (typeof module !== "undefined" && module.exports) {
	module.exports = VBPanel;
}
