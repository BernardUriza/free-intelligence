"""Chunking — pure text in, chunks out, and no database anywhere near it.

Its own file because these are the only tests here that need nothing running: a
corpus test that fails should mean Postgres or the query is wrong, not that a
string got split badly.
"""

from aire.chunking import CHUNK_CHARS, chunk


def test_a_long_document_is_split_on_paragraph_boundaries():
    text = "\n\n".join(f"párrafo {i} " + "x" * 400 for i in range(8))
    pieces = chunk(text)
    assert len(pieces) > 1
    assert all(len(p) <= CHUNK_CHARS or "\n\n" not in p for p in pieces)
    assert "".join(pieces).count("párrafo") == 8, "nothing is dropped"


def test_a_paragraph_longer_than_the_budget_rides_alone_uncut():
    huge = "y" * 3000
    assert chunk(f"corto\n\n{huge}") == ["corto", huge]


def test_blank_space_between_paragraphs_never_becomes_a_chunk():
    assert chunk("uno\n\n\n\n   \n\ndos") == ["uno\n\ndos"]


def test_matching_folds_accents_but_storage_keeps_them():
    """Postgres's spanish config stems and drops stopwords but does NOT fold
    diacritics without the `unaccent` extension, so `telemetría` and `telemetria`
    are two different words to it. Measured on the live gate: a model searching
    with the accent missed a document written without it and retried twice."""
    from aire.chunking import fold

    assert fold("telemetría") == fold("telemetria") == "telemetria"
    assert fold("autorizó ñandú Peña") == "autorizo nandu Pena"
    assert fold("sin acentos") == "sin acentos"
