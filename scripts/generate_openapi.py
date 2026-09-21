"""Genera la especificación OpenAPI 3.x de VistoBueno a partir de la app FastAPI.

Extrae el esquema OpenAPI generado por FastAPI y lo escribe en
docs/openapi_spec.json.

Uso:
    python scripts/generate_openapi.py
    python scripts/generate_openapi.py --output docs/openapi_spec.json
"""
import argparse
import json
import sys

from validator.api import app


def main():
    parser = argparse.ArgumentParser(
        description="Generar especificación OpenAPI de VistoBueno"
    )
    parser.add_argument(
        "--output",
        default="docs/openapi_spec.json",
        help="Ruta de salida (default: docs/openapi_spec.json)",
    )
    args = parser.parse_args()

    schema = app.openapi()

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"OpenAPI spec generada: {args.output}")
    print(f"  Versión: {schema['info']['version']}")
    print(f"  Endpoints: {len(schema['paths'])}")


if __name__ == "__main__":
    main()
