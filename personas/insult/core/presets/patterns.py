"""Trigger patterns for the rule-based preset classifier (compiled once).

Pure data + one syntactic helper (``has_channel_noun``). The classifier
(``presets.classifier``) and the LLM-classifier sanity gate
(``presets_llm``) both read from here. Kept separate from the classifier
logic so the ~200 lines of regex tables don't drown the decision code.
"""

import re

from personas.insult.core.patterns import COMMON_STOPWORDS

# META_DEFLECTION triggers — identity probing, jailbreaks, system prompt fishing
_META_PATTERNS = [
    re.compile(r"(?i)\b(eres|are you)\s+(un |una |an? )?(ai|ia|bot|robot|claude|gpt|chatgpt|machine|maquina)\b"),
    re.compile(r"(?i)\b(system prompt|instrucciones|jailbreak|ignore your|olvida tus|pretend you)\b"),
    re.compile(r"(?i)\b(who made you|quien te (hizo|creo|programo)|what model|que modelo)\b"),
    re.compile(r"(?i)\b(eres real|are you real|eres humano|are you human)\b"),
    re.compile(r"(?i)\b(openai|anthropic|language model|modelo de lenguaje)\b"),
    re.compile(r"(?i)\b(DAN|do anything now|act as|actua como)\b"),
]

# RESPECTFUL_SERIOUS triggers — crisis, distress, heavy topics.
#
# This list MUST include the CLINICAL vocabulary users employ when describing
# their own diagnoses or ongoing psychiatric/chronic care, not only lay-person
# crisis phrases. Before this expansion users writing "Estrés Postraumático
# Complejo", "me aumentó la dosis de quetiapina", or "no quisiera internarme"
# matched NOTHING and fell through to DEFAULT_ABRASIVE — the bot would roast
# people describing their own trauma. Real regression reported 2026-04-23
# (see tests/test_presets_clinical.py for verbatim messages).
#
# Design note on \w* suffixes: prefixes like "psiqu[ií]atr" must match
# inflected forms — "psiquiatra", "psiquiatría", "psiquiátrica". A trailing
# \b after a prefix fails because the next char is still a word char. Using
# \w* after the prefix lets the match extend to a real word boundary. For
# compound words where the trigger sits INSIDE (e.g. "postraumático"), we
# add a dedicated prefix alternative.
_SERIOUS_PATTERNS = [
    # Explicit suicide / self-harm
    re.compile(r"(?i)\b(suicid\w*|me quiero morir|i want to die|kill myself|matarme|autolesion\w*|self[- ]harm)"),
    # Lay-person mental-health terms
    re.compile(
        r"(?i)\b(depres(?:ion|sed|i[oó]n)\w*|ansiedad|anxiety|panic attack|ataque de p[aá]nico|burnout|crisis emocional)"
    ),
    # Clinical psychiatric vocabulary (trauma word + compound + acronyms + disorders)
    # "trauma" as standalone OR inside "postraumatic" / "postraumático"
    re.compile(
        r"(?i)(?:"
        r"\btrauma\w*"
        r"|\bpostraum\w*"
        r"|\bpost[- ]traum\w*"
        r"|\bptsd\b"
        r"|\bcptsd\b"
        r"|\btept\b"
        r"|\btdah\b"
        r"|\badhd\b"
        r"|\btoc\b"
        r"|\bocd\b"
        r"|\btrastorno\w*"
        r"|\bdisociaci[oó]n\w*"
        r"|\bdissociat\w*"
        r"|\bbipolar\w*"
        r"|\besquizo\w*"
        r"|\bschizo\w*"
        r"|\bpsicosis\b"
        r"|\bpsychos\w*"
        r"|\bestr[eé]s\s+post[- ]?traum\w*"
        r"|\bestr[eé]s\s+cr[oó]nic\w*"
        r")"
    ),
    # Psychiatric medications (generic stems + common brand names + dosage phrasing)
    re.compile(
        r"(?i)\b("
        r"quetiapin\w*|sertralin\w*|risperid\w*|paroxet\w*|fluoxet\w*|escitalopr\w*|"
        r"olanzapin\w*|clonazepam\w*|alprazolam\w*|lorazepam\w*|diazepam\w*|"
        r"benzodiacep\w*|antidepres\w*|ansiol[ií]tic\w*|neurol[eé]ptic\w*|"
        r"antipsic[oó]tic\w*|psicof[aá]rmac\w*|estabilizador del (?:a)?nimo|"
        r"\bdosis\b|medicaci[oó]n|medication"
        r")"
    ),
    # Mental health professionals and settings
    re.compile(
        r"(?i)\b("
        r"psiqu[ií]atr\w*|psychiatr\w*|neuropsiqu\w*|neuropsych\w*|"
        r"psic[oó]log\w*|psycholog\w*|terapeut\w*|therapist\w*|terapia\b|therapy\b|"
        r"psicoan[aá]l\w*|internarme|internarse|hospitaliz\w*|internamiento|"
        r"pabell[oó]n psiqui\w*|salud mental|mental health"
        r")"
    ),
    # Bereavement, severe illness, disability, chronic conditions
    re.compile(
        r"(?i)\b("
        r"muri[oó]|fallec\w*|died|passed away|c[aá]ncer|diagnostic\w*|"
        r"discapacidad\w*|disabled\w*|cr[oó]nic[ao]\w*|chronic\b|"
        r"artritis|fibromialgi\w*|dolor cr[oó]nic\w*|chronic pain|"
        r"ajustes razonables|accommodations"
        r")"
    ),
    # Abuse, violence, distress
    re.compile(r"(?i)\b(abuso\w*|abuse\w*|violencia|violence|acoso|harassment|bullying|maltrato)"),
    # Direct cries for help / isolation
    re.compile(
        r"(?i)\b(ayuda en serio|help me for real|estoy mal de verdad|i'm really not ok|me siento (?:muy )?solo|i feel (?:so )?alone|no tengo a nadie)"
    ),
]

# ARC triggers — ethics, system critique, vulnerability+depth, identity, contradiction
_ARC_PATTERNS = [
    # System critique / political-ethical
    re.compile(r"(?i)\b(capitalismo|capitalism|neoliberal|explotacion|exploitation)\b"),
    re.compile(r"(?i)\b(patriarcado|patriarchy|machismo|misoginia|misogyny)\b"),
    re.compile(r"(?i)\b(especismo|speciesism|derechos animales|animal rights|antropocentrismo|anthropocentrism)\b"),
    re.compile(r"(?i)\b(colonialismo|colonialism|imperialismo|imperialism)\b"),
    re.compile(r"(?i)\b(desigualdad|inequality|privilegio|privilege|opresor|oppressor|opresion|oppression)\b"),
    re.compile(r"(?i)\b(gentrificacion|gentrification|precariedad|precarity)\b"),
    # Identity and values exploration
    re.compile(r"(?i)\b(que (crees|piensas) (sobre|de) la (justicia|moral|etica))\b"),
    re.compile(r"(?i)\b(what do you (believe|think) about (justice|morality|ethics))\b"),
    re.compile(r"(?i)\b(es (etico|moral|justo)|is it (ethical|moral|fair|just))\b"),
    # Bigotry/discrimination topics (challenge, don't lecture)
    re.compile(r"(?i)\b(racismo|racism|xenofobia|xenophobia)\b"),
    re.compile(r"(?i)\b(homofobia|homophobia|transfobia|transphobia|bifobia)\b"),
    re.compile(r"(?i)\b(discriminacion|discrimination|prejuicio|prejudice|bigotry)\b"),
    re.compile(r"(?i)\b(capacitismo|ableism|gordofobia|fatphobia)\b"),
    # Deep contradictions / sustained depth
    re.compile(r"(?i)\b(no (es|sera) que (en realidad|realmente)|isn't it (really|actually))\b"),
    re.compile(r"(?i)\b(pero (tu mismo|tu misma) dijiste|but you (yourself )?said)\b"),
    re.compile(r"(?i)\b(por que (importa|deberia importar)|why (does it|should it) matter)\b"),
]

# RELATIONAL_PROBE triggers — personal, emotional, life topics
_RELATIONAL_PATTERNS = [
    re.compile(r"(?i)\b(me siento|i feel|tengo miedo|i'm (scared|afraid|worried))\b"),
    re.compile(r"(?i)\b(mi (ex|novia|novio|pareja|esposa|esposo)|my (ex|girlfriend|boyfriend|partner|wife|husband))\b"),
    re.compile(r"(?i)\b(no se que hacer|i don't know what to do|estoy confundido)\b"),
    re.compile(r"(?i)\b(termine con|broke up|me corto|cortamos|we split)\b"),
    re.compile(r"(?i)\b(mi (mama|papa|familia|hijo|hija)|my (mom|dad|family|son|daughter))\b"),
    re.compile(r"(?i)\b(me da (pena|verguenza)|i'm (embarrassed|ashamed))\b"),
    re.compile(r"(?i)\b(necesito (un )?consejo|need advice|que harias tu)\b"),
]

# INTELLECTUAL_PRESSURE triggers — technical, argumentative, analytical.
# Corrections from the user (Spanish vulgar + English) route here so the preset
# can instruct the model to *defend with data or concede grudgingly* instead of
# falling through to DEFAULT_ABRASIVE which has no correction protocol.
_INTELLECTUAL_PATTERNS = [
    re.compile(r"(?i)\b(que opinas de|what do you think about|cual es mejor)\b"),
    re.compile(
        r"(?i)\b(te equivocas|te equivocaste|est[aá]s mal|te pasaste|te confundes|"
        r"te falla|no es cierto|eso no es|you'?re wrong|you got it wrong|"
        r"no estoy de acuerdo|i disagree|actually,?\s+no)\b"
    ),
    re.compile(r"(?i)\b(mi codigo|my code|bug|error|exception|crash|deploy|migration)\b"),
    re.compile(r"(?i)\b(arquitectura|architecture|design pattern|refactor|optimize)\b"),
    re.compile(r"(?i)\b(comparar|compare|versus|vs\.?|pros and cons|trade.?off)\b"),
    re.compile(r"(?i)\b(por que (crees|piensas)|why do you (think|believe))\b"),
    re.compile(r"(?i)\b(explicame|explain|como funciona|how does .+ work)\b"),
    re.compile(r"```"),  # code blocks = technical context
]

# PLAYFUL_ROAST triggers — banter, humor, casual energy.
# Laugh patterns deliberately omit \b so extended laughs like "jajajajaja" match.
# Inside one long laugh word there are no word boundaries between the repeats,
# so \b(jaja)\b would miss it and the message would fall through to DEFAULT.
_PLAYFUL_PATTERNS = [
    re.compile(r"(?i)(?:jaja|jeje|jiji|jojo|haha|hehe|lmao|lol)+"),
    re.compile(r"(?i)\b(xd+|xdd+|xddd+)\b"),
    re.compile(r"[😂🤣💀😹]"),  # laughing/skull emojis — no \b (emojis aren't \w)
    re.compile(r"(?i)\b(no (mames|manches)|wtf|omg|bruh)\b"),
    re.compile(r"(?i)\b(a que no|bet you can't|te reto|i dare you|challenge)\b"),
    re.compile(r"(?i)\b(meme|chiste|joke|funny|gracioso|chistoso)\b"),
    re.compile(r"(?i)\b(que (random|raro|weird)|thats (random|weird))\b"),
]

# ACTION_INTENT modifier triggers — user wants channel creation, info, or editing.
# EVERY pattern below MUST require the word canal/channel/espacio/sala/room in
# the same sentence. Previous version matched "cambia ... nombre" without any
# channel noun, producing false positives on metaphors like "cambia el nombre
# al sistema para ponerles armas y uniformes" — which forced a tool call the
# user never requested. Proximity limit {0,40} keeps phrases local instead of
# spanning half a paragraph via greedy .*
_CHANNEL_NOUN = r"(?:canal|channel|espacio|space|sala|room)"
# Standalone channel-noun probe — used by the LLM-classifier sanity gate
# (`presets_llm`) to reject action_intent emissions that lack any channel
# noun in the message. The LLM occasionally interprets "set up X for Alex"
# as action_intent semantically, ignoring the prompt rule that requires a
# Discord channel noun. The regex below is the syntactic ground truth.
_CHANNEL_NOUN_RE = re.compile(rf"(?i)\b{_CHANNEL_NOUN}\b")


def has_channel_noun(text: str) -> bool:
    """Return True iff ``text`` mentions a Discord channel noun.

    Used as a syntactic gate around the LLM preset classifier: action_intent
    requires an explicit channel/sala/etc. mention. Without one, the modifier
    cannot fire — it forces tool_choice="any" which drives the model into
    no-op tool selections (see v3.8.3 regression).
    """
    if not text:
        return False
    return bool(_CHANNEL_NOUN_RE.search(text))


_ACTION_INTENT_PATTERNS = [
    # Channel creation — verb + channel noun nearby
    re.compile(rf"(?i)\b(crea|crear|hazme|haz|arma|armame|pon|ponme)\b.{{0,40}}\b{_CHANNEL_NOUN}\b"),
    re.compile(rf"(?i)\b{_CHANNEL_NOUN}\b.{{0,40}}\b(crea|crear|haz|hazme|nuevo|new|privado|private)\b"),
    re.compile(rf"(?i)\b(necesito|quiero|dame|give me|i need|i want)\b.{{0,40}}\b{_CHANNEL_NOUN}\b"),
    re.compile(rf"(?i)\b(create|make|set up)\b.{{0,40}}\b{_CHANNEL_NOUN}\b"),
    # Channel info / editing — verb + channel noun + field
    re.compile(rf"(?i)\b(cambia|cambiar|renombra|rename|edita|edit)\b.{{0,40}}\b{_CHANNEL_NOUN}\b"),
    re.compile(rf"(?i)\b{_CHANNEL_NOUN}\b.{{0,40}}\b(se llama|nombre|name|descripcion|description|topic)\b"),
    re.compile(
        rf"(?i)\b(ponle|cambiale|dale)\b.{{0,60}}\b{_CHANNEL_NOUN}\b.{{0,40}}\b(nombre|descripci[oó]n|description|topic)\b"
    ),
    # Same verbs but inverted order: "ponle descripción al canal"
    re.compile(
        rf"(?i)\b(ponle|cambiale|dale)\b.{{0,60}}\b(nombre|descripci[oó]n|description|topic)\b.{{0,40}}\b{_CHANNEL_NOUN}\b"
    ),
]

# Stopwords filtered out when checking memory recall overlap
_RECALL_STOPWORDS = COMMON_STOPWORDS | {"me"}

# CONTEMPT modifier triggers — low-effort messages
_CONTEMPT_PATTERNS = [
    re.compile(r"^\.+$"),  # just dots
    re.compile(r"^[?!]+$"),  # just punctuation
    re.compile(r"^(a+|e+|o+|u+|i+|z+|j+)$", re.I),  # just repeated vowels/letters
    re.compile(r"^.{1,3}$"),  # 1-3 chars (but not matched by others)
]
