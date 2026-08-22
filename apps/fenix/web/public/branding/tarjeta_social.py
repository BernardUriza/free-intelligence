"""Genera la tarjeta que se ve cuando alguien comparte el sitio por WhatsApp.

La anterior sólo decía "Fénix · Papelería · Cotizaciones": correcta de marca y
muda de mensaje. Una tarjeta compartida es un anuncio con un solo renglón de
atención — el que decide si la mamá abre el link o no — así que lleva la
promesa, no el rubro.

Va en oscuro (no en el papel de la portada) porque una miniatura clara sobre el
fondo de WhatsApp se desvanece; el contraste es lo que la hace visible en una
lista de chats.

Correr desde este directorio:  python3 tarjeta_social.py
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

AQUI = Path(__file__).parent
FONDO = (10, 14, 26)
PAPEL = (253, 250, 244)
FUEGO = (224, 80, 0)
TENUE = (148, 140, 128)

NEGRITA = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
NORMAL = "/System/Library/Fonts/Supplemental/Arial.ttf"


def tipo(ruta: str, tam: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(ruta, tam)


def componer(ancho: int, alto: int, destino: str) -> None:
    im = Image.new("RGB", (ancho, alto), FONDO)
    d = ImageDraw.Draw(im)

    # El ave, grande y sangrada a la derecha: da marca sin competir con el texto.
    ave = Image.open(AQUI / "emblem-transparente.png").convert("RGBA")
    lado = int(alto * 1.15)
    ave = ave.resize((lado, lado), Image.Resampling.LANCZOS)
    capa = Image.new("RGBA", im.size, (0, 0, 0, 0))
    capa.paste(ave, (ancho - int(lado * 0.72), int(alto * 0.5 - lado * 0.5)), ave)
    # Bajada de opacidad: es fondo, no protagonista.
    capa.putalpha(capa.getchannel("A").point(lambda a: int(a * 0.30)))
    im = Image.alpha_composite(im.convert("RGBA"), capa).convert("RGB")
    d = ImageDraw.Draw(im)

    x = int(ancho * 0.075)
    y = int(alto * 0.30)

    # La promesa, partida donde cae el acento de color.
    d.text((x, y), "La lista de tu hijo,", font=tipo(NEGRITA, int(alto * 0.115)), fill=PAPEL)
    y += int(alto * 0.135)
    d.text((x, y), "cotizada el mismo día", font=tipo(NEGRITA, int(alto * 0.115)), fill=FUEGO)
    y += int(alto * 0.175)

    d.text(
        (x, y),
        "Mándanos la foto por WhatsApp · Guadalajara",
        font=tipo(NORMAL, int(alto * 0.052)),
        fill=TENUE,
    )

    # La firma abajo, chica: quién lo dice.
    d.text(
        (x, int(alto * 0.86)),
        "SERVICIOS PAPELEROS FÉNIX",
        font=tipo(NEGRITA, int(alto * 0.038)),
        fill=(90, 84, 76),
    )

    im.save(AQUI / destino, quality=92)
    print(f"  {destino}  {im.size}")


if __name__ == "__main__":
    componer(1200, 630, "og-image.png")
    componer(1200, 600, "twitter-card.png")
