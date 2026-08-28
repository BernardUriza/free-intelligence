"""PSYCHIATRY's weighted signal corpora — migrated from the canary, not invented.

Provenance matters more than usual here, because these patterns decide whether
a person in crisis meets presence or meets a joke:

- The six CHRONIC groups and their weights migrate VERBATIM from discord-bot's
  ``khimeras_shared/behavior/vulnerability.py`` (``_SIGNAL_GROUPS`` +
  ``VULNERABLE_THRESHOLD``), where they ran in production since 2026-04-23.
  The weights were chosen so a single heavy signal is not enough on its own,
  but two correlated signals (diagnosis + medication) clear the threshold.
- The five ACUTE groups migrate verbatim from the same module's
  ``_ACUTE_CRISIS_PATTERNS`` (bilingual by construction, including
  "ya no puedo más" — the phrase Valentis first answered with). Today's
  consumer semantics are boolean (threshold 1); the per-group weights exist so
  a banded classifier (discord-bot #53) can grade them without re-migrating.
- The four NEW chronic groups (abuse, social_isolation, recent_grief,
  substance_use) detect categories the flat vocabulary always NAMED in
  ``PSYCH_HIGH_RISK_CONDITIONS`` but nothing could ever match. Their weights
  are PROPOSED (Alex's #52 close-out: "sumarlas con peso propio sí") and are
  hers to validate — change them with her, not casually.
"""

from __future__ import annotations

from .signals import SignalGroup, WeightedSignals

#: Chronic vulnerability over accumulated facts. Threshold 4 = a cluster, not
#: a mention (migrated verbatim; see module docstring).
PSYCH_CHRONIC_SIGNALS = WeightedSignals(
    threshold=4,
    groups=(
        SignalGroup.make(
            "named_diagnosis", 3,
            r"\b("
            r"ptsd|cptsd|tept|tdah|adhd|toc|ocd|"
            r"bipolar\w*|esquizo\w*|schizo\w*|psicosis|psychos\w*|"
            r"trastorno(?:\s+\w+)?|disociaci[oó]n\w*|dissociat\w*|"
            r"trauma\s+complej|postraum\w*|post[- ]traum\w*|"
            r"trastorno de estr[eé]s|estr[eé]s postraum"
            r")",
            category="diagnosis",
        ),
        SignalGroup.make(
            "psychiatric_medication", 3,
            r"\b("
            r"quetiapin\w*|sertralin\w*|risperid\w*|paroxet\w*|fluoxet\w*|"
            r"escitalopr\w*|olanzapin\w*|clonazepam\w*|alprazolam\w*|"
            r"lorazepam\w*|diazepam\w*|benzodiacep\w*|"
            r"antidepres\w*|ansiol[ií]tic\w*|neurol[eé]ptic\w*|"
            r"antipsic[oó]tic\w*|psicof[aá]rmac\w*"
            r")",
            category="medication",
        ),
        SignalGroup.make(
            "hospitalization", 2,
            r"\b(internamiento|internarme|internarse|hospitaliz\w*|"
            r"pabell[oó]n psiqui\w*|ingreso psiqui\w*)",
            category="hospitalización psiquiátrica previa",
        ),
        SignalGroup.make(
            "mental_health_clinician", 2,
            r"\b(psiqu[ií]atr\w*|neuropsiqu\w*|psychiatr\w*|psic[oó]log\w*|"
            r"psycholog\w*|terapeut\w*|therapist\w*|psicoan[aá]l\w*)",
            category="clinician",
        ),
        SignalGroup.make(
            "chronic_comorbidity", 1,
            r"\b(artritis|fibromialgi\w*|dolor cr[oó]nic\w*|chronic pain|"
            r"discapacidad\w*|disabled\w*|ajustes razonables|accommodations|"
            r"cr[oó]nic[ao]\s+(?:desde|de|por))",
            category="comorbidity",
        ),
        SignalGroup.make(
            "self_harm_history", 3,
            r"\b(suicid\w*|autolesion\w*|self[- ]harm|intento de suicidio|"
            r"pens[aá]\w+ suicid\w*)",
            category="intento de suicidio previo",
        ),
        # --- The four categories PSYCH_HIGH_RISK_CONDITIONS names and nothing
        # --- detected. Weights PROPOSED, pending Alex's clinical validation.
        SignalGroup.make(
            "abuse", 2,
            r"\b(abus[oó]\w*|abuse[dr]?\b|maltrat\w*|violencia\s+"
            r"(?:dom[eé]stica|familiar|de\s+pareja)|domestic\s+violence|"
            r"me\s+peg\w+|me\s+golpe\w+)",
            category="abuso",
        ),
        SignalGroup.make(
            "social_isolation", 2,
            r"\b(aislamiento\s+social|aislad[oa]\b|no\s+tengo\s+amigos|"
            r"no\s+hablo\s+con\s+nadie|socially\s+isolated|no\s+friends|"
            r"nadie\s+me\s+habla|siempre\s+sol[oa]\b)",
            category="aislamiento social",
        ),
        SignalGroup.make(
            "recent_grief", 2,
            r"\b(duelo|luto|falleci[oó]\w*|muri[oó]\s+mi\b|"
            r"p[eé]rdida\s+de\s+(?:mi|su)\b|passed\s+away|"
            r"(?:mi|su)\s+\w+\s+muri[oó]|grieving|in\s+mourning)",
            category="duelo reciente",
        ),
        SignalGroup.make(
            "substance_use", 2,
            r"\b(alcoholismo|alcoh[oó]lic\w*|adicci[oó]n\w*|adict[oa]\b|"
            r"drogadic\w*|sobredosis|overdose|reca[ií]\w*\s+en\s+"
            r"(?:el\s+alcohol|las\s+drogas)|substance\s+(?:ab)?use|"
            r"consumo\s+problem[aá]tico)",
            category="trastorno por uso de sustancias",
        ),
    ),
)

#: Acute crisis in the CURRENT message. Threshold 1 preserves today's boolean
#: consumer semantics; the graded weights are for a banded classifier (#53).
PSYCH_ACUTE_SIGNALS = WeightedSignals(
    threshold=1,
    groups=(
        SignalGroup.make(
            "explicit_ideation", 4,
            r"\b(suicid\w*|matarme|kill myself|me quiero morir|i want to die|"
            r"autolesion\w*|self[- ]harm)\b",
            category="riesgo suicida",
        ),
        SignalGroup.make(
            "at_the_limit", 3,
            r"\b(no puedo m[aá]s|ya no aguanto|no puedo seguir|i can'?t go on|"
            r"i can'?t do this anymore|me rindo)\b",
            category="desesperanza",
        ),
        SignalGroup.make(
            "crisis_now", 3,
            r"\b("
            r"estoy en crisis|i'?m in crisis|crisis emocional ahora|"
            r"ataque de p[aá]nico|panic attack|"
            r"estoy muy mal|i'?m really not ok|i'?m not safe"
            r")\b",
            category="crisis aguda",
        ),
        SignalGroup.make(
            "cry_for_help", 2,
            r"\b(ayuda en serio|help me for real|no estoy bien para nada|"
            r"estoy mal de verdad)\b",
            category="crisis aguda",
        ),
        SignalGroup.make(
            "acute_isolation", 2,
            r"\b(no tengo a nadie|me siento (muy )?solo de verdad|"
            r"i feel (so |really )?alone right now)\b",
            category="aislamiento social",
        ),
    ),
)
