"""Readable names outside, UUIDs inside. No mapping table.

The SDK requires `session_id` to be a UUID and validates it, but it lets you set
it. Deriving it deterministically from the name (`uuid5`) is what makes a mapping
table unnecessary: the same name always resolves to the same session, even after
a restart — which is the entire point of the memory.
"""

from __future__ import annotations

import uuid

AIRE_NAMESPACE = uuid.UUID("a13e0000-0000-4000-8000-000000000000")


def sdk_session_uuid(session: str) -> str:
    """The session's external name → the UUID the SDK demands.

    A name that ALREADY is a UUID is honoured verbatim instead of being hashed
    again: that is what lets this door continue a session another door started
    (the CLI mints its own UUIDs). One memory, whichever door wrote it.
    """
    try:
        return str(uuid.UUID(session))
    except ValueError:
        return str(uuid.uuid5(AIRE_NAMESPACE, session))
