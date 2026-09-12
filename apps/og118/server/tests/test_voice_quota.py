"""El tope por principal de las rutas de voz.

POR QUÉ EXISTE (medido 2026-09-09, cuota subida 2026-09-12). El gateway susurro
proxea deployments de Azure aprovisionados por RPM: `whisper` y `tts` están en
`capacity: 30` y ése es el techo de la suscripción (usage 30.0/30.0). El gateway
lo comparten discord-bot, inkbook, picturelock, visalaw-videopipe y el dictado de
og118, así que una llamada manos libres sin tope deja sin voz a toda la flota.

Se prueban las DOS ramas: que el tope corta, y que por debajo del tope no estorba
—una rama apagada sin test se pudre, y aquí la que se pudriría en silencio es la
que rompería el dictado que hoy funciona.
"""

from __future__ import annotations

import pytest

import voice_quota
from fastapi import HTTPException


def test_por_debajo_del_tope_no_estorba(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_VOICE_RPM", "3")
    for _ in range(3):
        voice_quota.verificar_cuota_de_voz("auth0|ana")


def test_la_cuarta_en_un_minuto_es_429_con_retry_after(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_VOICE_RPM", "3")
    for _ in range(3):
        voice_quota.verificar_cuota_de_voz("auth0|ana")

    with pytest.raises(HTTPException) as exc:
        voice_quota.verificar_cuota_de_voz("auth0|ana")

    assert exc.value.status_code == 429
    assert exc.value.detail["code"] == "VOICE_RATE_LIMITED"
    assert int(exc.value.headers["Retry-After"]) >= 1


def test_el_tope_es_POR_sujeto_no_global(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_VOICE_RPM", "1")
    voice_quota.verificar_cuota_de_voz("auth0|ana")
    voice_quota.verificar_cuota_de_voz("auth0|beto")  # otro sujeto, su propia ventana

    with pytest.raises(HTTPException):
        voice_quota.verificar_cuota_de_voz("auth0|ana")


def test_la_ventana_se_desliza(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_VOICE_RPM", "1")
    c = voice_quota.ContadorDeVoz()
    assert c.registrar("ana", 1, ahora=1000.0) == 0.0
    assert c.registrar("ana", 1, ahora=1030.0) > 0  # dentro del minuto: bloquea
    assert c.registrar("ana", 1, ahora=1061.0) == 0.0  # ya salió: pasa


def test_cero_desactiva_el_tope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OG118_VOICE_RPM", "0")
    for _ in range(50):
        voice_quota.verificar_cuota_de_voz("auth0|ana")


def test_el_default_deja_dos_tercios_del_techo_a_la_flota(monkeypatch: pytest.MonkeyPatch) -> None:
    """10 = un tercio del `capacity: 30` de whisper/tts: cabe una llamada de
    turnos cortos, y un sujeto que lo agote no deja sin voz al resto."""
    monkeypatch.delenv("OG118_VOICE_RPM", raising=False)
    assert voice_quota.limite_por_minuto() == 10
