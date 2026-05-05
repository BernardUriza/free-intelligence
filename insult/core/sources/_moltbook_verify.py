"""Moltbook anti-bot verification challenge solver.

Moltbook gates new posts and comments behind a math word problem
('lobster math'). The response includes:

    {
      "verification_code": "moltbook_verify_<hex>",
      "challenge_text":    "A] LoObBsTeR ClAw exerts twenty-three NeW-ToNs * seven nEwToOnS - how much force is total um?",
      "instructions":      "...respond with ONLY the number (NN.NN)..."
    }

Until POST /verify succeeds with the right answer, the post/comment stays
in `verification_status: 'pending'` and is invisible to other users —
which is why the bot's first comments looked like they posted but never
showed up.

The challenge text is heavily case-mashed and salted with junk symbols.
We:
  1) strip non-alphanumeric noise (keep digits, letters, spaces, and
     arithmetic operators)
  2) replace English word numbers with digits, including compounds like
     'twenty three' / 'twenty-three' → '23'
  3) regex-match the canonical 'A op B' shape and compute
"""

from __future__ import annotations

import re

_ONES: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
_TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}


def _decode_obfuscated(text: str) -> str:
    """Strip Moltbook's case-mashed obfuscation. Keep letters, digits,
    spaces, hyphens, and arithmetic operators. Lowercase + single-space.

    We do NOT collapse repeated letters here because that destroys
    legitimate doubles like 'three' → 'thre'. Instead, the word-number
    matcher uses permissive regex (every letter '+' once or more) so
    'thrreee' and 'three' both match the canonical 'three'."""
    cleaned = re.sub(r"[^a-zA-Z0-9 +\-*/x]", " ", text)
    cleaned = re.sub(r"([+*/])", r" \1 ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    cleaned = cleaned.replace("-", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def _permissive(word: str) -> str:
    r"""Build a regex pattern that matches `word` even with each letter
    repeated >=1 times (Moltbook anti-bot pattern)."""
    return "".join(c + "+" for c in word)


def _replace_word_numbers(text: str) -> str:
    """Replace English word numbers with digit equivalents. Compounds
    like 'twenty three' first, then standalone words. Tolerates Moltbook's
    consonant-doubling: 'twennty thrreee' and 'twenty three' both → '23'."""
    # Compounds: tens + ones → digits
    for tens_w, tens_v in _TENS.items():
        for ones_w, ones_v in _ONES.items():
            pattern = rf"\b{_permissive(tens_w)}\s+{_permissive(ones_w)}\b"
            text = re.sub(pattern, str(tens_v + ones_v), text)
    # Standalone tens
    for tens_w, tens_v in _TENS.items():
        text = re.sub(rf"\b{_permissive(tens_w)}\b", str(tens_v), text)
    # Standalone ones — order matters: longer first ('seventeen' before 'seven'
    # so that 'seventeen' isn't partially matched as 'seven')
    ordered = sorted(_ONES.items(), key=lambda kv: -len(kv[0]))
    for ones_w, ones_v in ordered:
        text = re.sub(rf"\b{_permissive(ones_w)}\b", str(ones_v), text)
    return text


def _detect_op(between: str) -> str:
    """Sniff the operator out of the words/symbols between two numbers.
    Defaults to '*' (lobster math is overwhelmingly multiplication).
    Order matters: 'multiplied by' before 'plus' so we don't match 'p'
    inside 'multiplied'."""
    if "*" in between or " x " in between or "times" in between or "multiplied by" in between:
        return "*"
    if "/" in between or "divided by" in between:
        return "/"
    if "+" in between or "plus" in between:
        return "+"
    if "minus" in between:
        return "-"
    # Plain '-' is ambiguous (it shows up as a word separator after the
    # hyphen→space replacement), so we don't trust it here.
    return "*"


def solve_math_challenge(challenge_text: str) -> str:
    """Decode + solve a Moltbook math word problem.

    Returns the answer as 'NN.NN' (two decimals — that's what /verify wants).
    Raises ValueError if the text can't be parsed."""
    decoded = _decode_obfuscated(challenge_text)
    decoded = _replace_word_numbers(decoded)

    digits = [(int(m.group()), m.start(), m.end()) for m in re.finditer(r"\d+", decoded)]
    if len(digits) < 2:
        raise ValueError(f"need 2+ numbers in decoded challenge, got {digits!r} from {decoded!r}")
    a, _, end_a = digits[0]
    b, start_b, _ = digits[1]
    between = decoded[end_a:start_b]
    op = _detect_op(between)

    if op == "*":
        result: float = a * b
    elif op == "+":
        result = a + b
    elif op == "-":
        result = a - b
    else:  # "/"
        if b == 0:
            raise ValueError("division by zero in challenge")
        result = a / b

    return f"{result:.2f}"
