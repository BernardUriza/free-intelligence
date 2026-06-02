#!/bin/bash
# Sync the bot's ARBOR_TTS_URL with the (ephemeral) cloudflared tunnel URL.
# Only calls az when the URL actually changed (cheap no-op otherwise).
export PATH="/opt/homebrew/bin:/usr/bin:/bin"
BASE="$HOME/Library/ArborTTS"
URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$BASE/cloudflared.log" 2>/dev/null | tail -1)
[ -z "$URL" ] && exit 0
LAST=$(cat "$BASE/.last_pushed_url" 2>/dev/null)
[ "$URL" = "$LAST" ] && exit 0
if az containerapp update -n discord-bot -g insult-rg --set-env-vars ARBOR_TTS_URL="$URL" -o none 2>>"$BASE/urlsync.log"; then
  echo "$URL" > "$BASE/.last_pushed_url"
  echo "$(date '+%F %T') updated ARBOR_TTS_URL -> $URL" >> "$BASE/urlsync.log"
else
  echo "$(date '+%F %T') FAILED update -> $URL" >> "$BASE/urlsync.log"
fi
