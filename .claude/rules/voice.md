# Voice (TTS) Rules

How Insult speaks. There are TWO TTS backends; which one runs is decided at
request time by whether `ARBOR_TTS_URL` is set.

## Two backends, one switch

| Backend | When | Voice | Where it runs |
|---|---|---|---|
| **Azure OpenAI TTS** (default/fallback) | `ARBOR_TTS_URL` unset | `onyx` (Insult) / `nova` (ALICE) | Azure `insult-openai` `tts` deployment |
| **Arbor TTS** (external) | `ARBOR_TTS_URL` set | `arbor` (ChatGPT consumer voice) | external HTTP service on a residential host |

Code: `insult/cogs/voice.py` — `on_raw_reaction_add` (🔊 reaction) →
`generate_arbor_tts_audio()` when `settings.arbor_tts_url` is truthy, else the
Azure `client.audio.speech.create(...)` path. Config vars in `insult/config.py`:
`arbor_tts_url`, `arbor_tts_token` (SecretStr), `arbor_tts_voice` (default
`arbor`), `arbor_tts_timeout_seconds` (default 240). The bot calls the service
with `Authorization: Bearer <token>` and `POST /tts {text, voice, format}`.

## The Arbor service (`arbor-tts/`)

A Node/Playwright "black box": text → ChatGPT's **Arbor** voice MP3 via the
undocumented `GET /backend-api/synthesize`. It is NOT an API — it drives a
logged-in ChatGPT web session. Self-contained docs in `arbor-tts/README.md`.

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

## Production deployment shape (Mac-as-backend)

Because only a residential IP + non-headless Chrome works, Arbor runs on Bernard's
Mac, exposed via a tunnel; the Azure `discord-bot` calls it.

- **Runtime lives at `~/Library/ArborTTS`, NOT in `~/Documents`** — launchd cannot
  access TCC-protected `~/Documents`/`~/Desktop`/`~/Downloads` ("Operation not
  permitted"). Deploy the runtime (src + node_modules + .env + auth) under
  `~/Library/...`.
- **launchd agents** (`~/Library/LaunchAgents/`): `com.bernard.arbor-tts` (the
  Node service, KeepAlive) and `com.bernard.arbor-tts-tunnel` (cloudflared).
- **SERVICE_TOKEN** in `~/.secrets/arbor-tts-token.txt` (never in the repo). Same
  value set as the `arbor-tts-token` Container App secret, referenced by
  `ARBOR_TTS_TOKEN=secretref:arbor-tts-token`.
- **Tunnel:** cloudflared Quick Tunnel works with zero account but its
  `*.trycloudflare.com` **URL is EPHEMERAL — it changes on every cloudflared
  restart and breaks `ARBOR_TTS_URL`.** The stable upgrade is **Tailscale Funnel**
  (`*.ts.net`, needs `sudo brew services start tailscale` + `tailscale up` +
  `tailscale funnel --bg 8799`); update `ARBOR_TTS_URL` once and it never changes.
- Wiring the bot is a Container App env change → new revision → restart. Safe now
  (data plane is Postgres, no blob race).

## Debugging "Insult went mute" (check in this order)

1. **Mac awake?** The service only answers when the Mac is on.
2. **Chrome on :9222 running?** (`curl -s -o /dev/null -w '%{http_code}'
   http://localhost:9222/json/version` → 200). CDP mode needs the logged-in,
   non-headless Chrome. This is the #1 cause.
3. **Tunnel URL still matches `ARBOR_TTS_URL`?** If cloudflared restarted, the
   `trycloudflare` URL changed — re-read it from
   `~/Library/ArborTTS/cloudflared.log` and update the Container App env.
4. **ChatGPT session alive?** `/api/auth/session` must return an `accessToken`.
   In CDP mode the live Chrome keeps it fresh; if expired, re-login in that Chrome.

A `404`/placeholder error from `/tts`
(`message_id=request-placeholder-...`, `conversation_id=undefined`) means message
creation failed — almost always headless/datacenter (wrong host) or Chrome :9222
down, NOT a code bug. `synthesize.js` already polls for a real UUID id.

## ToS / safety

Driving a personal ChatGPT account programmatically violates OpenAI's ToS; ban
risk scales with volume. Keep Arbor **on-demand only** (user presses 🔊) and
low-volume. Do NOT auto-speak every message — constant automated traffic is what
flags an account. When in doubt, the Azure `tts` fallback is always ToS-clean.
