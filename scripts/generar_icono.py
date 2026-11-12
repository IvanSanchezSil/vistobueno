"""Genera vistobueno.ico con el mismo trazo que frontend/public/favicon.svg."""

from pathlib import Path

from PIL import Image, ImageDraw

DESTINO = Path(__file__).resolve().parent.parent / "tools" / "launcher" / "vistobueno.ico"
TAMANO = 256
ESCALA = TAMANO / 64


def main() -> None:
    imagen = Image.new("RGBA", (TAMANO, TAMANO), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)
    dibujo.rounded_rectangle(
        (0, 0, TAMANO - 1, TAMANO - 1),
        radius=round(14 * ESCALA),
        fill="#2e7d32",
    )

    puntos = [(17, 34), (27, 44), (46, 21)]
    trazo = [(round(x * ESCALA), round(y * ESCALA)) for x, y in puntos]
    ancho = round(7 * ESCALA)
    dibujo.line(trazo, fill="white", width=ancho, joint="curve")

    radio = ancho // 2
    for x, y in (trazo[0], trazo[-1]):
        dibujo.ellipse((x - radio, y - radio, x + radio, y + radio), fill="white")

    imagen.save(
        DESTINO,
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)],
    )


if __name__ == "__main__":
    main()
