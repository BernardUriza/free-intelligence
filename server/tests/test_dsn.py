"""One database, one name, and no literal DSN anywhere in the daemon.

`AIRE_DSN` and `AIRE_DATABASE_URL` named the same Postgres until 2026-08-22 —
the provisioner copied one line into the other — and thirteen call sites split
between them. Two of those defaulted to `postgresql://<a developer's mac>@127.0.0.1`
when their name was missing. On the droplet that resolves to nothing, and
`gateway_mirror` swallows a dead connection by design ("the relay never pays for
the mirror"), so the gateway would have relayed perfectly while its memory quietly
stopped existing. That is the failure this file exists to keep dead."""

import re
from pathlib import Path

import pytest

from aire.deps import MissingDSN, dsn

REPO = Path(__file__).resolve().parent.parent.parent
AIRE = REPO / "server" / "aire"
# The daemon is not the only place that names the variable. The CI workflow set
# `AIRE_DSN` for pytest, and the first version of this test scanned `aire/` only
# — so the cutover shipped, the deploy went red, and the check that existed to
# prevent exactly that watched the one tree where the name was already gone.
WIRED = (*AIRE.rglob("*.py"), *(REPO / ".github" / "workflows").glob("*.yml"),
         *(REPO / "server" / "infra").rglob("*.sh"),
         *(REPO / "server" / "deploy").rglob("*"))
DSN_LITERAL = re.compile(r"postgres(?:ql)?://[^\"'\s]")


def test_the_absent_variable_raises_instead_of_guessing(monkeypatch):
    monkeypatch.delenv("AIRE_DATABASE_URL", raising=False)
    with pytest.raises(MissingDSN):
        dsn()


def test_the_variable_is_returned_verbatim(monkeypatch):
    monkeypatch.setenv("AIRE_DATABASE_URL", "postgresql://someone@example:5432/db")
    assert dsn() == "postgresql://someone@example:5432/db"


def test_an_empty_variable_counts_as_absent(monkeypatch):
    monkeypatch.setenv("AIRE_DATABASE_URL", "")
    with pytest.raises(MissingDSN):
        dsn()


def test_the_old_name_is_gone_from_everything_that_runs():
    """A cutover that leaves the old name alive anywhere EXECUTABLE is not a
    cutover — and "executable" includes the workflow that feeds pytest, not just
    the daemon. Comments keep it on purpose: they record why it died."""
    offenders = []
    for f in WIRED:
        if not f.is_file():
            continue
        for i, line in enumerate(f.read_text(errors="ignore").splitlines(), 1):
            stripped = line.lstrip()
            if "AIRE_DSN" in line and not stripped.startswith(("#", "//")):
                offenders.append(f"{f.relative_to(REPO)}:{i}")
    assert offenders == [], offenders


def test_no_module_carries_a_hardcoded_dsn():
    """The literal that started this: a default pointing at a laptop. A DSN is a
    credential-shaped value and belongs in the environment, never in a module —
    the one place a wrong one cannot be noticed is a fallback nobody reads."""
    offenders = [f"{p.relative_to(AIRE)}:{i}" for p in AIRE.rglob("*.py")
                 for i, line in enumerate(p.read_text().splitlines(), 1)
                 if DSN_LITERAL.search(line) and "..." not in line]
    assert offenders == [], offenders
