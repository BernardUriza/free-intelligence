# Steps 3-4: the droplet (idempotent — reused if it exists) and its public IP.
# Sourced by provision-do.sh; expects NAME/REGION/SIZE/IMAGE/FINGERPRINT. Sets IP.

ensure_droplet() {
  echo "==> [3/6] Droplet '$NAME'…"
  if doctl compute droplet get "$NAME" --format ID --no-header >/dev/null 2>&1; then
    echo "    already exists — reusing (not recreating)."
  else
    echo "    creating (--wait: blocks until ready)…"
    doctl compute droplet create "$NAME" \
      --region "$REGION" \
      --size "$SIZE" \
      --image "$IMAGE" \
      --ssh-keys "$FINGERPRINT" \
      --wait \
      --format ID,Name,Region,Status --no-header
    echo "    created."
  fi
}

capture_ip() {
  echo "==> [4/6] Capturing public IP…"
  IP="$(doctl compute droplet get "$NAME" --format PublicIPv4 --no-header)"
  if [[ -z "$IP" ]]; then
    echo "ERROR: could not obtain the droplet's public IP." >&2
    exit 1
  fi
  echo "    IP=$IP"
}
