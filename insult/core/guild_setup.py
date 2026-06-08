"""Guild setup: system channels for facts & reminders with cyberpunk formatting.

Creates a read-only category with two channels:
- #insult-facts: public log of safe (non-sensitive) extracted facts
- #insult-reminders: public log of reminder creation and delivery

All formatting uses Unicode box-drawing for a terminal/cyberpunk aesthetic.
"""

from __future__ import annotations

import contextlib
import re
from datetime import UTC, datetime
from typing import Protocol

import discord
import structlog

log = structlog.get_logger()


class GuildConfigStore(Protocol):
    """Host-side port for the guild-config slice of the memory store.

    Dependency inversion (demux destilado): guild setup depends on this
    narrow structural interface, NOT the concrete smart-side ``MemoryStore``.
    Any store exposing these two methods satisfies it — which keeps this host
    plumbing free of a ``insult.core.memory`` import. Don't widen it past what
    guild setup actually calls; the debug_server uses a far larger slice and
    is decoupled separately.
    """

    async def get_guild_config(self, guild_id: str) -> dict | None: ...

    async def save_guild_config(
        self,
        guild_id: str,
        category_id: str,
        facts_channel_id: str,
        reminders_channel_id: str,
    ) -> None: ...


# ═══════════════════════════════════════════════════════════════════════════
# Constants
# ═══════════════════════════════════════════════════════════════════════════

CATEGORY_NAME = "INSULT SYSTEMS"
FACTS_CHANNEL_NAME = "insult-facts"
REMINDERS_CHANNEL_NAME = "insult-reminders"

# ═══════════════════════════════════════════════════════════════════════════
# Fact Sensitivity Classifier
# ═══════════════════════════════════════════════════════════════════════════

# Categories from facts.py extraction: identity, profession, location,
# interests, technical, personal, preferences, general

# Categories that are ALWAYS safe to post publicly
_SAFE_CATEGORIES = {"identity", "profession", "location", "interests", "technical", "preferences", "general"}

# The "personal" category needs keyword filtering
_SENSITIVE_PATTERNS = [
    # Health — use (?i) without \b since Spanish accented chars break \b
    re.compile(
        r"(?i)(doctor|m[eé]dico|hospital|enferm|salud|diagnos|cirug[ií]a|"
        r"ansiedad|depres|terapi|pastilla|medicament|s[ií]ntoma|dolor|c[aá]ncer|"
        r"gastro|psic[oó]log|psiquiatr|cl[ií]nica|cita m[eé]dica|"
        r"alergi|operaci|tratamiento|rehabilit|receta|enfermedad)"
    ),
    # Finances
    re.compile(
        r"(?i)(deuda|salario|sueldo|dinero|pr[eé]stamo|quiebra|"
        r"hipoteca|tarjeta.*cr[eé]dito|cuenta.*banco|"
        r"desempleado|despid|cobrar|pagos?.*atrasad)"
    ),
    # Relationships / sexuality
    re.compile(
        r"(?i)(novi[oa]|ex[\s-]?novi|divorci|separad[oa]|infidelidad|"
        r"sexo|sexual|orientaci[oó]n|g[eé]nero|"
        r"aborto|embaraz|relaci[oó]n.*t[oó]xica)"
    ),
    # Beliefs
    re.compile(
        r"(?i)(religi[oó]n|iglesia|ateo|agn[oó]stic|"
        r"vot[oa]r?.*por|partido.*pol[ií]tic|izquierda|derecha|"
        r"feminism|ideolog[ií]a)"
    ),
    # Emotional distress
    re.compile(
        r"(?i)(suicid|autoles|llorar|llorando|p[aá]nico|"
        r"trauma|abuso|acoso|violencia|maltrat)"
    ),
    # Legal
    re.compile(
        r"(?i)(arrestad|detenid|c[aá]rcel|demanda|juicio|"
        r"abogado|multa|infracci[oó]n|antecedentes)"
    ),
]


def is_fact_safe(fact: dict) -> bool:
    """Return True if a fact is safe to post in a public channel.

    Categories like 'interests', 'technical', 'profession' are always safe.
    'personal' facts are checked against sensitive keyword patterns.
    """
    category = fact.get("category", "general")

    # Non-personal categories are safe
    if category in _SAFE_CATEGORIES and category != "general":
        return True

    # For 'personal' and 'general', check content
    text = fact.get("fact", "")
    return not any(p.search(text) for p in _SENSITIVE_PATTERNS)


def filter_safe_facts(facts: list[dict]) -> list[dict]:
    """Filter a list of facts to only include publicly safe ones."""
    return [f for f in facts if is_fact_safe(f)]


# ═══════════════════════════════════════════════════════════════════════════
# Cyberpunk Formatter
# ═══════════════════════════════════════════════════════════════════════════


def format_fact_logged(user_name: str, facts: list[dict], channel_name: str = "") -> str:
    """Format new facts for the #insult-facts channel."""
    now = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    lines = ["```"]
    lines.append("░▒▓ FACT LOGGED ▓▒░")
    lines.append(f"║ subject: {user_name}")
    for f in facts:
        lines.append(f"║ [{f.get('category', '?')}] «{f['fact']}»")
    if channel_name:
        lines.append(f"║ src: #{channel_name} · {now}")
    else:
        lines.append(f"║ ts: {now}")
    lines.append("╚" + "═" * 40 + "╝")
    lines.append("```")
    return "\n".join(lines)


def format_reminder_set(
    description: str,
    remind_at_str: str,
    user_mentions: str = "",
    recurring: str = "none",
    reminder_id: int | None = None,
) -> str:
    """Format a new reminder for the #insult-reminders channel."""
    lines = ["```"]
    lines.append("░▒▓ REMINDER SET ▓▒░")
    if reminder_id:
        lines.append(f"║ id: #{reminder_id}")
    if user_mentions:
        lines.append(f"║ target: {user_mentions}")
    lines.append(f"║ eta: {remind_at_str}")
    lines.append(f"║ «{description}»")
    if recurring != "none":
        lines.append(f"║ recurring: {recurring}")
    lines.append("╚" + "═" * 40 + "╝")
    lines.append("```")
    return "\n".join(lines)


def format_reminder_delivered(
    description: str,
    user_mentions: str = "",
    reminder_id: int | None = None,
) -> str:
    """Format a delivered reminder for the #insult-reminders channel."""
    now = datetime.now(UTC).strftime("%d/%m/%Y %H:%M UTC")
    lines = ["```"]
    lines.append("▓▒░ DELIVERED ░▒▓")
    if reminder_id:
        lines.append(f"║ id: #{reminder_id}")
    lines.append(f"║ «{description}»")
    if user_mentions:
        lines.append(f"║ → {user_mentions}")
    lines.append(f"║ status: SENT ✓ · {now}")
    lines.append("╚" + "═" * 40 + "╝")
    lines.append("```")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════
# Guild Setup
# ═══════════════════════════════════════════════════════════════════════════


def _readonly_overwrites(guild: discord.Guild) -> dict:
    """Build permission overwrites: everyone reads, only bot writes."""
    return {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=False,
            add_reactions=False,
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            embed_links=True,
        ),
    }


async def _ensure_category(guild: discord.Guild, name: str, overwrites: dict) -> discord.CategoryChannel:
    """Get existing category or create it. Idempotent."""
    existing = discord.utils.get(guild.categories, name=name)
    if existing:
        return existing
    return await guild.create_category(name, overwrites=overwrites)


async def _ensure_text_channel(
    guild: discord.Guild,
    name: str,
    category: discord.CategoryChannel,
    overwrites: dict,
    topic: str = "",
) -> discord.TextChannel:
    """Get existing channel in category or create it. Idempotent."""
    existing = discord.utils.get(guild.text_channels, name=name, category=category)
    if existing:
        return existing
    return await guild.create_text_channel(name, category=category, overwrites=overwrites, topic=topic)


async def setup_guild(guild: discord.Guild, memory: GuildConfigStore) -> dict:
    """Create system channels for the guild. Idempotent.

    Returns dict with category_id, facts_channel_id, reminders_channel_id.
    """
    bot_member = guild.me
    if not bot_member.guild_permissions.manage_channels:
        raise PermissionError("Bot needs Manage Channels permission")

    overwrites = _readonly_overwrites(guild)

    category = await _ensure_category(guild, CATEGORY_NAME, overwrites)
    facts_ch = await _ensure_text_channel(
        guild,
        FACTS_CHANNEL_NAME,
        category,
        overwrites,
        topic="System feed: extracted user facts (filtered for privacy)",
    )
    reminders_ch = await _ensure_text_channel(
        guild,
        REMINDERS_CHANNEL_NAME,
        category,
        overwrites,
        topic="System feed: reminder creation and delivery log",
    )

    await memory.save_guild_config(
        guild_id=str(guild.id),
        category_id=str(category.id),
        facts_channel_id=str(facts_ch.id),
        reminders_channel_id=str(reminders_ch.id),
    )

    log.info(
        "guild_setup_complete",
        guild=guild.name,
        category=category.name,
        facts_channel=facts_ch.name,
        reminders_channel=reminders_ch.name,
    )

    # Send welcome message to facts channel
    welcome = (
        "```\n"
        "░▒▓ INSULT FACTS SYSTEM ONLINE ▓▒░\n"
        "║\n"
        "║ Este canal registra lo que Insult\n"
        "║ aprende de cada usuario.\n"
        "║\n"
        "║ Solo se publican facts seguros.\n"
        "║ Info sensible (salud, finanzas,\n"
        "║ relaciones) se filtra.\n"
        "║\n"
        "╚════════════════════════════════════╝\n"
        "```"
    )
    with contextlib.suppress(discord.HTTPException):
        await facts_ch.send(welcome)

    # Send welcome to reminders channel
    welcome_rem = (
        "```\n"
        "░▒▓ INSULT REMINDERS LOG ONLINE ▓▒░\n"
        "║\n"
        "║ Registro de recordatorios creados\n"
        "║ y entregados por Insult.\n"
        "║\n"
        "║ Los reminders se entregan en el\n"
        "║ canal original. Aquí solo es log.\n"
        "║\n"
        "╚════════════════════════════════════╝\n"
        "```"
    )
    with contextlib.suppress(discord.HTTPException):
        await reminders_ch.send(welcome_rem)

    return {
        "category_id": str(category.id),
        "facts_channel_id": str(facts_ch.id),
        "reminders_channel_id": str(reminders_ch.id),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Channel Posting Helpers
# ═══════════════════════════════════════════════════════════════════════════


async def post_facts_to_channel(
    bot: discord.Client,
    memory: GuildConfigStore,
    guild_id: str,
    user_name: str,
    new_facts: list[dict],
    old_facts: list[dict],
    channel_name: str = "",
) -> None:
    """Post newly added safe facts to the #insult-facts channel."""
    config = await memory.get_guild_config(guild_id)
    if not config or not config["facts_channel_id"]:
        return

    # Find facts that are new (not in old_facts)
    old_texts = {f["fact"] for f in old_facts}
    added = [f for f in new_facts if f["fact"] not in old_texts]
    if not added:
        return

    # Filter for safety
    safe_added = filter_safe_facts(added)
    if not safe_added:
        return

    channel = bot.get_channel(int(config["facts_channel_id"]))
    if not channel:
        return

    msg = format_fact_logged(user_name, safe_added, channel_name)
    try:
        await channel.send(msg)
        log.debug("facts_posted_to_channel", user_name=user_name, count=len(safe_added))
    except discord.HTTPException:
        log.warning("facts_channel_post_failed", guild_id=guild_id)


async def post_reminder_set(
    bot: discord.Client,
    memory: GuildConfigStore,
    guild_id: str,
    description: str,
    remind_at_str: str,
    user_mentions: str = "",
    recurring: str = "none",
    reminder_id: int | None = None,
) -> None:
    """Post reminder creation to the #insult-reminders channel."""
    config = await memory.get_guild_config(guild_id)
    if not config or not config["reminders_channel_id"]:
        return

    channel = bot.get_channel(int(config["reminders_channel_id"]))
    if not channel:
        return

    msg = format_reminder_set(description, remind_at_str, user_mentions, recurring, reminder_id)
    try:
        await channel.send(msg)
    except discord.HTTPException:
        log.warning("reminder_channel_post_failed", guild_id=guild_id)


async def post_reminder_delivered(
    bot: discord.Client,
    memory: GuildConfigStore,
    guild_id: str | None,
    description: str,
    user_mentions: str = "",
    reminder_id: int | None = None,
) -> None:
    """Post reminder delivery to the #insult-reminders channel."""
    if not guild_id:
        return
    config = await memory.get_guild_config(guild_id)
    if not config or not config["reminders_channel_id"]:
        return

    channel = bot.get_channel(int(config["reminders_channel_id"]))
    if not channel:
        return

    msg = format_reminder_delivered(description, user_mentions, reminder_id)
    try:
        await channel.send(msg)
    except discord.HTTPException:
        log.warning("reminder_delivered_post_failed", guild_id=guild_id)
