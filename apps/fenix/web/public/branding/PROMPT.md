# Branding de Fénix — cómo se hizo y cómo se rehace

**Generado:** 2026-07-27 · **Gemini:** https://gemini.google.com/app/598922e7a50fcc10
**Masters aprobados:** `fenix-logo-v3.png` (1024×572) · `fenix-icon-v3.png` (1024×1024)

## La paleta NO se inventó

Salió del logo real que la papelería usa como foto de su grupo de WhatsApp. Se
descargó el avatar y se midieron sus píxeles saturados:

| Rol | Hex | HSL medido |
|---|---|---|
| Rojo fuego | `#E03020` | H 5 · S 75% · L 50% |
| Naranja fuego (dominante) | `#E05000` | H 21 · S 100% · L 43% |
| Ámbar | `#E06000` | H 25 · S 100% · L 43% |
| Fondo de la app | `#020617` | el mismo `--glass-chat-body` de fi-glass |

El ave de su logo es una silueta plana en degradado rojo→naranja sobre blanco.
Aquí se conserva el ave y el degradado, y se cambia el fondo a oscuro para que
viva dentro de la app.

## Por qué hubo tres versiones

- **v1** — bonita, pero el ave tenía más detalle interior que la suya.
- **v2** — se pidió por escrito "más simple, más plana": Gemini devolvió
  prácticamente la misma imagen. **Describir la silueta con palabras no funcionó.**
- **v3 — la aprobada.** Lo que sí funcionó fue **subirle su logo real como
  imagen de referencia** y pedirle que copiara esa silueta sin rediseñarla. Si
  hay que regenerar, empieza por ahí: adjunta el avatar, no lo describas.

## Prompt del logo (v3, con el avatar adjunto)

> This attached image is the shop's REAL logo. Use this exact bird silhouette — do not redesign it, do not add detail to it, do not stylize it further. Copy its proportions faithfully: the wings are built from a few long tapered blades separated by clean slits, the head is small and turned to the left with a simple beak and no eye, and the tail is a narrow bundle of pointed feathers hanging straight down. It is a flat solid cut-out with zero interior shading.
>
> Now place that same bird into a wide horizontal logo lockup: bird on the left keeping its fire gradient (deep red #E03020 on the left wing through orange #E05000 to amber #E06000 on the right wing), on a perfectly flat near-black #020617 background. To the right of the bird, the wordmark "Fénix" in a clean geometric sans-serif, medium weight, warm off-white #F5F5F0, with a correct accent on the e. Under the wordmark, small letter-spaced uppercase warm grey tagline "PAPELERÍA · COTIZACIONES". Generous negative space, crisp edges, high contrast. Do NOT draw any sparkle, star, glint, diamond or decorative mark anywhere on the canvas. No glow, no shadow, no 3D, no bevel.

## Prompt del icono (v3, misma conversación)

> Perfect, that bird is exactly right. Now give me the square app icon using that SAME bird, unchanged. Perfect 1:1 square canvas. Only the phoenix, centered, filling about 70% of the canvas with even margins on all four sides. Absolutely no text, no wordmark, no tagline. Same fire gradient from deep red #E03020 through orange #E05000 to amber #E06000, same perfectly flat near-black #020617 background. It must stay readable shrunk down to 16x16 pixels, so keep the negative space between the wing blades open and generous. No sparkle, no star, no glint, no diamond, no decorative mark anywhere. No border, no rounded frame, no glow, no shadow.

**Ojo:** aunque el prompt prohíbe la estrellita, Gemini la estampa igual — es su
marca de agua. `derivar.py` la recorta.

## Regenerar la colección

```bash
cd apps/fenix/web/public/branding
python3 derivar.py --logo fenix-logo-v3.png --icon fenix-icon-v3.png
```

Los masters son **read-only**: el script nunca los sobreescribe, y una
regeneración nueva se guarda como `-v4`.

## El tratamiento de fondo, si se prefiere en CSS

Los `bg-hero-*.png` traen el efecto horneado. El equivalente cliente:

```html
<img class="scale-125 object-cover opacity-40 blur-[3px]" src="/branding/emblem.png">
<div class="absolute inset-0 bg-gradient-to-r from-[#020617] via-[#020617]/10 to-[#020617]"></div>
<div class="absolute inset-0 bg-gradient-to-b from-[#020617]/80 via-[#020617]/40 to-[#020617]/90"></div>
```
