"""Test wiring for the og118 server.

Puts the server dir on sys.path so `import app` / `import tts` resolve regardless
of cwd, and provides shared dependency overrides: an isolated tmp ProjectRegistry
(autouse — so no test ever touches the real /opt/fi/data volume) and an
`as_account` helper to drive a specific authenticated principal.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def project_registry(tmp_path):
    """Override get_project_registry with a tmp-backed registry for every test —
    never the real volume path."""
    import app as app_module
    from projects import ProjectRegistry

    reg = ProjectRegistry(tmp_path / "projects.json")
    app_module.app.dependency_overrides[app_module.get_project_registry] = lambda: reg
    yield reg
    app_module.app.dependency_overrides.pop(app_module.get_project_registry, None)


@pytest.fixture
def as_account():
    """Override get_principal to authenticate as a chosen account (sub). Returns a
    setter so a test can switch accounts mid-test to exercise cross-account
    isolation. Without this fixture, routes use the default (bearer-mode legacy
    principal, sub='legacy-bearer')."""
    import app as app_module
    from fi_runner.auth import Principal

    state = {"sub": "acct-A"}
    app_module.app.dependency_overrides[app_module.get_principal] = lambda: Principal(sub=state["sub"])

    def _set(sub: str) -> None:
        state["sub"] = sub

    _set("acct-A")
    yield _set
    app_module.app.dependency_overrides.pop(app_module.get_principal, None)
