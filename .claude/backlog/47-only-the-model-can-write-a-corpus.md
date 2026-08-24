# Only the MODEL can write a corpus — the upload endpoint has no door

Status: **Done — both halves, by Bernard's decision on the read**
Proposed: 2026-08-24, from a regression shipped and rolled back the same hour

## The gap, and how it was found

#46 gave AIRE a `rag_store` tool and it works: verified on the live gate, a
document ingested in one session retrieved from another. On that evidence og118 got
its corpus binding back — and fifteen minutes later the real UI showed what the
verification had missed.

A user uploads an acta. The project panel shows it. The agent answers:

> *"No encuentro ningún documento en tu proyecto — el acta que mencionas no llegó o
> no se subió correctamente."*

**The `ingest` in the verification was done by Claude, calling the new tool.** The
product's own write path — og118's upload endpoint — still writes through
`RagStoreClient` to a local hdf5 file that nothing on the AIRE route reads. Half the
data path moved, so the corpus the agent searches is always empty, and the answer is
not merely unhelpful: it is confident, false, and it blames the user for an upload
that worked. Rolled back in free-intelligence #429 the same hour.

## What is missing

**A corpus door over HTTP.** Today a corpus can only be written from INSIDE a turn,
by the model, through the MCP tool. og118's upload is server code and has nothing to
call — the [[ssh-is-a-missing-endpoint]] formula exactly.

The write half is uncontroversial: `POST /projects/{p}/corpus/{corpus_id}/documents`
appends, `DELETE` removes. The daemon appends; that is what it is for.

**The read half was the decision, and Bernard took it on 2026-08-24**: the door
serves `GET .../documents` with the list and the capacity meter too, so og118 can
switch its local store off on this route instead of keeping a second one alive to
draw a panel. That widens [[write-only-daemon]]'s criterion — the rule now records
the reasoning and, more usefully, the sharper test that replaced it: *does the
caller own the rows it is asking for?* A consumer reading its own corpus back is
retrieving its data; the front reading everyone's transcripts to render them is
still the waiter's job.

What shipped: `POST .../documents` (replace by doc_id), `GET .../documents` (list +
capacity), `DELETE .../documents/{doc_id}` and `DELETE .../corpus/{corpus_id}`. All
behind the Bearer, all deriving `owner` from the casita's `@base` exactly as the
tool does — so a document uploaded through the door and a search run inside a turn
land on the same shelf by construction, not by two conventions that happen to
agree. `tests/test_corpus_door.py` pins that crossing directly: write through the
door in the base casita, search through the tool from a CHAT casita, find it.

## What NOT to do

Do not have the upload endpoint spend a turn asking the model to ingest. It works and
it is grotesque: a paid inference per uploaded file, and a write path whose success
depends on the model deciding to comply.

See #46 (the corpus), [[write-only-daemon]] (the criterion the read half tests),
[[ssh-is-a-missing-endpoint]] (a missing endpoint is the work, not the excuse).
