"""Invariantes de arranque — lo que el servidor se niega a hacer aunque se lo pidan.

Dos configuraciones se ven idénticas a un servidor sano y no lo son: una que
deja los expedientes abiertos, y una que atiende a terceros con la suscripción
personal de Bernard. Ninguna falla; las dos hacen daño en silencio. Por eso se
comprueban al importar, donde revientan a la vista, y no en un warning que nadie
lee.
"""

from __future__ import annotations

import os


class ConfiguracionInsegura(RuntimeError):
    """El servidor arrancaría con los expedientes abiertos y nadie lo pidió."""


class CredencialEquivocada(RuntimeError):
    """Se atendería a terceros con una credencial de uso personal."""


class CandadoHeredado(RuntimeError):
    """El candado de og118 dejaría al cibercafé sin poder preguntar."""


def _var(nombre: str) -> str:
    return (os.getenv(nombre) or "").strip()


def _declarado(nombre: str) -> bool:
    return _var(nombre).lower() in ("1", "true", "yes")


def exigir_puerta() -> None:
    """Sin token de mostrador, los expedientes quedan abiertos a cualquiera.

    Un deploy que olvidara `FENIX_ADMIN_TOKEN` servía la lista completa
    —nombres de alumnos, escuelas, WhatsApps de las mamás— y arrancaba
    perfecto. El modo abierto sigue existiendo para local, pero hay que
    teclearlo: un estado inseguro por omisión es un accidente esperando; uno
    declarado es una decisión.
    """
    if _var("FENIX_ADMIN_TOKEN") or _declarado("FENIX_MODO_ABIERTO"):
        return
    raise ConfiguracionInsegura(
        "sin FENIX_ADMIN_TOKEN los expedientes quedan abiertos a cualquiera que "
        "alcance el servidor. Pon el token, o declara el modo abierto a "
        "propósito con FENIX_MODO_ABIERTO=1 (sólo para local)."
    )


def exigir_credencial_de_terceros() -> None:
    """Atender a terceros exige llave de API, no la suscripción personal.

    `CLAUDE_CODE_OAUTH_TOKEN` es una credencial de suscripción Max: su licencia
    es de USO PERSONAL. Los niños del cibercafé y el equipo de la papelería son
    terceros, así que servirlos con ese token rompe el ToS de Anthropic —
    aunque técnicamente funcione igual de bien.

    Y el riesgo no es olvidarlo, es la AMBIGÜEDAD: el SDK elige el modo leyendo
    el entorno, así que un contenedor con las dos variables puede seguir en la
    suscripción sin avisar, y se ve idéntico a uno correcto. Aquí se prohíbe esa
    ambigüedad: o hay llave de API, o se declara que este arranque es Bernard
    probando en su máquina.
    """
    if _var("ANTHROPIC_API_KEY"):
        if _var("CLAUDE_CODE_OAUTH_TOKEN"):
            raise CredencialEquivocada(
                "hay ANTHROPIC_API_KEY y CLAUDE_CODE_OAUTH_TOKEN a la vez: el SDK "
                "elige por entorno y no se puede afirmar cuál paga. Quita el token "
                "OAuth del despliegue."
            )
        return
    if _declarado("FENIX_USO_PERSONAL"):
        return
    raise CredencialEquivocada(
        "sin ANTHROPIC_API_KEY este servidor atendería a la papelería y a los "
        "niños con una credencial de suscripción personal, lo que rompe el ToS "
        "de Anthropic. Pon la llave de API, o declara FENIX_USO_PERSONAL=1 si "
        "eres tú probando en tu máquina."
    )


def prohibir_candado_heredado() -> None:
    """`OG118_ACCESS_TOKEN` aquí deja mudo al cibercafé, y el servidor se ve sano.

    og118 es de una sola cuenta y protege sus rutas con un bearer compartido.
    Fénix atiende a dos públicos y separa distinto: el mostrador se identifica
    con `FENIX_ADMIN_TOKEN`, y lo público lo acota la cuota de turnos — un
    bearer no sirve en una PC donde cualquiera se sienta, porque para usarlo
    habría que dejárselo escrito.

    Con la variable puesta, ese bearer corre ANTES de la puerta: `/chat/stream`
    contesta 401 y la puerta nunca llega a autorizar. La página carga, pinta el
    logo y las tarjetas —`/expedientes/rol` es ruta propia y sí pasa—, así que
    el niño escribe su pregunta y recibe un error. Nada falla en los logs.

    En los tests la variable no existe, así que el bearer deja pasar todo y la
    cuota se ejercita como si nada: verde en local, mudo en producción.
    """
    if not _var("OG118_ACCESS_TOKEN"):
        return
    raise CandadoHeredado(
        "OG118_ACCESS_TOKEN está puesto: el bearer de og118 corre antes que la "
        "puerta de Fénix y /chat/stream responderá 401 a las PCs del cibercafé, "
        "con la página cargando bien. Quítalo del despliegue — aquí autoriza "
        "FENIX_ADMIN_TOKEN y acota la cuota de turnos."
    )


def exigir_contrasena_publica() -> None:
    """Sin contraseña, la URL ES la credencial — y una URL se descubre sola.

    `/chat/stream` es lo único que gasta dinero y está expuesto a internet. La
    cuota acota cuánto se puede quemar, pero no impide que un desconocido quede
    conectado a la llave de API de la papelería: basta con dar con la
    dirección, y las direcciones se comparten, se indexan y se escanean.

    El modo sin contraseña sigue existiendo para local, pero hay que teclearlo.
    Igual que con la puerta del mostrador: un estado inseguro por omisión es un
    accidente esperando; declarado, es una decisión.
    """
    if _var("FENIX_TUTOR_PASSWORD") or _declarado("FENIX_TUTOR_ABIERTO"):
        return
    raise ConfiguracionInsegura(
        "sin FENIX_TUTOR_PASSWORD cualquiera que descubra la URL puede gastar la "
        "llave de API de la papelería. Pon la contraseña, o declara el acceso "
        "abierto a propósito con FENIX_TUTOR_ABIERTO=1 (sólo para local)."
    )


def configurar_motor() -> None:
    """Nombra la casita de Fénix: `FENIX_AIRE_PROJECT` → `OG118_AIRE_PROJECT`.

    Fénix corre el runtime de og118 tal cual, así que la variable que nombra la
    casita vive allá. Ésta traduce el nombre de ESTA app al del runtime, y tiene
    que correr ANTES de importar `app`: og118 construye su runner al importar el
    módulo, no al primer request.

    `OG118_AIRE_PROJECT` nombra la casita base Y prefija la de cada chat, así que
    sin esto los chats de Fénix nacerían como `og118-{conversationId}` y las dos
    apps compartirían casita base — cada runner init-earía la misma con SU
    persona y el último en arrancar ganaría.

    **`FENIX_BACKEND` desapareció el 2026-08-29.** Elegía entre `claude-code` y
    `aire`, y ya no hay dos motores: la flota se consolidó en la puerta de AIRE
    y los hosts locales del SDK/CLI se borraron de fi-runner. Una variable que
    selecciona entre una sola opción no es configuración, es un residuo que la
    siguiente sesión lee como si todavía decidiera algo.
    """
    os.environ["OG118_AIRE_PROJECT"] = _var("FENIX_AIRE_PROJECT") or "fenix"


def exigir_config() -> None:
    """Todas las invariantes, en el orden en que duelen."""
    exigir_puerta()
    exigir_credencial_de_terceros()
    prohibir_candado_heredado()
    exigir_contrasena_publica()
