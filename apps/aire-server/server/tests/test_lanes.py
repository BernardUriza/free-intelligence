"""Consumer lanes (engine/lanes.py): an armed lane rides its own credential and
never the pool; an unarmed one changes nothing. The founding case is
2026-10-08 — four BAIR reviews emptied the primary's monthly cap."""

from aire.engine.contract import TurnSpec
from aire.engine.credentials import Rotor
from aire.engine.lanes import armed, lane_of, pick
from aire.intake import turn_spec

ENV = {"AIRE_BAIR_TOKEN": "bair-door", "ANTHROPIC_API_KEY_BAIR": "sk-bair",
       "CLAUDE_CODE_OAUTH_TOKEN": "oauth-1", "CLAUDE_CODE_OAUTH_TOKEN_BACKUP": "oauth-2"}


def test_the_door_token_names_the_lane():
    assert lane_of("bair-door", ENV) == "bair"
    assert lane_of("someone-else", ENV) == ""
    assert lane_of("", {"AIRE_BAIR_TOKEN": ""}) == ""  # an unset token names nobody


def test_an_armed_lane_is_its_own_metered_slot():
    slot = armed(ENV)["bair"]
    assert slot.name == "api-key-bair"
    assert slot.env == {"ANTHROPIC_API_KEY": "sk-bair", "CLAUDE_CODE_OAUTH_TOKEN": ""}


def test_an_armed_lane_never_touches_the_pool():
    rotor = Rotor(ENV)
    slots = armed(ENV)
    assert pick(rotor, "bair", slots).name == "api-key-bair"
    rotor.burn("api-key-bair")
    assert pick(rotor, "bair", slots) is None  # dry lane → credentials_exhausted
    assert pick(rotor, "", slots).name == "oauth-primary"  # the personas keep the pool


def test_an_unarmed_lane_rides_the_shared_chain_unchanged():
    rotor = Rotor(ENV)
    assert pick(rotor, "bair", armed({"AIRE_BAIR_TOKEN": "bair-door"})).name == "oauth-primary"


def test_the_lane_rides_the_spec_and_the_caller_cannot_claim_one():
    assert turn_spec({"mode": "complete", "lane": "bair"}).lane == ""
    assert turn_spec({"mode": "complete"}, "bair") == TurnSpec(mode="complete", lane="bair")
