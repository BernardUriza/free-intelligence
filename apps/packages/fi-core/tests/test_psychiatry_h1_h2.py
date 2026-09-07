"""Alex's H1/H2 decisions for PSYCHIATRY (discord-bot #55, 2026-09-04/05; fi #461).

Every row below is a clinical decision she already took; this file is where it
became executable. Three mechanisms carry them:

- H1: `preparatory_acts` on the acute axis at the highest weight, plus tight
  substrings in the critical vocabulary so the BAND goes CRITICAL too.
  `farewell_hint` is a weak signal: matched, weight 0, never crosses alone.
- H2: two chronic EXPOSURE groups (a relative's attempt, a relative's death)
  with the same weight, outside `recent_grief`, and — the defect they fix —
  read as exposure, never as the writer's own crisis.
- Demotions: idiom, media topic and work venting are EXCLUSIONS: the span is
  cut before anything reads a crisis into it, and reported as `excluded`.
  "no me quiero morir" is local negation (0.28.0) on the acute axis too.
"""

from __future__ import annotations

import pytest
from fi_core.cognitive import PSYCHIATRY, PatientContext

clf = PSYCHIATRY.urgency_classifier()
ACUTE = PSYCHIATRY.acute_signals
CHRONIC = PSYCHIATRY.chronic_signals


def band(text: str) -> str:
    hits = PSYCHIATRY.match(text)
    return clf.classify(PatientContext(symptoms=list(hits.symptoms))).level.value


# --- H1: preparatory acts ------------------------------------------------------

PREPARATORY = [
    "tengo las pastillas listas",
    "escribí mi carta de despedida",
    "ya decidí cómo lo voy a hacer",
    "estoy en el puente",
    "estoy en la azotea",
    "estoy en las vías",
    "compré una cuerda",
    "compré una soga",
    "compré una pistola",
    "regalé mis cosas",
    "ya me despedí de todos",
    "le voy a dar mi perro a mi hermana",
    "llevo semanas guardando pastillas",
    "gracias por todo, ya no te preocupes por mí",
    "i have a plan and the pills ready",
]


@pytest.mark.parametrize("text", PREPARATORY)
def test_preparatory_act_fires_the_acute_group_and_the_critical_band(text: str):
    scored = ACUTE.score([text])
    assert "preparatory_acts" in scored.matched
    assert scored.crosses
    assert band(text) == "CRITICAL", f"{text!r} must reach the CRITICAL band"


def test_preparatory_acts_carry_the_highest_acute_weight():
    by_name = {g.name: g.weight for g in ACUTE.groups}
    assert by_name["preparatory_acts"] == max(by_name.values())


def test_farewell_hint_is_a_weak_signal_that_never_fires_alone():
    scored = ACUTE.score(["ya no voy a estar el lunes"])
    assert scored.matched == ("farewell_hint",)
    assert scored.score == 0 and not scored.crosses
    assert band("ya no voy a estar el lunes") != "CRITICAL"


def test_arregle_mis_papeles_is_out():
    assert not ACUTE.score(["ya arreglé mis papeles"]).matched
    assert not PSYCHIATRY.match("ya arreglé mis papeles")


# --- H2: exposure to a relative's attempt / death ------------------------------


@pytest.mark.parametrize(
    ("text", "group"),
    [
        ("mi hermana intentó suicidarse", "exposicion_intento"),
        ("mi mejor amiga trató de matarse", "exposicion_intento"),
        ("my brother tried to kill himself", "exposicion_intento"),
        ("mi compañera se suicidó", "exposicion_consumado"),
        ("mi papá se quitó la vida", "exposicion_consumado"),
        ("perdí a mi primo por suicidio", "exposicion_consumado"),
        ("my sister died by suicide", "exposicion_consumado"),
    ],
)
def test_exposure_is_its_own_chronic_group_and_never_the_writers_crisis(text: str, group: str):
    chronic = CHRONIC.score([text])
    assert chronic.matched == (group,), "exposure scores itself and nothing else"
    assert "self_harm_history" not in chronic.matched
    assert "recent_grief" not in chronic.matched
    hits = PSYCHIATRY.match(text)
    assert not hits, f"{text!r} is not the writer's crisis"
    assert group in hits.excluded
    assert not ACUTE.score([text]).crosses
    assert band(text) == "LOW"


def test_exposure_groups_share_one_weight_and_map_to_high_risk_conditions():
    weights = {g.name: g.weight for g in CHRONIC.groups}
    assert weights["exposicion_intento"] == weights["exposicion_consumado"]
    categories = {g.name: g.category for g in CHRONIC.groups}
    assert categories["exposicion_intento"] in PSYCHIATRY.high_risk_conditions
    assert categories["exposicion_consumado"] in PSYCHIATRY.high_risk_conditions


def test_a_clinician_describing_the_patient_is_not_exposure():
    """The 3rd-person vocabulary exists for this case; exposure must not eat it."""
    assert band("mi paciente intentó suicidarse") == "CRITICAL"
    assert "self_harm_history" in CHRONIC.score(["mi paciente intentó suicidarse"]).matched


# --- Demotions ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "exclusion"),
    [
        ("me quiero morir de la risa", "modismo"),
        ("me muero de hambre", "modismo"),
        ("vi un documental sobre el suicidio", "tema_no_propio"),
        ("leí un artículo sobre la prevención del suicidio", "tema_no_propio"),
        ("ya no puedo más con este proyecto, el deploy me tiene harto", "desahogo_laboral"),
    ],
)
def test_idiom_topic_and_work_venting_are_excluded_everywhere(text: str, exclusion: str):
    acute = ACUTE.score([text])
    assert not acute.matched and exclusion in acute.excluded
    hits = PSYCHIATRY.match(text)
    assert not hits and exclusion in hits.excluded
    assert band(text) == "LOW"
    assert "self_harm_history" not in CHRONIC.score([text]).matched


def test_the_real_limit_still_fires():
    assert ACUTE.score(["no puedo más con mi vida"]).matched == ("at_the_limit",)
    assert ACUTE.score(["me quiero morir"]).crosses


def test_local_negation_reaches_the_acute_axis():
    scored = ACUTE.score(["no me quiero morir, solo estoy muy cansado"])
    assert not scored.matched and not scored.crosses
    assert scored.denied == ("explicit_ideation",)
    assert ACUTE.score(["no sé, me quiero morir"]).matched == ("explicit_ideation",)


def test_classifier_honors_the_domain_exclusions_directly():
    """A symptom string handed straight to the classifier is read the same way."""
    assert clf.classify(PatientContext(symptoms=["me quiero morir de la risa"])).level.value == "LOW"
    assert clf.classify(PatientContext(symptoms=["mi hermana intentó suicidarse"])).level.value == "LOW"
