#!/usr/bin/env bash
# Insult canary — Azure Container Apps Job (cron */5) creation.
#
# ⚠️ GATED / NOT auto-run. This is Bernard's call: it touches Azure + a real
# Discord bot token (secret). Run it by hand once the #canary channel exists and
# the reused POSTER token (Vultur) is in hand (~/.secrets/vultur-discord-token.txt).
# Mirrors the existing `fact-consolidation` ACA Job: SAME image
# (insultacr.azurecr.io/insult-bot), separate cron, one-shot command. The cd.yml
# image-sync step for this job is already wired (guarded no-op until it exists).
#
# The job runs:  python -m scripts.canary_probe
# which posts `CANARY insult <uuid>` in #canary (REST-only, no Gateway — the
# poster token is reused from the live Vultur bot, so a second IDENTIFY would
# flap it) and requires the Insult bot to echo `CANARY_OK <uuid>`; exit non-zero
# on any failure (timeout/wrong author/wrong nonce).
#
# Prereqs (all Discord snowflake IDs, never names):
#   CANARY_BOT_TOKEN     token of the reused POSTER bot (Vultur) — REST only
#   CANARY_CHANNEL_ID    the #canary channel id
#   INSULT_BOT_USER_ID   the Insult bot user id whose reply we require
#   CANARY_OPS_WEBHOOK_URL  (optional) Discord webhook for failure alerts
set -euo pipefail

RG=insult-rg
JOB=insult-canary
# Default to the image the discord-bot app currently runs (so the job starts on a
# real, pullable tag — `:latest` is not published). The cd.yml sync step keeps it
# current on each deploy. Override with ACR_IMAGE=... if needed.
ACR_IMAGE="${ACR_IMAGE:-$(az containerapp show --name discord-bot --resource-group "$RG" \
  --query "properties.template.containers[0].image" -o tsv)}"

: "${CANARY_BOT_TOKEN:?set CANARY_BOT_TOKEN}"
: "${CANARY_CHANNEL_ID:?set CANARY_CHANNEL_ID}"
: "${INSULT_BOT_USER_ID:?set INSULT_BOT_USER_ID}"
CANARY_OPS_WEBHOOK_URL="${CANARY_OPS_WEBHOOK_URL:-}"

# Resolve the managed environment from the existing discord-bot app — never
# hardcode the env name (the FQDN is nicecliff-10074f57.* but the resource name
# is read from Azure, not guessed).
ENV_ID=$(az containerapp show --name discord-bot --resource-group "$RG" \
  --query "properties.environmentId" -o tsv)
echo "Managed environment: $ENV_ID"

# The image lives in the private ACR. Mirror the fact-consolidation job's auth:
# ACR admin user (adminUserEnabled=true). The password is fetched here, never
# committed; az stores it as a job secret automatically.
ACR_SERVER=insultacr.azurecr.io
ACR_USERNAME=insultacr
ACR_PASSWORD=$(az acr credential show --name insultacr --query "passwords[0].value" -o tsv)

# Build secrets + env conditionally — the ops webhook is OPTIONAL, and Azure
# rejects an empty secret value, so only wire it when a URL is actually provided.
SECRETS=( "canary-token=$CANARY_BOT_TOKEN" )
ENV_VARS=(
  "PYTHONPATH=/app"
  "CANARY_BOT_TOKEN=secretref:canary-token"
  "CANARY_CHANNEL_ID=$CANARY_CHANNEL_ID"
  "INSULT_BOT_USER_ID=$INSULT_BOT_USER_ID"
  "CANARY_TIMEOUT_SECONDS=45"
)
if [ -n "$CANARY_OPS_WEBHOOK_URL" ]; then
  SECRETS+=( "ops-webhook=$CANARY_OPS_WEBHOOK_URL" )
  ENV_VARS+=( "CANARY_OPS_WEBHOOK_URL=secretref:ops-webhook" )
fi

az containerapp job create \
  --name "$JOB" \
  --resource-group "$RG" \
  --environment "$ENV_ID" \
  --trigger-type Schedule \
  --cron-expression "*/5 * * * *" \
  --replica-timeout 60 \
  --replica-retry-limit 0 \
  --replica-completion-count 1 \
  --parallelism 1 \
  --image "$ACR_IMAGE" \
  --registry-server "$ACR_SERVER" \
  --registry-username "$ACR_USERNAME" \
  --registry-password "$ACR_PASSWORD" \
  --cpu 0.25 --memory 0.5Gi \
  --command "python" --args "scripts/canary_probe.py" \
  --secrets "${SECRETS[@]}" \
  --env-vars "${ENV_VARS[@]}"

echo "Created job $JOB. Manual test:  az containerapp job start --name $JOB --resource-group $RG"
echo "Then watch:  az containerapp job execution list --name $JOB --resource-group $RG -o table"
