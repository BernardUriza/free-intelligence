"""BM25 over a small in-memory corpus: the lexical arm that sees every chunk.

`HybridRetriever` re-ranks the dense pool, so a chunk the dense arm missed never
comes back. `Bm25Index` scores the whole namespace, so an exact name the
embedder buried still reaches the fusion. Pure Python: fine up to tens of
thousands of chunks, which is where a database index becomes the right tool.
"""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from collections.abc import Sequence

from fi_core.rag.retrieval import SPANISH_ENGLISH_STOPWORDS
from fi_core.text import fold_accents

_WORD = re.compile(r"[a-z0-9]+")
_FOLDED_STOPWORDS = frozenset(fold_accents(w) for w in SPANISH_ENGLISH_STOPWORDS)


def lexical_terms(text: str, *, stopwords: frozenset[str] = _FOLDED_STOPWORDS) -> list[str]:
    """Accent-folded terms with Spanish/English plurals reduced, repeats kept."""
    out: list[str] = []
    for word in _WORD.findall(fold_accents(text)):
        if word in stopwords:
            continue
        if len(word) > 4 and word.endswith("es"):
            word = word[:-2]
        elif len(word) > 3 and word.endswith("s"):
            word = word[:-1]
        out.append(word)
    return out


class Bm25Index:
    """Okapi BM25 over `texts`; `rank` answers with positions into that sequence."""

    def __init__(self, texts: Sequence[str], *, k1: float = 1.2, b: float = 0.75) -> None:
        self._k1 = k1
        lengths: list[int] = []
        self._postings: dict[str, list[tuple[int, int]]] = defaultdict(list)
        for i, text in enumerate(texts):
            terms = lexical_terms(text)
            lengths.append(len(terms))
            for term, freq in Counter(terms).items():
                self._postings[term].append((i, freq))
        self._size = len(lengths)
        mean = (sum(lengths) / self._size) if self._size else 0.0
        self._norm = [k1 * (1 - b + b * (n / mean if mean else 0.0)) for n in lengths]

    def __len__(self) -> int:
        return self._size

    def rank(self, query: str, *, limit: int) -> list[int]:
        """Positions of the `limit` best texts, best first; texts sharing no term are left out."""
        scores: dict[int, float] = defaultdict(float)
        for term in set(lexical_terms(query)):
            postings = self._postings.get(term, ())
            idf = math.log(1 + (self._size - len(postings) + 0.5) / (len(postings) + 0.5))
            for i, freq in postings:
                scores[i] += idf * freq * (self._k1 + 1) / (freq + self._norm[i])
        return sorted(scores, key=lambda i: (-scores[i], i))[:limit]


__all__ = ["Bm25Index", "lexical_terms"]
