"""PR-B StancePort — positive (delegation) + resistance (no-import invariant).

Part of the S2/S5 domain-facets seam
(``.claude/plans/s2_s5_domain_facets_multipr.md``). The pipeline must consume
the stance-log service through the ``StancePort`` Protocol, never via a direct
``insult.core.stance_log`` import. Persistence (``get_stances`` /
``store_stance``) stays on the memory data plane.
"""

from __future__ import annotations

import ast
from pathlib import Path

from personas.insult.composition import default_stance_port
from personas.insult.core.stance_log import build_stance_prompt, extract_stances

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGES = REPO_ROOT / "personas" / "insult" / "cogs" / "chat" / "stages.py"


# --- Positive: the adapter delegates faithfully to insult.core.stance_log -----


def test_stance_port_render_block_delegates() -> None:
    port = default_stance_port()
    stances = [{"topic": "AI art", "position": "derivative without curation", "confidence": 0.8}]
    assert port.render_block(stances) == build_stance_prompt(stances)


def test_stance_port_render_block_empty() -> None:
    port = default_stance_port()
    assert port.render_block([]) == build_stance_prompt([])


def test_stance_port_derive_matches_core() -> None:
    """S5 write-facet: derive() must return exactly what extract_stances returns
    for the same inputs — same entries, same gate behavior."""
    port = default_stance_port()
    text = "Creo que el cine de superhéroes es ruido. La crítica seria importa."
    ts = 1718000000.0
    via_port = port.derive(text, 0.9, ts)
    via_core = extract_stances(text, 0.9, ts)
    assert [(e.topic, e.position, e.confidence) for e in via_port.entries] == [
        (e.topic, e.position, e.confidence) for e in via_core.entries
    ]


# --- Resistance: stages.py must NOT import personas.insult.core.stance_log -------------


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


def test_stages_does_not_import_core_stance_log() -> None:
    """The invariant PR-B exists to enforce: the turn pipeline depends on the
    StancePort Protocol, not on the concrete stance_log module. If this fails,
    someone re-coupled stages to insult.core.stance_log — route it through
    ctx.deps.stance."""
    imports = _imports_of(STAGES)
    offenders = {
        m for m in imports if m == "personas.insult.core.stance_log" or m.startswith("personas.insult.core.stance_log.")
    }
    assert not offenders, f"stages.py must not import personas.insult.core.stance_log (found {offenders})"
