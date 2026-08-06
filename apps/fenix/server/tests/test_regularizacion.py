"""El cuadernillo y su precio — el entregable de $25 y por qué no cuesta $26.

La escalera de precios la fijó la dirección: $10 la lámina suelta, $25 la
regularización completa, y $25 es el TOPE de la papelería. Estos tests existen
porque un techo que se puede rebasar no es un techo, y porque el precio va
IMPRESO: si sale mal, se cobra mal en el mostrador y nadie lo revisa.
"""

from fastapi.testclient import TestClient

from regularizacion import Cuadernillo, Ejemplo, Ejercicio, Paso, generar, nombre_archivo
from tarifa import PISO, TECHO, calcular


def test_la_lamina_suelta_cuesta_el_piso():
    """"Si sólo quieren la lámina de la cultura postpunk, eso en 10 pesos está
    bien" — la dirección, 6/ago."""
    assert calcular(color=True).total == PISO


def test_la_regularizacion_completa_llega_justo_al_techo():
    """Los escalones suman exactamente $25: ni sobra ni falta valor que cobrar."""
    d = calcular(
        color=True,
        tiene_ejemplos=True,
        tiene_ejercicios=True,
        tiene_respuestas=True,
        tokens=50_000,
        fuentes=3,
    )
    assert d.total == TECHO


def test_nada_en_esta_papeleria_pasa_de_veinticinco():
    """El techo es duro. Una mamá que sabe que nunca pagará más de $25 decide
    más rápido que una que tiene que preguntar."""
    exagerado = calcular(
        color=True,
        tiene_ejemplos=True,
        tiene_ejercicios=True,
        tiene_respuestas=True,
        tokens=10_000_000,
        fuentes=99,
    )
    assert exagerado.total == TECHO


def test_nada_baja_del_piso_aunque_sea_blanco_y_negro():
    """El papel y la tinta ya cuestan; por debajo de $10 se trabaja gratis."""
    assert calcular(color=False).total == PISO


def test_quemar_tokens_sin_traer_fuentes_no_se_le_cobra_al_cliente():
    """Divagar no es investigar. El cliente paga por datos verificados, no por
    lo que le costó al modelo llegar a ellos."""
    assert calcular(tokens=10_000_000, fuentes=0).total == PISO


def test_el_blanco_y_negro_sale_mas_barato_que_el_color():
    completo = dict(tiene_ejemplos=True, tiene_ejercicios=True, tiene_respuestas=True)
    assert calcular(color=False, **completo).total < calcular(color=True, **completo).total


def test_el_desglose_explica_el_precio_renglon_por_renglon():
    """Quien cobra tiene que poder contestar "¿por qué $19?" sin llamar a nadie."""
    d = calcular(color=True, tiene_ejercicios=True, tiene_respuestas=True)
    assert "Ejercicios" in d.texto and "Hoja de respuestas" in d.texto
    assert str(d.total) != "", "el desglose sin total no sirve en el mostrador"


def _cuadernillo_completo() -> Cuadernillo:
    return Cuadernillo(
        tema="Fracciones equivalentes",
        grado="4° de primaria",
        alumno="Mía Noriega",
        se_atora_en="Comparas 2/4 y 1/2 y dices que son distintas.",
        explicacion=["Son equivalentes cuando representan el mismo pedazo."],
        ejemplos=[Ejemplo("¿2/4 es 1/2?", [Paso("Divide entre 2", "Arriba y abajo")], "Sí")],
        ejercicios=[Ejercicio("¿3/6 es 1/2?", respuesta="Sí", pista="Divide entre 3")],
        fuentes=["SEP — Desafíos Matemáticos 4°"],
        tokens=20_000,
    )


def test_el_pdf_sale_y_no_va_vacio():
    datos = generar(_cuadernillo_completo())
    assert datos[:4] == b"%PDF", "no es un PDF"
    assert len(datos) > 2000, "un PDF de dos kilobytes no trae cuadernillo adentro"


def test_las_respuestas_no_se_imprimen_junto_al_ejercicio():
    """Un cuadernillo con la respuesta al lado no se practica: se copia. Por eso
    van en su propia hoja, que se separa."""
    import fitz

    datos = generar(_cuadernillo_completo())
    doc = fitz.open(stream=datos, filetype="pdf")
    paginas = [p.get_text() for p in doc]
    ejercicio = next(i for i, t in enumerate(paginas) if "¿3/6 es 1/2?" in t)
    respuestas = next(i for i, t in enumerate(paginas) if "Para quien revisa" in t)
    assert respuestas > ejercicio, "la hoja de respuestas debe ir DESPUÉS y aparte"


def test_el_precio_va_impreso_en_la_hoja():
    """Nadie tasa en el mostrador: se cobra lo que dice el papel."""
    import fitz

    c = _cuadernillo_completo()
    doc = fitz.open(stream=generar(c), filetype="pdf")
    primera = doc[0].get_text()
    assert f"${c.precio().total}" in primera
    assert "Cobrar" in primera


def test_el_nombre_del_archivo_distingue_lamina_de_regularizacion():
    """Se manda por WhatsApp: llamar "Regularización" a una infografía suelta
    hace que se cobre de más."""
    regu = _cuadernillo_completo()
    lamina = Cuadernillo(tema="La cultura postpunk", alumno="Ángel")
    assert nombre_archivo(regu).startswith("Regularizacion")
    assert nombre_archivo(lamina).startswith("Lamina")
    assert nombre_archivo(lamina).endswith(".pdf")


def test_un_signo_de_menor_no_revienta_el_documento():
    """El modelo escribe "5 < 8" y reportlab lee eso como una etiqueta abierta:
    sin escapar, el PDF entero deja de generarse."""
    c = Cuadernillo(tema="Comparar números", ejercicios=[Ejercicio("¿5 < 8 y 9 > 2?")])
    assert generar(c)[:4] == b"%PDF"


def test_el_markdown_del_modelo_no_se_imprime_como_basura():
    import fitz

    c = Cuadernillo(tema="## Las **fracciones**", explicacion=["Un **medio** es la mitad."])
    doc = fitz.open(stream=generar(c), filetype="pdf")
    texto = doc[0].get_text()
    assert "**" not in texto and "##" not in texto


def test_el_endpoint_lo_pide_el_nino_no_el_mostrador(app_fenix):
    """El cuadernillo se genera en el cibercafé, que es quien lo paga. Lo protege
    la contraseña y la cuota, no el token del mostrador."""
    c = TestClient(app_fenix)
    r = c.post("/expedientes/regularizacion", json={"tema": "Fracciones equivalentes"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert r.headers["X-Fenix-Precio"] == str(PISO)
    assert r.content[:4] == b"%PDF"


def test_el_cliente_no_puede_dictar_su_propio_precio(app_fenix):
    """Si el precio viajara en el request, cualquiera pediría su cuadernillo a $10."""
    c = TestClient(app_fenix)
    r = c.post(
        "/expedientes/regularizacion",
        json={
            "tema": "Fracciones",
            "total": 1,
            "precio": 1,
            "ejercicios": [{"enunciado": "¿3/6 es 1/2?", "respuesta": "Sí"}],
            "ejemplos": [{"enunciado": "x", "pasos": [{"que": "y"}]}],
        },
    )
    assert r.status_code == 200
    # El servidor lo recalcula: lámina + ejemplos + ejercicios + respuestas.
    assert int(r.headers["X-Fenix-Precio"]) == 10 + 4 + 5 + 3


def test_un_cuadernillo_sin_tema_se_rechaza(app_fenix):
    c = TestClient(app_fenix)
    assert c.post("/expedientes/regularizacion", json={"tema": "   "}).status_code == 422
