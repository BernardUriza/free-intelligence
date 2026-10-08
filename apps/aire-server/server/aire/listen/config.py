"""Env knobs for the listener. The story lives in docs/listener-doctrine.md."""

import os
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

LOG = Path(os.environ.get("AIRE_LOG", _ROOT / "aire.log"))
HOST = os.environ.get("AIRE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AIRE_PORT", "9099"))
DSN = os.environ.get("AIRE_DATABASE_URL", "")
WORKSPACES = Path(os.environ.get("AIRE_WORKSPACES", _ROOT / "workspaces"))
VERB_TOKEN = os.environ.get("AIRE_VERB_TOKEN", "")
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
RATE_LIMIT_LINES_PER_MIN = int(os.environ.get("AIRE_RATE_LIMIT", "120"))
MAX_LINE_BYTES = 4096
MAX_CONNECTIONS = int(os.environ.get("AIRE_MAX_CONNECTIONS", "256"))
# How long a connection may say NOTHING before it is dropped. The caps below
# bound how MANY sockets may be open; this bounds how LONG one may sit there
# holding a slot. Without it, four sockets that never send a newline jam the
# door on a port that is deliberately open to the whole internet — measured, not
# theorised. Generous on purpose: a device with nothing to say can reconnect,
# which is what TCP is for.
IDLE_TIMEOUT_S = float(os.environ.get("AIRE_IDLE_TIMEOUT_S", "300"))
# The FIRST line gets a much shorter one, and that is the half that actually
# closes the hole rather than bounding it. A device that has connected and not
# finished one line in ten seconds is never legitimate — a real report arrives in
# milliseconds — while the generous window above exists for a device that has
# already spoken and is waiting to speak again. Two situations, not two knobs for
# one: with a single 300s window a reconnecting attacker keeps the door jammed
# forever; with this, a socket that never says anything costs him ten seconds.
HANDSHAKE_TIMEOUT_S = float(os.environ.get("AIRE_HANDSHAKE_TIMEOUT_S", "10"))
MAX_CONNECTIONS_PER_IP = int(os.environ.get("AIRE_MAX_CONN_PER_IP", "16"))
DB_TIMEOUT_S = int(os.environ.get("AIRE_DB_TIMEOUT", "10"))
WHITELIST_ENFORCE = os.environ.get("AIRE_WHITELIST_ENFORCE") == "1"
