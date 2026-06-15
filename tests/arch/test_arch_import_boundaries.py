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

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Host-facing modules: the lightweight Discord plumbing (demux-to-be). Globs
# ending in /** expand to every .py beneath. Only existing files are tested.
#
# Post-demux (Etapa 3, 2026-06-15): these paths were re-pointed from the dead
# flat `insult/` tree to `personas/insult/`. Before the re-point they resolved
# to ZERO existing files, so the whole boundary guard passed vacuously — a
# fake-green. _resolve_host_files() now also FAILS LOUD on an empty result
# (test_host_facing_patterns_resolve_to_real_files) so a future tree move that
# orphans these globs can never silently disable the guard again.
HOST_FACING_PATTERNS: list[str] = [
    "personas/insult/bot.py",
    "personas/insult/app.py",
    "personas/insult/__main__.py",
    "personas/insult/config.py",
    "personas/insult/cogs/chat/**",
    "personas/insult/core/routing.py",
    "personas/insult/core/triviality.py",
    "personas/insult/core/delivery.py",
    "personas/insult/core/errors.py",
    "personas/insult/core/guild_setup.py",
    "personas/insult/core/health_state.py",
    "personas/insult/core/debug_server/**",
    "personas/insult/core/metrics.py",
    "personas/insult/core/backup.py",
]

# Smart/persona/runner internals the host must never reach into.
FORBIDDEN_MODULES: list[str] = [
    "personas.insult.core.memory",
    "personas.insult.core.deep_memory",
    "personas.insult.core.vectors",
    "personas.insult.core.facts",
    # NOTE: the [REMEMBER:] marker pipeline relocated to insult.cogs.chat.remembers
    # (host-side post-LLM marker parse + strip + a persist that takes the memory
    # store INJECTED — it owns no persistence, same shape as the reactions adapter).
    # No longer a smart module, so insult.core.remembers is intentionally absent here.
    "personas.insult.core.transcribe",
    "personas.insult.core.attachments",
    "personas.insult.core.summaries",
    "personas.insult.core.memory_consolidator",
    "personas.insult.core.character",
    "personas.insult.core.presets",
    # NOTE: attachment processing relocated to insult.cogs.chat.attachments
    # (host-side Discord ingest adapter, zero persona/memory/LLM). No longer a
    # smart module, so insult.core.attachments is intentionally absent here.
    "personas.insult.core.presets_llm",
    "personas.insult.core.flows",
    "personas.insult.core.vulnerability",
    # NOTE: disclosure scanning relocated to insult.cogs.chat.disclosure
    # (host-side pre-LLM regex classifier, zero persona/memory/LLM — same shape
    # as triviality). No longer a smart module, so insult.core.disclosure is
    # intentionally absent here.
    "personas.insult.core.arc_tracker",
    "personas.insult.core.style",
    "personas.insult.core.proactive",
    # NOTE: the [REACT:] marker pipeline + Discord reaction egress relocated to
    # insult.cogs.chat.reactions (host-side: parse/strip markers + add_reactions
    # via the Discord API, pure stdlib+discord, zero persona/memory/LLM — same
    # shape as attachments/disclosure). No longer a smart module, so
    # insult.core.reactions is intentionally absent here.
    "personas.insult.core.language",
    "personas.insult.core.stance_log",
    "personas.insult.agent",
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
# test in test_arc_port.py; -1 via PR-D RetrievalPort (FIRST capability seam,
# `.claude/plans/capability_seams_retrieval_preset.md`): stages consumes
# finished retrieval blocks through insult.cogs.chat.capability_ports —
# rendering policy moved into insult.core.deep_memory.build_user_memory_block,
# the adapter in insult.composition owns the best-effort boundary + the
# lexical film gate; -2 via PR-E PresetEnginePort (second capability seam,
# same design doc): stages drops presets AND presets_llm together — the
# dual-strategy arbitration (LLM timeout/fallback + regex shadow-run +
# divergence telemetry) and guidance rendering live in the composition
# adapter built WITH judge_client+settings; the PresetSelection/PresetModifier
# vocabulary re-points to insult.core.contracts, which is legal for host;
# -1 via PR-F S1bPolicyPort (S1b seam, `.claude/plans/s1b_ground_truth.md`):
# stages drops flows entirely — analyze + flow render + layer composition live
# in the composition adapter built WITH expression_history (state stays
# host-owned), the S5 validators ride the same port as the assess facet, and
# the private other-people block renders behind other_people_block(); the
# stages→character entry survives only for its post-LLM S4 mutation half;
# -1 via PR-G OutputMutationPort (same design doc): the guardrailed S4
# mutation pipeline (echo-strip → length variation → opener dedup → marker
# strips, with max_shrink/must_preserve policy) moved into the composition
# adapter — stages drops its LAST character import and the edge falls. The
# [REACT:]/[REMEMBER:] parsers stay host-side in the stage, untouched.)
# They are TOLERATED for now; the guard below fails only on NEW violations.
# When a phase removes one, DELETE its line here — the guard will tell you to
# (a baseline entry no longer present is reported so the ratchet only tightens).
BASELINE_VIOLATIONS: frozenset[tuple[str, str]] = frozenset(
    {
        # All governance edges closed (PR-gov 2026-06-12):
        #   __main__ → memory          — routed via composition.create_memory_store()
        #   __main__ → memory_consolidator — re-exported from composition
        #   app      → memory          — routed via composition.create_memory_store()
        # voice → transcribe closed (PR-voice 2026-06-12):
        #   cogs.chat.voice → transcribe — routed via composition.default_transcription_port()
        # Ratchet: 14 → 4 → 1 → 0. Program complete.
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


def test_host_facing_modules_do_not_import_smart_internals() -> None:
    """STRICT goal reached — ZERO host→smart imports (2026-06-12, ratchet 14→0).

    Was xfail during the demux destilado refactor; the xfail is removed now
    that all 14 violations are gone and the boundary is clean. This is a
    permanent regression gate: any new host→smart import will fail both this
    test and ``test_no_new_host_to_smart_import_violations``."""
    violations = _violations()
    assert not violations, f"{len(violations)} host→smart import-boundary violation(s) remain"


def test_host_facing_patterns_resolve_to_real_files() -> None:
    """ANTI-FAKE-GREEN guard (Etapa 3, 2026-06-15).

    The host→smart ratchet is only meaningful if HOST_FACING_PATTERNS actually
    match real files. Before the demux re-point these globs pointed at the dead
    flat ``insult/`` tree, resolved to an EMPTY set, and every host→smart test
    passed vacuously. This guard makes an empty resolution a hard FAIL so a
    future tree move that orphans the globs surfaces immediately instead of
    silently disabling the boundary checks."""
    files = _resolve_host_files()
    assert files, (
        "HOST_FACING_PATTERNS resolved to ZERO files — the host→smart ratchet is "
        "testing nothing (fake-green). The repo tree moved and these globs are "
        "stale; re-point them at the current host plumbing."
    )


# --- Cross-boundary fitness functions (Etapa 3 demux físico, 2026-06-15) -------
#
# The host→smart ratchet above guards ONE edge (insult plumbing → insult smart
# internals). Etapa 3 adds the inter-package boundaries the coagent mandated:
#   - a persona must NOT import another persona,
#   - shared/khimeras_shared must NOT import any persona,
#   - the persona_gateway (explicit host wiring) imports of persona internals
#     are tracked toward removal in the capability moves (PR-1).
PERSONA_ROOTS: tuple[str, ...] = ("personas/insult", "personas/alice")
SHARED_ROOTS: tuple[str, ...] = ("shared", "khimeras_shared")


def _scan_py(roots: tuple[str, ...]) -> list[Path]:
    files: list[Path] = []
    for r in roots:
        base = REPO_ROOT / r
        if base.is_dir():
            files.extend(p for p in base.rglob("*.py") if "__pycache__" not in p.parts)
    return sorted(files)


def _persona_of(module: str) -> str | None:
    if module.startswith("personas.insult"):
        return "personas.insult"
    if module.startswith("personas.alice"):
        return "personas.alice"
    return None


def _cross_persona_violations() -> list[tuple[str, str]]:
    """(importer_module, imported_persona_module) where a persona reaches into
    a DIFFERENT persona package."""
    found: list[tuple[str, str]] = []
    for f in _scan_py(PERSONA_ROOTS):
        mod = _module_name_for(f)
        own = _persona_of(mod)
        if own is None:
            continue
        other = "personas.alice" if own == "personas.insult" else "personas.insult"
        for imp in _imported_modules(f):
            if imp == other or imp.startswith(other + "."):
                found.append((mod, imp))
    return sorted(set(found))


# Persona→other-persona edges: NONE. The ALICE→Insult film-criticism edge was
# closed in PR-1 (2026-06-15) by moving build_film_references_block + the RAG
# primitives to khimeras_shared.corpus.{film_references,pg_rag} — a neutral
# capability both personas consume. Empty baseline = the ratchet now fails on
# ANY cross-persona import (test_no_new_cross_persona_imports), zero tolerated.
CROSS_PERSONA_BASELINE: frozenset[tuple[str, str]] = frozenset()


def test_no_new_cross_persona_imports() -> None:
    """A persona must not import another persona's internals. Tolerates the known
    baseline, fails on any NEW cross-persona edge; ratchet only tightens."""
    current = set(_cross_persona_violations())
    new = current - CROSS_PERSONA_BASELINE
    assert not new, (
        f"{len(new)} NEW cross-persona import(s) — a persona must not know another "
        f"persona. Move the shared capability to khimeras_shared:\n"
        + "\n".join(f"  {m} ─imports→ {i}" for m, i in sorted(new))
    )
    stale = CROSS_PERSONA_BASELINE - current
    assert not stale, (
        "Baseline cross-persona edge(s) gone — drop the entry in CROSS_PERSONA_BASELINE "
        "to lock the win:\n" + "\n".join(f"  {m} ─imports→ {i}" for m, i in sorted(stale))
    )


def test_shared_never_imports_personas() -> None:
    """STRICT — shared/khimeras_shared must never depend on any persona (currently
    clean; locked at zero). Capability/shared code is consumed BY personas, never
    the reverse."""
    found = [
        (_module_name_for(f), imp)
        for f in _scan_py(SHARED_ROOTS)
        for imp in _imported_modules(f)
        if imp == "personas" or imp.startswith("personas.")
    ]
    assert not found, (
        f"{len(found)} shared→persona import(s) — shared/khimeras_shared must not "
        f"depend on personas:\n" + "\n".join(f"  {m} ─imports→ {i}" for m, i in sorted(found))
    )


# persona_gateway is explicit host wiring, but it still reaches into Insult
# persona internals for capabilities that belong in the shared layer. Captured
# as baseline 2026-06-15; the capability moves drop them one by one:
#   - agent_client edge CLOSED in PR-1b (AgentRunnerClient → khimeras_shared.runner)
#   - memory edge falls in PR-1c (MemoryStore subsystem → khimeras_shared)
#   - config edge falls in the Etapa 3 wiring cleanup
# DELETE entries as they go.
GATEWAY_PERSONA_BASELINE: frozenset[tuple[str, str]] = frozenset(
    {
        ("persona_gateway.gateway", "personas.insult.core.memory"),
        ("persona_gateway.gateway", "personas.insult.config"),
    }
)


def test_no_new_gateway_persona_imports() -> None:
    """persona_gateway may do explicit wiring, but its reach into Insult persona
    internals is tracked toward removal (PR-1 capability moves). Fails on NEW
    edges, requires deleting baselined ones once the capability moves out."""
    current = {
        (_module_name_for(f), imp)
        for f in _scan_py(("persona_gateway",))
        for imp in _imported_modules(f)
        if (imp == "personas" or imp.startswith("personas."))
    }
    new = current - GATEWAY_PERSONA_BASELINE
    assert not new, f"{len(new)} NEW persona_gateway→persona import(s):\n" + "\n".join(
        f"  {m} ─imports→ {i}" for m, i in sorted(new)
    )
    stale = GATEWAY_PERSONA_BASELINE - current
    assert not stale, (
        "Baseline gateway→persona edge(s) gone — drop the entry in GATEWAY_PERSONA_BASELINE:\n"
        + "\n".join(f"  {m} ─imports→ {i}" for m, i in sorted(stale))
    )
