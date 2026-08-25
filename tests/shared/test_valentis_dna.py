"""Valentis acompaña, no trata (issue #41).

Valentis es la persona de acompañamiento psicológico: la amistad con columna.
Escucha, opina honesto, desdramatiza con humor y sabe cuándo tender el puente
al profesional — sin soltar la mano. Su ADN lo escribió Álex, que es quien
tiene el oficio clínico, y varias de sus frases son textuales suyas.

QUÉ PRUEBA ESTE ARCHIVO — y qué NO. No se puede testear lo que el modelo va a
decir: cada respuesta es distinta y ninguna aserción la alcanza. Lo que sí se
puede testear es que el ADN conserve las decisiones clínicas que producen ese
comportamiento. Es un test del texto, no del bot, y decirlo es parte de la
honestidad del arnés.

Lo que se protege, y por qué cada cosa:

Positivo:
  1. el archivo existe y tiene cuerpo — sin esto todo lo demás es verde
     decorativo sobre una cadena vacía;
  2. las líneas de crisis con sus números EXACTOS. Un dígito mal en un
     teléfono de crisis no es un typo: es una persona marcando a la nada.

Resistencia — cada una es una regla que se puede perder reescribiendo el texto
sin darse cuenta de que se perdió:
  1. las líneas de crisis viven en el escenario de crisis Y traen su propia
     prohibición de recitarse fuera de él. Dichas a destiempo son alarma;
  2. derivar NUNCA cierra la conversación. La frase de derivación tiene que
     llevar la continuidad en la misma respiración — media frase sin la otra
     mitad es el rebote seco que Álex vivió y que este ADN existe para evitar;
  3. no se diagnostica, con las tres puertas cerradas: nombrar el trastorno,
     confirmarlo y descartarlo;
  4. no se promete secreto absoluto — el límite se nombra ANTES, con la frase
     textual de Álex, no como reglamento después;
  5. cero fuga de identidad: Valentis nunca nombra la tecnología que la hace
     posible. Post-purga NO existe guardia regex que lo ataje — esta línea del
     ADN carga sola con esa responsabilidad (ver .claude/rules/persona.md).
"""

from __future__ import annotations

from pathlib import Path

DNA = Path(__file__).resolve().parents[2] / "shared" / "personas" / "valentis.md"

# Los dos teléfonos, tal como se marcan. Se comparan con espacios y todo:
# así están escritos en el ADN y así los va a leer quien esté en crisis.
SAPTEL = "55 5259 8121"
LINEA_DE_LA_VIDA = "800 911 2000"


def dna() -> str:
    """El ADN en minúsculas y con los espacios normalizados a uno solo.

    El colapso de whitespace no es cosmético: el ADN viene acomodado a ~76
    columnas, así que la mitad de las frases que aquí importan están partidas
    por un salto de línea ("no nombras / la tecnología que te hace posible").
    Buscarlas sobre el texto crudo fallaría por el formato, no por el
    contenido — y peor, volvería a fallar sole cada vez que alguien reacomode
    el margen sin cambiar una palabra.
    """
    return " ".join(DNA.read_text(encoding="utf-8").lower().split())


def test_the_dna_file_exists_and_has_a_body():
    """Anti-verde-decorativo: si el archivo desaparece o queda vacío, los
    asserts de abajo buscarían sobre una cadena vacía y fallarían por la razón
    equivocada. Éste falla por la razón correcta y primero."""
    assert DNA.exists(), f"no existe {DNA} — el ADN de Valentis es el issue entero"
    assert len(dna().strip()) > 1000, "el ADN está prácticamente vacío"


def test_crisis_lines_are_present_with_exact_numbers():
    """POSITIVO: los números exactos, ambos. Un dígito mal aquí manda a alguien
    en crisis a marcar a la nada, y ninguna otra prueba lo atraparía."""
    body = dna()
    assert "saptel" in body, "falta SAPTEL"
    assert SAPTEL in body, f"el número de SAPTEL no es {SAPTEL}"
    assert "línea de la vida" in body, "falta la Línea de la Vida"
    assert LINEA_DE_LA_VIDA in body, f"el número de la Línea de la Vida no es {LINEA_DE_LA_VIDA}"


def test_crisis_lines_carry_their_own_prohibition_of_being_recited():
    """RESISTENCIA 1: los teléfonos solos no bastan.

    Una persona no está en crisis todo el tiempo, y un bot que recita los
    números en cada mensaje de tristeza convierte el salvavidas en alarma. El
    ADN dice explícitamente que sólo aparecen en crisis; si alguien reescribe
    el escenario y se lleva esa condición, el texto queda verde y el
    comportamiento cambia por completo.
    """
    body = dna()
    assert "solo aquí" in body or "sólo aquí" in body, (
        "se perdió la condición de que las líneas de crisis aparecen SOLO en crisis"
    )
    assert "no recitas las líneas de crisis fuera de crisis" in body, (
        "se perdió la prohibición explícita de recitar las líneas fuera de crisis"
    )


def test_referral_never_closes_the_conversation():
    """RESISTENCIA 2: la mitad que se pierde primero.

    Ésta es la decisión más cargada del ADN: a Álex le tocó ser referide sin
    tacto en un momento vulnerable, y lo describió como una puerta cerrándose.
    Por eso la frase de derivación trae DOS mitades: el puente al profesional y
    la continuidad del acompañamiento, en la misma respiración. Un test que
    sólo buscara "profesional" daría verde con el rebote seco.
    """
    body = dna()
    assert "sería conveniente revisarlo con un profesional" in body, "se perdió la frase de derivación de Álex"
    assert "mientras tanto podemos continuar aquí" in body, (
        "la derivación perdió su segunda mitad: sin la continuidad es el rebote seco"
    )
    assert "no cierras la puerta al derivar" in body, "se perdió la regla explícita"


def test_diagnosis_is_refused_through_all_three_doors():
    """RESISTENCIA 3: no diagnosticar no es sólo no nombrar el trastorno.

    Decir "no, no tienes depresión" también es diagnosticar — descartar es un
    acto clínico igual que confirmar. Las tres puertas tienen que estar
    cerradas en el texto, no sólo la obvia.
    """
    body = dna()
    assert "no diagnosticas" in body, "se perdió la prohibición de diagnosticar"
    assert "no nombras el trastorno" in body, "se perdió la puerta de nombrar"
    assert "ni lo confirmas ni lo descartas" in body, (
        "se perdieron las puertas de confirmar y descartar — descartar también es diagnosticar"
    )


def test_absolute_secrecy_is_never_promised_and_the_limit_comes_first():
    """RESISTENCIA 4: el límite dicho antes es cuidado; dicho después, traición.

    La frase es textual de Álex y la regla que la acompaña es proactiva: el
    límite se nombra la primera vez que alguien confía terreno delicado, no
    cuando ya pidió el secreto. Si sobrevive la frase pero se pierde el
    "ANTES", el ADN queda describiendo exactamente la traición que evita.
    """
    body = dna()
    assert "no puedo prometerte confidencialidad mientras haya un riesgo que valga la pena atender" in body, (
        "se perdió la frase textual de Álex sobre el límite de la confidencialidad"
    )
    assert "no prometes secreto absoluto" in body, "se perdió la regla"
    assert "el límite se dice antes de que te lo pidan" in body, (
        "se perdió lo proactivo: dicho después se siente traición"
    )


def test_no_identity_leak():
    """RESISTENCIA 5: post-purga esta línea del ADN carga sola.

    La guardia regex que atajaba las fugas de identidad murió con el monolito
    (.claude/rules/persona.md § Character Guard) y no tiene equivalente vivo.
    Hoy lo único que impide que Valentis se describa con vocabulario de
    sistemas es este párrafo — así que se testea como lo que es: la última
    línea de defensa, no un adorno.
    """
    body = dna()
    assert "nunca dices qué eres por dentro" in body, "se perdió la regla de identidad"
    assert "tu mecánica es invisible" in body, "se perdió la invisibilidad de la mecánica"
    assert "no nombras la tecnología que te hace posible" in body, (
        "se perdió la prohibición explícita de nombrar la tecnología"
    )
