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
- 0.29.0 (Alex's decisions in discord-bot #55, 2026-09-04/05; fi #461):
  ``preparatory_acts`` on the acute axis at the highest weight — "this is what
  the CRITICAL band needs to mean something"; ``farewell_hint`` as a WEAK
  signal that never fires alone; two chronic EXPOSURE groups (a relative's
  attempt, a relative's death by suicide — PLOS Med 2020,
  doi 10.1371/journal.pmed.1003074) with the same weight and outside
  ``recent_grief``; and the EXCLUSIONS — idiom, media topic, work venting and
  those same two exposure groups — which cut text that is not about the
  writer before anything can read a crisis into it.
"""

from __future__ import annotations

from .signals import SignalGroup, WeightedSignals

# --- Exclusions: text that is NOT about the writer's own state ---------------
#: Third-party exposure. Excluded from the writer's crisis AND scored as its own
#: chronic group — one definition, two roles. "mi paciente …" is left alone: a
#: clinician describing the patient is the 3rd-person case the flat vocabulary
#: exists for.
EXPOSURE_ATTEMPT = SignalGroup.make(
    "exposicion_intento", 2,
    r"\b(?:"
    r"(?:mi|su|tu|nuestr[oa]|un[a]?\s+(?:amig[oa]|compañer[oa]|companer[oa]|conocid[oa]))\s+"
    r"(?!paciente\b)(?:\w+\s+){0,2}?(?:intent[oó]|trat[oó]\s+de|quiso)\s+"
    r"(?:suicidarse|matarse|quitarse\s+la\s+vida|ahorcarse|cortarse\s+las\s+venas)|"
    r"intento\s+de\s+suicidio\s+de\s+(?:mi|su)\s+\w+|"
    r"(?:my|his|her|their)\s+(?!patient\b)\w+\s+(?:tried|attempted)\s+to\s+(?:kill|hang)\s+"
    r"(?:him|her|them)self|"
    r"(?:my|his|her|their)\s+(?!patient\b)\w+\s+attempted\s+suicide"
    r")",
    category="exposición a intento de suicidio",
)
EXPOSURE_COMPLETED = SignalGroup.make(
    "exposicion_consumado", 2,
    r"\b(?:"
    r"(?:mi|su|tu|nuestr[oa])\s+(?!paciente\b)(?:\w+\s+){1,2}?se\s+"
    r"(?:suicid[oó]|mat[oó]|ahorc[oó]|quit[oó]\s+la\s+vida|peg[oó]\s+un\s+tiro)|"
    r"perd[ií]\s+a\s+(?:mi|un[a]?)\s+\w+\s+por\s+suicidio|"
    r"suicidio\s+de\s+(?:mi|su)\s+\w+|"
    r"(?:my|his|her|their)\s+(?!patient\b)\w+\s+"
    r"(?:killed\s+(?:him|her|them)self|committed\s+suicide|died\s+by\s+suicide|"
    r"took\s+(?:his|her|their)\s+(?:own\s+)?life)"
    r")",
    category="exposición a suicidio consumado",
)
#: "me muero de risa" is not ideation. Weight 0: an exclusion, never a score.
IDIOM = SignalGroup.make(
    "modismo", 0,
    r"\b(?:"
    r"me\s+(?:quiero|voy\s+a)\s+morir\s+de\s+(?:la\s+)?(?:risa|verg[üu]enza|pena)|"
    r"(?:me\s+)?muero\s+de\s+(?:la\s+)?(?:risa|hambre|sue[ñn]o|fr[ií]o|calor|ganas|verg[üu]enza|aburrimiento)|"
    r"(?:para|de)\s+morirse\s+de\s+risa|matarme\s+de\s+risa|"
    r"dying\s+of\s+laughter|(?:could|gonna|going\s+to)\s+die\s+laughing"
    r")",
    category="modismo",
)
#: A documentary, a book, a class ABOUT suicide is a topic, not the writer.
TOPIC_NOT_SELF = SignalGroup.make(
    "tema_no_propio", 0,
    r"\b(?:"
    r"(?:documental|pel[ií]cula|serie|libro|art[ií]culo|noticia|podcast|video|reportaje|"
    r"charla|clase|tesis|ensayo|novela|canci[oó]n|cap[ií]tulo|episodio)\b[^.;!?]*?\b(?:suicid\w*|autolesi\w*)|"
    r"(?:documentary|movie|film|book|article|podcast|episode|class)\b[^.;!?]*?\bsuicid\w*|"
    r"(?:tasas?|cifras|estad[ií]sticas|prevenci[oó]n|d[ií]a\s+mundial)\s+(?:de\s+|del\s+)?(?:la\s+)?"
    r"(?:prevenci[oó]n\s+del\s+)?suicidio"
    r")",
    category="tema, no sobre quien escribe",
)
#: "ya no puedo más con este proyecto" is venting about work, not a limit.
WORK_VENTING = SignalGroup.make(
    "desahogo_laboral", 0,
    r"\b(?:ya\s+)?no\s+puedo\s+m[aá]s\s+con\s+(?:este|esta|estos|estas|el|la|los|las|mi|mis|tanto|tanta|tantos|tantas)\s+"
    r"(?:\w+\s+)?(?:proyecto|trabajo|chamba|deploy|c[oó]digo|tarea|tareas|examen|ex[aá]menes|escuela|"
    r"semestre|jefe|jefa|cliente|clientes|bug|bugs|servidor|tesis|entrega|entregas|junta|juntas|pendientes|"
    r"materia|clase|migraci[oó]n|sprint|release)\b",
    category="desahogo laboral",
)
#: What ClinicalDomain.match and the ACUTE axis cut before reading the writer.
#: Substance use. A GROUP on the chronic axis (weight 2, a comorbidity) and a
#: SILENCER on the recovery axis (Alex, #55 H4): with someone on substances
#: there is no intervention, only containment, so what they say is not a
#: reliable signal of improvement in either direction. Extracted to a constant
#: the day it got its second reader — one pattern, two roles, never two copies.
SUBSTANCE_USE = SignalGroup.make(
    "substance_use", 2,
    r"\b(alcoholismo|alcoh[oó]lic\w*|adicci[oó]n\w*|adict[oa]\b|"
    r"drogadic\w*|sobredosis|overdose|reca[ií]\w*\s+en\s+"
    r"(?:el\s+alcohol|las\s+drogas)|substance\s+(?:ab)?use|"
    r"consumo\s+problem[aá]tico)",
    category="trastorno por uso de sustancias",
)

#: Substance use AS SOMEONE SAYS IT IN A CHAT, not as a clinical record states
#: it. `SUBSTANCE_USE` above is written for extracted FACTS —"alcoholismo",
#: "adicción", "consumo problemático"— and silently missed every way a person
#: actually reports it mid-conversation: "volví a recaer", "ando en una
#: recaída", "me puse hasta atrás". Discovered on the recovery axis (#55 H4),
#: where the same concept had to be read off a live message instead of a
#: dossier: one concept, two registers, and reusing only the clinical one left
#: the silencer dead for the exact texts it exists to catch.
#:
#: Deliberately broad. On this axis a false silence only keeps the care a while
#: longer, which Álex named as the cheap error; a missed one withdraws care from
#: someone in a relapse.
SUBSTANCE_USE_SPOKEN = SignalGroup.make(
    "substance_use", 2,
    r"\b(?:"
    r"reca[eií]\w*|volv[ií]\s+a\s+(?:tomar|beber|consumir|usar|reca[eií]\w*)|"
    r"(?:ando|estoy|andaba|estaba)\s+(?:en\s+)?(?:una\s+)?(?:reca[ií]da|peda|borrach\w+|crud[oa])|"
    r"me\s+(?:puse|ped[ií])\s+(?:hasta\s+atr[aá]s|una\s+peda)|"
    r"(?:me\s+)?(?:met[ií]|drogu[eé]|emborrach[eé])\b|"
    r"consum(?:o|iendo|[ií])\s+(?:drogas|coca|crist|mota|alcohol)|"
    r"relapse[dn]?\b|got\s+(?:drunk|high)|i'?m\s+(?:drunk|high)"
    r")",
    category="trastorno por uso de sustancias",
)

PSYCH_EXCLUSIONS: tuple[SignalGroup, ...] = (
    IDIOM, TOPIC_NOT_SELF, WORK_VENTING, EXPOSURE_ATTEMPT, EXPOSURE_COMPLETED,
)

#: Chronic vulnerability over accumulated facts. Threshold 4 = a cluster, not
#: a mention (migrated verbatim; see module docstring). The exposure groups are
#: BOTH groups and exclusions here: "mi hermana intentó suicidarse" scores
#: exposicion_intento and never self_harm_history.
PSYCH_CHRONIC_SIGNALS = WeightedSignals(
    threshold=4,
    exclusions=(IDIOM, TOPIC_NOT_SELF, EXPOSURE_ATTEMPT, EXPOSURE_COMPLETED),
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
        SUBSTANCE_USE,
        # --- Exposure to a relative's suicide attempt / death (Alex, #55 H2).
        # --- Same weight as each other, deliberately NOT inside recent_grief.
        EXPOSURE_ATTEMPT,
        EXPOSURE_COMPLETED,
    ),
)

#: Acute crisis in the CURRENT message. Threshold 1 preserves today's boolean
#: consumer semantics; the graded weights are for a banded classifier (#53).
PSYCH_ACUTE_SIGNALS = WeightedSignals(
    threshold=1,
    exclusions=PSYCH_EXCLUSIONS,
    groups=(
        # Preparatory acts — means secured, farewell written, place reached,
        # possessions given away. Alex (#55 H1): "esto es lo que la banda
        # CRITICAL necesita para significar algo". Highest acute weight.
        SignalGroup.make(
            "preparatory_acts", 4,
            r"\b(?:"
            r"(?:tengo|ten[ií]a|guard[eé]|junt[eé]|compr[eé]|consegu[ií])\s+(?:las\s+|unas\s+|mis\s+)?pastillas|"
            r"pastillas\s+listas|(?:llevo\s+\w+\s+)?(?:guardando|juntando)\s+pastillas|"
            r"(?:escrib[ií]|dej[eé]|tengo)\s+(?:mi\s+|una\s+|la\s+)?(?:carta|nota)\s+de\s+despedida|"
            r"(?:carta|nota)\s+de\s+despedida|"
            r"ya\s+(?:decid[ií]|s[eé])\s+c[oó]mo\s+(?:lo\s+voy\s+a\s+hacer|hacerlo|me\s+voy\s+a\s+(?:matar|ir))|"
            r"estoy\s+en\s+(?:el\s+puente|la\s+azotea|las\s+v[ií]as|el\s+techo|el\s+balc[oó]n|la\s+orilla)|"
            r"(?:compr[eé]|consegu[ií])\s+(?:una\s+|la\s+|un\s+)?(?:cuerda|soga|pistola|arma|navaja)|"
            r"regal[eé]\s+(?:todas\s+)?mis\s+cosas|regalando\s+mis\s+cosas|"
            r"ya\s+me\s+desped[ií]\s+de\s+todos|me\s+estoy\s+despidiendo|"
            r"voy\s+a\s+dar(?:le)?\s+mi\s+(?:perr[oa]|gat[oa]|mascota|cosas)\s+a\s+|"
            r"ya\s+no\s+te\s+preocupes\s+por\s+m[ií]|"
            r"(?:i\s+)?have\s+(?:a\s+plan\s+and\s+)?the\s+pills\s+ready|pills\s+ready|"
            r"wrote\s+(?:my\s+)?(?:goodbye|suicide)\s+(?:note|letter)|"
            r"gave\s+away\s+my\s+(?:things|stuff|belongings)|"
            r"bought\s+(?:a\s+)?(?:rope|gun)|i'?m\s+on\s+the\s+(?:bridge|roof|tracks|ledge)"
            r")",
            category="riesgo inminente",
        ),
        # Weak signal (Alex): reported in `matched`, weight 0 so it never
        # crosses alone. "ya arreglé mis papeles" is deliberately OUT.
        SignalGroup.make(
            "farewell_hint", 0,
            r"\b(?:ya\s+no\s+voy\s+a\s+estar\s+(?:el|la|para|este|esta|ma[ñn]ana|aqu[ií])\b|"
            r"i\s+won'?t\s+be\s+(?:here|around)\s+(?:on|by|next|tomorrow))",
            category="riesgo suicida",
        ),
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


#: Recovery in the CURRENT message — the axis nobody was reading. Threshold 4
#: against groups of 3 means NOTHING fires alone, deliberately: the corpus only
#: knew how to climb the ladder, and 145 turns sat in `stability` without a
#: single recovery signal, which is not stability but nobody watching the other
#: side (Alex, discord-bot #55 H4, 2026-09-09).
#:
#: THE RULE UNDERNEATH, in her words: *the generic weighs little, the specific
#: weighs*. Saying you are better does not count; saying what you DID does.
#:
#: Everything else follows from that:
#:
#: - **Only the past counts.** "mañana voy a ir a la cita" scores nothing. A
#:   promise is the easiest thing to say to be left alone, and nothing that
#:   happens after is verifiable. What was already done already happened.
#: - **Closing the conversation SUBTRACTS.** "ya estoy bien, ya no quiero hablar
#:   de eso" is +3 self-report and −3 closure: zero, does not fire. That person
#:   is not improving, they are shutting down — and they look more like someone
#:   improving than anyone else does.
#: - **Integration is what unlocked this hallazgo.** Rumination is detected by
#:   what a person STOPS saying, which needs turn history. But someone who
#:   connects today to their own pattern ("siempre me pasa cuando siento que no
#:   me creen") and then moves to the present is visibly on the way out — and
#:   that is legible in a SINGLE message.
#: - **Everything weighs 3, nothing weighs 4**, because the two errors do not
#:   cost the same: firing too easily withdraws care from someone still unwell;
#:   firing too rarely just keeps the care a while longer. Even integration —
#:   the hardest to fake — stays at 3, because a person can produce a real
#:   insight and remain exactly as bad.
PSYCH_RECOVERY_SIGNALS = WeightedSignals(
    threshold=4,
    exclusions=PSYCH_EXCLUSIONS,
    # Substance use turns this axis off entirely — see `silenced_by`. There is
    # no intervention there, only containment.
    silenced_by=(SUBSTANCE_USE, SUBSTANCE_USE_SPOKEN),
    groups=(
        # Self-report. NOT split into strong and weak, for two reasons Alex
        # gave: deciding which phrasing counts less is a judgement that ages
        # badly once written into code, and since none of them crosses alone,
        # splitting them would almost never change the outcome anyway. A group
        # scores at most once per evaluation, so three of these are worth one.
        SignalGroup.make(
            "self_report_better", 3,
            r"\b(?:"
            r"ya\s+(?:me\s+siento|estoy)\s+(?:mejor|bien|m[aá]s\s+tranquil[oae])|"
            r"ya\s+se\s+me\s+pas[oó]|ya\s+me\s+calm[eé]|ya\s+la\s+libr[eé]|"
            r"creo\s+que\s+ya\s+estoy\s+(?:mejor|bien|m[aá]s\s+tranquil[oae])|"
            r"ya\s+no\s+me\s+siento\s+tan\s+mal|"
            r"i\s+feel\s+better\s+now|i'?m\s+okay\s+now"
            r")",
            category="autorreporte de mejoría",
        ),
        # Something ALREADY DONE — past only. The "ya" is load-bearing: it is
        # what separates "ya le hablé a mi hermana" from "voy a hablarle".
        SignalGroup.make(
            "action_taken", 3,
            r"\b(?:"
            r"ya\s+(?:le\s+)?habl[eé]\s+(?:con|a)\s+|"
            r"ya\s+me\s+tom[eé]\s+(?:la|las|mi|mis)\s+(?:pastilla|medicin|medicament)|"
            r"ya\s+com[ií]\b|ya\s+desayun[eé]|ya\s+cen[eé]|"
            r"ya\s+sal[ií]\s+a\s+(?:caminar|correr|dar\s+una\s+vuelta)|"
            r"ya\s+(?:fui|estuve)\s+(?:a|con)\s+(?:mi\s+)?(?:terapia|terapeut|psic[oó]log|psiquiatr)|"
            r"i\s+already\s+(?:called|talked\s+to|ate|took\s+my\s+med)"
            r")",
            category="acción ya realizada",
        ),
        # Integration — the person explains their own reaction, connecting today
        # to a pattern of theirs. The hardest of the three to fake, and still 3.
        SignalGroup.make(
            "integration", 3,
            r"\b(?:"
            r"creo\s+que\s+ya\s+entend[ií]|me\s+di\s+cuenta\s+de\s+que|"
            r"siempre\s+me\s+pasa\s+cuando|"
            r"(?:es\s+que\s+)?en\s+realidad\s+lo\s+que\s+me\s+(?:doli[oó]|peg[oó]|dio)|"
            r"i\s+think\s+i\s+get\s+it\s+now|i\s+reali[sz]ed\s+that"
            r")",
            category="integración",
        ),
        # Closing the conversation SUBTRACTS. The only negative weight in the
        # corpus, and the reason the axis needs one: this phrasing rides ON TOP
        # of a self-report ("ya estoy bien, ya no quiero hablar de eso") and
        # cancels it to exactly zero.
        SignalGroup.make(
            "conversation_closure", -3,
            r"\b(?:"
            r"ya\s+no\s+quiero\s+hablar\s+(?:de\s+eso|del\s+tema|de\s+esto)|"
            r"no\s+te\s+preocupes\s+por\s+m[ií]|ya\s+d[eé]jalo|"
            r"olv[ií]dalo|da\s+igual\b|ya\s+ni\s+s[eé]\b|"
            r"mejor\s+(?:ya\s+)?ni\s+hablemos|cambiemos\s+de\s+tema|"
            r"i\s+don'?t\s+want\s+to\s+talk\s+about\s+(?:it|this)\s+anymore"
            r")",
            category="cierre de conversación",
        ),
    ),
)
