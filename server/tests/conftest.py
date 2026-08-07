"""Test wiring: make the `aire` package importable from `server/` and point the
mirror at the local Postgres BEFORE anything imports the app."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ.setdefault("AIRE_DSN", "postgresql://bernardurizaorozco@127.0.0.1:5432/aire")
