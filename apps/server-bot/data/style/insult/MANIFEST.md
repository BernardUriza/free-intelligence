# Voice pool — insult

Real colloquial Mexican Spanish that the persona reads as **register and rhythm
only**, never as facts (`shared/corpus/style_headers/insult.md`). Retrieved per
turn by `persona_core/corpus/style.py`, never through the topical reranker.

| File | Source | Curated | Lines |
|---|---|---|---|
| `voz-bernard.txt` (gitignored) | Bernard's own Discord messages to the personas (`messages`, `user_name='bernard2389'`), 636 candidates with colloquial markers | 2026-11-20, by hand | 81 |

## Curation criteria
- Only Bernard's own words: no message by anyone else.
- Out: health, medication, drugs, self-harm, sexuality and gender, religion,
  politics, and anything about a third party (names removed or the line dropped).
- Out: mentions of the personas by name, URLs, numbers.
- Light edits only: accents, punctuation, a trimmed clause. The vocabulary stays.

## Why not a public corpus
Researched 2026-11-20: no downloadable corpus of real Mexican vulgar dialogue
carries a license for this use (PRESEEA/CSCM are research-only, CC BY-NC-ND;
MEX-A3T/OffendMEX are isolated tweets on request), and scraping X, Reddit,
Facebook or YouTube breaks their terms.

Load: `python scripts/ingest_style_pool.py --persona insult` (replaces the namespace).
