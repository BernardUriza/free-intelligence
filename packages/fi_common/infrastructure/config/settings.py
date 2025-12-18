from __future__ import annotations

"""Central settings facade.

Transitional stub to centralize environment-backed settings. Replace scattered
config_loader usages with this module during migration.
"""

import os
from dataclasses import dataclass


@dataclass(slots=True)
class AppSettings:
    environment: str = os.getenv("ENVIRONMENT", "development")
    backend_url: str | None = os.getenv("BACKEND_URL")


__all__ = ["AppSettings"]
