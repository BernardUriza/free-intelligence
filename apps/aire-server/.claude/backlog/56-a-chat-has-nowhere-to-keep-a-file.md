# 56 — A chat has nowhere to keep a file

Status: **Proposed**
Proposed: 2026-11-17 by Bernard (*"no hay entonces storage para mí en el droplet? en caso de que mis
chats quieran guardar info pdf o h5? files?"*)

## What it is

A chat that produces or receives a binary (a PDF to keep, an `.h5`, a dataset, a render) has no durable
place in AIRE to put it and no way to ask for it back as a file. Read from the code on 2026-11-17:

| Surface | What it keeps | Where it stops |
|---|---|---|
| Casita disk, `/opt/aire/workspaces/<casita>/` | Any file the agent writes, binaries included; listed and fetched through `GET /projects/{project}/artifacts[/{subpath}]` (`server/aire/artifacts.py`) | The droplet's mortal disk. Only `CLAUDE.md` is made deathless (`server/aire/casita.py`). No upload door: only the model writes there |
| Corpus (#46, #47, #55) | Text in the owner's Postgres, searchable, versioned | Text only, 1 MB per document (`corpus_door.MAX_DOC_BYTES`) |
| Turn attachments (#50) | Images and PDFs by signed URL; the PDF stays in the transcript as base64 | Input to a turn, not a store: 4 documents per message, 100 pages and 24 MB per session, resent on every turn; any other binary is a 422. Nothing hands the file back |

Two facts that size the gap:

- The droplet is `s-1vcpu-512mb-10gb` with DigitalOcean backups off (`server/infra/README.md`,
  `provision-do.sh`). Ten gigabytes total, shared with the OS, the venv and the Codex binary. The free
  space on the live box was NOT measured for this card.
- [`07-backups.md`](07-backups.md) covers Postgres only (Azure 7-day PITR). Nothing backs up
  `/opt/aire/workspaces`. A rebuilt box brings every casita back with its transcript and its persona and
  none of its files.

## Correction, 2026-11-17 — the monorepo already has an `.h5` and a durable volume, neither on the droplet

Bernard, the same day: *"pero tiene el h5"*. He is right that it exists; the first draft of this card
searched only `apps/aire-server` and missed it.

- **The `.h5` is fi-core's chunk store** (`fi_core/stores/hdf5.py`): namespaces, documents and text
  chunks with an in-memory cosine index. It holds text for retrieval, not a caller's files, and it is not
  a place to drop an arbitrary binary.
- **og118 stopped reading it.** `apps/og118/server/deps.py` `get_rag_store` returns `AireCorpusClient`
  only, since the consolidation of 2026-08-24; its own comment says nobody reads the container's HDF5.
- **The durable volume is real and already paid.** `og118-api` mounts the Azure Files share `ragstore`
  (storage account `og118ragstore`, `og118-rg`, 5 GiB quota) at `/opt/fi/data`. Measured 2026-11-17:
  1,608,192 bytes used. og118 keeps its conversations, project registry and device tokens there as JSON.
  It belongs to og118's container; the droplet does not mount it.

So point 1 below is cheaper than first written: `og118ragstore` is a StorageV2 account, and a blob
container in it is no new resource.

## Canonical path to reuse (Art. 6)

- `og118ragstore` (above) is the store that already exists and survives every box.

- `server/aire/artifacts.py` is already the download half, with the cage's `escapes` as the one
  confinement rule. The missing half is durability and an upload, not a new read surface.
- `server/aire/casita.py` is the proven pattern for making a disk file deathless: `offer` pushes a changed
  file, `restore` re-materializes an absent one, disk wins. That pattern is sound for a 4 KB `CLAUDE.md`
  in Postgres. It must not be copied as-is for binaries: the transcript already carries 35 MB of images
  (#50, item 13), and an `.h5` in a Postgres row is the same mistake at a larger size.
- `server/aire/engine/fetch.py` is the SSRF-pinned fetch, should an upload arrive by reference like #50.

## The decision that's the owner's

1. **Where the bytes live.** An object store outside the droplet (Azure Blob in `og118-rg`, where
   `insultstorage` already sits) with the casita as a cache. That is the only shape that passes the litmus
   test: a DigitalOcean volume or Space keeps the files in a body, and [[do-budget]] lists both as
   outside the budgeted inventory (one droplet, nothing else). Any of them spends money: Bernard's call.
2. **Who may write.** Only the agent (today's rule), or also the caller through an upload door, as #47
   did for the corpus.
3. **Caps.** Per file and per project, and whether an invited key (#51) may store at all.

## Status / next step

Nothing built. Next: read the live disk figure (costwatch already goes red past 80%, [[do-budget]]) and
the weight of `/opt/aire/workspaces`, then Bernard picks the store in point 1.
