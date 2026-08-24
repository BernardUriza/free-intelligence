# Only the MODEL can write a corpus — the upload endpoint has no door

Status: **Proposed — blocks Projects on the AIRE route**
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

**The read half is the decision, and it is Bernard's.** og118's project panel draws a
document list and a capacity meter, which is a read whose result reaches a HUMAN'S
EYES — the thing [[write-only-daemon]]'s criterion excludes. Two defensible readings:

- It is a consumer reading ITS OWN corpus through an API, not AIRE rendering a view;
  the rule is about the daemon never becoming a renderer, and JSON is not a view.
- It is a waiter read wearing a consumer's clothes, and the honest home is the front.

Nothing gets built on the read half until that is settled. The write half plus a
`GET` that answers the machine (does this doc exist, how many chunks) may be enough
to unblock the upload without touching the question at all — that is the shape to
try first.

## What NOT to do

Do not have the upload endpoint spend a turn asking the model to ingest. It works and
it is grotesque: a paid inference per uploaded file, and a write path whose success
depends on the model deciding to comply.

See #46 (the corpus), [[write-only-daemon]] (the criterion the read half tests),
[[ssh-is-a-missing-endpoint]] (a missing endpoint is the work, not the excuse).
