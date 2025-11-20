"""Python version compatibility shims.

This module provides compatibility for features that differ between Python versions.
"""
import sys

# Python 3.11+ has datetime.UTC, Python 3.10 needs datetime.timezone.utc
if sys.version_info >= (3, 11):
    from datetime import UTC
else:
    from datetime import timezone
    UTC = timezone.utc

__all__ = ["UTC"]
