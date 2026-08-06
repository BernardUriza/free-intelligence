# Los colores de Fénix — lo que eligió la dueña

Fuente única para pintar los promocionales, la app (`apps/fenix/web`) y el
cuadernillo (`apps/fenix/server/regularizacion.py`). Antes de tocar un color en
cualquiera de los tres, se lee este archivo.

Salieron de la carta de color (`paleta-fenix.svg`, la genera
`generar-paleta.py`) que se le mandó a Lidia por WhatsApp el 6-ago-2026. Los
eligió por número, no por nombre: "naranja" y "verde pasto" son familias
enteras, y adivinar habría significado repintar las tres superficies dos veces.

## Naranjas — CONFIRMADOS (Lidia, 6-ago-2026, "3 con 4")

| | Hex | Era el | Para qué |
|---|---|---|---|
| **3** | `#F76707` | "fuerte" | el acento vivo |
| **4** | `#E05000` | "el de ahora" | el que ya traía la marca |

Eligió **dos naranjas y ningún verde**, y no fue un descuido: son los dos
extremos de la rampa de fuego que el ave ya usa. `#E05000` es literalmente el
`--fx-fuego` que estaba en `globals.css`, así que lo que hizo fue **confirmar el
naranja existente y sumarle uno más vivo** — la identidad no cambia, se abre.

## Verdes pasto — PENDIENTE

Los verdes de la carta van del **8 al 15** y **todavía no elige**. Bernard,
6-ago: *"ahorita te digo qué verdes"*.

**Hasta que lleguen, no se repinta nada.** Media paleta pintada es peor que la
paleta vieja: obliga a una segunda pasada por los tres lados y deja carteles
impresos que ya no combinan con la app.

## Lo que NO se toca

El **negro y el papel** se quedan: `#1A1712` de tinta y `#FDFAF4` de papel. Lidia
dijo *"así en esos colores negro rojo está muy elegante, pero para que vaya con
los colores que manejo"* — lo que pidió cambiar es el **rojo**, no la elegancia.
El fondo oscuro de la app (`#020617`) tampoco: ahí el naranja es lo que resalta.

## Cuando lleguen los verdes

Tres lugares, una sola pasada:

1. `apps/fenix/web/app/globals.css` y `landing.css` — los tokens `--fx-fuego*`.
2. `apps/fenix/branding/generar-promocionales.py` (en `~/Desktop/fenix-promocionales/`)
   — regenerar los 3 carteles.
3. `apps/fenix/server/regularizacion.py` — `FUEGO` y `FUEGO_ROJO`, que son los
   del PDF que se imprime.
