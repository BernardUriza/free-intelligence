"""Where a real Postgres SERVER lives on this host — one answer, one copy.

Two test modules needed it and each carried its own, which is how the same bug
survives being fixed: both fell through to `shutil.which`, both landed on libpq's
client-only bin, and both ERRORED at initdb instead of skipping.
"""

from __future__ import annotations

import shutil


def pg_bin(name: str) -> str | None:
    """The SERVER's binary, not the client's.

    The docstring here already named the trap — `which initdb` lands on libpq's
    client-only bin dir and fails at initdb time — and then walked straight into
    it: the explicit list held ONE version (`postgresql@17`), so any other
    install fell through to `shutil.which`, which is exactly libpq. On a Mac with
    postgresql@14 and libpq brewed, this suite ERRORED three times per run rather
    than skipping, and a suite that is red by default is one people stop reading.

    A bin dir qualifies only if the SERVER lives in it: `postgres` next to
    `initdb` and `pg_ctl`. That is the property that matters, so it is the
    property that gets checked, instead of a version number that goes stale every
    release. Kegs are globbed for the same reason.
    """
    from pathlib import Path as _Path

    candidates = sorted(_Path("/opt/homebrew/opt").glob("postgresql@*/bin"))
    candidates += sorted(_Path("/usr/local/opt").glob("postgresql@*/bin"))
    on_path = shutil.which(name)
    if on_path:
        candidates.append(_Path(on_path).resolve().parent)
    for bin_dir in candidates:
        if all((bin_dir / b).exists() for b in ("postgres", "initdb", "pg_ctl")):
            return str(bin_dir / name)
    return None
