#!/usr/bin/env bash
# Read-only snapshot of the live Khimeras production estate.
#
# A hand-written inventory rots the day Bernard changes infra. This prints the
# truth instead, so `docs/runbook_dr.md` only has to carry what a query cannot
# know: the ORDER of reconstruction and the traps.
#
# Secrets are printed as 12-char SHA-256 fingerprints, never values — enough to
# tell "the Azure secret matches my ~/.secrets/ backup" without exposing either.
#
#   ./scripts/dr_inventory.sh            # full inventory
#   ./scripts/dr_inventory.sh secrets    # just the secret fingerprint audit
set -uo pipefail

RG=insult-rg
ENVNAME=prod-env
APPS=(discord-bot persona-gateway persona-runner)
JOBS=(insult-canary fact-consolidation)

fp() { printf '%s' "${1:-}" | shasum -a 256 | cut -c1-12; }
hdr() { printf '\n\033[1m══ %s\033[0m\n' "$1"; }

inventory_core() {
  hdr "Managed environment"
  az containerapp env show -n "$ENVNAME" -g "$RG" \
    --query "{name:name, location:location, state:properties.provisioningState, workspace:properties.appLogsConfiguration.logAnalyticsConfiguration.customerId}" -o tsv

  hdr "Container Apps"
  for app in "${APPS[@]}"; do
    az containerapp show -n "$app" -g "$RG" -o tsv --query \
      "{a:name, b:properties.template.containers[0].resources.cpu, c:properties.template.containers[0].resources.memory, d:properties.template.scale.minReplicas, e:properties.template.scale.maxReplicas, f:properties.configuration.ingress.targetPort, g:properties.configuration.ingress.external, h:properties.latestReadyRevisionName, i:properties.template.containers[0].image}" \
      | awk -F'\t' '{printf "  %-16s cpu=%s mem=%s replicas=%s/%s port=%s external=%s\n    ready=%s\n    image=%s\n", $1,$2,$3,$4,$5,$6,$7,$8,$9}'
  done

  hdr "Jobs"
  for job in "${JOBS[@]}"; do
    az containerapp job show -n "$job" -g "$RG" -o tsv --query \
      "{a:name, b:properties.configuration.scheduleTriggerConfig.cronExpression, c:properties.configuration.replicaTimeout, d:properties.template.containers[0].image}" \
      | awk -F'\t' '{printf "  %-20s cron=%-14s replicaTimeout=%ss\n    image=%s\n", $1,$2,$3,$4}'
  done

  hdr "Data plane (the ONLY irreplaceable resource)"
  az postgres flexible-server show -n development-pg-n66dz -g "$RG" -o tsv --query \
    "{a:name, b:version, c:sku.name, d:storage.storageSizeGb, e:backup.backupRetentionDays, f:backup.geoRedundantBackup, g:highAvailability.mode}" \
    | awk -F'\t' '{printf "  %s  pg%s  %s  %sGB\n  backupRetentionDays=%s  geoRedundant=%s  HA=%s\n", $1,$2,$3,$4,$5,$6,$7}'

  hdr "Alerting"
  az monitor action-group show -n prod-trust-ag -g "$RG" -o tsv \
    --query "{a:name, b:enabled, c:join(',', emailReceivers[].emailAddress)}" 2>/dev/null \
    | awk -F'\t' '{printf "  action group %s enabled=%s → %s\n", $1,$2,$3}'
  for a in insult-canary-heartbeat-absent insult-turn-failure-rate invite-accepted-without-completion; do
    az resource show -g "$RG" -n "$a" --resource-type Microsoft.Insights/scheduledqueryrules -o tsv \
      --query "{a:name, b:properties.enabled, c:properties.severity, d:properties.evaluationFrequency}" 2>/dev/null \
      | awk -F'\t' '{printf "  alert %-38s enabled=%s sev=%s every=%s\n", $1,$2,$3,$4}'
  done
}

# Which secrets can a recovery regenerate alone, and which need Bernard?
# Prints Azure fp vs local backup fp. A mismatch means the backup is STALE and
# the credential would be lost with the subscription.
secret_audit() {
  hdr "Secret audit — Azure vs ~/.secrets backup (fingerprints, never values)"
  printf "  %-26s %-14s %-14s %s\n" SECRET AZURE BACKUP STATUS

  check() { # app_kind app secret backup_path
    local kind=$1 app=$2 name=$3 path=$4 azv lov
    if [ "$kind" = job ]; then
      azv=$(az containerapp job secret show -n "$app" -g "$RG" --secret-name "$name" --query value -o tsv 2>/dev/null)
    else
      azv=$(az containerapp secret show -n "$app" -g "$RG" --secret-name "$name" --query value -o tsv 2>/dev/null)
    fi
    lov=$(tr -d '\n' < "$path" 2>/dev/null)
    local status
    if   [ -z "$azv" ];        then status="⚠️  no leído de Azure"
    elif [ -z "$lov" ];        then status="❌ SIN BACKUP — se pierde con la sub"
    elif [ "$azv" = "$lov" ];  then status="✓ respaldado"
    else                            status="❌ BACKUP STALE"
    fi
    printf "  %-26s %-14s %-14s %s\n" "$name" "$(fp "$azv")" "$(fp "$lov")" "$status"
  }

  check app discord-bot     discord-token             "$HOME/.secrets/discord-bot-insult-discord-token.txt"
  check app discord-bot     postgres-url              "$HOME/.secrets/discord-bot-postgres-url.txt"
  check app discord-bot     debug-token               "$HOME/.secrets/discord-bot-debug-token.v2.txt"
  check app discord-bot     insult-to-alice-token     "$HOME/.secrets/discord-bot-insult-to-alice-token.txt"
  check app discord-bot     susurro-key               "$HOME/.secrets/discord-bot-susurro-key.txt"
  check app discord-bot     azure-openai-key          "$HOME/.secrets/discord-bot-azure-openai-key.txt"
  check app persona-runner  claude-oauth-token        "$HOME/.secrets/discord-bot-claude-oauth-token.txt"
  check app persona-runner  insult-agent-runner-token "$HOME/.secrets/discord-bot-agent-runner-token.txt"
  check app persona-gateway vultur-discord-token      "$HOME/.secrets/vultur-discord-token.txt"
  check app persona-gateway alice-discord-token       "$HOME/.secrets/discord-bot-alice-discord-token.txt"
  check app persona-gateway frugivoro-discord-token   "$HOME/.secrets/frugivoro-discord-token.txt"
  check job insult-canary   canary-token              "$HOME/.secrets/vultur-discord-token.txt"

  cat <<'EOF'

  Recuperables sin Bernard (no necesitan backup):
    acr-password   → az acr credential show -n insultacr
    azure-openai-key → az cognitiveservices account keys list -n insult-openai -g insult-rg

  Requieren a Bernard (login + MFA, NO regenerables por el agente):
    *-discord-token    → Discord Developer Portal (regenerar INVALIDA el vivo)
    claude-oauth-token → OAuth Claude Max

  Nota: canary-token ES el token de Vultur (el probe postea como Vultur vía REST).
EOF
}

case "${1:-all}" in
  secrets) secret_audit ;;
  *)       inventory_core; secret_audit ;;
esac
