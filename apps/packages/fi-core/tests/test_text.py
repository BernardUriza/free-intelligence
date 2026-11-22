from fi_core.text import fit_prefix, fit_ranked, truncate


def test_truncate_leaves_fitting_text_alone():
    assert truncate("hola", 4) == "hola"


def test_truncate_counts_the_ellipsis_inside_the_limit():
    out = truncate("abcdefghij", 5)
    assert out == "abcd…"
    assert len(out) == 5


def test_truncate_backs_off_to_a_word_within_reach():
    assert truncate("uno dos tresxxxxxx", 12, word_backoff=8) == "uno dos…"


def test_truncate_cuts_mid_word_when_the_space_is_too_far_back():
    assert truncate("uno dosxxxxxxxxxxx", 12, word_backoff=3) == "uno dosxxxx…"


def test_truncate_takes_any_marker():
    assert truncate("x" * 20, 10 + len("\n[…]"), ellipsis="\n[…]") == "x" * 10 + "\n[…]"


def test_fit_ranked_skips_an_oversized_line_and_keeps_a_later_one():
    kept, truncated = fit_ranked(["aaaa", "bbbbbbbbbb", "cc"], 7)
    assert kept == [(0, "aaaa"), (2, "cc")]
    assert truncated is False


def test_fit_ranked_always_admits_the_first_line_cut():
    kept, truncated = fit_ranked(["x" * 50, "y"], 10)
    assert kept[0] == (0, "x" * 9 + "…")
    assert truncated is True


def test_fit_prefix_stops_at_the_first_line_over_budget():
    assert fit_prefix(["aa", "bbbbbb", "c"], 5, separator_chars=1) == ["aa"]


def test_fit_prefix_from_end_keeps_the_newest_in_order():
    assert fit_prefix(["old", "mid", "new"], 8, separator_chars=1, from_end=True) == ["mid", "new"]
