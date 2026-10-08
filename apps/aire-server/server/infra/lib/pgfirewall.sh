# Step 4b: the pen writes to AZURE Postgres — its firewall must admit the
# droplet's (new) IP, or the fresh box boots memory-blind: PEN down, whitelist
# unloadable, restore impossible. Learned on the first real kill test
# (2026-07-20): everything provisioned green while every Postgres connection
# timed out, because only the DEAD droplet's IP was allowed.
# Sourced by provision-do.sh; expects IP, PG_SERVER, PG_RG.

ensure_pg_firewall() {
  echo "==> [4b/6] Azure Postgres firewall (the pen's door)…"
  if ! command -v az >/dev/null 2>&1; then
    echo "    WARNING: az CLI missing — allow $IP on $PG_SERVER BY HAND or the pen is blind." >&2
    return 0
  fi
  if az postgres flexible-server firewall-rule create -n "$PG_SERVER" -g "$PG_RG" \
       --rule-name aire-droplet-do --start-ip-address "$IP" --end-ip-address "$IP" \
       -o none 2>/dev/null; then
    echo "    rule aire-droplet-do → $IP"
  else
    echo "    WARNING: could not set the PG firewall — the pen may be blind on this box." >&2
  fi
}
