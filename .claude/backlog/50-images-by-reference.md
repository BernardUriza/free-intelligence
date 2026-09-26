# 50 — Images by reference: the caller sends a signed URL, AIRE fetches the bytes

Status: **Done** 2026-09-25 end to end — AIRE `5cd1cee`, fi-runner 0.22.0 (free-intelligence PR #495), server-bot v4.41.0 + PR #100 (v4.41.2); live probe passed in #general. PDFs and text files (item 6) closed the same day by reference — see *Documents by reference*. Proposed 2026-09-25 by Bernard (*"un bypass SOLO para las imágenes, saltarlas directo de discord a AIRE como datos, y en el pipeline van solo los metadatos"*). Not started. Consumer-side twin: server-bot `.claude/backlog/imagenes-claim-check-discord-aire.md`.

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

## What the 2026-09-25 research added (receipts, not guesses)

7. **Resize, don't just compress: long edge ≤ 2000 px.** When a request carries
   more than 20 images, *counting the ones resent from earlier turns*, every
   image must be ≤ 2000 px per side or the API rejects the **whole request**
   (`invalid_request_error`, "many-image requests"). Once a session crosses 20
   images, one old 4000 px photo kills every later turn. Downscaling to 2000 px
   loses almost nothing (the hi-res tier downsamples to 2576 anyway), and it also
   shrinks the bytes that sit in the transcript forever.
   ([vision docs](https://platform.claude.com/docs/en/build-with-claude/vision))
8. **History is resent every turn.** Base64 images ride in the payload on every
   later turn of the session, against a **32 MB request limit**. Today it is
   latent: the worst session holds 4 images / ~2 MB, and zero `many-image` /
   `request_too_large` errors are in the store. It stays latent only while the
   consumers keep rotating sessions, so the cap on images per session belongs here,
   not by accident in the consumer.
9. **The real API cap is 10 MB base64 per image** (5 MB is Bedrock/Vertex). The
   limit that bites on this box is RAM, not Anthropic.
10. **SSRF: a host allowlist is not enough.** Resolve the host once, reject
    private/loopback/link-local/CGNAT/metadata IPs, and connect to that IP
    (Host + SNI preserved). Re-validate after every redirect, or disable
    redirects. Otherwise DNS rebinding gets around the allowlist. httpx 0.28.1 is
    already in the venv.
11. **Pillow is not installed** on the droplet. When it comes in: keep
    `MAX_IMAGE_PIXELS` (never `None`), turn `DecompressionBombWarning` into an
    error, and decode with `draft()`/`thumbnail()` so a 12 MP JPEG decodes small
    and not as ~36 MB of RGB on a box with ~186 MB free.
12. **Timeouts on the fetch** (connect/read, total ≤ ~15 s). A CDN read with no
    timeout hangs for 60-120 s (hermes-agent #33400).
13. **Storage weight is real:** 85 image entries = **35 MB of the 132 MB**
    `claude_session_store` (26%) in 5 weeks, never swept (the store is deathless
    by design). Resizing to 2000 px is also the growth fix.

## Tests it needs

Positive: a `{url}` image on the allowlist reaches `query_input` as a base64 block;
an oversize image comes back under the cap. Resistance: off-allowlist host →
refused without a request; redirect to a foreign host → refused; expired/404 →
declared error; 5 images → still refused (the cap does not move); count in the
result equals images attached.

## What landed (AIRE side, 2026-09-25)

- `engine/fetch.py` — the `{url}` fetch: allowlist (`AIRE_IMAGE_HOSTS`), resolve once,
  refuse the name if ANY address is non-global, connect to the pinned IP with `Host`
  + SNI on the real name (TLS still verified), 3xx refused, 15 s total, 10 MiB cap
  while streaming. Items 1, 4, 10, 12.
- `engine/shrink.py` — Pillow, lazy-imported: bomb guard armed and its warning made an
  error, JPEG `draft()`, ≤ 2000 px, EXIF rotation baked in, media type DETECTED. An
  image already ≤ 2000 px, ≤ 1 MB and upright rides byte-identical. Items 2, 7, 11.
- `engine/image_budget.py` — before the turn, the session's images already in
  `claude_session_store` + this turn's must fit 100 images / 24 MB base64, or 422
  "start a new session"; unreadable store → 503. Item 8.
- `result` SSE event carries `images_attached`. Item 3. Inline `{media_type, data}`
  still accepted and now also shrunk; its edge cap rose to 14 M chars (~10 MB, the API's
  real cap) because oversize is shrunk, not refused. Item 5.
- `pillow` in `requirements.txt` → the deploy installs it on the droplet.

Receipts:
- Live, from the Mac: four real #general attachments by signed URL through
  `prepare_images` in 2.4 s — the pinned-IP TLS handshake to `cdn.discordapp.com`
  works; three 2160×2880 iPhone photos of 2.7-4.7 MB came out 1500×2000 at 0.65-1.07 MB
  (q85); the 17 KB PNG rode untouched; the bare path → declared `404`.
- The budget SQL against the real store returns the measured numbers (4 images /
  1.68 MB, 4 / 1.90, 3 / 0.84) in 77-157 ms from the Mac.
- Mutation: disabling the IP check or enabling redirects turns 8 fetch tests red;
  dropping the bomb-warning promotion turns its test red; dropping `exif_transpose`
  turns the rotation test red.
- **Through the real door** (deploy `f594160`, `gate.bernarduriza.com`, 2026-09-25): a
  turn with two `{url}` images answered correctly about both, so Pillow and the
  pinned fetch run on the droplet; `169.254.169.254` → 422 "host not allowed"; the
  bare path → 422 "answered 404"; `result` carries `images_attached`. In the store the
  photo sits as 1500×2000 / 467 KB — the CLI re-encodes once more after AIRE, so what
  the transcript keeps is still the CLI's choice.

**Correction to item 7/13, measured, not assumed:** all 90 images in the store are
already ≤ 2000 px (max side exactly 2000) — the bundled CLI resizes before it writes
(its bundle carries `maxWidth:2000` / `maxHeight:2000` / `maxBase64Size:5242880`). So
the many-image rule was never exposed on the native path, and resizing to 2000 alone
does not shrink what the store keeps. What AIRE's shrink adds is ownership of the rule
(not an undocumented CLI internal), a q85 re-encode that cuts phone photos ~70-75%
before they reach the CLI's own encoder, and a CLI that never decodes a 12 MP photo
on a 512 MB box.

Still open: the consumer twin (discord-bot) switching to `{url}` and deleting its own
`5_000_000` cap and 2048-px compressor; comparing `images_attached` there; PDFs (item 6).

## Closed end to end (2026-09-25)

- **fi-runner 0.22.0**: `TurnImage(url=...)`, `TurnResult.images_attached`, and an
  `[attachments_lost]` AIREDoorError when the door's count differs from what was sent.
- **server-bot v4.41.0**: the gateway sends the signed URL (URL-source block) and never
  downloads an image; its 2048-px compressor and `5_000_000` cap are deleted (one owner of
  the caps: this repo). `turn_jobs` keeps the references, so a resumed job carries its
  images; a signature that expired before the resume is `not_resumable`, out loud. The
  consumer does NOT re-sign with `refresh-urls`: that would hand the runner a Discord bot
  token. **PR #100 (v4.41.2)** rescued the parts of the parallel PR #97 that main lacked:
  `job_id` across gateway/runner logs and the over-4-images note in the persona's voice.
- **Live probe**: `probe-50.png` (3200×2400, "MANGO 5082") sent to @Vultur in Khimeras
  #general at 22:35 UTC. Vultur read "MANGO 5082 sobre verde selva, círculo magenta" and
  signed ᵛ⁴·⁴¹·¹. In `claude_session_store` it sits as a 2000×1500 JPEG of 56,619 bytes.

## Documents by reference (item 6, 2026-09-25)

- **AIRE `6b59010`** — `documents: [{url, title?}]` through the same SSRF-pinned fetch;
  the type is DETECTED (`%PDF-` → base64 PDF block, else UTF-8/latin-1 text, binary
  refused, text capped at 200k chars). The engine now carries ready content blocks as
  one `attachments` tuple; `image_budget` became `attachment_budget` (documents weigh
  against the 24 MB resend cap; a missing store table reads as an empty session). The
  `result` event carries `documents_attached`. ACP: text rides as text, a PDF is 422
  at the door.
- **Verified before building**: the bundled CLI takes both document shapes through
  streaming input — a local turn read "PERA 7719" from a PDF and "LIMA 4402" from a
  text document.
- **fi-runner 0.23.0** (free-intelligence PR #496): `TurnDocument`,
  `TurnResult.documents_attached`, `attachments_lost` on a short count; `Runner.run` /
  `run_stream` take `documents=`.
- **server-bot v4.42.0** (PR #106): PDFs and text files ride as URL-source `document`
  blocks; the consumer downloads nothing anymore. Caps told in character: 10 MB per PDF,
  200 KB per text file, 4 documents per message.
- **Real-door resistance**: a real Discord MP3 as a document → 422 "neither a PDF nor
  text"; an off-allowlist host → 422.
