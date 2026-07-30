#!/usr/bin/env python3
"""Deriva la colección de branding de fenix a partir de los dos masters.

Los masters (`fenix-logo-vN.png`, `fenix-icon-vN.png`) son READ-ONLY: este
script nunca los sobreescribe. Una regeneración escribe -v2, -v3… y aquí se
apunta a la versión aprobada.

USO
    python3 derivar.py --logo fenix-logo-v2.png --icon fenix-icon-v2.png
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

AQUI = Path(__file__).resolve().parent

# Paleta extraída del logo REAL del grupo de WhatsApp de la papelería, no
# inventada: el ave está rellena con una rampa de fuego en ese rango de tono.
FUEGO_ROJO = (224, 48, 32)
FUEGO_NARANJA = (224, 80, 0)
FUEGO_AMBAR = (224, 96, 0)
FONDO = (2, 6, 23)  # el mismo --glass-chat-body de la app


def quitar_marca_agua(im: Image.Image) -> Image.Image:
    """Gemini estampa una estrellita en la esquina inferior derecha.

    Es un artefacto del generador, no parte de la marca. El parche se mide por
    FRACCIÓN de cada eje, no por el lado menor: medida sobre los masters, la
    estrella cae en x≥0.86 / y≥0.81, y un cuadrado del 13% del lado menor
    empezaba justo DONDE LA ESTRELLA TERMINA — la dejaba intacta y sólo pintaba
    un rectángulo más oscuro al lado, que era peor que no hacer nada.
    """
    fuera = im.convert("RGB")
    w, h = fuera.size
    relleno = fuera.getpixel((2, 2))
    x0, y0 = int(w * 0.83), int(h * 0.77)
    fuera.paste(Image.new("RGB", (w - x0, h - y0), relleno), (x0, y0))
    return fuera


def recortar_al_contenido(im: Image.Image, umbral: int = 26) -> Image.Image:
    """Quita el margen vacío del master.

    Los masters traen una viñeta sutil en los bordes; pegados tal cual en una
    tarjeta social se leen como una CAJA superpuesta en vez de como un lockup
    integrado. Recortar al contenido real elimina la costura.
    """
    gris = im.convert("L").point(lambda v: 255 if v > umbral else 0)
    caja = gris.getbbox()
    if not caja:
        return im
    margen = int(min(im.size) * 0.02)
    x0, y0, x1, y1 = caja
    return im.crop((max(x0 - margen, 0), max(y0 - margen, 0),
                    min(x1 + margen, im.width), min(y1 + margen, im.height)))


def recorte_cuadrado(im: Image.Image) -> Image.Image:
    w, h = im.size
    lado = min(w, h)
    return im.crop(((w - lado) // 2, (h - lado) // 2, (w + lado) // 2, (h + lado) // 2))


def cover(im: Image.Image, W: int, H: int) -> Image.Image:
    """Escala tipo object-cover: llena el marco sin deformar."""
    escala = max(W / im.width, H / im.height)
    nuevo = im.resize((int(im.width * escala), int(im.height * escala)), Image.Resampling.LANCZOS)
    x = (nuevo.width - W) // 2
    y = (nuevo.height - H) // 2
    return nuevo.crop((x, y, x + W, y + H))


def _rampa(n: int, tramos) -> bytes:
    """Valores 0..255 interpolando entre (posición 0..1, alfa) consecutivos."""
    salida = bytearray(n)
    for i in range(n):
        t = i / max(n - 1, 1)
        for (t0, a0), (t1, a1) in zip(tramos, tramos[1:]):
            if t0 <= t <= t1:
                f = (t - t0) / max(t1 - t0, 1e-6)
                salida[i] = int(a0 + (a1 - a0) * f)
                break
    return bytes(salida)


def rampa_vertical(W: int, H: int, tramos) -> Image.Image:
    return Image.frombytes("L", (1, H), _rampa(H, tramos)).resize((W, H))


def rampa_horizontal(W: int, H: int, tramos) -> Image.Image:
    return Image.frombytes("L", (W, 1), _rampa(W, tramos)).resize((W, H))


def fondo_hero(icon: Image.Image, W: int, H: int) -> Image.Image:
    """El tratamiento 'render entre sombras', horneado en el PNG.

    Equivale al CSS `scale-125 object-cover opacity-40 blur-[3px]` más los dos
    gradientes de oscurecimiento. Se hornea para que el hero no dependa de que
    el consumidor recuerde aplicar las capas.
    """
    base = cover(icon, int(W * 1.25), int(H * 1.25))
    base = base.crop(((base.width - W) // 2, (base.height - H) // 2,
                      (base.width - W) // 2 + W, (base.height - H) // 2 + H))
    base = base.filter(ImageFilter.GaussianBlur(3))
    base = ImageEnhance.Brightness(base).enhance(0.45)

    fondo = fondo_real(icon)
    lienzo = Image.new("RGB", (W, H), fondo)
    lienzo.paste(base, (0, 0))

    oscuro = Image.new("RGB", (W, H), fondo)
    lienzo.paste(oscuro, (0, 0), rampa_vertical(W, H, [(0.0, 204), (0.5, 102), (1.0, 230)]))
    lienzo.paste(oscuro, (0, 0), rampa_horizontal(W, H, [(0.0, 255), (0.5, 26), (1.0, 255)]))
    return lienzo


def fondo_real(im: Image.Image) -> tuple[int, int, int]:
    """El fondo que el generador pintó, no el que pedimos.

    Gemini no respeta el hex al pixel; el master queda unos tonos más claro que
    #020617. Componer la tarjeta con la constante deja el panel del logo
    visiblemente más claro que el lienzo — una costura que se nota justo en la
    imagen que la gente ve compartida.
    """
    return im.convert("RGB").getpixel((2, 2))  # type: ignore[return-value]


def tarjeta_social(logo: Image.Image, icon: Image.Image, W: int, H: int) -> Image.Image:
    """Panel de marca a la izquierda, emblema sangrando por el borde derecho."""
    FONDO = fondo_real(logo)
    lienzo = Image.new("RGB", (W, H), FONDO)

    # Emblema grande, sangrado a la derecha y atenuado
    emblema = recorte_cuadrado(icon).resize((int(H * 1.35), int(H * 1.35)), Image.Resampling.LANCZOS)
    emblema = ImageEnhance.Brightness(emblema).enhance(0.55)
    lienzo.paste(emblema, (W - int(H * 0.95), int(H * -0.18)))

    # Costura invisible: degradado del fondo sobre la mitad izquierda
    velo = Image.new("RGB", (W, H), FONDO)
    lienzo.paste(velo, (0, 0), rampa_horizontal(W, H, [(0.0, 255), (0.55, 255), (1.0, 0)]))

    # Lockup del logo a la izquierda, recortado al contenido para que no se lea
    # como una caja pegada encima del fondo.
    contenido = recortar_al_contenido(logo)
    ancho_logo = int(W * 0.44)
    prop = ancho_logo / contenido.width
    lock = contenido.resize((ancho_logo, int(contenido.height * prop)), Image.Resampling.LANCZOS)
    lienzo.paste(lock, (int(W * 0.06), (H - lock.height) // 2))
    return lienzo


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--logo", default="fenix-logo-v1.png")
    p.add_argument("--icon", default="fenix-icon-v1.png")
    args = p.parse_args()

    logo = quitar_marca_agua(Image.open(AQUI / args.logo))
    icon = quitar_marca_agua(Image.open(AQUI / args.icon))
    icon_sq = recorte_cuadrado(icon)

    generados = []

    def guardar(im: Image.Image, nombre: str, **kw):
        ruta = AQUI / nombre
        im.save(ruta, **kw)
        generados.append((nombre, im.size, ruta.stat().st_size))

    guardar(logo, "logo-full.png")
    guardar(icon_sq, "emblem.png")

    # Favicon multi-resolución. El .ico es el entregable más importante.
    ico = icon_sq.resize((48, 48), Image.Resampling.LANCZOS)
    ico.save(AQUI / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48)])
    generados.append(("favicon.ico", (48, 48), (AQUI / "favicon.ico").stat().st_size))

    guardar(icon_sq.resize((180, 180), Image.Resampling.LANCZOS), "apple-touch-icon.png")
    guardar(icon_sq.resize((192, 192), Image.Resampling.LANCZOS), "icon-192.png")
    guardar(icon_sq.resize((512, 512), Image.Resampling.LANCZOS), "icon-512.png")

    # Monocromo blanco: se conserva el alfa y se pinta el RGB de blanco, para
    # fondos claros donde el degradado de fuego pierde contraste.
    rgba = logo.convert("RGBA")
    blanco = Image.new("L", rgba.size, 255)
    # El master no trae alfa (fondo plano), así que se deriva del brillo: lo
    # que no es fondo se vuelve opaco.
    gris = rgba.convert("L").point(lambda v: 255 if v > 40 else 0)
    guardar(Image.merge("RGBA", (blanco, blanco, blanco, gris)), "logo-white.png")

    guardar(tarjeta_social(logo, icon, 1200, 630), "og-image.png")
    guardar(tarjeta_social(logo, icon, 1200, 600), "twitter-card.png")
    guardar(tarjeta_social(logo, icon, 1584, 396), "linkedin-banner.png")
    guardar(fondo_hero(icon, 1920, 1080), "bg-hero-1920.png")
    guardar(fondo_hero(icon, 3440, 1440), "bg-hero-3440.png")

    print(f"{'archivo':<26}{'dimensiones':<16}peso")
    for nombre, dim, peso in generados:
        print(f"{nombre:<26}{f'{dim[0]}x{dim[1]}':<16}{peso/1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
