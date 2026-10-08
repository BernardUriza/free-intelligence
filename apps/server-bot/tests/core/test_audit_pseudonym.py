"""El seudónimo de auditoría cumple las dos condiciones de Álex (issue #54).

La decisión 3 del #54 no fue "guardar el user_id hasheado". Fue un código que
**agrupa pero no identifica**, con dos condiciones que forman parte de la
decisión: que se haga con llave secreta, y —al implementarlo, 2026-09-08— que
esa llave rote cada mes.

Los dos tests que sostienen el archivo son los negativos:

- `test_sin_llave_no_hay_seudonimo`: si no hay llave, NO se guarda nada. Un
  fallback a hash pelón sería "protección de mentiras", que es la frase con la
  que Álex lo rechazó.
- `test_dos_llaves_distintas_dan_codigos_distintos`: **un sha256 pelón reprueba
  este test**, porque su salida no depende de ninguna llave. Es el arnés que
  detecta que alguien "simplificó" el HMAC en un refactor futuro.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from persona_core.audit import AUDIT_KEY_ENV, audit_period, pseudonymous_user

UNA_PERSONA = "284712993456127001"
OTRA_PERSONA = "284712993456127002"

SEPTIEMBRE = datetime(2026, 9, 8, 15, 20, tzinfo=UTC)
OCTUBRE = datetime(2026, 10, 1, 0, 5, tzinfo=UTC)


@pytest.fixture
def con_llave(monkeypatch):
    """El entorno de producción: la llave existe."""
    monkeypatch.setenv(AUDIT_KEY_ENV, "llave-de-prueba-no-es-la-de-produccion")


# ---------------------------------------------------------------------------
# Las dos condiciones de la decisión
# ---------------------------------------------------------------------------


def test_sin_llave_no_hay_seudonimo(monkeypatch):
    """Condición 1: sin llave se guarda NADA, nunca un hash pelón."""
    monkeypatch.delenv(AUDIT_KEY_ENV, raising=False)
    assert pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE) is None


def test_una_llave_vacia_cuenta_como_no_tener_llave(monkeypatch):
    """`CRISIS_AUDIT_KEY=""` en el App Service es la falla realista, no la ausencia."""
    monkeypatch.setenv(AUDIT_KEY_ENV, "   ")
    assert pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE) is None


def test_dos_llaves_distintas_dan_codigos_distintos(monkeypatch):
    """Condición 1, por el otro lado: UN SHA256 PELÓN REPRUEBA ESTE TEST.

    Si alguien cambia el HMAC por `sha256(user_id)`, el resultado deja de
    depender de la llave y las dos ramas de abajo empatan. Éste es el guardián
    de que la protección es real y no decorativa.
    """
    monkeypatch.setenv(AUDIT_KEY_ENV, "llave-A")
    con_a = pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE)
    monkeypatch.setenv(AUDIT_KEY_ENV, "llave-B")
    con_b = pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE)
    assert con_a != con_b


def test_la_llave_rota_cada_mes(con_llave):
    """Condición 2: la misma persona es otro código el mes siguiente."""
    assert pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE) != pseudonymous_user(UNA_PERSONA, now=OCTUBRE)


def test_el_periodo_va_visible_al_frente(con_llave):
    """Para que en KQL no se pueda agrupar sin querer a través de meses."""
    assert pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE).startswith("2026-09:")
    assert pseudonymous_user(UNA_PERSONA, now=OCTUBRE).startswith("2026-10:")
    assert audit_period(SEPTIEMBRE) == "2026-09"


# ---------------------------------------------------------------------------
# Lo que el código tiene que seguir sirviendo: agrupar
# ---------------------------------------------------------------------------


def test_la_misma_persona_en_el_mismo_mes_agrupa(con_llave):
    """40 turnos de una persona tienen que verse como una, no como 40."""
    assert pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE) == pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE)


def test_dos_personas_distintas_no_se_confunden(con_llave):
    """...y 40 personas una vez tienen que verse como 40."""
    assert pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE) != pseudonymous_user(OTRA_PERSONA, now=SEPTIEMBRE)


def test_el_codigo_no_contiene_el_user_id(con_llave):
    """Lo obvio, escrito: el identificador de Discord no viaja al log."""
    assert UNA_PERSONA not in pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE)


# ---------------------------------------------------------------------------
# Fail-safe — esto corre en el camino del turno
# ---------------------------------------------------------------------------


def test_sin_user_id_no_hay_seudonimo(con_llave):
    """Un turno sin usuario (webhook, sistema) no inventa un código."""
    assert pseudonymous_user("", now=SEPTIEMBRE) is None


def test_una_falla_adentro_devuelve_none_y_no_revienta(con_llave, monkeypatch):
    """La regla dura del issue: el registro no puede matar el turno."""

    def truena(*_args, **_kwargs):
        raise RuntimeError("el hmac se atragantó")

    monkeypatch.setattr("persona_core.audit.hmac.new", truena)
    assert pseudonymous_user(UNA_PERSONA, now=SEPTIEMBRE) is None
