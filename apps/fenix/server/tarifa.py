"""Cuánto cobrar por lo que se acaba de generar — y por qué ese número.

QUÉ PROBLEMA RESUELVE. Quien atiende el mostrador no puede ponerse a tasar cada
trabajo: son turnos de veinte minutos, hay fila, y "¿esto cuánto le cobro?" es
justo la pregunta que frena una venta. Así que el precio no lo decide la
persona: lo trae impreso la hoja. Se cobra lo que dice el papel.

LA ESCALERA, decidida por la dirección (Bernard, 6/ago/2026):

- **$10** — la lámina suelta. Una infografía de un tema ("la cultura postpunk a
  lo largo de la historia del arte"): se explica, se cita de dónde salió, se
  imprime y ya.
- **$50** — la regularización completa, y es el **TOPE**. Nada en esta papelería
  cuesta más de $50, aunque el trabajo haya sido enorme. Un techo que la mamá
  conoce de antemano vende más que un precio que hay que preguntar.

EL TECHO LO SUBIÓ LA DUEÑA, no el costo. Arrancó en $25 y Lidia lo corrigió el
6/ago viendo el primer cuadernillo: *"sobre todo ese de regularización, yo lo
incrementaría a 40 o 50 dependiendo; pues al día de hoy los chavos creo que son
solventes más que antes."* Ella conoce a las mamás del barrio y yo sólo tenía el
precio del mercado; su dato gana. Su "40 o 50 **dependiendo**" es exactamente
esta escalera: un cuadernillo sin investigación cae en ~$43 y el completo en
$50. Y sigue siendo 3× más barato que una hora de maestro particular ($100-300).

Entre los dos extremos, el precio sube por LO QUE EL NIÑO SE LLEVA, no por lo
que trabajó el modelo. Ésa es la diferencia entre cobrar valor y cobrar esfuerzo:
al cliente no le sirve que la máquina haya pensado mucho si se lleva una hoja
suelta.

EL COSTO DE TOKENS ES UN FACTOR, NO EL PRECIO. Medido: una lámina cuesta ~$1.50
MXN de modelo y la impresión a color ~$2.50 — la tinta cuesta más que la IA. Por
eso los tokens sólo mueven el precio cuando hubo INVESTIGACIÓN de verdad
(búsqueda en internet, fuentes que hubo que verificar), que es lo único que el
cliente sí reconoce como trabajo extra: "me trajo los datos y me dice de dónde
salieron".
"""

from __future__ import annotations

from dataclasses import dataclass

PISO = 10
TECHO = 50
DESCUENTO_BLANCO_Y_NEGRO = 5

# Cada escalón es algo que el cliente puede VER en la hoja. Sumados dan
# exactamente el techo: la regularización completa vale $50 y ni un peso más.
# El de ejercicios pesa más que el resto a propósito — es lo único que obliga al
# niño a trabajar, y es lo que distingue estudiar de leer una lámina bonita.
VALE_EJEMPLOS = 10  # ejemplos resueltos paso a paso, lo del pizarrón
VALE_EJERCICIOS = 15  # ejercicios para que los haga solo
VALE_RESPUESTAS = 8  # la hoja que se separa para quien revisa
VALE_INVESTIGACION = 7  # fuentes verificadas, no inventadas

# A partir de aquí se considera que hubo investigación de verdad y no sólo
# redacción. Es un umbral de TOKENS porque buscar, leer y verificar es lo que
# los consume; por debajo, el modelo escribió de lo que ya sabía.
TOKENS_DE_INVESTIGACION = 12_000


@dataclass
class Desglose:
    """El precio y su explicación, renglón por renglón.

    Se imprime en la hoja para que quien cobra pueda responder "¿por qué $18?"
    sin llamar a nadie.
    """

    total: int
    color: bool
    conceptos: list[tuple[str, int]]

    @property
    def texto(self) -> str:
        return " + ".join(f"{n} ${v}" for n, v in self.conceptos if v)


def calcular(
    *,
    color: bool = True,
    tiene_ejemplos: bool = False,
    tiene_ejercicios: bool = False,
    tiene_respuestas: bool = False,
    tokens: int = 0,
    fuentes: int = 0,
) -> Desglose:
    """El precio de este trabajo, entre $10 y $25.

    `tokens` y `fuentes` van juntos a propósito: gastar muchos tokens SIN traer
    fuentes no es investigación, es divagar, y eso no se le cobra al cliente.
    """
    conceptos: list[tuple[str, int]] = [("Lámina", PISO)]

    if tiene_ejemplos:
        conceptos.append(("Ejemplos resueltos", VALE_EJEMPLOS))
    if tiene_ejercicios:
        conceptos.append(("Ejercicios", VALE_EJERCICIOS))
    if tiene_respuestas:
        conceptos.append(("Hoja de respuestas", VALE_RESPUESTAS))
    if tokens >= TOKENS_DE_INVESTIGACION and fuentes > 0:
        conceptos.append(("Investigación con fuentes", VALE_INVESTIGACION))

    total = sum(v for _, v in conceptos)

    if not color:
        conceptos.append(("Blanco y negro", -DESCUENTO_BLANCO_Y_NEGRO))
        total -= DESCUENTO_BLANCO_Y_NEGRO

    # El techo es duro y el piso también: por mucho que se acumule, nadie paga
    # más de $25 en esta papelería, y nada baja de $10 porque la impresión y el
    # papel ya cuestan.
    total = max(PISO, min(TECHO, total))
    return Desglose(total=total, color=color, conceptos=conceptos)
