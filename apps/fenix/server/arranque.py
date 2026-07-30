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


def exigir_config() -> None:
    """Todas las invariantes, en el orden en que duelen."""
    exigir_puerta()
    exigir_credencial_de_terceros()
