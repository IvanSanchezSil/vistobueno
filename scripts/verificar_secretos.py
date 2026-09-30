#!/usr/bin/env python3
"""Verificador de filtración de credenciales SMTP (capa 2 y 3).

Bloquea cualquier asignación con valor REAL de VISTOBUENO_SMTP_PASSWORD y
cualquier archivo .env / .env.* presente en el árbol. Se usa en dos capas:

- Hook de pre-commit (``.pre-commit-config.yaml``): recibe los archivos
  staged como argumentos y falla el commit si detecta una violación.
- CI (``.github/workflows/ci.yml``): se ejecuta con ``--all`` sobre todo el
  árbol de trabajo, cubriendo el caso ``git commit --no-verify``.

Valores permitidos (placeholders documentales/dummy): ``dummy``, ``prueba``,
``test``, ``changeme``, ``<valor>`` y autorreferencias de variables (``$...``).

El propio verificador y sus tests están excluidos: contienen el patrón
deliberadamente (para probarlo) pero nunca un valor real.

Uso:
    python3 scripts/verificar_secretos.py ARCHIVO...   # modo pre-commit
    python3 scripts/verificar_secretos.py --all        # modo CI/árbol completo

Salida:
    0 = sin violaciones; 1 = violación detectada (con detalle en stdout).
"""

import re
import sys
from pathlib import Path

NOMBRE_SECRETO = "VISTOBUENO_SMTP_PASSWORD"

# Asignación del secret con un valor no vacío: VAR=valor, VAR: valor
PATRON_ASIGNACION = re.compile(
    rf"{NOMBRE_SECRETO}\s*[=:]\s*(\S+)",
)

# Valores que NO son secretos reales (placeholders de docs/tests/scripts).
PLACEHOLDERS = {"dummy", "prueba", "test", "changeme", "<valor>"}

# Archivos que contienen el patrón deliberadamente (el verificador y sus
# tests); comparación por ruta relativa POSIX desde la raíz del repo.
EXCLUIDOS = {
    "scripts/verificar_secretos.py",
    "tests/test_verificar_secretos.py",
}

# Directorios nunca escaneados en modo --all.
DIRS_EXCLUIDOS = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", "result"}

MSG_VIOLACION = (
    "VIOLACIÓN: {ruta}:{linea}: asignación de {var} con valor real "
    "(use una variable de entorno del proceso, nunca un archivo)"
)
MSG_ENV = (
    "VIOLACIÓN: {ruta}: archivo .env en el repo "
    "(la configuración vive en el entorno, no en archivos)"
)


def _valor_permitido(valor: str) -> bool:
    """True si el valor capturado es placeholder o autorreferencia ($VAR)."""
    limpio = valor.strip().strip("\"'")
    if limpio.startswith("$"):
        # Autorreferencia de variable de entorno (${VAR}, $VAR)
        return True
    return limpio.lower() in PLACEHOLDERS


def _es_archivo_env(ruta: Path) -> bool:
    """True para archivos .env o .env.<algo> excepto .env.example.

    ``.env.example`` es una plantilla documental inerte (convención Vite, ver
    ``frontend/.env.example``) y no la carga ninguna herramienta: se permite
    como archivo, pero su CONTENIDO se escanea igual que cualquier otro.
    """
    if ruta.name == ".env.example":
        return False
    return ruta.name == ".env" or ruta.name.startswith(".env.")


def verificar_archivo(ruta: Path) -> list[str]:
    """Devuelve la lista de violaciones (mensajes) encontradas en un archivo.

    Un archivo .env/.env.* es violación por sí mismo, sin importar su
    contenido (cubre el caso de credenciales en formato libre).
    """
    if _es_archivo_env(ruta):
        return [MSG_ENV.format(ruta=ruta)]

    violaciones: list[str] = []
    try:
        texto = ruta.read_text(encoding="utf-8", errors="replace")
    except OSError, UnicodeDecodeError:
        # Legibilidad ante archivos raros: no se puede verificar y no se
        # bloquea; la capa de asignaciones es la protección principal.
        return violaciones

    for n, linea in enumerate(texto.splitlines(), start=1):
        m = PATRON_ASIGNACION.search(linea)
        if m and not _valor_permitido(m.group(1)):
            # No se imprime el valor: nunca repetir un posible secreto en logs.
            violaciones.append(MSG_VIOLACION.format(ruta=ruta, linea=n, var=NOMBRE_SECRETO))
    return violaciones


def verificar_arbol(raiz: Path) -> list[str]:
    """Escanea recursivamente el árbol (modo --all), respetando exclusiones."""
    violaciones: list[str] = []
    for ruta in sorted(raiz.rglob("*")):
        if not ruta.is_file():
            continue
        partes = set(ruta.relative_to(raiz).parts)
        if partes & DIRS_EXCLUIDOS:
            continue
        rel = ruta.relative_to(raiz).as_posix()
        if rel in EXCLUIDOS:
            continue
        violaciones.extend(verificar_archivo(ruta))
    return violaciones


def main(argv: list[str]) -> int:
    if "--all" in argv:
        raiz = Path.cwd()
        violaciones = verificar_arbol(raiz)
    else:
        archivos = [a for a in argv if not a.startswith("-")]
        if not archivos:
            print("Uso: verificar_secretos.py ARCHIVO... | --all", file=sys.stderr)
            return 2
        violaciones = []
        for a in archivos:
            violaciones.extend(verificar_archivo(Path(a)))

    if violaciones:
        for v in violaciones:
            print(v)
        print(
            f"\n{len(violaciones)} violación(es). "
            "Configure el secret como variable de entorno del proceso; "
            "nunca como texto en el repo.",
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
