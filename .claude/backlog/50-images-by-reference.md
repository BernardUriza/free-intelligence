# 50 — Images by reference: the caller sends a signed URL, AIRE fetches the bytes

Status: **Proposed** 2026-09-25 by Bernard (*"un bypass SOLO para las imágenes, saltarlas directo de discord a AIRE como datos, y en el pipeline van solo los metadatos"*). Not started. Consumer-side twin: server-bot `.claude/backlog/imagenes-claim-check-discord-aire.md`.

## Why

Today an image rides base64 through four hops (Discord → persona-gateway →
persona-runner → AIRE → Claude) and no hop checks that what leaves is what
arrives. Two losses in September, both silent:

- **23→25-sep:** the runner rebuilt a resumed job from its `turn_jobs` row, which
  never stored the image — Insult answered "the image didn't load" for two days
  (fixed consumer-side, server-bot #92, v4.40.21).
- **8→19-sep, 18 turns:** images between ~3.7 and 5 MB hit `MAX_IMAGE_B64` → 422
  → the whole turn died. Fixed by copying `5_000_000` by hand into the consumer —
  the cap now lives in two repos.

Still open: a message with ≥5 photos (Discord allows 10) → `MAX_IMAGES=4` → 422,
turn dead; PDFs are dropped by the consumer because this door only takes images.

## The decision: Claim Check, Discord's CDN as the store

Not a bypass: the **reference** rides the pipeline (the full signed URL + size +
`media_type`), AIRE — the last hop — fetches the bytes. The consumer persists the
reference, so a resumed/rebuilt job carries the image by construction.

Receipts (2026-09-25, from the droplet):
- `curl` the signed URL of a real #general attachment → `200`, 17,795 B, `image/png`.
- Same URL without `ex/is/hm` → `404`: the reference is the whole URL, not the path.
- `ex - is = 86400`: signatures live **24 h** — plenty against a 600 s turn budget,
  not a durable store.
- **The 24 h window is closed by refreshing, not by storing** (verified 2026-09-25):
  the bare path of a real #general attachment → `404`; the same bare path through
  Discord's `POST /api/v10/attachments/refresh-urls` (`{"attachment_urls": [...]}`,
  bot token) → a freshly signed URL → `200`, 2,677,920 B. So the consumer persists
  the **path**, and re-signs it right before each send, resumes included. A job
  resumed days later still carries a live image.
- **Refreshing is the consumer's job, never AIRE's.** It takes a Discord bot token,
  and AIRE holds no consumer's credentials (a credential is scoped to the surface it
  was handed to). AIRE only fetches what it receives; an expired URL stays a
  declared error (item 4 below).
- **After the turn the image is durable anyway:** the transcript stores the image
  block in base64 (85 `image` entries in `claude_session_store` on 2026-09-25), and
  `resume` hands it back to Claude. The signed URL only has to live until the turn
  runs. No OCR, no embeddings: they would downgrade an image Claude already sees
  natively and store a copy of what the memory already holds.

## What it has to carry (or it opens new holes)

1. **Host allowlist** — `cdn.discordapp.com`, `media.discordapp.net`. AIRE serves
   other consumers; a door that fetches arbitrary URLs is SSRF. No redirects off
   the allowlist, bounded download size, short connect/read timeouts.
2. **Compression moves here**, next to `MAX_IMAGES` and `MAX_IMAGE_B64`
   (`server/aire/engine/vision.py:15-16`): an image over the cap is re-encoded to
   JPEG to fit instead of 422-ing. One owner for the caps; the consumer's copy of
   `5_000_000` gets deleted. **512 MB box: one image at a time**, never the four in
   parallel.
3. **The result reports how many images were attached** (`TurnResult` / the
   `result` SSE event), so the consumer can compare against the references it sent
   and fail loud (`attachments_lost`) on a mismatch instead of answering blind.
4. **A fetch failure is a declared error** (expired signature, 404, off-allowlist,
   too big) — a 422 naming which image, never a silent text-only turn.
5. **`{media_type, data}` stays accepted** alongside `{url}` during rollout (other
   consumers, half-rolled deploys); retire it when nobody sends it.
6. Later, same mechanism: PDFs as `document` blocks.

**Not doing:** passing the URL to Anthropic (`source: url`). Unverified with the
Agent SDK + OAuth, and it loses compression and error control.

## Tests it needs

Positive: a `{url}` image on the allowlist reaches `query_input` as a base64 block;
an oversize image comes back under the cap. Resistance: off-allowlist host →
refused without a request; redirect to a foreign host → refused; expired/404 →
declared error; 5 images → still refused (the cap does not move); count in the
result equals images attached.
