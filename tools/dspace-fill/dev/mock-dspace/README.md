# Ensayo general (mock-dspace)

Simulación local del flujo de depósito para ejercitar el userscript **sin
Tampermonkey y sin tocar la instancia real**. El mock imita el DOM del
formulario oficial (mismos `name`/`id`); la lógica Angular se reduce al
mínimo indispensable (filas repetibles, combobox, botón Depositar).

Qué SÍ cubre: la lógica del userscript (compuertas, mapeador, ejecutor,
buzón, timestamp, handle) y la mecánica DOM de relleno. Qué NO cubre: los
comportamientos del Angular real — esos quedan para el piloto con la
instancia real (borrador descartable).

## Requisitos

- VistoBueno corriendo: `nix run .#serve -- validator.api:app --port 8000`
- El mock: `nix run .#mock-dspace` (puerto 8080)
- Un DOCX de prueba (la plantilla de `recursos/` o el doc bueno del factory)
- El dist construido: `cd tools/dspace-fill && npm run build` (o `npm test`)

## Checklist (10 pasos)

1. Abre `http://127.0.0.1:8080/` — debe mostrar el índice del mock.
2. Valida el DOCX contra la API real y guarda la ficha de la respuesta:
   `curl -s -F "archivo=@plantilla.docx" http://127.0.0.1:8000/validar | python3 -c "import json,sys; r=json.load(sys.stdin); print(json.dumps(r['ficha_deposito'], ensure_ascii=False))" > ficha.json`
   (la ficha solo viaja si el semáforo es verde).
3. Llena los manuales en `ficha.json` (matrícula, DNIs, ORCID) y publícala:
   `curl -s -X POST -H "Content-Type: application/json" -d @ficha.json http://127.0.0.1:8000/ficha-pendiente -o /dev/null -w "%{http_code}\n"` → 204.
4. Abre `http://127.0.0.1:8080/mock/submit` — el formulario debe
   auto-rellenarse y aparecer el toast con el resumen (llenos / a mano /
   sin dato) y el botón flotante con el título.
5. Verifica los campos: título, autores, asesor, resumen, palabras clave,
   año, DNI (tipo + número), ORCID.
6. Verifica el combobox: "Acceso abierto" debe quedar seleccionado (el
   fix del bug dc.rights).
7. Con dos autores: el botón "+ Agregar autor" debe haber creado la fila
   extra y el segundo nombre debe estar lleno.
8. Pulsa **Depositar** → navega al ítem del mock → debe aparecer el toast
   "Handle enviado a VistoBueno ✓".
9. Verifica el buzón: `curl -s http://127.0.0.1:8000/deposito` → JSON con
   el handle, el título y el timestamp del clic en Depositar.
10. Genera el papeleo con esa respuesta: `POST /fila-registro` y
    `POST /constancia` (una descarga por autor) con la ficha + handle +
    timestamp de ese JSON.

## Notas

- El buzón viaja por el proxy `/api-proxy/*` (same-origin): la API real
  mantiene su invariante sin-CORS; solo Tampermonkey (producción) habla
  directo con `http://localhost:8000`.
- Reiniciar la API vacía el buzón (memoria del proceso): re-publica la
  ficha (paso 3) y repite.
- Falla visible: si algo no se llena, el toast lo nombra en "a mano" —
  ese es el comportamiento correcto, no un bug.
