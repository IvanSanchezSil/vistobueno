// ==UserScript==
// @name         VistoBueno — rellenador del formulario de depósito UNT
// @namespace    vistobueno
// @version      1.2.5
// @description  Pre-llena el formulario oficial de depósito de DSpace (repositorio UNT) con la ficha de VistoBueno, registra el momento del clic en Depositar y pide al operador que confirme el ítem archivado. Protocolo 2: el archivo solo se registra con atestación explícita. Ver docs/CONTRATO_API.md.
// @match        https://repositorio.unitru.edu.pe/*
// @run-at       document-idle
// @grant        GM_xmlhttpRequest
// @grant        GM_setValue
// @grant        GM_getValue
// @connect      localhost
// @updateURL    https://raw.githubusercontent.com/retblast/vistobueno/master/tools/dspace-fill/dist/vistobueno-dspace-fill.user.js
// @downloadURL  https://raw.githubusercontent.com/retblast/vistobueno/master/tools/dspace-fill/dist/vistobueno-dspace-fill.user.js
// ==/UserScript==
