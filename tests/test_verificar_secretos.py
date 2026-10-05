"""Tests del verificador de secretos SMTP (scripts/verificar_secretos.py).

El verificador es la capa estricta anti-filtración de credenciales: estos
tests prueban que BLOQUEA asignaciones con valor real y archivos .env, y que
PERMITE menciones documentales y placeholders. Los "secretos" aquí son
cadenas de prueba obviamente falsas, y este archivo está excluido del
escaneo (ver EXCLUIDOS en el script) precisamente para poder probarlo.
"""

import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "verificar_secretos.py"


def correr(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Ejecuta el verificador como subproceso (igual que pre-commit/CI)."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=cwd,
    )


def test_detecta_password_con_valor_real(tmp_path):
    """Una asignación con valor no-placeholder debe salir con código 1."""
    archivo = tmp_path / "config.txt"
    archivo.write_text(
        "VISTOBUENO_SMTP_HOST=smtp.unitru.edu.pe\n"
        "VISTOBUENO_SMTP_PASSWORD=Secr3to-Institucional-XYZ\n",
        encoding="utf-8",
    )
    r = correr([str(archivo)])
    assert r.returncode == 1
    assert str(archivo) in r.stdout
    # El valor nunca se imprime (no repetir posibles secretos en logs)
    assert "Secr3to" not in r.stdout


def test_detecta_password_con_dos_puntos_y_comillas(tmp_path):
    """Formato YAML/JSON (`VAR: "valor"`) también debe bloquearse."""
    archivo = tmp_path / "config.yaml"
    archivo.write_text('VISTOBUENO_SMTP_PASSWORD: "hunter2-real"\n', encoding="utf-8")
    r = correr([str(archivo)])
    assert r.returncode == 1


def test_permite_placeholders_dummy(tmp_path):
    """Valores dummy/prueba/test/changeme/<valor> no son secreto."""
    archivo = tmp_path / "ejemplos.txt"
    archivo.write_text(
        "VISTOBUENO_SMTP_PASSWORD=dummy\n"
        'VISTOBUENO_SMTP_PASSWORD: "prueba"\n'
        "VISTOBUENO_SMTP_PASSWORD=test\n"
        "VISTOBUENO_SMTP_PASSWORD=changeme\n"
        "VISTOBUENO_SMTP_PASSWORD=<valor>\n",
        encoding="utf-8",
    )
    r = correr([str(archivo)])
    assert r.returncode == 0, r.stdout


def test_permite_autorreferencia_y_vacio(tmp_path):
    """Autorreferencias ($VAR) y asignación vacía no filtran nada."""
    archivo = tmp_path / "deploy.txt"
    archivo.write_text(
        "export NUEVA=$VISTOBUENO_SMTP_PASSWORD\nVISTOBUENO_SMTP_PASSWORD=\n",
        encoding="utf-8",
    )
    r = correr([str(archivo)])
    assert r.returncode == 0, r.stdout


def test_permite_menciones_documentales(tmp_path):
    """Mencionar la variable sin asignar valor (docs/AGENTS) es válido."""
    archivo = tmp_path / "docs.md"
    archivo.write_text(
        "| `VISTOBUENO_SMTP_PASSWORD` | Contraseña SMTP — nunca al repo |\n"
        "Configure VISTOBUENO_SMTP_PASSWORD en su entorno local.\n",
        encoding="utf-8",
    )
    r = correr([str(archivo)])
    assert r.returncode == 0, r.stdout


def test_bloquea_archivo_env_por_nombre(tmp_path):
    """Cualquier archivo .env o .env.* es violación por sí mismo."""
    (tmp_path / ".env").write_text("algo=1\n", encoding="utf-8")
    (tmp_path / ".env.local").write_text("VISTOBUENO_SMTP_HOST=smtp\n", encoding="utf-8")
    r = correr([str(tmp_path / ".env"), str(tmp_path / ".env.local")])
    assert r.returncode == 1
    assert ".env" in r.stdout
    assert ".env.local" in r.stdout


def test_permite_env_example_pero_escanea_su_contenido(tmp_path):
    """.env.example es plantilla documental (convención Vite), no un secret.

    El archivo en sí es válido, pero una asignación con valor REAL dentro de
    él debe detectarse igual: el contenido siempre se escanea.
    """
    bueno = tmp_path / ".env.example"
    bueno.write_text("VITE_API_URL=\n", encoding="utf-8")
    r = correr([str(bueno)])
    assert r.returncode == 0, r.stdout

    malo = tmp_path / "otro.env.example"
    malo.write_text("VISTOBUENO_SMTP_PASSWORD=Clave-Real-De-Prueba\n", encoding="utf-8")
    r = correr([str(malo)])
    assert r.returncode == 1
    assert "otro.env.example" in r.stdout


def test_all_escanea_arbol_completo(tmp_path, monkeypatch):
    """Modo --all (CI) detecta violaciones anidadas en el árbol."""
    (tmp_path / "deploy").mkdir()
    secreto = tmp_path / "deploy" / "provision.sh"
    secreto.write_text("VISTOBUENO_SMTP_PASSWORD=Clave-Real-De-Prueba\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    r = correr(["--all"])
    assert r.returncode == 1
    assert "provision.sh" in r.stdout
