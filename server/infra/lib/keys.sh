# Steps 1-2: the dedicated ed25519 key pair + its fingerprint in DigitalOcean.
# Sourced by provision-do.sh; expects SSH_KEY. Sets FINGERPRINT.

ensure_ssh_key() {
  echo "==> [1/6] SSH key ($SSH_KEY)…"
  if [[ -f "$SSH_KEY" ]]; then
    echo "    already exists — reusing (not regenerating)."
  else
    mkdir -p "$(dirname "$SSH_KEY")"
    ssh-keygen -t ed25519 -f "$SSH_KEY" -N '' -C "aire-vm"
    echo "    generated."
  fi
}

ensure_do_fingerprint() {
  echo "==> [2/6] Public key in DigitalOcean…"
  FINGERPRINT="$(doctl compute ssh-key list --format Name,FingerPrint --no-header \
    | awk '$1 == "aire-vm" { print $2; exit }')"
  if [[ -z "$FINGERPRINT" ]]; then
    echo "    'aire-vm' not in DO — importing…"
    FINGERPRINT="$(doctl compute ssh-key import aire-vm \
      --public-key-file "${SSH_KEY}.pub" \
      --format FingerPrint --no-header)"
    echo "    imported. fingerprint=$FINGERPRINT"
  else
    echo "    'aire-vm' already in DO — reusing. fingerprint=$FINGERPRINT"
  fi
  if [[ -z "$FINGERPRINT" ]]; then
    echo "ERROR: could not obtain the SSH key fingerprint." >&2
    exit 1
  fi
}
