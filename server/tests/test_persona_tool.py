"""The living persona's two-owner contract (#36): the `init` endpoint owns the
BASE, the `persona` tool owns the LIVING part, and neither can touch the other's
half. These tests pin the split/merge/rebase algebra and the update flow the
in-process server performs against a real file."""

from pathlib import Path

from aire.engine.persona_tool import MARKER, MAX_LIVING, _write, merge, rebase, split

BASE = "You are og118 — element 118, Oganesson.\n\nLANGUAGE: Mexican Spanish."
LIVING = "The user prefers blunt answers and hates bullet lists."


def test_split_of_a_plain_init_file_has_no_living_half():
    assert split(BASE + "\n") == (BASE, "")


def test_merge_without_living_stays_byte_identical_to_what_init_wrote():
    assert merge(BASE, "") == BASE + "\n"
    assert MARKER not in merge(BASE, "")


def test_split_merge_roundtrip_keeps_both_halves():
    text = merge(BASE, LIVING)
    assert split(text) == (BASE, LIVING)
    assert MARKER in text


def test_rebase_refreshes_the_base_and_keeps_the_living():
    grown = merge(BASE, LIVING)
    rebased = rebase(grown, "A brand new base.")
    assert split(rebased) == ("A brand new base.", LIVING)


def test_rebase_of_a_plain_file_never_invents_a_marker():
    assert rebase(BASE + "\n", "New base.") == "New base.\n"


def test_update_flow_protects_the_base(tmp_path: Path):
    md = tmp_path / "CLAUDE.md"
    md.write_text(BASE + "\n", encoding="utf-8")
    base = split(md.read_text(encoding="utf-8"))[0]
    _write(md, merge(base, LIVING))
    assert split(md.read_text(encoding="utf-8")) == (BASE, LIVING)
    _write(md, merge(split(md.read_text(encoding="utf-8"))[0], ""))
    assert md.read_text(encoding="utf-8") == BASE + "\n"
    assert not (tmp_path / "CLAUDE.md.tmp").exists()


def test_a_marker_smuggled_inside_the_living_cannot_reach_the_base():
    tricky = f"pre {MARKER} post"
    base, living = split(merge(BASE, tricky))
    assert base == BASE  # split cuts at the FIRST marker — the base stays whole
    assert living == tricky


def test_max_living_is_a_page_not_a_book():
    assert MAX_LIVING == 8_000
