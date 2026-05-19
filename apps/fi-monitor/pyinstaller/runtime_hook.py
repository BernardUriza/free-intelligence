"""PyInstaller runtime hook — fix bare imports inside bundled packages.

rag_service modules use bare imports (e.g., `import state`, `from config import ...`)
that resolve when running from the source tree but fail inside PyInstaller's _MEIPASS
because the package directories aren't on sys.path. This hook adds them.
"""

import os
import sys

if getattr(sys, "_MEIPASS", None):
    for pkg in ("rag_service", "gateway"):
        pkg_path = os.path.join(sys._MEIPASS, pkg)
        if os.path.isdir(pkg_path) and pkg_path not in sys.path:
            sys.path.insert(0, pkg_path)
