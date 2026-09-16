"""Generador de DOCXs sintéticos para tests.

Proporciona funciones para crear archivos DOCX de tamaño controlado,
útiles para probar límites de tamaño, validación de entrada, etc.

Uso:
    from _docx_builder import build_large_docx

    contenido = build_large_docx(target_bytes=10 * 1024 * 1024)
"""
import io
import random
import zipfile

from docx import Document


def build_large_docx(target_bytes, seed=42):
    """Genera un DOCX válido de tamaño aproximado a target_bytes.

    Crea un DOCX mínimo con python-docx y lo rellena con bytes aleatorios
    (no comprimibles) usando un archivo dummy dentro del ZIP. Esto permite
    generar archivos grandes rápidamente sin consumir mucha memoria.

    Args:
        target_bytes: Tamaño objetivo en bytes.
        seed: Semilla para el generador de números aleatorios (reproducibilidad).

    Returns:
        bytes: Contenido del DOCX generado.
    """
    # Crear DOCX mínimo válido
    doc = Document()
    doc.add_paragraph("Documento de prueba para validación de tamaño")
    buf_base = io.BytesIO()
    doc.save(buf_base)

    contenido_base = buf_base.getvalue()
    # Reservar espacio para overhead de headers del ZIP
    padding_necesario = target_bytes - len(contenido_base) - 4096

    if padding_necesario <= 0:
        # El DOCX base ya supera el tamaño objetivo
        buf_base.seek(0)
        return buf_base.read()

    random.seed(seed)
    padding = bytes(random.getrandbits(8) for _ in range(padding_necesario))

    resultado = io.BytesIO()
    buf_base.seek(0)
    with zipfile.ZipFile(buf_base, "r") as zin:
        with zipfile.ZipFile(resultado, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                zout.writestr(item, zin.read(item.filename))
            zout.writestr("dummy/padding.bin", padding)

    resultado.seek(0)
    return resultado.read()
