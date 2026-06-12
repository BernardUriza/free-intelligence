"""Tests for the Moltbook verification challenge solver."""

import pytest

from personas.insult.core.sources._moltbook_verify import (
    _decode_obfuscated,
    _replace_word_numbers,
    solve_math_challenge,
)


class TestDecode:
    def test_strips_brackets_and_special_chars(self):
        raw = "A] lOoObBsStTeEr] cLaW] eX eRrT s] tWeNnTy] tHrReEe] nEuToOnNs] ^* ]sEeVvEeN] nEuToOnNs] -] hOw] mUcH] fOrCe] iS] tOtAl] uM? ~"
        out = _decode_obfuscated(raw)
        # The decoder lowercases + strips junk but keeps doubled letters
        # (the permissive matcher in _replace_word_numbers handles those).
        assert "twennty" in out  # 'tWeNnTy' lowercased — still doubled
        assert "thrreee" in out
        assert "*" in out
        assert "]" not in out
        assert "?" not in out

    def test_preserves_arithmetic_operators(self):
        assert "*" in _decode_obfuscated("a * b")
        assert "+" in _decode_obfuscated("a + b")
        assert "/" in _decode_obfuscated("a / b")
        # Hyphens are stripped (they appear inside compounds like
        # 'twenty-three' and 'NeW-ToNs', so we treat them as separators)
        assert "-" not in _decode_obfuscated("a-b")

    def test_lowercases(self):
        assert _decode_obfuscated("LOBSTER") == "lobster"


class TestWordNumbers:
    def test_simple_ones(self):
        assert _replace_word_numbers("seven claws") == "7 claws"

    def test_simple_tens(self):
        assert _replace_word_numbers("twenty newtons") == "20 newtons"

    def test_compound_tens_plus_ones(self):
        assert _replace_word_numbers("twenty three newtons") == "23 newtons"
        assert _replace_word_numbers("forty seven") == "47"


class TestSolve:
    def test_real_challenge_one_23x7(self):
        chal = "A] lOoObBsStTeEr] cLaW] eX eRrT s] tWeNnTy] tHrReEe] nEuToOnNs] ^* ]sEeVvEeN] nEuToOnNs] -] hOw] mUcH] fOrCe] iS] tOtAl] uM? ~"
        assert solve_math_challenge(chal) == "161.00"

    def test_real_challenge_two_25x3(self):
        chal = "A LoObBsTeR ClAw-FoRcE Is TwEnTy FiVe NeW-ToNs * ThReE ClAwS WhAtS ThE ToTaL FoRcE, Um lobster?"
        assert solve_math_challenge(chal) == "75.00"

    def test_word_operator_times(self):
        assert solve_math_challenge("six times nine") == "54.00"

    def test_addition(self):
        assert solve_math_challenge("twelve + eight") == "20.00"

    def test_subtraction(self):
        assert solve_math_challenge("forty minus seven") == "33.00"

    def test_division(self):
        assert solve_math_challenge("twenty divided by four") == "5.00"

    def test_unparseable_raises(self):
        with pytest.raises(ValueError):
            solve_math_challenge("just some words with no numbers at all")

    def test_decreases_by_is_subtraction(self):
        # Real production challenge: lobster speed 32, decreases by 7 → 25
        chal = (
            "A] LoOoBbSstTeEr S^wImS lOoOokS liKe ThIs Um At/ tH/iRrTy T wOo MeTeR "
            "sPeErRss -^ aNd HeM mM cOlLiIdEs{ wItH} aN oThEr~ ObJeCt AnD sPeEd "
            "DeCrEeAsEs bY[ sEeVvEn, WhAtS ]tHe ReMaInInG/ veL aWcItEe?}"
        )
        assert solve_math_challenge(chal) == "25.00"

    def test_drops_by_is_subtraction(self):
        assert solve_math_challenge("speed of forty drops by twelve") == "28.00"

    def test_increases_by_is_addition(self):
        assert solve_math_challenge("force of fifteen increases by eight") == "23.00"

    def test_combined_with_is_addition(self):
        assert solve_math_challenge("ten newtons combined with seven newtons total") == "17.00"
