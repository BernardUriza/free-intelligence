"""Guards for the routing-contracts extraction (`insult.core.contracts`).

The flow/preset vocabulary now lives in the neutral `insult.core.contracts`
package; the old `insult.core.flows.types` / `insult.core.presets.types` modules
re-export from there. These tests lock in the two properties that make that
extraction safe:

1. Enum/dataclass IDENTITY is preserved across every import path — the type is
   defined exactly once, so `isinstance` checks and enum-member comparisons that
   span modules keep working.
2. The contracts module is a stdlib-only leaf — it must not import back into the
   smart/persona packages, or the whole point (a neutral host-importable layer)
   is lost.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_preset_enum_identity_across_all_import_paths() -> None:
    from personas.insult.core.contracts.presets import PresetMode as Canonical
    from personas.insult.core.contracts.presets import PresetModifier as CanonicalMod
    from personas.insult.core.contracts.presets import PresetSelection as CanonicalSel
    from personas.insult.core.presets import PresetMode as ViaBarrel
    from personas.insult.core.presets.types import PresetMode as ViaShim

    # Same class object everywhere — not just equal, identical.
    assert Canonical is ViaShim is ViaBarrel
    # Members are the same singletons too.
    assert Canonical.ARC is ViaShim.ARC is ViaBarrel.ARC

    from personas.insult.core.presets import PresetModifier as ViaBarrelMod
    from personas.insult.core.presets import PresetSelection as ViaBarrelSel
    from personas.insult.core.presets.types import PresetModifier as ViaShimMod
    from personas.insult.core.presets.types import PresetSelection as ViaShimSel

    assert CanonicalMod is ViaShimMod is ViaBarrelMod
    assert CanonicalSel is ViaShimSel is ViaBarrelSel


def test_flow_enum_identity_across_all_import_paths() -> None:
    from personas.insult.core.contracts.flows import FlowAnalysis as Canonical
    from personas.insult.core.contracts.flows import UserState as CanonicalState
    from personas.insult.core.flows import FlowAnalysis as ViaBarrel
    from personas.insult.core.flows import UserState as ViaBarrelState
    from personas.insult.core.flows.types import FlowAnalysis as ViaShim
    from personas.insult.core.flows.types import UserState as ViaShimState

    assert Canonical is ViaShim is ViaBarrel
    assert CanonicalState is ViaShimState is ViaBarrelState
    assert CanonicalState.VULNERABLE is ViaShimState.VULNERABLE is ViaBarrelState.VULNERABLE


def test_expression_history_identity_across_all_import_paths() -> None:
    from personas.insult.core.contracts.history import ExpressionHistory as Canonical
    from personas.insult.core.flows import ExpressionHistory as ViaBarrel
    from personas.insult.core.flows.history import ExpressionHistory as ViaShim

    # Same class object across contracts / flows.history shim / flows barrel.
    assert Canonical is ViaShim is ViaBarrel


def test_server_pulse_helpers_identity_across_import_paths() -> None:
    # The host imports these from the neutral module; summaries.py re-exports
    # them for backwards compatibility. Same function objects both ways.
    from personas.insult.core.server_pulse import build_server_pulse as canonical_pulse
    from personas.insult.core.server_pulse import filter_by_permissions as canonical_filter
    from personas.insult.core.summaries import build_server_pulse as shim_pulse
    from personas.insult.core.summaries import filter_by_permissions as shim_filter

    assert canonical_pulse is shim_pulse
    assert canonical_filter is shim_filter


def test_memory_store_satisfies_debug_memory_port() -> None:
    """The concrete smart-side MemoryStore must structurally satisfy the
    host-side DebugMemoryPort — otherwise the debug_server handlers would
    call methods the store doesn't have. Asserts every port method exists on
    the store class so the port can't silently drift from the real surface."""
    from personas.insult.core.contracts.memory import DebugMemoryPort
    from personas.insult.core.memory import MemoryStore

    port_methods = [
        name
        for name in dir(DebugMemoryPort)
        if not name.startswith("_") and callable(getattr(DebugMemoryPort, name, None))
    ]
    assert port_methods, "DebugMemoryPort exposes no methods — extraction is wrong"
    missing = [m for m in port_methods if not hasattr(MemoryStore, m)]
    assert not missing, f"MemoryStore is missing DebugMemoryPort methods: {missing}"


def test_routing_uses_the_canonical_enum_members() -> None:
    """The router compares preset.mode against PresetMode members. If routing
    imported a *different* PresetMode object, those `in`/`==` checks would
    silently never match. This asserts the wiring is shared end to end."""
    from personas.insult.core.contracts.flows import (
        AwarenessAnalysis,
        ConversationPattern,
        EpistemicAnalysis,
        EpistemicMove,
        ExpressionAnalysis,
        FlowAnalysis,
        PressureAnalysis,
        ResponseShape,
        StyleFlavor,
        UserState,
    )
    from personas.insult.core.contracts.presets import PresetMode, PresetSelection
    from personas.insult.core.routing import ModelTier, select_model

    flow = FlowAnalysis(
        epistemic=EpistemicAnalysis(0.0, 0.0, 0.0, False, 0, EpistemicMove.NONE, ""),
        pressure=PressureAnalysis(UserState.NEUTRAL, 0.5, 2, "", False),
        expression=ExpressionAnalysis(ResponseShape.ONE_HIT, StyleFlavor.DRY, "", ""),
        awareness=AwarenessAnalysis(ConversationPattern.NONE, 0.0, None, None, 0),
    )
    # ARC is a DEPTH preset — proves the member reaches the router's set lookup.
    choice = select_model(
        PresetSelection(mode=PresetMode.ARC),
        flow,
        disclosure_severity=0,
        casual_model="h",
        depth_model="s",
        crisis_model="o",
    )
    assert choice.tier is ModelTier.DEPTH
    assert choice.reason == "depth_preset"


def test_contracts_package_is_a_stdlib_only_leaf() -> None:
    """The neutral contracts must not import any insult.* module — that would
    re-couple the host-importable layer to smart/persona internals."""
    pkg = REPO_ROOT / "personas" / "insult" / "core" / "contracts"
    for path in pkg.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            mods: list[str] = []
            if isinstance(node, ast.Import):
                mods = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                mods = [node.module]
            for m in mods:
                # The package barrel may import its own submodules; nothing else.
                assert not (m.startswith("personas.insult.") and not m.startswith("personas.insult.core.contracts")), (
                    f"{path.name} imports {m} — contracts must stay a neutral leaf"
                )
