"""Stat cards (uptime / messages / latency / errors) + the freshness pill and banner."""

from browser import document, html

from py import freshness
from py.state import store
from py.views.shared import fmt_time, fmt_uptime

_PILL_TEXT = {
    freshness.FRESH: "live",
    freshness.STALE: "stale",
    freshness.DEAD: "sin productor",
    freshness.UNDATED: "sin fecha",
    freshness.UNREACHABLE: "sin respuesta",
}

_REAL_OBSERVABILITY = (
    "La observabilidad real vive en Azure Log Analytics (KQL) y en Postgres."
)

_NO_PRODUCER_NOTE = (
    "A esta antigüedad no hay productor: el container que publicaba estos blobs "
    "(discord-bot / plumbing) está retirado a 0 réplicas y no queda ningún uploader "
    f"en el repo. Lo de abajo es un fósil, no el estado del bot. {_REAL_OBSERVABILITY}"
)

_LAGGING_NOTE = (
    "Estos números no son el estado actual del bot; el productor viene atrasado. "
    f"{_REAL_OBSERVABILITY}"
)

_BANNER_NOTE = {
    freshness.STALE: _LAGGING_NOTE,
    freshness.DEAD: _NO_PRODUCER_NOTE,
    freshness.UNDATED: _LAGGING_NOTE,
}

_BANNER_HEADLINE = {
    freshness.STALE: "Datos atrasados",
    freshness.DEAD: "Datos congelados — superficie fósil",
    freshness.UNDATED: "Datos sin fecha — antigüedad desconocida",
    freshness.UNREACHABLE: "Métricas inalcanzables",
}


def render_stats():
    counters = store.metrics.get("counters", {})
    bot = store.metrics.get("bot", {})
    db = store.metrics.get("db", {})

    document["val-uptime"].text = fmt_uptime(store.metrics.get("uptime_seconds", 0))
    document["val-messages"].text = str(db.get("total_messages", counters.get("messages_total", 0)))
    document["val-latency"].text = f"{bot.get('latency_ms', 0)}ms"
    # `llm_errors` died with its emitter (the legacy LLMClient); these three DO fire.
    document["val-errors"].text = str(
        counters.get("facts_failed", 0)
        + counters.get("alice_failovers", 0)
        + counters.get("gateway_zombie_restarts", 0)
    )


def render_freshness():
    state = store.data_state
    age = store.data_age
    age_text = fmt_uptime(age) if age is not None else "?"

    pill = document["status-indicator"]
    pill.text = _PILL_TEXT.get(state, state)
    if state != freshness.UNREACHABLE and age is not None:
        pill.text = f"{pill.text} · {age_text}"
    pill.className = f"status status-{freshness.PILL_CLASS.get(state, 'error')}"

    trustworthy = freshness.is_trustworthy(state)
    document["app"].classList.remove("data-stale")
    if not trustworthy:
        document["app"].classList.add("data-stale")

    _render_banner(state, age_text)


def _render_banner(state, age_text):
    banner = document.select_one("#stale-banner")
    if banner is None:
        return

    if freshness.is_trustworthy(state):
        banner.clear()
        banner.className = "stale-banner"
        banner.style.display = "none"
        return

    banner.clear()
    banner.style.display = ""
    banner.className = f"stale-banner stale-banner-{freshness.PILL_CLASS.get(state, 'error')}"

    banner <= html.DIV(_BANNER_HEADLINE.get(state, "Datos no verificados"), Class="stale-banner-title")

    if state == freshness.UNREACHABLE:
        banner <= html.DIV(
            "El blob de métricas no respondió. Nada de lo que aparece abajo está verificado.",
            Class="stale-banner-body",
        )
        return

    note = _BANNER_NOTE.get(state, _REAL_OBSERVABILITY)
    stamp = fmt_time(store.data_produced_at, "%Y-%m-%d %H:%M", "desconocida")
    detail = (
        f"Última escritura: {stamp} (hace {age_text}). {note}"
        if store.data_produced_at
        else f"El payload no trae timestamp. {note}"
    )
    banner <= html.DIV(detail, Class="stale-banner-body")


def report_data(produced_at):
    store.data_produced_at = produced_at
    store.data_age = freshness.age_of(produced_at)
    store.data_state = freshness.classify(store.data_age)
    render_freshness()


def report_unreachable():
    store.data_produced_at = None
    store.data_age = None
    store.data_state = freshness.UNREACHABLE
    render_freshness()
