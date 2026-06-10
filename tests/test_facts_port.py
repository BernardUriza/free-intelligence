"""PR-A FactsPort — positive (delegation) + resistance (no-import invariant).

Part of the S2/S5 domain-facets seam
(``.claude/plans/s2_s5_domain_facets_multipr.md``). The pipeline must consume
the facts service through the ``FactsPort`` Protocol, never via a direct
``insult.core.facts`` import.
"""

from __future__ import annotations

import ast
from pathlib import Path

from insult.composition import default_facts_port
from insult.core.facts import build_facts_prompt, extract_facts, merge_facts_additive

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGES = REPO_ROOT / "insult" / "cogs" / "chat" / "stages.py"


# --- Positive: the adapter delegates faithfully to insult.core.facts ----------


def test_facts_port_render_block_delegates() -> None:
    port = default_facts_port()
    name = "Alex"
    facts = [{"category": "medication", "fact": "uses quetiapina"}]
    assert port.render_block(name, facts) == build_facts_prompt(name, facts)


def test_facts_port_exposes_write_callables() -> None:
    """S5 write-facet: extract_fn / merge_fn are the real core callables, so the
    injected ``extract_user_facts(..., extract_facts_fn=, merge_facts_fn=)`` call
    is behavior-identical to the pre-PR inline import."""
    port = default_facts_port()
    assert port.extract_fn is extract_facts
    assert port.merge_fn is merge_facts_additive


def test_facts_port_render_block_empty() -> None:
    port = default_facts_port()
    assert port.render_block("Alex", []) == build_facts_prompt("Alex", [])


# --- Resistance: stages.py must NOT import insult.core.facts ------------------


def _imports_of(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            out.add(node.module)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name)
    return out


def test_stages_does_not_import_core_facts() -> None:
    """The invariant PR-A exists to enforce: the turn pipeline depends on the
    FactsPort Protocol, not on the concrete facts module. If this fails, someone
    re-coupled stages to insult.core.facts — route it through ctx.deps.facts."""
    imports = _imports_of(STAGES)
    offenders = {m for m in imports if m == "insult.core.facts" or m.startswith("insult.core.facts.")}
    assert not offenders, f"stages.py must not import insult.core.facts (found {offenders})"
