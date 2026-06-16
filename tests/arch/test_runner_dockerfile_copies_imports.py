"""Image packaging invariant — the COPY allowlists must not drift.

Prod P0 (2026-06-16): the Etapa 3 demux (PR #26) moved neutral capabilities
into ``khimeras_shared``; ``personas.insult`` now transitively imports
``khimeras_shared.*``, but NEITHER Dockerfile was updated to
``COPY khimeras_shared/``:

  * ``infra/azure/runner.Dockerfile`` (insult-runner) → the agent loop 502'd on
    EVERY turn with ``ModuleNotFoundError: No module named 'khimeras_shared'``
    for ~2h while /health stayed green; all Insult turns fell over to ALICE.
  * ``Dockerfile`` (discord-bot plumbing) → every NEW revision crashlooped on
    boot (``app.py`` imports ``khimeras_shared.runner.agent_client`` at start);
    only a pre-demux revision still serving masked it.

Root cause: BOTH images carry a MANUAL COPY allowlist that drifts from the
actual import graph. This test makes the drift fail in CI instead of in prod:
every LOCAL top-level package that ``personas.insult`` imports must be copied
into BOTH images that run the insult code.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
INSULT_PKG = REPO_ROOT / "personas" / "insult"
RUNNER_DOCKERFILE = REPO_ROOT / "infra" / "azure" / "runner.Dockerfile"
PLUMBING_DOCKERFILE = REPO_ROOT / "Dockerfile"

# Local top-level packages that live in the repo root and are import roots the
# runner could need. Anything imported from outside this set is a third-party
# dep installed via environment.yml, not a COPY target.
LOCAL_TOP_LEVEL_PACKAGES = {
    "khimeras_shared",
    "shared",
    "personas",
    "demux_ai",
    "persona_gateway",
}


def _imported_local_top_levels() -> set[str]:
    found: set[str] = set()
    for py in INSULT_PKG.rglob("*.py"):
        tree = ast.parse(py.read_text(encoding="utf-8"), filename=str(py))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    if top in LOCAL_TOP_LEVEL_PACKAGES:
                        found.add(top)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                top = node.module.split(".")[0]
                if top in LOCAL_TOP_LEVEL_PACKAGES:
                    found.add(top)
    return found


def _dockerfile_copy_roots(dockerfile: Path) -> set[str]:
    roots: set[str] = set()
    copy_re = re.compile(r"^\s*COPY\s+(.+)$")
    for line in dockerfile.read_text(encoding="utf-8").splitlines():
        m = copy_re.match(line)
        if not m:
            continue
        tokens = m.group(1).split()
        # COPY <src>... <dest>; the source paths are everything but the last token.
        for src in tokens[:-1]:
            roots.add(src.strip("/").split("/")[0])
    return roots


@pytest.mark.parametrize(
    ("dockerfile", "image"),
    [
        (RUNNER_DOCKERFILE, "insult-runner"),
        (PLUMBING_DOCKERFILE, "discord-bot plumbing"),
    ],
)
def test_dockerfile_copies_every_local_package_insult_imports(dockerfile: Path, image: str) -> None:
    imported = _imported_local_top_levels()
    copied = _dockerfile_copy_roots(dockerfile)
    missing = sorted(imported - copied)
    assert not missing, (
        f"{dockerfile.relative_to(REPO_ROOT)} ({image}) is missing COPY for local "
        f"package(s) that personas.insult imports: {missing}. Without these the "
        "image fails with ModuleNotFoundError at runtime (prod P0 2026-06-16). "
        "Add `COPY <pkg>/ <pkg>/` to the Dockerfile."
    )
