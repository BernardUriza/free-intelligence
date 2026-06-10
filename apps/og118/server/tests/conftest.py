"""Put the og118 server dir on sys.path so `import app` / `import tts` resolve
regardless of the cwd pytest is launched from (CI may not run from server/)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
