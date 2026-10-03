"""`persona_core` never imports a surface or a host.

The turn pipeline moved into `persona_core` (F3, 2026-09-28) so every surface
can run it. That only holds while the arrow points one way: surfaces and hosts
(`persona_gateway`, `persona_runner`, `demux_ai`) import the core, never the
other way around. One `from persona_gateway.config import CONFIG` inside the
core, the shape `turn_context.py` had before the move, and the runner could no
longer import the pipeline without dragging Discord along.

The check walks the AST of every module, so an import hidden inside a function
counts too.
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE = Path(__file__).resolve().parents[2] / "persona_core"
FORBIDDEN = ("persona_gateway", "persona_runner", "demux_ai")


def _imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            roots.add(node.module.split(".")[0])
    return roots


def test_persona_core_imports_no_surface_or_host():
    offenders = {
        str(path.relative_to(CORE.parent)): sorted(_imported_roots(ast.parse(path.read_text())) & set(FORBIDDEN))
        for path in sorted(CORE.rglob("*.py"))
    }
    offenders = {path: roots for path, roots in offenders.items() if roots}
    assert not offenders, f"persona_core must stay surface-free: {offenders}"


def test_the_check_sees_an_import_hidden_in_a_function():
    tree = ast.parse("def f():\n    from persona_gateway.config import CONFIG\n")
    assert "persona_gateway" in _imported_roots(tree)
