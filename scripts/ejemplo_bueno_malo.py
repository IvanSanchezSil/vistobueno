#!/usr/bin/env python3
"""Genera un par de ejemplo (documento bueno / documento malo) y sus respuestas.

El documento bueno sale del factory determinista (`tests/docx_factory.py`):
cumple todas las reglas aplicables. El documento malo es el mismo documento
con un conjunto fijo de desvíos mínimos, uno por regla.

Las respuestas se piden al endpoint real (`POST /validar`) con el cliente de
prueba de FastAPI: es exactamente el JSON que devuelve la API, sin levantar
un servidor ni usar documentos reales.

Uso:
    python scripts/ejemplo_bueno_malo.py
    python scripts/ejemplo_bueno_malo.py --salida /ruta/de/salida

Salida (por defecto `docs/ejemplos/`):
    doc_bueno.docx, respuesta_doc_bueno.json
    doc_malo.docx,  respuesta_doc_malo.json
"""

import argparse
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tests"))

from docx_factory import aplicar_mutacion, compilar_docx, configuracion_base  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from validator.api import app  # noqa: E402

# El peer y el Host van en loopback: la API solo se sirve desde la máquina
# local (AUD-09) y el `TestClient` por defecto usa "testserver".
CLIENTE = TestClient(app, client=("127.0.0.1", 50000), base_url="http://127.0.0.1")

# Desvíos del documento malo: uno por regla, visibles y fáciles de explicar.
MUTACIONES = [
    "margen_izquierdo",
    "fuente_principal",
    "tamano_cuerpo",
    "interlineado",
    "sangria_parrafo",
]

TIPO_DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def validar(docx: Path) -> dict:
    """Sube el DOCX a POST /validar y devuelve la respuesta JSON."""
    with docx.open("rb") as archivo:
        respuesta = CLIENTE.post(
            "/validar",
            files={"archivo": (docx.name, archivo, TIPO_DOCX)},
        )
    respuesta.raise_for_status()
    return respuesta.json()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", default=str(RAIZ / "docs" / "ejemplos"))
    args = parser.parse_args()

    salida = Path(args.salida)
    salida.mkdir(parents=True, exist_ok=True)

    bueno_cfg = configuracion_base()
    malo_cfg = bueno_cfg
    for rule_id in MUTACIONES:
        malo_cfg = aplicar_mutacion(rule_id, malo_cfg)

    for nombre, cfg in (("doc_bueno", bueno_cfg), ("doc_malo", malo_cfg)):
        temporal = Path(compilar_docx(cfg))
        destino = salida / f"{nombre}.docx"
        destino.write_bytes(temporal.read_bytes())
        temporal.unlink(missing_ok=True)

        datos = validar(destino)
        (salida / f"respuesta_{nombre}.json").write_text(
            json.dumps(datos, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        resumen = datos["resumen"]
        print(
            f"{destino.name}: semáforo {datos['semaforo']}, "
            f"{resumen['fallidos_error']} error(es), "
            f"{resumen['fallidos_warning']} warning(s), "
            f"{resumen['total_evaluadas']} reglas evaluadas"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
