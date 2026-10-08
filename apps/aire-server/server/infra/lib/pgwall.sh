# Step 6: the reader wall (infra/wall.py) — the kill test's other half.
#
# Everything else in this directory resurrects the DROPLET, which is the mortal
# body. The memory lives in the owner's Postgres, and until now NOTHING here
# rebuilt the two roles and the default-ACL that make the front a read-only
# waiter. They existed only because someone typed them into psql on 2026-07-13.
#
# Runs ON the droplet, with the daemon's OWN credential from /etc/aire/env, so
# it needs no extra secret. Idempotent. It fails the provision when the wall is
# gone, because a provision that reports success over a missing wall is exactly
# the fake-green the whole kill test exists to prevent.
#
# Sourced by provision-do.sh; expects $SSH, $IP and $REMOTE_DIR.

ensure_reader_wall() {
  echo "==> [6/6] Asserting the reader wall on the pen's Postgres…"
  if $SSH "root@${IP}" "set -a; . /etc/aire/env; set +a; \
      ${REMOTE_DIR}/.venv/bin/python3 ${REMOTE_DIR}/server/infra/wall.py"; then
    return 0
  fi
  echo "ERROR: the front's read-only credential cannot read the pen's tables." >&2
  echo "       Run the CREATE ROLE above as the Postgres admin, then re-run this." >&2
  exit 1
}
