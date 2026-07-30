"""El presupuesto de turnos: lo único que acota el gasto en la superficie pública.

Autenticar no lo hace — el bearer vive en el navegador de una máquina donde
cualquiera se sienta. Ver la cabecera de `cuota.py`.
"""

import pytest

from cuota import Cuota, CuotaAgotada, clave_de


class Reloj:
    """Tiempo controlado: probar ventanas con sleeps reales sería lento y flaky."""

    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t

    def avanza(self, segundos: float) -> None:
        self.t += segundos


def test_la_rafaga_se_corta_en_seco():
    reloj = Reloj()
    c = Cuota(por_minuto=3, por_hora=100, reloj=reloj)
    for _ in range(3):
        c.consumir("ip")
    with pytest.raises(CuotaAgotada):
        c.consumir("ip")


def test_pasado_el_minuto_se_puede_seguir():
    """El límite frena un bucle, no castiga a quien trabaja despacio."""
    reloj = Reloj()
    c = Cuota(por_minuto=3, por_hora=100, reloj=reloj)
    for _ in range(3):
        c.consumir("ip")
    reloj.avanza(61)
    c.consumir("ip")


def test_el_techo_por_hora_aguanta_aunque_el_ritmo_sea_humano():
    """Con sólo la ventana de minuto, una tarde entera a ritmo lento no tiene tope."""
    reloj = Reloj()
    c = Cuota(por_minuto=100, por_hora=5, reloj=reloj)
    for _ in range(5):
        reloj.avanza(30)
        c.consumir("ip")
    reloj.avanza(30)
    with pytest.raises(CuotaAgotada):
        c.consumir("ip")


def test_el_turno_rechazado_no_se_cobra():
    """Si el rechazo contara, un cliente que reintenta se auto-extiende el castigo."""
    reloj = Reloj()
    c = Cuota(por_minuto=2, por_hora=100, reloj=reloj)
    c.consumir("ip")
    c.consumir("ip")
    for _ in range(5):
        with pytest.raises(CuotaAgotada):
            c.consumir("ip")
    reloj.avanza(61)
    c.consumir("ip")  # pasado el minuto entra, no arrastra los 5 rechazos


def test_dice_cuanto_falta():
    reloj = Reloj()
    c = Cuota(por_minuto=1, por_hora=100, reloj=reloj)
    c.consumir("ip")
    reloj.avanza(20)
    with pytest.raises(CuotaAgotada) as e:
        c.consumir("ip")
    assert 35 <= e.value.segundos <= 45


def test_cada_quien_su_cubo():
    reloj = Reloj()
    c = Cuota(por_minuto=1, por_hora=100, reloj=reloj)
    c.consumir("una")
    c.consumir("otra")


def test_rotar_la_clave_no_revienta_la_memoria():
    """Un atacante que rota cabeceras haría crecer el dict sin techo."""
    reloj = Reloj()
    c = Cuota(por_minuto=5, por_hora=100, max_claves=10, reloj=reloj)
    for i in range(500):
        reloj.avanza(0.1)
        c.consumir(f"ip-{i}")
    assert len(c._marcas) <= 10


# --- De quién es el turno ----------------------------------------------------


def test_por_default_no_se_cree_la_cabecera(monkeypatch):
    """Confiar en X-Forwarded-For sin proxy vuelve el límite evitable rotándola."""
    monkeypatch.delenv("FENIX_PROXY_CONFIABLE", raising=False)
    assert clave_de("10.0.0.5", "1.2.3.4") == "10.0.0.5"


def test_con_proxy_declarado_se_usa_el_cliente_real(monkeypatch):
    monkeypatch.setenv("FENIX_PROXY_CONFIABLE", "1")
    assert clave_de("10.0.0.5", "1.2.3.4, 10.0.0.1") == "1.2.3.4"


def test_sin_nada_hay_clave_igual(monkeypatch):
    """Sin clave, un turno pasaría sin cobrarse a nadie."""
    monkeypatch.delenv("FENIX_PROXY_CONFIABLE", raising=False)
    assert clave_de(None, None) == "desconocido"
