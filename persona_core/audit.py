"""El seudónimo de auditoría — agrupar sin identificar (issue #54, decisión 3).

El registro del veredicto de banda necesita saber si 40 turnos en crisis son
**una persona cuarenta veces o cuarenta personas una vez**: clínicamente no es
lo mismo, y sin ningún identificador esa pregunta no se puede contestar. Pero
el `user_id` de Discord completo deja, en un log que se guarda años, una lista
de cuentas reales ligadas a "estuvo en crisis".

La decisión de Álex (2026-09-07, issue #54) es la tercera vía: **un código que
agrupa pero no identifica**, con dos condiciones que NO son opcionales.

## Condición 1 — con llave secreta, o no se guarda nada

Un sha256 pelón del `user_id` es reversible y no un poquito: los IDs de Discord
son un espacio chico y conocido, así que quien tenga la lista de miembros del
servidor los hashea todos y compara. Eso es protección de mentiras.

Por eso el HMAC va con llave (`CRISIS_AUDIT_KEY`) y **sin llave esta función
devuelve `None`** — nunca cae a un hash sin llave. Palabras de Álex: "si se hace
sin llave, prefiero la opción de no guardar nada". El evento sale igual, con el
campo vacío; lo que no sale es un seudónimo falso.

El test que defiende esto es `test_dos_llaves_distintas_dan_codigos_distintos`:
un hash pelón lo reprobaría, porque su resultado no depende de ninguna llave.

## Condición 2 — la llave rota cada mes

Con una llave eterna, el mismo código sigue a la misma persona durante años, y
el día que esa llave se filtre el histórico completo se abre de un jalón. Con
rotación mensual se conserva justo lo que la decisión pedía —distinguir el
patrón DENTRO de una ventana de análisis— y una fuga expone un mes, no la vida
del servidor. Lo que se pierde, dicho de frente: no se puede seguir la
trayectoria de alguien a lo largo del año.

El periodo va **visible al frente del código** (`2026-09:a3f91c…`) para que en
KQL sea imposible agrupar sin querer a través de meses: dos códigos de meses
distintos no son comparables ni cuando pertenecen a la misma persona. El mes no
revela nada que el timestamp del log no dijera ya.

FAIL-SAFE: esto corre en el camino del turno. Cualquier falla devuelve `None`
— un evento sin seudónimo, nunca una excepción que suba.
"""

from __future__ import annotations

import hmac
import os
from datetime import UTC, datetime
from functools import lru_cache
from hashlib import sha256

import structlog

# `sha256_payload` es de fi-core (`fi_core.cognitive`) y es lo que el issue #54
# pide explícitamente: "usa sha256_payload de fi-core, no escribas un
# hashlib.sha256 a mano". El import va tolerante A PROPÓSITO, por una razón que
# no es comodidad: sin él, este módulo —el que decide qué se guarda de personas
# reales en crisis— dejaría de poder verificarse en la máquina de Álex, que no
# tiene fi-core instalado. Con el import tolerante, sus 24 tests corren en su
# compu y el hash lo cubre el CI, donde fi-core sí vive.
#
# Y el silencio no es riesgo: media suite de este repo importa `fi_core` al
# tope de sus archivos, así que un CI sin fi-core no llega a "el hash salió
# vacío" — truena mucho antes. En producción, además, la ausencia se avisa.
try:
    from fi_core.cognitive import sha256_payload
except ImportError:  # pragma: no cover — sólo en máquinas sin fi-core
    sha256_payload = None

log = structlog.get_logger()

#: La llave del HMAC. Sin ella no hay seudónimo (condición 1).
AUDIT_KEY_ENV = "CRISIS_AUDIT_KEY"

#: 64 bits de digest. Suficiente para que dos personas del servidor no choquen
#: y corto para leerse en KQL; la protección la da la llave, no el largo.
_DIGEST_CHARS = 16


@lru_cache(maxsize=1)
def _warn_key_missing() -> None:
    """Avisa UNA vez por proceso: en cada turno sería ruido en Log Analytics."""
    log.warning(
        "crisis_audit_key_missing",
        env=AUDIT_KEY_ENV,
        consecuencia="los eventos de banda salen sin seudónimo de usuario",
    )


@lru_cache(maxsize=1)
def _warn_fi_core_missing() -> None:
    """Avisa UNA vez por proceso que los eventos van sin `audit_hash`."""
    log.warning(
        "crisis_audit_hash_unavailable",
        motivo="fi_core.cognitive.sha256_payload no se pudo importar",
        consecuencia="los eventos de banda salen sin audit_hash",
    )


def audit_period(now: datetime | None = None) -> str:
    """El periodo de rotación de la llave: el mes en UTC, como `2026-09`."""
    moment = now or datetime.now(UTC)
    return f"{moment.year:04d}-{moment.month:02d}"


def pseudonymous_user(user_id: str, *, now: datetime | None = None) -> str | None:
    """El código seudónimo de esta persona para el mes en curso, o `None`.

    Devuelve `None` —y el evento se emite sin seudónimo— cuando no hay
    `user_id`, cuando no hay llave en el entorno, o ante cualquier falla. Nunca
    devuelve un hash sin llave: esa es la condición 1 de la decisión.
    """
    if not user_id:
        return None
    key = os.environ.get(AUDIT_KEY_ENV, "").strip()
    if not key:
        _warn_key_missing()
        return None
    try:
        period = audit_period(now)
        digest = hmac.new(key.encode(), f"{period}:{user_id}".encode(), sha256).hexdigest()
        return f"{period}:{digest[:_DIGEST_CHARS]}"
    except Exception:
        # Sin `user_id` en el log: sería filtrar justo lo que este módulo protege.
        log.exception("crisis_audit_pseudonym_failed")
        return None


# ---------------------------------------------------------------------------
# Los dos eventos del veredicto (issue #54)
# ---------------------------------------------------------------------------
#
# Este módulo NO importa `persona_core.behavior` a propósito: recibe valores
# planos. Así el registro no arrastra a fi-core, y sus tests corren en una
# máquina sin el paquete instalado — que es exactamente la de Álex.
#
# POR QUÉ SON DOS Y NO UNO. La lección fundadora de este repo
# (`.claude/rules/router-observability.md`) es que `recovered_without_context`
# era un contador INALCANZABLE: su cero no significaba "no pasó", significaba
# "no puede pasar". Un solo evento de crisis tiene esa forma — si el detector
# se rompe mañana, deja de emitir y el silencio se lee idéntico a "no hubo
# crisis esta semana". El segundo evento es el denominador: mientras
# `crisis_band_absent` suba, sabemos que los turnos siguen llegando, y un
# `classified` en cero pasa a ser una alarma en vez de una buena noticia.
#
# La prueba de la regla, aplicada: si la banda estuviera rota ahora mismo,
# `crisis_band_classified` dejaría de aparecer en KQL **y** `crisis_band_absent`
# subiría con `reason=crisis_band_failed`. Sube algo. No es decorativo.

#: El veredicto de este turno.
CLASSIFIED_EVENT = "crisis_band_classified"

#: El turno que pasó sin veredicto — el denominador.
ABSENT_EVENT = "crisis_band_absent"

#: `reasons` recortado a 3 (decisión 2 de Álex, 2026-09-07): es el número que
#: ya corre en observación y ya está medido. Se ajusta cuando haya una semana
#: de log real enfrente, no antes.
MAX_REASONS = 3

#: Bandas que NO llevan seudónimo (decisión de Álex, 2026-09-08). El veredicto
#: se registra en TODOS los turnos —si no, no hay denominador— pero el código
#: de persona sólo aparece cuando hubo algo que mirar. Sin esto, el log
#: terminaría con un identificador pegado a cada mensaje del clima.
BANDS_WITHOUT_PSEUDONYM = frozenset({"LOW"})


def _audit_hash(payload: dict[str, object]) -> str | None:
    """El sha256 del payload — la prueba de que el renglón no se editó después.

    Es la disciplina del patrón `DomainEvent`: **la decisión y su registro son
    la misma operación**, no "se decide y ojalá alguien loguee". Un veredicto
    sobre una persona en crisis que se puede reescribir en el log a posteriori
    no es un registro auditable, es una nota.

    Lo que el hash CUBRE: todo lo que sale en el evento, el nombre del evento
    incluido (si no, un `crisis_band_absent` podría reetiquetarse como
    veredicto sin que el hash se moviera).

    Lo que NO cubre, dicho de frente: el `TimeGenerated` que Azure le pone al
    renglón. Ese sello es de Log Analytics y vive fuera del payload; el hash
    prueba que el CONTENIDO no cambió, no la hora en que se archivó.

    Devuelve `None` si no hay fi-core o si el cálculo falla. El evento sale
    igual: un renglón sin hash sigue siendo mejor que un turno perdido.
    """
    if sha256_payload is None:
        _warn_fi_core_missing()
        return None
    try:
        return sha256_payload(payload)
    except Exception:
        log.exception("crisis_audit_hash_failed")
        return None


def _emit(event: str, **fields: object) -> None:
    """Emite con su hash de auditoría, y se traga cualquier falla.

    El registro NUNCA mata el turno — regla dura del issue #54 y de
    `.claude/rules/robustness.md`. Un campo raro, un serializador atragantado o
    un fi-core ausente cuestan la métrica, jamás la respuesta que alguien está
    esperando del otro lado.
    """
    payload: dict[str, object] = {**fields, "event": event}
    try:
        log.info(event, **fields, audit_hash=_audit_hash(payload))
    except Exception:
        log.exception("crisis_audit_emit_failed", intento=event)


def log_crisis_band_classified(
    *,
    band: str,
    gravity: float,
    reasons: list[str],
    critical_override: bool,
    signals: list[str],
    persona_id: str,
    user_id: str = "",
    now: datetime | None = None,
) -> None:
    """Registra el veredicto de banda de este turno.

    `signals` son los NOMBRES de los grupos que dispararon
    (`matched_acute_groups`), nunca el texto de quien escribió: así se puede
    auditar si la persona entró a presencia de crisis por la razón correcta sin
    guardar una palabra suya (decisión 1 de Álex).
    """
    pseudonym = None if band in BANDS_WITHOUT_PSEUDONYM else pseudonymous_user(user_id, now=now)
    _emit(
        CLASSIFIED_EVENT,
        band=band,
        gravity=gravity,
        reasons=list(reasons[:MAX_REASONS]),
        critical_override=critical_override,
        signals=list(signals),
        persona_id=persona_id,
        user_id=pseudonym,
    )


def log_crisis_band_absent(*, persona_id: str, reason: str) -> None:
    """Registra un turno que pasó por el guardián y NO produjo veredicto.

    `reason` dice cuál de los caminos fue (`mensaje_vacio`,
    `crisis_band_failed`, `guidance_build_failed`), que es la diferencia entre
    "no había nada que clasificar" y "el detector se cayó".

    Va con `user_id=None` siempre y a propósito. La tabla del issue lo pedía
    con seudónimo; la decisión de Álex del 2026-09-08 lo recorta, porque sin
    veredicto no sabemos si el turno era grave y el apodo sólo va en los
    graves. El campo se emite vacío en vez de omitirse para que en KQL el
    hueco se vea, en lugar de parecer un evento de otra forma.
    """
    _emit(ABSENT_EVENT, persona_id=persona_id, user_id=None, reason=reason)
