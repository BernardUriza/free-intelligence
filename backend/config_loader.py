"""Compatibility wrapper - re-exports from packages.fi_common.config.config_loader"""

from __future__ import annotations

import sys
from pathlib import Path

# Add packages directory to path if not already there
project_root = Path(__file__).parent.parent
packages_dir = project_root / "packages"
if str(packages_dir) not in sys.path:
    sys.path.insert(0, str(packages_dir))

try:
    from fi_common.config.config_loader import *  # noqa: F403  # type: ignore[import]
except ImportError:
    # Fallback: provide minimal config functionality
    def load_config(config_path=None):
        """Stub config loader"""
        return {"log_level": "INFO"}
