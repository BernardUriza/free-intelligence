"""PR-C ArcPort — positive (delegation) + resistance (opacity invariant).

Part of the S2/S5 domain-facets seam
(``.claude/plans/s2_s5_domain_facets_multipr.md``). The pipeline must consume
the arc service through the ``ArcPort`` Protocol AND treat the arc value as an
opaque carry: stages transports it between S2 and S5 but never reads its
fields. Two resistance tests enforce both halves.
"""

from __future__ import annotations

import ast
from pathlib import Path

from personas.insult.composition import default_arc_port
from personas.insult.core.arc_tracker import ArcState, arc_to_dict, build_arc_prompt, update_arc

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGES = REPO_ROOT / "personas" / "insult" / "cogs" / "chat" / "stages.py"


# --- Positive: the adapter delegates faithfully to insult.core.arc_tracker ----


def test_arc_port_load_none_gives_fresh_state() -> None:
    port = default_arc_port()
    assert arc_to_dict(port.load(None)) == arc_to_dict(ArcState())


def test_arc_port_load_roundtrips_dict() -> None:
    port = default_arc_port()
    raw = arc_to_dict(
        update_arc(ArcState(), disclosure_severity=3, user_state="vulnerable", preset_mode="respectful_serious")
    )
    assert port.dump(port.load(raw)) == raw


def test_arc_port_render_and_phase_delegate() -> None:
    port = default_arc_port()
    arc = port.load(None)
    assert port.render_block(arc) == build_arc_prompt(arc)
    assert port.phase(arc) == arc_to_dict(arc)["phase"]


def test_arc_port_advance_matches_core() -> None:
    """S5 write-facet: advance() must produce exactly what update_arc produces.

    ``update_arc`` stamps ``time.time()`` into ``phase_since`` on transitions,
    so two consecutive calls differ by microseconds there — compare everything
    BUT the wall-clock field."""
    port = default_arc_port()
    start = ArcState()
    via_port = port.dump(
        port.advance(start, disclosure_severity=4, user_state="distressed", preset_mode="respectful_serious")
    )
    via_core = arc_to_dict(
        update_arc(start, disclosure_severity=4, user_state="distressed", preset_mode="respectful_serious")
    )
    via_port.pop("phase_since")
    via_core.pop("phase_since")
    assert via_port == via_core


# --- Resistance 1: stages.py must NOT import personas.insult.core.arc_tracker ----------


def _ast(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_stages_does_not_import_core_arc_tracker() -> None:
    """If this fails, someone re-coupled stages to insult.core.arc_tracker —
    route it through ctx.deps.arc."""
    offenders: set[str] = set()
    for node in ast.walk(_ast(STAGES)):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("personas.insult.core.arc_tracker")
        ):
            offenders.add(node.module)
        elif isinstance(node, ast.Import):
            offenders.update(a.name for a in node.names if a.name.startswith("personas.insult.core.arc_tracker"))
    assert not offenders, f"stages.py must not import personas.insult.core.arc_tracker (found {offenders})"


# --- Resistance 2: the OPACITY invariant — stages never reads arc fields ------


def test_stages_never_reads_arc_state_attributes() -> None:
    """The arc value is an opaque carry owned by the ArcPort. stages may
    TRANSPORT ``ctx.arc_state`` / ``src.arc_state`` (pass it as an argument)
    but must never read an attribute off it (``ctx.arc_state.phase`` etc.).
    Telemetry scalars go through the port (``ctx.deps.arc.phase(...)``).

    AST shape forbidden: Attribute(value=Attribute(attr="arc_state")) — any
    ``<x>.arc_state.<field>`` chain. If this fails, expose what you need as an
    ArcPort method instead of reaching into ArcState.
    """
    violations: list[str] = []
    for node in ast.walk(_ast(STAGES)):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute) and node.value.attr == "arc_state":
            violations.append(f"line {node.lineno}: .arc_state.{node.attr}")
    assert not violations, f"stages.py reads ArcState fields (opacity violation): {violations}"
