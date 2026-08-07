"""La carta de color para que la dueña elija los tonos de la papelería.

Pidió "naranja y verde pasto". Las dos son familias, no colores: hay veinte
naranjas distintos y "verde pasto" puede ser el del césped recién regado o el
del zacate seco. Adivinar significaría rehacer los promocionales, la app y el
cuadernillo dos veces, así que primero se elige y luego se pinta.

Van numerados y con su código: ella contesta "el 5 y el 11" por WhatsApp y con
eso se pinta todo. El PNG es para que lo vea en el celular —WhatsApp no muestra
SVG en el chat— y el SVG es el que queda como fuente para trabajar.
"""

from PIL import Image, ImageDraw, ImageFont

NARANJAS = [
    ("1", "#C2410C", "quemado"),
    ("2", "#E8590C", "ladrillo"),
    ("3", "#F76707", "fuerte"),
    ("4", "#E05000", "el de ahora"),
    ("5", "#FD7E14", "clásico"),
    ("6", "#FF922B", "vivo"),
    ("7", "#FFA94D", "claro"),
]
VERDES = [
    ("8", "#1E6B2E", "pasto oscuro"),
    ("9", "#2B8A3E", "pasto"),
    ("10", "#37B24D", "pasto vivo"),
    ("11", "#40C057", "brillante"),
    ("12", "#69DB7C", "claro"),
    ("13", "#5C940D", "olivo"),
    ("14", "#7CB518", "limón"),
    ("15", "#94D82D", "lima"),
]

W, H = 1400, 1560
MARGEN = 70
COLS = 4
CAJA = 290
ALTO_CAJA = 250
GAP = 24

PAPEL = "#FDFAF4"
TINTA = "#1A1712"
SUAVE = "#5E564A"


def _fuente(tam, negrita=True):
    for ruta in (
        "/System/Library/Fonts/Avenir Next.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ):
        try:
            return ImageFont.truetype(ruta, tam, index=2 if negrita else 0)
        except Exception:
            continue
    return ImageFont.load_default()


def _claro(hexa: str) -> bool:
    r, g, b = (int(hexa[i : i + 2], 16) for i in (1, 3, 5))
    return (0.299 * r + 0.587 * g + 0.114 * b) > 150


def dibujar() -> Image.Image:
    img = Image.new("RGB", (W, H), PAPEL)
    d = ImageDraw.Draw(img)

    d.text((MARGEN, 55), "¿Cuáles son los colores de Fénix?", font=_fuente(58), fill=TINTA)
    d.text(
        (MARGEN, 130),
        "Dime un número de naranja y uno de verde, y con esos pinto todo.",
        font=_fuente(30, False),
        fill=SUAVE,
    )

    y = 215
    for titulo, grupo in (("NARANJAS", NARANJAS), ("VERDES PASTO", VERDES)):
        d.text((MARGEN, y), titulo, font=_fuente(30), fill=SUAVE)
        y += 52
        for i, (num, hexa, nombre) in enumerate(grupo):
            col, fila = i % COLS, i // COLS
            x = MARGEN + col * (CAJA + GAP)
            yy = y + fila * (ALTO_CAJA + GAP)
            d.rounded_rectangle([x, yy, x + CAJA, yy + ALTO_CAJA], radius=18, fill=hexa)
            tinta = TINTA if _claro(hexa) else "#FFFFFF"
            d.text((x + 22, yy + 18), num, font=_fuente(86), fill=tinta)
            d.text((x + 22, yy + ALTO_CAJA - 76), nombre, font=_fuente(26, False), fill=tinta)
            d.text((x + 22, yy + ALTO_CAJA - 44), hexa.upper(), font=_fuente(24), fill=tinta)
        y += ((len(grupo) - 1) // COLS + 1) * (ALTO_CAJA + GAP) + 40

    d.text(
        (MARGEN, H - 48),
        "SERVICIOS PAPELEROS FÉNIX",
        font=_fuente(26),
        fill=SUAVE,
    )
    return img


def svg() -> str:
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{PAPEL}"/>',
        f'<text x="{MARGEN}" y="105" font-family="Avenir Next,Helvetica,sans-serif" '
        f'font-size="58" font-weight="700" fill="{TINTA}">¿Cuáles son los colores de Fénix?</text>',
    ]
    y = 215
    for titulo, grupo in (("NARANJAS", NARANJAS), ("VERDES PASTO", VERDES)):
        partes.append(
            f'<text x="{MARGEN}" y="{y + 24}" font-family="Avenir Next,Helvetica,sans-serif" '
            f'font-size="30" font-weight="700" fill="{SUAVE}">{titulo}</text>'
        )
        y += 52
        for i, (num, hexa, nombre) in enumerate(grupo):
            col, fila = i % COLS, i // COLS
            x = MARGEN + col * (CAJA + GAP)
            yy = y + fila * (ALTO_CAJA + GAP)
            tinta = TINTA if _claro(hexa) else "#FFFFFF"
            partes.append(
                f'<rect x="{x}" y="{yy}" width="{CAJA}" height="{ALTO_CAJA}" rx="18" fill="{hexa}"/>'
                f'<text x="{x + 22}" y="{yy + 100}" font-family="Avenir Next,Helvetica,sans-serif" '
                f'font-size="86" font-weight="700" fill="{tinta}">{num}</text>'
                f'<text x="{x + 22}" y="{yy + ALTO_CAJA - 50}" font-family="Avenir Next,Helvetica,sans-serif" '
                f'font-size="26" fill="{tinta}">{nombre}</text>'
                f'<text x="{x + 22}" y="{yy + ALTO_CAJA - 18}" font-family="Avenir Next,Helvetica,sans-serif" '
                f'font-size="24" font-weight="700" fill="{tinta}">{hexa.upper()}</text>'
            )
        y += ((len(grupo) - 1) // COLS + 1) * (ALTO_CAJA + GAP) + 40
    partes.append("</svg>")
    return "\n".join(partes)


if __name__ == "__main__":
    import sys

    destino = sys.argv[1]
    dibujar().save(f"{destino}/paleta-fenix.png")
    open(f"{destino}/paleta-fenix.svg", "w").write(svg())
    print(f"{destino}/paleta-fenix.png")
    print(f"{destino}/paleta-fenix.svg")
