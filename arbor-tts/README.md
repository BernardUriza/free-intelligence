# arbor-tts

A headless **black-box TTS** service that turns text into ChatGPT's **Arbor** voice
audio. Input: text. Output: an `mp3` (or `aac`/`opus`) spoken in the same
consumer voice you hear when you click **Read aloud** in the ChatGPT app — a voice
that is **not reachable through any public API**.

It works by driving your logged-in ChatGPT session with Playwright (headless) and
calling ChatGPT's own undocumented `/backend-api/synthesize` endpoint.

> ⚠️ This automates a logged-in ChatGPT web session with your personal account.
> That may be against OpenAI's Terms of Service. Use it for your own personal
> experiments at your own risk. Do not resell or abuse it.

---

## How it works (reverse-engineered 2026-06-01)

The ChatGPT "Read aloud" button is **not a stream**. It's a single GET that returns
a complete audio file:

```
GET https://chatgpt.com/backend-api/synthesize
    ?message_id=<assistant message id>
    &conversation_id=<conversation id>
    &voice=<internal voice id>      # Arbor = "fathom"
    &format=<mp3 | aac | opus>      # wav -> 422
Authorization: Bearer <session accessToken>   # cookies alone -> 401
```

Hard-won facts:

| Fact | Value |
|---|---|
| Endpoint | `/backend-api/synthesize` (GET, returns full file) |
| Auth | `Authorization: Bearer <token>` from `/api/auth/session` (cookies alone = 401) |
| Formats | `mp3` → `audio/mpeg`, `aac` → `audio/aac`, `opus` → `audio/ogg`; `wav` → 422 |
| Works on | **assistant** messages only (user message id → 403) |
| "Arbor" | a **display name** — its internal voice id is **`fathom`** (`voice=arbor` → 404) |

Because `synthesize` only voices **assistant** messages, the service sends your text
to an **echo GPT** so the assistant reply *is* your text, then synthesizes that reply.

### Voice mapping (display name → internal id)

| Pick in ChatGPT | `voice=` id | 200? |
|---|---|---|
| **Arbor** | **`fathom`** | ✅ |
| Cove | `cove` | ✅ |
| Breeze | `breeze` | ✅ |
| Vale | `vale` | ✅ |
| Maple | `maple` | ✅ |
| Ember | `ember` | ✅ |
| Juniper | `juniper` | ✅ |
| Spruce | `orbit` | ✅ |
| Sol | `glimmer` | ✅ |

Pass either form to this service (`voice: "arbor"` or `voice: "fathom"`).

---

## Setup

```bash
cd arbor-tts
npm install
npx playwright install chromium     # one-time browser download
cp .env.example .env                # then edit if needed

# One-time interactive login (opens a VISIBLE browser; log in by hand):
npm run login                       # saves ./auth/state.json
```

`auth/state.json` holds your ChatGPT cookies/token — it is **gitignored**. The
session expires periodically (ChatGPT tokens last ~days); when synthesize starts
returning 401/`login expired`, just run `npm run login` again.

---

## Usage

### As an HTTP service

```bash
npm start          # listens on :8799 (PORT in .env)

# client names the file:
curl -s -X POST http://localhost:8799/tts \
  -H 'content-type: application/json' \
  -d '{"text":"Hola, esta es la voz Arbor","voice":"arbor","format":"mp3"}' \
  --output arbor.mp3

# or let the service ALSO save it under output/ with an auto name:
curl -s -X POST http://localhost:8799/tts \
  -H 'content-type: application/json' \
  -d '{"text":"Hola, esta es la voz Arbor","voice":"arbor","save":true}' \
  -D - --output /dev/null      # see the X-Saved-Path response header
```

Response body is the raw audio (`Content-Type: audio/mpeg`), with `X-Voice-Id` /
`X-Voice-Name` headers. With `"save": true` it is also written under `output/` and
the path is returned in `X-Saved-Path`. If `SERVICE_TOKEN` is set in `.env`, send
`Authorization: Bearer <SERVICE_TOKEN>`.

By default, `/tts` is fail-closed for deployed use: `REQUIRE_SERVICE_TOKEN=1`
means the service refuses synthesis unless `SERVICE_TOKEN` is configured. It also
ships with conservative in-memory caps:

| Env | Default |
|---|---:|
| `TTS_ENABLED` | `1` |
| `RATE_LIMIT_WINDOW_MS` | `3600000` |
| `RATE_LIMIT_MAX_REQUESTS` | `20` |
| `DAILY_REQUEST_CAP` | `100` |
| `DAILY_TEXT_CHAR_CAP` | `100000` |

Set a cap to `0` to disable it. These are guardrails against accidental loops and
shared-token abuse; they are not a way to evade platform limits.

### Callback delivery

For service-to-service flows, the same endpoint can synthesize and then POST the
audio to one of your endpoints:

```bash
curl -s -X POST http://localhost:8799/tts \
  -H 'authorization: Bearer <SERVICE_TOKEN>' \
  -H 'content-type: application/json' \
  -d '{
    "text":"Hola desde Arbor",
    "voice":"arbor",
    "format":"mp3",
    "request_id":"job-123",
    "callback_url":"https://your-service.example/tts-ready",
    "callback_headers":{"authorization":"Bearer <callback-token>"}
  }'
```

Callbacks are disabled unless `CALLBACK_ALLOWLIST` contains the callback host.
The callback receives JSON with `audio_base64`, `content_type`, `bytes`,
`voice_id`, `voice_name`, `request_id`, and optional `saved_path`.

### As a CLI

```bash
# voice + path are optional and order-independent:
node src/cli.js "Texto a leer en voz alta"                 # auto name in output/
node src/cli.js "Texto a leer en voz alta" arbor           # pick voice, auto name
node src/cli.js "Texto a leer en voz alta" output/demo.mp3 # explicit path
```

---

## Output file naming

When a path is **not** given (CLI without an explicit file, or server with
`"save": true`), files are named deterministically under `output/`:

```
output/2026-06-01T16-22-03_arbor_la-historia-de-alemania_a1b2c3.mp3
        └── timestamp ───┘ └voz┘ └─ slug del texto (≤40) ─┘ └hash┘
```

- **timestamp** — chronological, never overwrites a previous run.
- **voice** — display name (arbor, cove, ember, …).
- **slug** — accent-stripped, lowercased text, hyphenated, capped at 40 chars.
- **hash** — first 6 hex of `sha256(text)`; same text ⇒ same hash.

If you pass an explicit path it is used verbatim (and overwrites). The server's
default response never touches disk — it streams the bytes and the caller names
the file; disk write only happens with `"save": true`.

## The echo GPT (important for clean output)

`synthesize` voices a stored **assistant** message, so the assistant reply must
equal your text. Default `CHATGPT_GPT_URL` is the **Mirror Emoji** GPT, which
echoes your text **plus 16 emojis**. Emojis are not vocalized, so audio is fine,
but the reply isn't strictly verbatim.

For guaranteed-verbatim output, create your own GPT with instructions like:

> Repeat the user's message back to them **verbatim**. Output only that text —
> no preamble, no emojis, no commentary.

…then put its URL in `CHATGPT_GPT_URL`.

---

## Caveats / known limitations

- **Login expiry:** re-run `npm run login` when the session dies.
- **Cloudflare + headless:** ChatGPT sits behind Cloudflare. A saved session
  usually passes headless, but a challenge can still appear; if so, run `npm run
  login` again (or set `HEADLESS=0` to debug). If headless gets challenged often,
  consider `chromium.launch({ channel: "chrome" })`.
- **DOM selectors** (`#prompt-textarea`, `[data-message-author-role="assistant"]`)
  are ChatGPT internals and may change without notice — update `synthesize.js` if
  sends stop working.
- **Serialized:** one ChatGPT session = one conversation at a time; requests are
  queued internally.
- **ToS:** see the warning at the top.

## Azure VM deployment

Infra scripts live in `../infra/azure/arbor-tts/`. They create a small Ubuntu VM,
install Node/nginx, deploy this service under `systemd`, and document the env vars
needed by the Discord bot (`ARBOR_TTS_URL`, `ARBOR_TTS_TOKEN`, `ARBOR_TTS_VOICE`).
