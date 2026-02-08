"""Password hashing and verification using bcrypt directly.

passlib is abandoned and incompatible with bcrypt>=4.1.
Using bcrypt directly is simpler and fully supported.
"""

from __future__ import annotations

import bcrypt


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt (12 rounds)."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
