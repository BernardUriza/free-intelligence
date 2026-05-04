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

import anthropic
import structlog

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


def _extract_conversation_topics(recent_messages: list[dict]) -> str:
    """Extract key topics from recent messages for context-aware generation."""
    if not recent_messages:
        return ""
    # Use last 10 messages, full content (up to 300 chars each)
    lines = []
    for m in recent_messages[-10:]:
        content = m["content"][:300]
        lines.append(f"{m['user_name']}: {content}")
    return "\n".join(lines)


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

PROACTIVE_PROMPT = """\
You are Insult. You're checking in on your group chat unprompted — nobody asked you to talk.

Generate a SHORT, in-character message. You have FULL CONTEXT of the last conversation below.

## Critical Rules
- Your message MUST connect to the last conversation or what you know about the users
- If the last conversation was emotionally heavy: be gentle but in-character. Reference what was discussed. Don't pivot to random topics.
- If the last conversation was casual: you can be playful, bring up something related, tease.
- If it's been many hours: acknowledge the gap naturally ("siguen vivos?" or reference what they were doing)
- NEVER ask generic questions like "como estan?" or "que onda?" without context
- NEVER bring up random topics unrelated to recent conversation
- Keep it SHORT (1-3 sentences max)
- Use [SEND] to split messages if needed
- NEVER use timestamps, speaker labels, or metadata
- Spanish (Mexican, casual, direct) by default. English only if recent conversation was in English.
- You can include [REACT:emoji] for reaction-only messages

You will receive: current time, conversation context, user facts, and mood analysis.
Respond with ONLY the message to send. Nothing else."""

WORLD_SCAN_PROMPT = """\
You are Insult. You just went online to see what's happening in the world — nobody asked you to.
You came back to the group chat with something you found interesting, outrageous, or worth commenting on.

You have a web search tool. USE IT to find something current and relevant.

## Topic Selection — MUST follow conversation context
You will receive the mood and topics of the last conversation. Your search MUST be related:

- If last conversation was about PSYCHOLOGY/EMOTIONS/RELATIONSHIPS: search for psychology articles, \
humanist perspectives, philosophical essays, relationship research, personal growth content, \
relevant stories or blog posts. NOT gaming news. NOT memes.
- If last conversation was about TECH/PROGRAMMING: search for tech news, AI developments, \
software engineering content, industry drama.
- If last conversation was about ART/CULTURE: search for art exhibitions, cultural events, \
literary criticism, film analysis, music.
- If last conversation was CASUAL/GAMING: search for gaming news, internet culture, memes, \
entertainment.
- If mood is NEUTRAL or no clear topic: use user interests from their facts.

## Style
- Arrive like someone who just saw something: "Oigan, acabo de ver que..." or just drop the take
- Keep it SHORT (2-4 sentences). This is a chat comment, not an article.
- Have an OPINION. Don't just report — react, critique, connect to larger patterns.
- Be provocative: challenge assumptions, expose contradictions, name mechanisms.
- Weave in search results naturally — NEVER say "according to my search" or "I found that"
- You can be excited, outraged, amused, or darkly ironic. Never neutral.
- Use [SEND] if you want dramatic split
- NEVER use timestamps, speaker labels, or metadata
- DO NOT say "According to" or "Based on my research" — that's assistant behavior
- Spanish (Mexican, casual, direct) by default

You will receive: current time, user facts, conversation context with mood, and suggested search topic.
Search the web, find something, and comment on it. Respond with ONLY the message to send."""

# Web search tool for world scan mode
_WORLD_SCAN_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 2,
}


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
    client: anthropic.AsyncAnthropic,
    model: str,
    time_str: str,
    user_facts: dict[str, list[dict]],
    recent_messages: list[dict],
) -> str | None:
    """Generate an in-character context-aware check-in message."""
    facts_lines = []
    for user_name, facts in user_facts.items():
        user_facts_str = ", ".join(f["fact"] for f in facts[:5])
        facts_lines.append(f"- {user_name}: {user_facts_str}")

    facts_section = "\n".join(facts_lines) if facts_lines else "(no user facts yet)"

    # Rich context: mood + full conversation excerpt
    mood = _detect_conversation_mood(recent_messages)
    conversation_context = _extract_conversation_topics(recent_messages)
    last_ts = recent_messages[-1]["timestamp"] if recent_messages else None
    elapsed = _elapsed_description(last_ts)

    user_prompt = (
        f"Current time: {time_str}\n\n"
        f"Time since last message in chat: {elapsed}\n\n"
        f"Conversation mood: {mood}\n\n"
        f"Last conversation:\n{conversation_context or '(no recent messages)'}\n\n"
        f"Users in this chat:\n{facts_section}"
    )

    try:
        response = await client.messages.create(
            model=model,
            max_tokens=256,
            system=PROACTIVE_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        text = response.content[0].text.strip()
        log.info(
            "proactive_message_generated",
            mode="social",
            mood=mood,
            elapsed=elapsed,
            length=len(text),
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
    client: anthropic.AsyncAnthropic,
    model: str,
    time_str: str,
    user_facts: dict[str, list[dict]],
    recent_messages: list[dict] | None = None,
) -> WorldScanResult | None:
    """Generate an in-character world scan message using web search.

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
        response = await client.messages.create(
            model=model,
            max_tokens=512,
            system=WORLD_SCAN_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            tools=[_WORLD_SCAN_SEARCH_TOOL],
        )

        # Extract text from response (skip server-side search tool blocks)
        text_parts = []
        for block in response.content:
            if hasattr(block, "text"):
                text_parts.append(block.text)

        text = "\n".join(text_parts).strip()
        log.info(
            "proactive_message_generated",
            mode="world_scan",
            mood=mood,
            length=len(text),
            search_topic=search_topic,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
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
