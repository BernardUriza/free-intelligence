"""Can THIS host run the pgvector-backed tests? One answer, one copy.

Two test modules needed it and each carried its own copy, which is how a bug gets
fixed once and survives: both were selecting a `pg_ctl` that could not start a
server, so the suites ERRORED instead of skipping — 28 red results on a laptop
that simply lacks the extension, which trains everyone to ignore the suite.
"""

from __future__ import annotations

import shutil


def detect_postgres_executable() -> str | None:
    """Return a pg_ctl that can actually start a server WITH pgvector, or None.

    The old version got both halves wrong and failed in the worst direction: it
    returned a `pg_ctl` that could not run, so the suite ERRORED 28 times instead
    of skipping once, and a red-by-default suite is a suite people stop reading.

    - It accepted any `pg_ctl` on PATH. On a Mac with Homebrew's `libpq` — which
      is simply what you get when you install `psql` — that is a CLIENT-ONLY
      package: it ships `pg_ctl` and `initdb` but no `postgres` server binary, so
      initdb runs and the server can never come up.
    - It looked for `vector.control` anywhere under `/opt/homebrew/share`, a tree
      that has nothing to do with the chosen `pg_ctl`. A pgvector built for
      postgresql@17 made a postgresql@14 (or a libpq) look pgvector-capable.

    Both are fixed by asking Postgres instead of guessing: `pg_config --sharedir`
    reports the extension directory of THAT installation, and a real server has
    `postgres` sitting next to `pg_ctl`. Homebrew kegs are globbed rather than
    listed by version, so a new major release does not silently drop off.
    """
    import subprocess
    from pathlib import Path

    # Homebrew (Apple Silicon, then Intel), then the Debian/Ubuntu layout — which
    # is where CI lives, and which keeps its server binaries OFF `PATH`, so
    # without this glob the probe skipped on the one machine that could actually
    # run these tests. Globbed by version for the same reason everywhere: a
    # hardcoded major goes stale the next release and silently stops finding
    # anything.
    candidates: list[Path] = sorted(Path("/opt/homebrew/opt").glob("postgresql@*/bin/pg_ctl"))
    candidates += sorted(Path("/usr/local/opt").glob("postgresql@*/bin/pg_ctl"))
    candidates += sorted(Path("/usr/lib/postgresql").glob("*/bin/pg_ctl"), reverse=True)
    on_path = shutil.which("pg_ctl")
    if on_path:
        candidates.append(Path(on_path))

    def _usable(pg_ctl: Path) -> bool:
        bin_dir = pg_ctl.resolve().parent
        if not (bin_dir / "postgres").exists() or not (bin_dir / "initdb").exists():
            return False  # a client-only keg: pg_ctl with nothing to control
        pg_config = bin_dir / "pg_config"
        if not pg_config.exists():
            return False
        try:
            share = subprocess.run([str(pg_config), "--sharedir"], capture_output=True,
                                   text=True, timeout=10, check=True).stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return False
        return bool(share) and (Path(share) / "extension" / "vector.control").exists()

    for pg_ctl in candidates:
        if _usable(pg_ctl):
            return str(pg_ctl)
    return None
