"""Proactive messaging — Insult checks in on users and scans the world.

Two modes:
1. Social check-in (~70%): context-aware messages grounded in recent conversation
2. World scan (~30%): searches the web for content relevant to conversation topics

Architecture follows Nomi AI pattern:
- 3-state activity model (ACTIVE/COOLING_DOWN/IDLE) prevents interruptions
- Exponential backoff on unanswered proactives
- Context-grounded generation (not template-based)
- Topic extraction from recent conversation for world scan relevance
"""

import random
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import structlog

from insult.core.prompts_loader import load_prompt

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Conversation state model
# ---------------------------------------------------------------------------


class ConversationState(Enum):
    """3-state model for conversation activity detection."""

    ACTIVE = "active"  # Someone spoke recently — do NOT interrupt
    COOLING_DOWN = "cooling_down"  # Conversation ended recently — let it settle
    IDLE = "idle"  # Safe to send proactive message


# Thresholds in seconds
ACTIVE_THRESHOLD = 15 * 60  # 15 min — conversation is live
COOLING_THRESHOLD = 2 * 3600  # 2 hrs — conversation settling
# Beyond COOLING_THRESHOLD = IDLE


def get_conversation_state(last_user_message_ts: float | None) -> ConversationState:
    """Determine conversation state from last user message timestamp."""
    if last_user_message_ts is None:
        return ConversationState.IDLE

    elapsed = datetime.now().timestamp() - last_user_message_ts

    if elapsed < ACTIVE_THRESHOLD:
        return ConversationState.ACTIVE
    if elapsed < COOLING_THRESHOLD:
        return ConversationState.COOLING_DOWN
    return ConversationState.IDLE


# ---------------------------------------------------------------------------
# Exponential backoff
# ---------------------------------------------------------------------------

# Base interval between proactive messages (seconds)
BASE_INTERVAL_HOURS = 2.0
MAX_INTERVAL_HOURS = 24.0


def compute_backoff_interval(unanswered_count: int) -> float:
    """Compute wait interval in hours based on unanswered proactive count.

    Each unanswered proactive doubles the wait: 2h → 4h → 8h → 24h (cap).
    Resets to BASE when a user responds after a proactive.
    """
    interval = BASE_INTERVAL_HOURS * (2**unanswered_count)
    return min(interval, MAX_INTERVAL_HOURS)


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------


def should_send_now(
    hour: int,
    last_proactive_ts: float | None,
    last_user_message_ts: float | None,
    unanswered_count: int = 0,
) -> bool:
    """Decide if we should send a proactive message now.

    Checks: quiet hours → conversation state → backoff interval → probability.
    """
    # Quiet hours: 3am-7am, never send
    if 3 <= hour < 7:
        return False

    # Activity state: NEVER interrupt active or cooling conversations
    state = get_conversation_state(last_user_message_ts)
    if state != ConversationState.IDLE:
        log.debug("proactive_suppressed", reason=state.value)
        return False

    # Exponential backoff based on unanswered proactives
    min_interval_hours = compute_backoff_interval(unanswered_count)
    if last_proactive_ts:
        elapsed_hours = (datetime.now().timestamp() - last_proactive_ts) / 3600
        if elapsed_hours < min_interval_hours:
            return False

    # 40% probability per eligible check
    return random.random() < 0.4


def should_world_scan() -> bool:
    """Decide if this proactive message should be a world scan (~30%)."""
    return random.random() < 0.3


# ---------------------------------------------------------------------------
# Conversation mood detection
# ---------------------------------------------------------------------------

_HEAVY_PATTERNS = [
    re.compile(r"(?i)\b(duelo|grief|muerte|death|perdida|loss)\b"),
    re.compile(r"(?i)\b(trauma|depres|ansiedad|anxiety|suicid)\b"),
    re.compile(r"(?i)\b(ghosting|ghoste|bloque|blocked)\b"),
    re.compile(r"(?i)\b(llorar|crying|dolor|pain|culpa|guilt)\b"),
    re.compile(r"(?i)\b(terapia|therapy|psicolog|psycholog)\b"),
    re.compile(r"(?i)\b(abuso|abuse|violencia|violence)\b"),
    re.compile(r"(?i)\b(divorcio|divorce|separacion|breakup|ruptura)\b"),
    re.compile(r"(?i)\b(crisis|emergencia|emergency|hospital)\b"),
]

_CASUAL_PATTERNS = [
    re.compile(r"(?i)\b(jajaj|lol|lmao|xd|hahah)\b"),
    re.compile(r"(?i)\b(meme|chiste|joke|funny|chistos)\b"),
    re.compile(r"(?i)\b(gaming|juego|game|stream|twitch)\b"),
    re.compile(r"(?i)\b(comida|food|comer|cena|dinner|lunch)\b"),
    re.compile(r"(?i)\b(pelicula|movie|serie|show|netflix)\b"),
]


def _detect_conversation_mood(recent_messages: list[dict]) -> str:
    """Detect mood from recent messages: 'heavy', 'intellectual', 'casual', or 'neutral'."""
    if not recent_messages:
        return "neutral"

    text = " ".join(m["content"][:200] for m in recent_messages[-10:])

    heavy_hits = sum(1 for p in _HEAVY_PATTERNS if p.search(text))
    casual_hits = sum(1 for p in _CASUAL_PATTERNS if p.search(text))

    if heavy_hits >= 2:
        return "heavy"
    if casual_hits >= 2:
        return "casual"
    # Check for intellectual/deep discussion (longer messages, no jokes)
    avg_len = sum(len(m["content"]) for m in recent_messages[-5:]) / max(len(recent_messages[-5:]), 1)
    if avg_len > 150 and heavy_hits == 0 and casual_hits == 0:
        return "intellectual"
    return "neutral"


_SELF_LABEL = "YOU (Insult)"


def _extract_conversation_topics(recent_messages: list[dict], self_label: str = _SELF_LABEL) -> str:
    """Extract key topics from recent messages for context-aware generation.

    Distinguishes the bot's own past turns from human user turns so the
    LLM has unambiguous speaker identity. The 2026-05-07 regression
    (request_id at TimeGenerated 04:28:48Z) was a proactive_social
    message where the bot narrated *"bernard2389 sigue creyendo..."*
    as if reporting about Bernard to a third party — because the
    context block formatted user and assistant rows symmetrically as
    ``{name}: {content}``, leaving role ambiguous. By labeling
    assistant rows with ``YOU (Insult)`` we anchor the model in its
    own identity before generation.
    """
    if not recent_messages:
        return ""
    # Use last 10 messages, full content (up to 300 chars each)
    lines = []
    for m in recent_messages[-10:]:
        content = m["content"][:300]
        speaker = self_label if m.get("role") == "assistant" else m.get("user_name") or "user"
        lines.append(f"{speaker}: {content}")
    return "\n".join(lines)


def _extract_participants(recent_messages: list[dict]) -> list[str]:
    """Distinct human user names from the recent window, in first-seen order.

    Excludes the bot itself (``role == "assistant"``). Used by the
    proactive prompt to render an explicit Participants section so
    the model treats them as live interlocutors, not log entries.
    """
    seen: set[str] = set()
    out: list[str] = []
    for m in recent_messages:
        if m.get("role") != "user":
            continue
        name = m.get("user_name")
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


def _elapsed_description(last_user_message_ts: float | None) -> str:
    """Human-readable time since last user message."""
    if not last_user_message_ts:
        return "unknown time"
    elapsed = datetime.now().timestamp() - last_user_message_ts
    hours = elapsed / 3600
    if hours < 1:
        return f"{int(elapsed / 60)} minutos"
    if hours < 24:
        return f"{hours:.1f} horas"
    return f"{elapsed / 86400:.1f} dias"


# ---------------------------------------------------------------------------
# Prompts — context-aware
# ---------------------------------------------------------------------------

# Prompts live in insult/prompts/proactive_social.md and proactive_world_scan.md


# ---------------------------------------------------------------------------
# Search topic selection — conversation-aware
# ---------------------------------------------------------------------------

_MOOD_TOPICS = {
    "heavy": [
        "psychology resilience grief processing research",
        "humanist philosophy relationships loss essays",
        "emotional intelligence research findings",
        "personal growth stories overcoming adversity blog",
        "stoic philosophy practical modern life",
        "attachment theory relationships research",
        "boundary setting healthy relationships psychology",
    ],
    "intellectual": [
        "philosophy contemporary essays thought-provoking",
        "science discoveries implications society",
        "critical theory cultural analysis essays",
        "literary criticism notable books essays",
        "cognitive science consciousness research",
    ],
    "casual": [
        "gaming news releases industry 2026",
        "internet culture memes trending viral",
        "technology gadgets fun interesting",
        "entertainment movies series releases 2026",
        "Mexico noticias cultura trending hoy",
    ],
}

# Word-boundary patterns. Bare substrings ("art" matching "parte" /
# "departamento" / "artista" indiscriminately) caused the bot to default
# to the same single art topic on almost every world_scan — the keyword
# triggered on routine words and the "art" bucket only had one topic.
# Patterns now require whole-word boundaries and Spanish/English variants
# are listed explicitly. Each bucket also holds enough alternatives that
# `random.choice` actually varies what it picks.
_INTEREST_PATTERNS: list[tuple[re.Pattern[str], list[str]]] = [
    (
        re.compile(r"\b(programming|coding|software|developer)\b", re.IGNORECASE),
        ["tech news AI development 2026", "software engineering industry"],
    ),
    (
        re.compile(r"\bpython\b", re.IGNORECASE),
        ["Python programming news updates 2026"],
    ),
    (
        re.compile(r"\b(gaming|videogames?|videojuegos?)\b", re.IGNORECASE),
        ["gaming news releases 2026", "videogames industry drama"],
    ),
    (
        re.compile(r"\b(vegan|veganism|veganismo|vegana?s?)\b", re.IGNORECASE),
        ["animal rights news 2026", "veganism movement"],
    ),
    (
        re.compile(r"\b(music|m[uú]sica|canci[oó]n|banda)\b", re.IGNORECASE),
        [
            "music releases Mexico Latin America 2026",
            "indie music Mexico City scene 2026",
            "Latin alternative music releases 2026",
        ],
    ),
    (
        # "expo" alone matches the word but NOT "exporta"/"exponencial".
        # Same reasoning for the other forms.
        re.compile(r"\b(arte|artista|exposici[oó]n|expo|museo|galer[ií]a|escultura|pintura)\b", re.IGNORECASE),
        [
            "contemporary art exhibitions Mexico 2026",
            "Mexico independent cinema releases 2026",
            "Latin American contemporary literature 2026",
            "experimental theater performance Mexico City 2026",
            "indie music Mexico Latin America scene 2026",
            "documentary photography Mexico 2026",
        ],
    ),
    (
        re.compile(r"\b(pol[ií]tica|elecciones?|gobierno|gobiernos?)\b", re.IGNORECASE),
        ["Mexico politics social movements 2026"],
    ),
    (
        re.compile(r"\b(psicolog[íi]a|terapia|salud mental)\b", re.IGNORECASE),
        ["psychology research findings human behavior"],
    ),
    (
        re.compile(r"\b(filosof[íi]a|fenomenolog[íi]a|epistemolog[íi]a)\b", re.IGNORECASE),
        ["philosophy contemporary essays ideas"],
    ),
]

_DEFAULT_TOPICS = [
    "Mexico noticias trending hoy",
    "psychology human behavior interesting research",
    "cultural events Mexico today",
    "social movements Latin America news",
    "philosophy essays thought provoking",
    "science discoveries 2026",
]


def _pick_search_topic(user_facts: dict[str, list[dict]], mood: str, recent_text: str) -> str:
    """Pick a search topic based on conversation mood first, then user interests."""
    # Priority 1: Mood-based topics (match conversation energy)
    if mood in _MOOD_TOPICS:
        return random.choice(_MOOD_TOPICS[mood])

    # Priority 2: Extract topics from recent conversation text
    matched_topics: list[str] = []
    for pattern, topics in _INTEREST_PATTERNS:
        if pattern.search(recent_text):
            matched_topics.extend(topics)

    # Priority 3: User facts
    if not matched_topics:
        all_facts_text = " ".join(f["fact"] for facts in user_facts.values() for f in facts)
        for pattern, topics in _INTEREST_PATTERNS:
            if pattern.search(all_facts_text):
                matched_topics.extend(topics)

    if matched_topics:
        return random.choice(matched_topics)

    return random.choice(_DEFAULT_TOPICS)


# ---------------------------------------------------------------------------
# Message generation
# ---------------------------------------------------------------------------


async def generate_proactive_message(
    judge,
    model: str,
    time_str: str,
    user_facts: dict[str, list[dict]],
    recent_messages: list[dict],
) -> str | None:
    """Generate an in-character context-aware check-in message.

    Routed through the runner's one-shot ``judge.utility_call`` (/v1/judge,
    OAuth Max). The persona prompt (``proactive_social``) is handed in as the
    system prompt, so Insult's voice survives even though /v1/judge applies
    none of the legacy post-generation guards (character_break, language_cure).
    For a background check-in that tradeoff is fine."""
    facts_lines = []
    for user_name, facts in user_facts.items():
        user_facts_str = ", ".join(f["fact"] for f in facts[:5])
        facts_lines.append(f"- {user_name}: {user_facts_str}")

    facts_section = "\n".join(facts_lines) if facts_lines else "(no user facts yet)"

    # Rich context: mood + full conversation excerpt
    mood = _detect_conversation_mood(recent_messages)
    conversation_context = _extract_conversation_topics(recent_messages)
    participants = _extract_participants(recent_messages)
    last_ts = recent_messages[-1]["timestamp"] if recent_messages else None
    elapsed = _elapsed_description(last_ts)

    # Identity-anchored Participants block. The bot is listed as YOU
    # (not by display name) so the model cannot mistake itself for a
    # third party named "Insult" living in the chat alongside humans.
    if participants:
        participants_block = "\n".join(f"- {p} (human user)" for p in participants)
    else:
        participants_block = "- (no human users have spoken recently)"
    participants_block += f"\n- {_SELF_LABEL} — that's you. NOT a third party."

    user_prompt = (
        f"Current time: {time_str}\n\n"
        f"Time since last message in chat: {elapsed}\n\n"
        f"Conversation mood: {mood}\n\n"
        f"Participants in this thread:\n{participants_block}\n\n"
        f"Recent exchange (chronological — anything labeled '{_SELF_LABEL}' is what YOU already said):\n"
        f"{conversation_context or '(no recent messages)'}\n\n"
        f"Facts you know:\n{facts_section}\n\n"
        "Now write the check-in. Speak DIRECTLY to the human user(s) in second person ('tú/te'). "
        "NEVER narrate any user in third person ('bernard2389 sigue creyendo...') — that's the "
        "speaker-confusion failure mode and reads as cold and alienating. NEVER speak about "
        "yourself in third person — you ARE Insult."
    )

    try:
        response = await judge.utility_call(
            load_prompt("proactive_social"),
            [{"role": "user", "content": user_prompt}],
            model=model,
        )
        text = response.text.strip()
        log.info(
            "proactive_message_generated",
            mode="social",
            mood=mood,
            elapsed=elapsed,
            length=len(text),
            model_used=response.model_used,
        )
        return text if text else None
    except Exception:
        log.exception("proactive_generation_failed", mode="social")
        return None


@dataclass
class WorldScanResult:
    """Result of a world scan — commentary + metadata for persistence."""

    commentary: str  # The in-character message to send
    topic: str  # What was searched for
    findings: str  # Raw summary of what was found


async def generate_world_scan_message(
    judge,
    model: str,
    time_str: str,
    user_facts: dict[str, list[dict]],
    recent_messages: list[dict] | None = None,
) -> WorldScanResult | None:
    """Generate an in-character world scan message.

    Routed through the runner's one-shot ``judge.utility_call`` (/v1/judge).
    NOTE: /v1/judge is text-only — it does NOT run the ``web_search`` server
    tool the legacy path used, so this is now a knowledge-grounded "scan"
    rather than a live web search. Reviving real web search means adding a
    tool-capable endpoint on the runner; until then the commentary is
    generated from the model's own knowledge + the suggested topic.

    Returns WorldScanResult with commentary + metadata, or None on failure.
    """
    mood = _detect_conversation_mood(recent_messages or [])
    recent_text = _extract_conversation_topics(recent_messages or [])
    search_topic = _pick_search_topic(user_facts, mood, recent_text)

    facts_lines = []
    for user_name, facts in user_facts.items():
        user_facts_str = ", ".join(f["fact"] for f in facts[:5])
        facts_lines.append(f"- {user_name}: {user_facts_str}")

    facts_section = "\n".join(facts_lines) if facts_lines else "(no user facts yet)"

    user_prompt = (
        f"Current time: {time_str}\n\n"
        f"Conversation mood: {mood}\n\n"
        f"Last conversation topics:\n{recent_text or '(no recent messages)'}\n\n"
        f"Users in this chat and their interests:\n{facts_section}\n\n"
        f"Suggested search topic (MUST match conversation mood): {search_topic}"
    )

    try:
        response = await judge.utility_call(
            load_prompt("proactive_world_scan"),
            [{"role": "user", "content": user_prompt}],
            model=model,
        )
        text = response.text.strip()
        log.info(
            "proactive_message_generated",
            mode="world_scan",
            mood=mood,
            length=len(text),
            search_topic=search_topic,
            model_used=response.model_used,
        )
        if not text:
            return None

        return WorldScanResult(
            commentary=text,
            topic=search_topic,
            findings=text[:500],
        )
    except Exception:
        log.exception("proactive_generation_failed", mode="world_scan")
        return None
