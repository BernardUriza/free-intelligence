"""#36, the thin birth: a per-chat casita's CLAUDE.md opens with ``@base
<project>`` and the engine dereferences it at spawn — the shared base lives
ONCE, every chat inherits its freshest version, the chat file stays pure soul.
The persona tool needs no change: to split/merge, the ``@base`` line IS the
protected base half."""

from pathlib import Path

import pytest

from aire.engine import core, options
from aire.engine.persona_tool import MARKER, merge, rebase, split

BASE = "You are og118 — Oganesson. Speak Mexican Spanish."
SOUL = f"{MARKER}\n\nUsuario: Bernard\nTema: astronomía"


@pytest.fixture
def workspaces(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(core, "WORKSPACES", tmp_path)
    (tmp_path / "og118").mkdir()
    (tmp_path / "og118" / "CLAUDE.md").write_text(BASE + "\n", encoding="utf-8")
    return tmp_path


def _chat_casita(workspaces: Path, text: str) -> str:
    chat = workspaces / "og118-chat1"
    chat.mkdir()
    (chat / "CLAUDE.md").write_text(text, encoding="utf-8")
    return str(chat)


def test_a_thin_file_resolves_to_the_shared_base_plus_the_soul(workspaces: Path):
    cwd = _chat_casita(workspaces, f"@base og118\n\n{SOUL}\n")
    prompt = options._casita_prompt(cwd)
    assert prompt.startswith(BASE)
    assert "Usuario: Bernard" in prompt
    assert "@base" not in prompt


def test_a_thin_file_with_no_soul_yet_is_just_the_base(workspaces: Path):
    cwd = _chat_casita(workspaces, "@base og118\n")
    assert options._casita_prompt(cwd) == BASE


def test_editing_the_shared_base_reaches_the_chat_on_the_next_spawn(workspaces: Path):
    cwd = _chat_casita(workspaces, f"@base og118\n\n{SOUL}\n")
    (workspaces / "og118" / "CLAUDE.md").write_text("A refreshed base.\n", encoding="utf-8")
    assert options._casita_prompt(cwd).startswith("A refreshed base.")


def test_a_missing_or_invalid_base_leaves_the_file_verbatim(workspaces: Path):
    cwd = _chat_casita(workspaces, "@base no-such-casita\n\nsoul text\n")
    assert options._casita_prompt(cwd) == "@base no-such-casita\n\nsoul text"
    cwd2 = str(workspaces / "og118")  # no @base line at all → unchanged
    assert options._casita_prompt(cwd2) == BASE


def test_a_traversal_in_the_base_name_is_refused_not_resolved(workspaces: Path):
    cwd = _chat_casita(workspaces, "@base ../../etc\n\nsoul\n")
    assert options._casita_prompt(cwd) == "@base ../../etc\n\nsoul"


def test_the_persona_tool_treats_the_base_line_as_the_protected_half():
    thin = merge("@base og118", "Usuario: Bernard")
    assert split(thin) == ("@base og118", "Usuario: Bernard")
    assert rebase(thin, "@base og118") == thin  # re-init: soul survives, stub intact
