# Voice (TTS) Rules

How personas speak, post-purga. **Prod runs susurro only.** The old Insult
VoiceCog (`personas/insult/cogs/voice/cog.py`) and its arbor switch died with
`personas/` in 2f8d9ad; the live voice path is entirely in the gateway:

- **Trigger**: 🔊 reaction on one of the persona's OWN messages →
  `persona_gateway/gateway.py::on_raw_reaction_add` → `PersonaVoice.speak`
  (`persona_gateway/voice.py`). Auto-speak fires for replies at/above
  a configurable char threshold (0 = manual 🔊 only).
- **Backend**: `khimeras_shared/tts.py::synthesize_susurro_tts` against the
  **susurro gateway** — `sus.bernarduriza.com` (`POST /v1/tts`; STT via
  `/v1/stt`, client in `khimeras_shared/stt.py`). Project-keyed proxy over a
  dedicated Azure OpenAI; key in `~/.secrets/susurro-key-discord-bot.txt`,
  gateway config `susurro_url`/`susurro_key` (`persona_gateway/config.py`).
  The old direct Azure `tts`/`whisper` deployments were DELETED at the susurro
  migration (2026-06-19).
- **Arbor is NOT wired**: the gateway path hardcodes `arbor_active=False` and
  its config has no arbor vars — there is no prod arbor switch anymore. Arbor
  remains a RETIRED, LOCAL-ONLY tool (2026-06-01 decision), documented below
  as reference because its facts were expensive to discover.

Voice is fail-soft: no susurro creds → `build_susurro_tts_client` returns
`None` → voice is simply off, never a crashed persona.

---

## REFERENCE — the retired Arbor service (`arbor-tts/`, local-only, no prod path)

A Node/Playwright "black box": text → ChatGPT's **Arbor** voice MP3 via the
undocumented `GET /backend-api/synthesize`. It is NOT an API — it drives a
logged-in ChatGPT web session. Self-contained docs in `arbor-tts/README.md`.
Nothing in the live packages calls it (`grep -rn ARBOR_TTS_URL --include='*.py' .`
→ empty); reopening it in prod is a decision for Bernard, not a default.

### Hard, expensive-to-rediscover facts (verified 2026-06-01)

- **"Arbor" is a display name; its internal voice id is `fathom`.** `voice=arbor`
  → 404; `voice=fathom` → 200. The voice map lives in `arbor-tts/src/voices.js`.
  Other ids: cove, breeze, vale, maple, ember, juniper, spruce=`orbit`, sol=`glimmer`.
- **`fathom` is NOT an official-API voice.** Tested against Azure OpenAI `tts`
  (tts-1) → 400 ("allowed values are: nova, shimmer, echo, onyx, fable, alloy").
  It is reachable ONLY through the ChatGPT web backend. Do not propose
  `/v1/audio/speech` for the Arbor voice — it will not work.
- **`synthesize` is token-portable** (works with `Bearer` accessToken from
  `/api/auth/session`, no cookies, any IP) BUT **only on assistant message ids**
  (user message id → 403). So the service sends text to an echo GPT and
  synthesizes the echoed reply.
- **Message creation needs a real browser.** `sentinel/chat-requirements` returns
  `proofofwork.required: true` (+ turnstile). A headless Chromium gets flagged
  (placeholder message id, no `/c/<uuid>`), even on a residential IP. The
  **logged-in non-headless Chrome via CDP passes.** Therefore the service must run
  in **CDP mode** (`CDP_URL=http://127.0.0.1:9222`), attached to the user's
  debug-profile Chrome — NOT headless `storageState`.
- **A cloud VM cannot run it.** Azure datacenter IPs get **403** on
  `/backend-api/conversation/init`, `/sentinel/chat-requirements/prepare`, etc.
  (residential IP works; datacenter does not). `infra/azure/arbor-tts/` exists but
  the VM path is a dead end — keep it only as reference.

### Deployment shape it used (Mac-as-backend, for the record)

- Runtime at `~/Library/ArborTTS`, NOT `~/Documents` — launchd cannot access
  TCC-protected `~/Documents`/`~/Desktop`/`~/Downloads`.
- launchd agents: `com.bernard.arbor-tts` (Node service) +
  `com.bernard.arbor-tts-tunnel` (cloudflared).
- `SERVICE_TOKEN` in `~/.secrets/arbor-tts-token.txt` (never in the repo).
- cloudflared Quick Tunnel URLs are EPHEMERAL (change on every restart);
  Tailscale Funnel (`*.ts.net`) was the stable upgrade.
- Debug order when it went mute: Mac awake? → Chrome :9222 answering? →
  tunnel URL still current? → ChatGPT session (`/api/auth/session`) alive?
  A placeholder-id `404` from `/tts` means message creation failed
  (headless/datacenter/Chrome down), not a code bug.

### ToS / safety

Driving a personal ChatGPT account programmatically violates OpenAI's ToS; ban
risk scales with volume. That risk profile is part of why arbor stays retired:
susurro (`/v1/tts`) is the ToS-clean path and the only one wired.
