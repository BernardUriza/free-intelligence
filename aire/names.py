"""A `project` / `session` comes from the URL: hostile input until proven
otherwise. It is used to build a filesystem path (`workspaces/<project>`) and a
Postgres key, so a `..` or a slash breaks it out of its cage. The defense is not
sanitizing (stripping the `..` and praying): it is a narrow ALLOWLIST. Whatever
doesn't fit is rejected — never "fixed".
"""

from __future__ import annotations

import re

_VALID = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")


class InvalidName(ValueError):
    """The project/session failed the allowlist."""


def clean(kind: str, value: str) -> str:
    if not _VALID.match(value or ""):
        raise InvalidName(f"invalid {kind}: {value!r} (allowed: letters, digits, - and _, 1–64)")
    return value
