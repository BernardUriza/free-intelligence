"""El cuadernillo de regularización — lo que hace que $25 no sea un chat caro.

QUÉ PROBLEMA RESUELVE. Una hora de regularización en México cuesta entre $100 y
$300 (promedio ~$168). Cobrar $25 sólo se sostiene si el niño se lleva algo que
se PAREZCA a una regularización, no una conversación que se cierra al salir del
cibercafé. Un chat no se puede revisar en casa, la mamá no lo ve, y al día
siguiente no queda nada.

Lo que sí se parece: el cuadernillo que un maestro particular deja hecho.
Diagnóstico de dónde se atoró, la explicación a su nivel, ejemplos resueltos
paso a paso —lo del pizarrón—, ejercicios para que los haga SOLO, y una hoja
final de respuestas para quien revisa. Ese último detalle es el que convierte
esto en regularización de verdad: la mamá puede corregirle sin saber el tema.

MISMO PATRÓN QUE `presupuesto.py`, y por la misma razón. El modelo produce los
DATOS y el servidor aplica el FORMATO. `ToolPolicy.companion()` le bloquea
`Bash`/`Write` al agente —y debe seguir así—, de modo que un modelo al que se le
pide "haz un PDF" termina entregando texto en el chat: se ve útil y no lo es,
porque lo que el niño se lleva a su casa es una hoja impresa. Además, con el
formato aquí no hay nada que improvisar entre un cuadernillo y el siguiente.

LO QUE ESTE ARCHIVO NO HACE. No decide pedagogía: eso vive en la persona del
tutor (`prompts/tutor.md`) y en la directiva de tutoría. Aquí sólo se maqueta lo
que el modelo ya razonó.
"""

from __future__ import annotations

import io
import re
import unicodedata
from dataclasses import dataclass, field

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from tarifa import Desglose, calcular

# Los mismos de la marca, elegidos por la dueña de una carta numerada el
# 6-ago-2026 (ver apps/fenix/branding/COLORES.md): el cuadernillo se imprime en
# la misma papelería que el cartel y tiene que verse de la misma casa.
FUEGO = colors.HexColor("#e05000")
FUEGO_VIVO = colors.HexColor("#f76707")
# El verde marca lo que ya está resuelto: la hoja de respuestas de quien revisa.
# Impreso importa más que en pantalla — es lo que separa la hoja del niño de la
# de su mamá cuando el fajo sale de la impresora y hay que repartirlo.
PASTO = colors.HexColor("#37b24d")
TINTA = colors.HexColor("#1a1712")
TINTA_SUAVE = colors.HexColor("#5e564a")
LINEA = colors.HexColor("#e6dcc9")
PAPEL_HONDO = colors.HexColor("#f5efe3")

MARGEN = 1.8 * cm


@dataclass
class Paso:
    """Un renglón del pizarrón: qué se hace y por qué se hace."""

    que: str
    porque: str = ""


@dataclass
class Ejemplo:
    enunciado: str
    pasos: list[Paso] = field(default_factory=list)
    resultado: str = ""


@dataclass
class Ejercicio:
    """La respuesta NO se imprime junto al ejercicio: va en la hoja de quien
    revisa. Un cuadernillo con las respuestas al lado no se practica, se copia."""

    enunciado: str
    respuesta: str = ""
    pista: str = ""
    renglones: int = 3


@dataclass
class Cuadernillo:
    tema: str
    grado: str = ""
    alumno: str = ""
    fecha: str = ""
    se_atora_en: str = ""
    explicacion: list[str] = field(default_factory=list)
    ejemplos: list[Ejemplo] = field(default_factory=list)
    ejercicios: list[Ejercicio] = field(default_factory=list)
    fuentes: list[str] = field(default_factory=list)
    # A color por defecto porque es lo que se ve bien pegado en un cuaderno; el
    # blanco y negro baja el precio y se pide cuando el trabajo no lleva imagen.
    color: bool = True
    # Los del turno que generó esto. Sólo mueven el precio si además hay fuentes
    # (ver `tarifa.py`): muchos tokens sin fuentes no es investigación.
    tokens: int = 0

    def precio(self) -> Desglose:
        return calcular(
            color=self.color,
            tiene_ejemplos=bool(self.ejemplos),
            tiene_ejercicios=bool(self.ejercicios),
            tiene_respuestas=any(e.respuesta for e in self.ejercicios),
            tokens=self.tokens,
            fuentes=len(self.fuentes),
        )


def _estilos() -> dict[str, ParagraphStyle]:
    base = ParagraphStyle(
        "base",
        fontName="Helvetica",
        fontSize=11,
        leading=16,
        textColor=TINTA,
        alignment=TA_LEFT,
    )
    return {
        "cuerpo": base,
        "titulo": ParagraphStyle(
            "titulo", parent=base, fontName="Helvetica-Bold", fontSize=23, leading=27
        ),
        "seccion": ParagraphStyle(
            "seccion",
            parent=base,
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=FUEGO,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "sub": ParagraphStyle(
            "sub", parent=base, fontName="Helvetica-Bold", fontSize=11.5, leading=15
        ),
        "chico": ParagraphStyle(
            "chico", parent=base, fontSize=9, leading=12.5, textColor=TINTA_SUAVE
        ),
        "paso": ParagraphStyle("paso", parent=base, fontSize=10.5, leading=15),
    }


def _limpiar(texto: str) -> str:
    """El modelo escribe markdown por costumbre; aquí sólo se imprime texto.

    Se quitan los asteriscos y almohadillas —que en un PDF se ven como basura, no
    como negritas— y se escapan los tres caracteres que reportlab interpreta como
    marcado. Un enunciado con "5 < 8" reventaba el documento entero.
    """
    t = (texto or "").strip()
    t = re.sub(r"^#{1,6}\s*", "", t)
    t = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", t)
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return t


class _Documento(BaseDocTemplate):
    """El pie va en todas las páginas: la hoja se separa, se presta y se pierde."""

    def __init__(self, buffer: io.BytesIO, cuadernillo: Cuadernillo) -> None:
        super().__init__(
            buffer,
            pagesize=letter,
            leftMargin=MARGEN,
            rightMargin=MARGEN,
            topMargin=MARGEN,
            bottomMargin=MARGEN + 0.8 * cm,
            title=f"Regularización — {cuadernillo.tema}",
            author="Servicios Papeleros Fénix",
        )
        self._c = cuadernillo
        marco = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            id="normal",
            showBoundary=0,
        )
        self.addPageTemplates([PageTemplate(id="fenix", frames=[marco], onPage=self._pie)])

    def _pie(self, canvas, doc) -> None:  # noqa: ANN001
        canvas.saveState()
        y = self.bottomMargin - 0.7 * cm
        canvas.setStrokeColor(LINEA)
        canvas.setLineWidth(0.7)
        canvas.line(self.leftMargin, y + 0.35 * cm, self.leftMargin + self.width, y + 0.35 * cm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(TINTA_SUAVE)
        canvas.drawString(self.leftMargin, y, "Servicios Papeleros Fénix · WhatsApp 33 3858 2967")
        canvas.drawRightString(self.leftMargin + self.width, y, f"Página {doc.page}")
        canvas.restoreState()


def _portada(c: Cuadernillo, s: dict) -> list:
    quien = " · ".join(x for x in (c.alumno, c.grado) if x)
    cinta = Table(
        [[""]], colWidths=[17.4 * cm - 2 * MARGEN + 2 * MARGEN], rowHeights=[0.22 * cm]
    )
    cinta.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FUEGO)]))
    piezas: list = [
        Paragraph("REGULARIZACIÓN", s["chico"]),
        Spacer(1, 0.15 * cm),
        Paragraph(_limpiar(c.tema), s["titulo"]),
        Spacer(1, 0.25 * cm),
    ]
    if quien:
        piezas.append(Paragraph(_limpiar(quien), s["cuerpo"]))
    if c.fecha:
        piezas.append(Paragraph(_limpiar(c.fecha), s["chico"]))
    piezas.append(Spacer(1, 0.4 * cm))
    piezas.append(cinta)
    return piezas


def _bloque_atore(c: Cuadernillo, s: dict) -> list:
    if not c.se_atora_en:
        return []
    caja = Table([[Paragraph(_limpiar(c.se_atora_en), s["cuerpo"])]], colWidths=[16.2 * cm])
    caja.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PAPEL_HONDO),
                ("BOX", (0, 0), (-1, -1), 0.7, LINEA),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return [Paragraph("Lo que vamos a repasar", s["seccion"]), caja]


def _bloque_ejemplos(c: Cuadernillo, s: dict) -> list:
    if not c.ejemplos:
        return []
    piezas: list = [Paragraph("Vamos juntos", s["seccion"])]
    for i, ej in enumerate(c.ejemplos, 1):
        grupo: list = [
            Paragraph(f"Ejemplo {i}. {_limpiar(ej.enunciado)}", s["sub"]),
            Spacer(1, 0.15 * cm),
        ]
        filas = []
        for n, paso in enumerate(ej.pasos, 1):
            texto = _limpiar(paso.que)
            if paso.porque:
                texto += f"<br/><font size=9 color='#5e564a'>{_limpiar(paso.porque)}</font>"
            filas.append([Paragraph(f"<b>{n}</b>", s["paso"]), Paragraph(texto, s["paso"])])
        if filas:
            tabla = Table(filas, colWidths=[0.9 * cm, 15.3 * cm])
            tabla.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("TEXTCOLOR", (0, 0), (0, -1), FUEGO),
                        ("LINEBELOW", (0, 0), (-1, -2), 0.5, LINEA),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ]
                )
            )
            grupo.append(tabla)
        if ej.resultado:
            grupo.append(Spacer(1, 0.15 * cm))
            grupo.append(Paragraph(f"<b>Resultado:</b> {_limpiar(ej.resultado)}", s["cuerpo"]))
        grupo.append(Spacer(1, 0.4 * cm))
        # KeepTogether: un ejemplo partido a la mitad por un salto de página deja
        # los pasos huérfanos y deja de enseñar nada.
        piezas.append(KeepTogether(grupo))
    return piezas


def _bloque_ejercicios(c: Cuadernillo, s: dict) -> list:
    if not c.ejercicios:
        return []
    # El encabezado viaja pegado al primer ejercicio: suelto al pie de una página
    # deja un hueco grande y un título que no encabeza nada.
    encabezado: list = [
        Paragraph("Ahora tú", s["seccion"]),
        Paragraph(
            "Resuélvelos aquí mismo. Si te atoras, la pista está debajo del renglón.",
            s["chico"],
        ),
        Spacer(1, 0.3 * cm),
    ]
    piezas: list = []
    for i, ex in enumerate(c.ejercicios, 1):
        grupo: list = [Paragraph(f"{i}. {_limpiar(ex.enunciado)}", s["cuerpo"])]
        # Renglones de verdad para escribir a mano: sin ellos el niño escribe en
        # el margen o en otra hoja, y el cuadernillo deja de ser donde se trabaja.
        renglones = [[""] for _ in range(max(1, ex.renglones))]
        tabla = Table(renglones, colWidths=[16.2 * cm], rowHeights=[0.85 * cm] * len(renglones))
        tabla.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.5, LINEA)]))
        grupo.append(Spacer(1, 0.2 * cm))
        grupo.append(tabla)
        if ex.pista:
            grupo.append(Paragraph(f"Pista: {_limpiar(ex.pista)}", s["chico"]))
        grupo.append(Spacer(1, 0.45 * cm))
        piezas.append(KeepTogether((encabezado + grupo) if i == 1 else grupo))
    return piezas


def _hoja_de_respuestas(c: Cuadernillo, s: dict) -> list:
    """La página que convierte esto en regularización.

    Va al final y en su propia hoja para poder separarla: quien revisa se queda
    con ésta y el niño trabaja con el resto. Sin ella, una mamá que no domina el
    tema no puede corregir, y corregir es la mitad de regularizar.
    """
    con_respuesta = [e for e in c.ejercicios if e.respuesta]
    if not con_respuesta:
        return []
    # En verde y no en naranja: cuando el fajo sale de la impresora hay que
    # repartirlo, y este encabezado es lo único que distingue la hoja de quien
    # revisa de las del niño. Un color distinto se ve desde el otro lado del
    # mostrador; un título más no.
    verde = ParagraphStyle("seccion_verde", parent=s["seccion"], textColor=PASTO)
    piezas: list = [
        PageBreak(),
        Paragraph("Para quien revisa", verde),
        Paragraph(
            "Esta hoja se separa. Aquí están las respuestas para poder corregir sin "
            "tener que estudiar el tema.",
            s["chico"],
        ),
        Spacer(1, 0.35 * cm),
    ]
    # El encabezado va sobre banda negra, así que su texto lleva su propio color:
    # `TEXTCOLOR` del TableStyle no pisa el color que ya trae cada Paragraph, y
    # la fila salía en negro sobre negro — vacía a la vista.
    blanco = ParagraphStyle("hdr", parent=s["paso"], textColor=colors.white)
    filas = [[Paragraph("<b>#</b>", blanco), Paragraph("<b>Respuesta</b>", blanco)]]
    for i, ex in enumerate(c.ejercicios, 1):
        if not ex.respuesta:
            continue
        filas.append([Paragraph(str(i), s["paso"]), Paragraph(_limpiar(ex.respuesta), s["paso"])])
    tabla = Table(filas, colWidths=[1.2 * cm, 15 * cm], repeatRows=1)
    tabla.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, 0), PASTO),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("LINEBELOW", (0, 0), (-1, -1), 0.5, LINEA),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    piezas.append(tabla)
    return piezas


def _bloque_precio(c: Cuadernillo, s: dict) -> list:
    """El precio va IMPRESO, y por eso nadie tiene que tasar en el mostrador.

    Va al pie de la primera hoja, que es la que queda arriba cuando se entrega el
    fajo. Lleva el desglose para poder contestar "¿por qué $18?" sin llamar a
    nadie, y dice a color o blanco y negro porque de eso depende el precio.
    """
    d = c.precio()
    tinta = "a color" if d.color else "en blanco y negro"
    izquierda = Paragraph(
        f"<b>Cobrar ${d.total}</b><br/>"
        f"<font size=8 color='#5e564a'>{_limpiar(d.texto)} · impreso {tinta}</font>",
        s["cuerpo"],
    )
    derecha = Paragraph(
        f"<para align=right><font size=22 color='#e05000'><b>${d.total}</b></font></para>",
        s["cuerpo"],
    )
    caja = Table([[izquierda, derecha]], colWidths=[12.2 * cm, 4 * cm])
    caja.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BACKGROUND", (0, 0), (-1, -1), PAPEL_HONDO),
                ("LINEABOVE", (0, 0), (-1, 0), 1.6, FUEGO),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return [Spacer(1, 0.5 * cm), caja]


def _bloque_fuentes(c: Cuadernillo, s: dict) -> list:
    if not c.fuentes:
        return []
    piezas: list = [
        Paragraph("De dónde salió esto", s["seccion"]),
        Paragraph(
            "Si tu maestro pregunta de dónde lo sacaste, aquí está. Poder decirlo "
            "es la diferencia entre haber estudiado y haber copiado.",
            s["chico"],
        ),
        Spacer(1, 0.2 * cm),
    ]
    for f in c.fuentes:
        piezas.append(Paragraph(f"· {_limpiar(f)}", s["chico"]))
    return piezas


def generar(c: Cuadernillo) -> bytes:
    """El PDF completo, en bytes, listo para imprimir o mandar por WhatsApp."""
    buffer = io.BytesIO()
    doc = _Documento(buffer, c)
    s = _estilos()

    piezas: list = []
    piezas += _portada(c, s)
    piezas += _bloque_precio(c, s)
    piezas += _bloque_atore(c, s)
    if c.explicacion:
        piezas.append(Paragraph("Cómo funciona", s["seccion"]))
        for parrafo in c.explicacion:
            piezas.append(Paragraph(_limpiar(parrafo), s["cuerpo"]))
            piezas.append(Spacer(1, 0.22 * cm))
    piezas += _bloque_ejemplos(c, s)
    piezas += _bloque_ejercicios(c, s)
    piezas += _bloque_fuentes(c, s)
    piezas += _hoja_de_respuestas(c, s)

    doc.build(piezas)
    return buffer.getvalue()


def nombre_archivo(c: Cuadernillo) -> str:
    """Se manda por WhatsApp: el nombre tiene que decir qué es y de quién sin abrirlo.

    Distingue lámina de regularización porque son dos productos con dos precios:
    llamar "Regularización" a una infografía suelta confunde a quien cobra.
    """

    def limpio(t: str) -> str:
        sin_acento = unicodedata.normalize("NFKD", t or "").encode("ascii", "ignore").decode()
        return re.sub(r"[^A-Za-z0-9]+", "_", sin_acento).strip("_")[:40]

    que = "Regularizacion" if c.ejercicios else "Lamina"
    partes = [p for p in (que, limpio(c.alumno), limpio(c.tema)) if p]
    return "_".join(partes) + ".pdf"
