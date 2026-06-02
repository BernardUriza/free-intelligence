# Arbor TTS — macOS host stack

This is the **production deployment** of `arbor-tts` (it does NOT run in Azure —
ChatGPT's conversation API 403s from datacenter IPs; it must run on a residential
machine with a real, on-screen, logged-in Chrome). It runs as **four launchd
LaunchAgents** on Bernard's Mac. The Azure `discord-bot` reaches it over a tunnel.

## Architecture

```
Discord 🔊 → discord-bot (Azure)  ──HTTP(ARBOR_TTS_URL)──▶  cloudflared tunnel
                                                              │
                                                              ▼
                                          arbor-tts service :8799 (Node)
                                                              │ CDP
                                                              ▼
                                   Chrome :9333 (logged-in profile) → /backend-api/synthesize → Arbor mp3
```

- **Port 9333** is deliberate: the `chrome-devtools-mcp` owns 9222, and two CDP
  clients on one Chrome fight ("Browser context management is not supported").
  arbor-tts gets its own Chrome on 9333 so they never collide.
- The service is **self-healing**: it reconnects if Chrome restarts (KeepAlive) or
  if it started before Chrome after a reboot, and drops a crashed/stale page.

## The four LaunchAgents (in `~/Library/LaunchAgents/`)

| plist | role |
|---|---|
| `com.bernard.arbor-chrome.plist` | Chrome on :9333, `--user-data-dir=~/.chrome-debug-profile`, KeepAlive |
| `com.bernard.arbor-tts.plist` | the Node service (`~/Library/ArborTTS/run.sh` → `node src/server.js`), KeepAlive |
| `com.bernard.arbor-tts-tunnel.plist` | cloudflared Quick Tunnel → `:8799` |
| `com.bernard.arbor-tts-urlsync.plist` | every 120s runs `update-tunnel-url.sh`: if the (ephemeral) tunnel URL changed, `az containerapp update`s the bot's `ARBOR_TTS_URL` |

`update-tunnel-url.sh` lives in `~/Library/ArborTTS/` (copy from here). It replaces
Tailscale: instead of a stable URL, it keeps the bot pointed at whatever URL
cloudflared currently has.

## Rebuild on a fresh Mac

Prereqs: Google Chrome, Node 18+, `cloudflared` (`brew install cloudflared`),
`az` logged in (`az login`), and this repo cloned.

```bash
# 1. Runtime out of ~/Documents (launchd cannot read TCC-protected Documents)
mkdir -p ~/Library/ArborTTS
rsync -a --exclude node_modules --exclude auth --exclude '*.log' \
  <repo>/arbor-tts/ ~/Library/ArborTTS/
cd ~/Library/ArborTTS && npm ci && npx playwright install chromium

# 2. .env (SERVICE_TOKEN lives in ~/.secrets/arbor-tts-token.txt — never commit it)
cp <repo>/arbor-tts/.env.example ~/Library/ArborTTS/.env
#   set: SERVICE_TOKEN=<token>, CDP_URL=http://127.0.0.1:9333,
#        CHATGPT_GPT_URL=<an echo GPT>, ARBOR_VOICE=arbor

# 3. run.sh wrapper (sources .env, runs node)
cat > ~/Library/ArborTTS/run.sh <<'SH'
#!/bin/bash
cd ~/Library/ArborTTS
set -a; [ -f .env ] && . ./.env; set +a
exec /opt/homebrew/bin/node src/server.js
SH
chmod +x ~/Library/ArborTTS/run.sh

# 4. updater script
cp <repo>/infra/macos/arbor-tts/update-tunnel-url.sh ~/Library/ArborTTS/

# 5. Log into ChatGPT ONCE in the debug profile (real, on-screen window):
open -na "Google Chrome" --args --remote-debugging-port=9333 \
  --user-data-dir="$HOME/.chrome-debug-profile" --no-first-run \
  --no-default-browser-check "https://chatgpt.com/"
#   → log in, then quit it (the LaunchAgent will relaunch it)

# 6. Install the agents (edit the hardcoded /Users/<you>/ paths in the plists first)
cp <repo>/infra/macos/arbor-tts/com.bernard.arbor-*.plist ~/Library/LaunchAgents/
for a in arbor-chrome arbor-tts arbor-tts-tunnel arbor-tts-urlsync; do
  launchctl load ~/Library/LaunchAgents/com.bernard.$a.plist
done

# 7. Wire the bot once (the urlsync keeps it current afterwards)
az containerapp secret set -n discord-bot -g insult-rg --secrets arbor-tts-token=<token>
az containerapp update -n discord-bot -g insult-rg --set-env-vars \
  ARBOR_TTS_URL=<current trycloudflare url> ARBOR_TTS_VOICE=arbor \
  ARBOR_TTS_TOKEN=secretref:arbor-tts-token
```

## Reboot behavior

FileVault is ON, so a reboot **requires the FileVault password at the boot screen**
— nothing (auto-login, LaunchAgents) runs until the disk is unlocked. There is no
fully-unattended reboot with FileVault on (by design). After you unlock + log in:

1. All four agents start.
2. Chrome comes up logged in; the service self-heals its CDP connection.
3. cloudflared gets a NEW tunnel URL; `urlsync` pushes it to the bot within 120s.
4. Arbor works again — no further manual steps.

For a *planned* reboot you can skip the boot password once with
`sudo fdesetup authrestart`.

## Troubleshooting ("Insult went mute")

Check in order:
1. **Mac awake?** The stack only runs while the Mac is on.
2. **Chrome :9333 up?** `curl -s -o /dev/null -w '%{http_code}' http://localhost:9333/json/version` → 200.
3. **Service wedged?** If `/tts` hangs (HTTP 000) but a standalone Playwright
   probe works, the service process is stuck — `launchctl reload` is NOT enough;
   **hard-kill it**: `pkill -f "ArborTTS/src/server.js"` then
   `launchctl load ~/Library/LaunchAgents/com.bernard.arbor-tts.plist`.
4. **Bot URL stale?** Compare the tunnel URL (`~/Library/ArborTTS/cloudflared.log`)
   with the bot's `ARBOR_TTS_URL`; the urlsync agent should reconcile within 120s
   (`~/Library/ArborTTS/urlsync.log`).
5. **ChatGPT session expired?** Re-log into chatgpt.com in the :9333 Chrome.

Do NOT try to "fix" by killing/relaunching Chrome repeatedly — it degrades a
working setup. The common root causes are the wedged service process (#3) and a
stale tunnel URL (#4), not the browser.

> ToS note: this automates a personal ChatGPT account; keep it on-demand and
> low-volume. The Azure OpenAI `onyx`/`nova` path is the always-clean fallback
> when `ARBOR_TTS_URL` is unset on the bot.
