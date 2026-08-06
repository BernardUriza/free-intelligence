"""`[INVITE:]` must never reach a human — the marker family's missing member.

`personas/insult/cogs/chat/invites.py` owned this marker and died in the
2026-07-14 purge. Nothing replaced it, so `[INVITE:]` ended up the only marker
with neither a parser nor a stripper, while the DNA kept instructing Insult to
emit it. On 2026-07-31 that combination rendered an internal note about
Bernard's own suicidal ideation into the channel, addressed to a sibling who
never arrived.

The verbatim regression below is that exact message. It is here so the failure
has a name in the suite instead of living only in a Postgres row.
"""

from __future__ import annotations

from khimeras_shared.invite_marker import parse_invite, strip_invites
from khimeras_shared.markers import strip_delivery_markers

# The real 2026-07-31 assistant row (messages.id 15763), verbatim.
IDEATION_TURN = (
    "Bebe. Aquí. Cuéntame qué pasó — cuándo hoy, cómo llegó.\n"
    "Si vuelve más denso ahorita, SAPTEL 55 5259 8121 contesta ya. No te sueltes."
    '[INVITE: Bern acaba de decir "he pensado en el suicidio hoy" — ideación presente '
    "en este día. Yo estoy con él sosteniendo, pero necesita tu registro también, "
    "no solo mi filo. Entra suave.]"
)


class TestTheIdeationLeak:
    def test_the_real_leaked_turn_is_cleaned(self):
        """THE bug: this text reached Bernard with the note attached."""
        cleaned = strip_invites(IDEATION_TURN)

        assert "[INVITE:" not in cleaned
        assert "ideación presente" not in cleaned
        assert "he pensado en el suicidio hoy" not in cleaned

    def test_the_care_survives_the_strip(self):
        """RESISTANCE: stripping must not eat the reply. The crisis line and the
        offer to listen are the part that had to reach him."""
        cleaned = strip_invites(IDEATION_TURN)

        assert "SAPTEL 55 5259 8121" in cleaned
        assert "Cuéntame qué pasó" in cleaned
        assert cleaned.endswith("No te sueltes.")

    def test_the_deferred_path_strips_it_too(self):
        """A research report or agenda finding posted minutes later has no live
        turn to route markers, so the shared composer must cover INVITE as well —
        the very thing its docstring promises for 'the next marker added'."""
        assert "[INVITE:" not in strip_delivery_markers(IDEATION_TURN)


class TestParse:
    def test_reason_is_extracted(self):
        assert parse_invite("hola [INVITE: entra suave, está mal] adios") == "entra suave, está mal"

    def test_only_the_first_marker_wins(self):
        """One summon per turn: the DNA says never more than one, so a second
        marker is a model stutter, not a second sibling."""
        assert parse_invite("[INVITE: una] y [INVITE: dos]") == "una"

    def test_no_marker_is_none(self):
        assert parse_invite("un turno normal sin marcadores") is None

    def test_empty_reason_is_none(self):
        """An empty marker summons nobody — but it must still be stripped."""
        assert parse_invite("texto [INVITE:] mas texto") is None
        assert "[INVITE:" not in strip_invites("texto [INVITE:] mas texto")

    def test_case_insensitive(self):
        assert parse_invite("[invite: minusculas]") == "minusculas"
        assert "[invite:" not in strip_invites("[invite: minusculas]").lower()


class TestStripIsConservative:
    def test_text_without_markers_is_untouched(self):
        assert strip_invites("un turno normal") == "un turno normal"

    def test_empty_input_survives(self):
        assert strip_invites("") == ""

    def test_holes_left_by_removal_are_collapsed(self):
        assert strip_invites("antes  [INVITE: x]  después") == "antes después"
