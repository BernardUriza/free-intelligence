"""Architectural fitness function: host-facing code must NOT import smart/persona internals.

The destilado (`.claude/plans/khimeras_demux_destilado.md`) splits the `insult/`
god-package into a lightweight HOST (demux: receive/route/deliver/health) and
SMART persona internals (memory, RAG, transcribe, facts, behavior). This test
codifies the boundary BEFORE any code moves: host-facing modules may not import
the forbidden smart/persona/runner internals.

It parses each host-facing file's AST (does NOT import it — no .env / heavy deps
needed) and flags any import of a forbidden module. Relative imports are resolved
to their absolute dotted name so `from ..core.presets import X` is caught too.

Step 1 (Red) reality: the current plumbing (`insult/cogs/chat/**`) is deeply
coupled to persona logic, so this WILL report many pre-existing violations. Those
are the legacy debt the refactor will pay down phase by phase — they are NOT
fixed here. See test_arch_no_new_import_boundary_violations for the CI-safe
baseline guard that prevents NEW violations while tolerating known ones.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Host-facing modules: the lightweight Discord plumbing (demux-to-be). Globs
# ending in /** expand to every .py beneath. Only existing files are tested.
HOST_FACING_PATTERNS: list[str] = [
    "insult/bot.py",
    "insult/app.py",
    "insult/__main__.py",
    "insult/config.py",
    "insult/cogs/chat/**",
    "insult/core/routing.py",
    "insult/core/triviality.py",
    "insult/core/delivery.py",
    "insult/core/errors.py",
    "insult/core/guild_setup.py",
    "insult/core/health_state.py",
    "insult/core/debug_server/**",
    "insult/core/metrics.py",
    "insult/core/backup.py",
]

# Smart/persona/runner internals the host must never reach into.
FORBIDDEN_MODULES: list[str] = [
    "insult.core.memory",
    "insult.core.deep_memory",
    "insult.core.vectors",
    "insult.core.facts",
    # NOTE: the [REMEMBER:] marker pipeline relocated to insult.cogs.chat.remembers
    # (host-side post-LLM marker parse + strip + a persist that takes the memory
    # store INJECTED — it owns no persistence, same shape as the reactions adapter).
    # No longer a smart module, so insult.core.remembers is intentionally absent here.
    "insult.core.transcribe",
    "insult.core.attachments",
    "insult.core.summaries",
    "insult.core.memory_consolidator",
    "insult.core.character",
    "insult.core.presets",
    # NOTE: attachment processing relocated to insult.cogs.chat.attachments
    # (host-side Discord ingest adapter, zero persona/memory/LLM). No longer a
    # smart module, so insult.core.attachments is intentionally absent here.
    "insult.core.presets_llm",
    "insult.core.flows",
    "insult.core.vulnerability",
    # NOTE: disclosure scanning relocated to insult.cogs.chat.disclosure
    # (host-side pre-LLM regex classifier, zero persona/memory/LLM — same shape
    # as triviality). No longer a smart module, so insult.core.disclosure is
    # intentionally absent here.
    "insult.core.arc_tracker",
    "insult.core.style",
    "insult.core.proactive",
    # NOTE: the [REACT:] marker pipeline + Discord reaction egress relocated to
    # insult.cogs.chat.reactions (host-side: parse/strip markers + add_reactions
    # via the Discord API, pure stdlib+discord, zero persona/memory/LLM — same
    # shape as attachments/disclosure). No longer a smart module, so
    # insult.core.reactions is intentionally absent here.
    "insult.core.language",
    "insult.core.stance_log",
    "insult.agent",
]


def _resolve_host_files() -> list[Path]:
    """Expand the host-facing patterns to existing .py files."""
    files: list[Path] = []
    for pat in HOST_FACING_PATTERNS:
        if pat.endswith("/**"):
            base = REPO_ROOT / pat[:-3]
            if base.is_dir():
                files.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
        else:
            p = REPO_ROOT / pat
            if p.is_file():
                files.append(p)
    return sorted(set(files))


def _module_name_for(path: Path) -> str:
    """Dotted module name of a file relative to the repo root, e.g.
    insult/cogs/chat/stages.py -> insult.cogs.chat.stages."""
    rel = path.relative_to(REPO_ROOT).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imported_modules(path: Path) -> set[str]:
    """All absolute module names imported by a file, resolving relatives."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    self_mod = _module_name_for(path)
    self_parts = self_mod.split(".")
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0:
                if node.module:
                    out.add(node.module)
            else:
                # Relative import: drop `level` trailing components from the
                # package of this module, then append the relative module.
                # For a module a.b.c.d, `from . import x` (level=1) bases at a.b.c.
                base_parts = self_parts[: len(self_parts) - node.level]
                base = ".".join(base_parts)
                resolved = f"{base}.{node.module}" if node.module else base
                out.add(resolved.lstrip("."))
    return out


def _violations() -> list[tuple[str, str]]:
    """(host_file_module, forbidden_import) pairs across all host-facing files."""
    found: list[tuple[str, str]] = []
    for f in _resolve_host_files():
        mod = _module_name_for(f)
        for imp in _imported_modules(f):
            for forbidden in FORBIDDEN_MODULES:
                if imp == forbidden or imp.startswith(forbidden + "."):
                    found.append((mod, forbidden))
    return sorted(set(found))


# --- Baseline of KNOWN legacy violations (captured 2026-06-06, v4.21.2) -------
#
# These 9 host→smart imports are the structural coupling the demux destilado
# (`.claude/plans/khimeras_demux_destilado.md`) will pay down phase by phase.
# (Was 22; -2 via routing→{flows,presets} contracts extraction; -3 via the
# contracts batch: cog→flows ExpressionHistory, debug_server.keys→memory
# DebugMemoryPort Protocol, context→summaries pure helpers → server_pulse; -1
# via tasks→facts dependency injection (extract_facts/merge_facts_additive
# now injected by stages, which already owns the facts import); -2 via the
# post-LLM mutations seam (Wave 2): reactions + remembers relocated to host
# (insult.cogs.chat.{reactions,remembers}) — pure-stdlib marker pipelines, the
# remembers persist takes the memory store injected so no persistence ownership
# moved; -1 via PR-A FactsPort (S2/S5 domain facets): stages depends on the
# FactsPort Protocol (insult.cogs.chat.ports), the concrete adapter is wired by
# the composition seam (insult.composition) which is the only module that knows
# both the Protocol and insult.core.facts — no new host→smart edge; -1 via
# PR-B StancePort, same seam: render_block (S2) + derive (S5) behind the
# Protocol, get/store_stance stay on the memory data plane; -1 via PR-C
# ArcPort, same seam + OPACITY: ArcState is owned by the port, stages
# transports the carry without reading its fields (load/phase/render_block
# pre-LLM, advance/dump post-LLM), enforced by the anti-access resistance
# test in test_arc_port.py.)
# They are TOLERATED for now; the guard below fails only on NEW violations.
# When a phase removes one, DELETE its line here — the guard will tell you to
# (a baseline entry no longer present is reported so the ratchet only tightens).
BASELINE_VIOLATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("insult.__main__", "insult.core.memory"),
        ("insult.__main__", "insult.core.memory_consolidator"),
        ("insult.app", "insult.core.memory"),
        ("insult.cogs.chat.stages", "insult.core.character"),
        ("insult.cogs.chat.stages", "insult.core.deep_memory"),
        ("insult.cogs.chat.stages", "insult.core.flows"),
        ("insult.cogs.chat.stages", "insult.core.presets"),
        ("insult.cogs.chat.stages", "insult.core.presets_llm"),
        ("insult.cogs.chat.voice", "insult.core.transcribe"),
    }
)


def test_no_new_host_to_smart_import_violations() -> None:
    """CI-SAFE RATCHET — the guard that actually runs in the pipeline.

    Fails only when a NEW host→smart import appears (one not in the baseline).
    This protects the boundary going forward while tolerating the known legacy
    coupling, so the destilado can proceed phase by phase without a red build.
    """
    current = set(_violations())
    new = current - BASELINE_VIOLATIONS
    if new:
        lines = "\n".join(f"  {mod}  ─imports→  {forbidden}" for mod, forbidden in sorted(new))
        raise AssertionError(
            f"{len(new)} NEW host→smart import-boundary violation(s) introduced:\n{lines}\n\n"
            "Host-facing plumbing must not reach into smart/persona internals. "
            "Either route through the runner / a capability boundary, or (if this "
            "is genuinely host code) reconsider the design — do NOT add it to the "
            "baseline to silence it."
        )

    # Ratchet only tightens: if a baseline entry no longer exists (a phase fixed
    # it), make us delete it so the baseline can't hide regained ground.
    stale = BASELINE_VIOLATIONS - current
    if stale:
        lines = "\n".join(f"  {mod}  ─imports→  {forbidden}" for mod, forbidden in sorted(stale))
        raise AssertionError(
            f"{len(stale)} baseline violation(s) no longer present — delete them from "
            f"BASELINE_VIOLATIONS to lock in the win:\n{lines}"
        )


@pytest.mark.xfail(
    reason="legacy host→persona coupling (26 known); target is 0 after the demux destilado. "
    "Tracked actively by test_no_new_host_to_smart_import_violations.",
    strict=False,
)
def test_host_facing_modules_do_not_import_smart_internals() -> None:
    """STRICT goal — ZERO host→smart imports. xfail until the refactor lands;
    flips to xpass when the destilado finishes, signalling the boundary is clean."""
    violations = _violations()
    assert not violations, f"{len(violations)} host→smart import-boundary violation(s) remain"
