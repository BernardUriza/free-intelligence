"""Text-budget operations shared by every consumer: cut a string, fit lines to a char budget."""

from __future__ import annotations

from collections.abc import Sequence


def truncate(text: str, max_chars: int, *, ellipsis: str = "…", word_backoff: int = 0) -> str:
    """`text` cut to at most `max_chars`, ellipsis included.

    @param word_backoff: when > 0, the cut moves back to the last space if that
        space is at most this many chars before the cut; 0 cuts anywhere.
    @returns `text` unchanged when it already fits.
    """
    if len(text) <= max_chars:
        return text
    cut = text[: max(max_chars - len(ellipsis), 0)]
    if word_backoff > 0:
        space = cut.rfind(" ")
        if space > 0 and space >= len(cut) - word_backoff:
            cut = cut[:space]
    return cut.rstrip() + ellipsis


def fit_ranked(lines: Sequence[str], max_chars: int, *, word_backoff: int = 0) -> tuple[list[tuple[int, str]], bool]:
    """Lines in rank order that fit `max_chars` together, skipping the ones that do not.

    @returns `(kept, truncated)`: `kept` pairs each line with its index in
        `lines`; the first line always enters, cut with `truncate` when it alone
        is over the budget, and then `truncated` is True.
    """
    kept: list[tuple[int, str]] = []
    total = 0
    truncated = False
    for i, line in enumerate(lines):
        if total + len(line) <= max_chars:
            kept.append((i, line))
            total += len(line)
        elif not kept:
            short = truncate(line, max_chars, word_backoff=word_backoff)
            kept.append((i, short))
            total += len(short)
            truncated = True
    return kept, truncated


def fit_prefix(lines: Sequence[str], max_chars: int, *, separator_chars: int = 0, from_end: bool = False) -> list[str]:
    """The longest run of whole lines that fits `max_chars`, stopping at the first that does not.

    @param separator_chars: chars each line costs on top of its length (1 for a newline join).
    @param from_end: take the run from the end of `lines` (newest last); order is preserved.
    """
    picked: list[str] = []
    total = 0
    for line in reversed(lines) if from_end else lines:
        total += len(line) + separator_chars
        if total > max_chars:
            break
        picked.append(line)
    return picked[::-1] if from_end else picked
