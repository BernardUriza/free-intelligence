"""`fi_core.audit` (0.30.0) — the pseudonym and the hashed event, ported from
discord-bot #54 (`khimeras_shared/audit.py`, tests/core/test_audit_*.py).

The two negatives are the ones that matter, and they are Alex's conditions:

- without a key there is NO code — never a keyless hash ("protección de
  mentiras"); and
- two keys give two codes — **a bare sha256 fails this test**, because its
  output depends on no key. It is the harness against a future "simplification".
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from fi_core.audit import DEFAULT_DIGEST_CHARS, audit_period, audited, pseudonym, sha256_payload

ONE_PERSON = "284712993456127001"
ANOTHER = "284712993456127002"
KEY = "llave-de-prueba-no-es-la-de-produccion"
SEPTEMBER = datetime(2026, 9, 8, 15, 20, tzinfo=timezone.utc)
OCTOBER = datetime(2026, 10, 1, 0, 5, tzinfo=timezone.utc)


# --- the two conditions -----------------------------------------------------


def test_without_a_key_there_is_no_code():
    assert pseudonym(ONE_PERSON, key=None, period="2026-09") is None
    assert pseudonym(ONE_PERSON, key="", period="2026-09") is None
    assert pseudonym(ONE_PERSON, key="   ", period="2026-09") is None


def test_two_keys_give_two_codes_so_a_bare_sha256_cannot_pass():
    a = pseudonym(ONE_PERSON, key="llave-A", period="2026-09")
    b = pseudonym(ONE_PERSON, key="llave-B", period="2026-09")
    assert a != b
    bare = hashlib.sha256(ONE_PERSON.encode()).hexdigest()[:DEFAULT_DIGEST_CHARS]
    assert bare not in (a, b)


def test_the_period_rotates_the_code_and_is_visible_in_front():
    sep = pseudonym(ONE_PERSON, key=KEY, period=audit_period(SEPTEMBER))
    oct_ = pseudonym(ONE_PERSON, key=KEY, period=audit_period(OCTOBER))
    assert sep != oct_
    assert sep.startswith("2026-09:") and oct_.startswith("2026-10:")


# --- what it must still do: group ----------------------------------------------


def test_same_person_same_period_groups():
    assert pseudonym(ONE_PERSON, key=KEY, period="2026-09") == pseudonym(ONE_PERSON, key=KEY, period="2026-09")


def test_two_people_do_not_collide():
    assert pseudonym(ONE_PERSON, key=KEY, period="2026-09") != pseudonym(ANOTHER, key=KEY, period="2026-09")


def test_the_code_does_not_contain_the_subject():
    assert ONE_PERSON not in pseudonym(ONE_PERSON, key=KEY, period="2026-09")


def test_no_subject_no_code():
    assert pseudonym("", key=KEY, period="2026-09") is None


def test_digest_length_is_a_parameter_with_the_canary_default():
    code = pseudonym(ONE_PERSON, key=KEY, period="2026-09")
    assert len(code) == len("2026-09:") + 16
    assert len(pseudonym(ONE_PERSON, key=KEY, period="2026-09", digest_chars=32)) == len("2026-09:") + 32


def test_byte_compatible_with_discord_bot_pseudonymous_user():
    """Computed with khimeras_shared.audit.pseudonymous_user (v4.38.15) on
    2026-09-08: the September codes already in Log Analytics stay comparable
    after discord-bot switches to this function."""
    assert pseudonym(ONE_PERSON, key=KEY, period=audit_period(SEPTEMBER)) == "2026-09:df068944ec77436d"


# --- audit_period ----------------------------------------------------------------


def test_audit_period_is_the_utc_month():
    assert audit_period(SEPTEMBER) == "2026-09"
    assert audit_period(OCTOBER) == "2026-10"
    assert audit_period() == datetime.now(timezone.utc).strftime("%Y-%m")


def test_audit_period_converts_an_aware_local_time_to_utc():
    mexico = timezone(timedelta(hours=-6))
    late_on_the_30th = datetime(2026, 9, 30, 23, 30, tzinfo=mexico)  # already October in UTC
    assert audit_period(late_on_the_30th) == "2026-10"


# --- audited ---------------------------------------------------------------------


def test_audited_returns_fields_plus_event_plus_hash():
    row = audited("crisis_band_classified", band="HIGH", gravity=7.0, user_id=None)
    assert row["event"] == "crisis_band_classified"
    assert row["band"] == "HIGH" and row["gravity"] == 7.0 and row["user_id"] is None
    assert set(row) == {"event", "band", "gravity", "user_id", "audit_hash"}


def test_the_hash_covers_the_event_name():
    """Without it an `absent` row could be relabeled `classified` and still verify."""
    classified = audited("crisis_band_classified", persona_id="valentis")
    absent = audited("crisis_band_absent", persona_id="valentis")
    assert classified["audit_hash"] != absent["audit_hash"]


def test_the_hash_is_sha256_payload_of_exactly_what_is_emitted():
    row = audited("crisis_band_classified", band="HIGH", signals=["explicit_ideation"])
    emitted = {k: v for k, v in row.items() if k != "audit_hash"}
    assert row["audit_hash"] == sha256_payload(emitted)
    assert row["audit_hash"] == hashlib.sha256(
        json.dumps(emitted, sort_keys=True, default=str).encode()
    ).hexdigest()


def test_two_different_verdicts_two_different_hashes_and_same_verdict_same_hash():
    high = audited("crisis_band_classified", band="HIGH")
    critical = audited("crisis_band_classified", band="CRITICAL")
    assert high["audit_hash"] != critical["audit_hash"]
    assert high["audit_hash"] == audited("crisis_band_classified", band="HIGH")["audit_hash"]


def test_audited_refuses_a_caller_supplied_hash():
    with pytest.raises(ValueError):
        audited("crisis_band_classified", audit_hash="hash-de-mentiras")


def test_sha256_payload_still_reachable_from_cognitive():
    from fi_core.cognitive import sha256_payload as via_cognitive

    assert via_cognitive is sha256_payload
