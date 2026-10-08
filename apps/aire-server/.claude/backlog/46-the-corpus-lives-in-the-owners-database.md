# `rag_store` joins the registry — and the corpus lives in the owner's database

Status: **Done — schema, tool, scope, watched. Lexical retrieval, by decision**
Proposed: 2026-08-24 by Bernard (`/ultra-lord`, "sí, ejecutar ahora")

## What it is

The registry's fourth tenant. A consumer uploads documents into a corpus and the
agent searches it mid-turn instead of guessing. `aire/corpus.py` is the storage,
`engine/corpus_tool.py` the tools — fi-core's names exactly, because a consumer's
prompt binding orders the model to call `search_documents` and a rename here would
leave it reaching for a tool that does not answer.

## Why this is not a vendoring job like #45

fi-core's `rag` is ~2,000 lines: an embedder, an hdf5 store, chunking, hybrid
retrieval, a reranker. All of it assumes a machine with room, and this droplet has
512 MB and a $20/mo ceiling ([[do-budget]]).

What actually decided it was the law rather than the budget: **the memory lives in
the owner's database, never on the mortal box** ([[log-is-the-truth]] prohibition
2). A corpus on the droplet's disk dies with the droplet — it would be the same
defect AIRE was built to fix, reintroduced for documents instead of transcripts.

So the corpus is a table in the owner's Postgres and the retrieval is Postgres's
own full-text search: `tsvector` + a GIN index, already shipping inside the
database that holds the transcript. No embedder, no model, no network, nothing to
install. **It matches on words, not on meaning** — a real ceiling, stated here so
nobody discovers it as a bug later. The `spanish` configuration, because that is
what these users write; an English document still matches its own unstemmed words.

## The scope, and its honest boundary

Rows carry an `owner`, derived from the casita's `@base` (#36) and **read off disk,
never off the wire**. Every chat of one consumer resolves to the same shelf — which
is what makes a project's documents visible from more than the chat that uploaded
them — and a casita of a different consumer cannot name that shelf at all.

Inside a shelf, `corpus_id` separates one project from another. Separating a
consumer's END USERS from each other is the CONSUMER's job, done by making
`corpus_id` a per-user id. That is exactly the guarantee its local store gave,
carried over unchanged — AIRE is not adding a boundary here, and it is not
removing one either. If that ever needs to be AIRE's job, the honest place is a
scope derived from the door token, not from the wire.

## What the broom does NOT do, and who watches instead

`aire_corpus_chunk` is the SECOND table the sweep deliberately never touches: a
document does not stop being wanted because it is thirty days old. It shrinks only
when someone deletes it through the tool.

Unbounded by design means watched on purpose, so it went into `infra/growth.py`'s
map the same hour. That map is explicit — a table absent from it is a table nobody
is measuring — which is the [[do-budget]] lesson about never watching only the
place where the spend is already frozen.

## The correction the live turn forced

The first shape indexed the accented text directly, and the very first real turn
found the hole: a model searching `telemetría` missed a document that said
`telemetria` and retried twice with narrower queries before it landed. Postgres's
`spanish` configuration stems and drops stopwords but does NOT fold diacritics
without the `unaccent` extension — and in Spanish that is the single most common
way a search quietly fails, paid for in retries the user never sees.

Folded in Python (`chunking.fold`) rather than by installing `unaccent`: it works
on any Postgres, needs no extension enabled and no superuser asked. The row keeps
its ORIGINAL text for reading; a `norm` column holds the folded copy and the
tsvector is generated over that. `corpus_schema.py` carries the migration that
brings an already-created table to that shape, guarded on the catalog so it runs
exactly once.

This is the loop doing its job: the first version was untested, the first real turn
corrected it, and only then was it right.

## Verified

Against the real Postgres, not a fake, because everything load-bearing here is the
database's: the generated `tsvector`, `websearch_to_tsquery` surviving a model's
prose (`to_tsquery` raises on a bare sentence, which would turn a retrieval into an
error mid-turn), re-ingest replacing instead of appending, and the `owner` scope.
A fake would have passed while any of the four was wrong.
