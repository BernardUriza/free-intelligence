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
MAX_CONNECTIONS_PER_IP = int(os.environ.get("AIRE_MAX_CONN_PER_IP", "16"))
DB_TIMEOUT_S = int(os.environ.get("AIRE_DB_TIMEOUT", "10"))
WHITELIST_ENFORCE = os.environ.get("AIRE_WHITELIST_ENFORCE") == "1"
