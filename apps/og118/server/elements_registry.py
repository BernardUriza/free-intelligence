"""og118 elementos — the finite 118-slot persona registry (OG118-ELEMENTS-ADR-1).

An "elemento" is a named, numbered persona (a periodic-table slot) backed by an
existing bot. The registry is TWO layers (the ADR's D4): this module loads the
STRUCTURAL catalog (`elements/elements.registry.json` — a data file, not a
model-facing prompt, so JSON is correct and does NOT violate prompts-as-content)
and resolves a slot's persona to its per-element `.md` (loaded via `load_prompt`
at the call site, hot-reloadable). The cap is HARD (118, D3): the loader refuses a
registry that exceeds it or numbers a slot outside 1..118.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CAP = 118
ELEMENTS_DIR = Path(__file__).parent / "elements"
REGISTRY_PATH = ELEMENTS_DIR / "elements.registry.json"
# PERSONA-SSOT-1: a persona's shared CORE lives once in the fi-personas package
# (apps/packages/fi-personas), consumed by every surface that speaks it (og118
# element, the Discord bot). An element with `personaCorePath` composes that core
# + its own operative-context block, so the character is not copied per repo.
FI_PERSONAS_DIR = Path(__file__).resolve().parents[2] / "packages" / "fi-personas" / "personas"
CONTEXT_MARKER = "<!-- CONTEXTO_OPERATIVO -->"

_VALID_STATUS = {"empty", "reserved", "active", "deprecated", "disabled"}


class ElementsRegistryError(ValueError):
    """The registry is malformed or violates an invariant (cap, uniqueness, a
    missing persona file for an active slot). Raised at load time — a broken
    catalog fails fast instead of resolving to a wrong/empty persona at run time."""


_ENGINE_KINDS = {"local_runner_persona", "shared_persona_prompt", "external_http_engine"}


@dataclass(frozen=True)
class EngineBinding:
    """How an element's turn is executed (ENGINE-BINDING-ADR-1). Default (absent)
    is local: og118's own fi-runner runs the turn with the composed persona.
    `external_http_engine` proxies the turn to an already-running FI engine (e.g.
    the live Vultur runner) — `persona_id` selects the persona on that engine."""

    kind: str
    persona_id: str | None = None

    @property
    def is_external(self) -> bool:
        return self.kind == "external_http_engine"


@dataclass(frozen=True)
class Element:
    atomic_number: int
    symbol: str
    slug: str
    display_name: str
    status: str
    backing_bot_id: str | None = None
    persona_prompt_path: str | None = None
    # PERSONA-SSOT-1: the shared persona core in fi-personas. When set, the active
    # element's system prompt is composed = core (marker spliced with the
    # persona_prompt_path block), instead of persona_prompt_path being the whole
    # prompt. Absent → persona_prompt_path is the full standalone persona (legacy).
    persona_core_path: str | None = None
    # ENGINE-BINDING-ADR-1: how this element runs. None → local (og118's runner).
    engine_binding: EngineBinding | None = None
    aliases: tuple[str, ...] = ()

    @property
    def id(self) -> str:
        """Canonical id: ``element-008-o-oxigeno`` (atomic number is the PK, D2)."""
        return f"element-{self.atomic_number:03d}-{self.symbol.lower()}-{self.slug}"

    @property
    def display_label(self) -> str:
        return f"{self.atomic_number} · {self.symbol} · {self.display_name}"

    @property
    def is_active(self) -> bool:
        return self.status == "active"


def _to_engine_binding(raw: dict | None) -> EngineBinding | None:
    if not raw:
        return None
    kind = raw.get("kind")
    if kind not in _ENGINE_KINDS:
        raise ElementsRegistryError(
            f"engineBinding.kind {kind!r} not one of {sorted(_ENGINE_KINDS)}"
        )
    return EngineBinding(kind=kind, persona_id=raw.get("personaId"))


def _to_element(raw: dict) -> Element:
    return Element(
        atomic_number=raw["atomicNumber"],
        symbol=raw["symbol"],
        slug=raw["slug"],
        display_name=raw["displayName"],
        status=raw["status"],
        backing_bot_id=raw.get("backingBotId"),
        persona_prompt_path=raw.get("personaPromptPath"),
        persona_core_path=raw.get("personaCorePath"),
        engine_binding=_to_engine_binding(raw.get("engineBinding")),
        aliases=tuple(raw.get("aliases", ())),
    )


@dataclass(frozen=True)
class ElementsRegistry:
    elements: tuple[Element, ...]

    @classmethod
    def load(cls, path: Path = REGISTRY_PATH) -> "ElementsRegistry":
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as e:
            raise ElementsRegistryError(f"registry not found: {path}") from e
        except json.JSONDecodeError as e:
            raise ElementsRegistryError(f"registry is not valid JSON: {e}") from e
        cap = doc.get("cap", CAP)
        elements = tuple(_to_element(r) for r in doc.get("elements", []))
        reg = cls(elements=elements)
        reg._validate(cap)
        return reg

    def _validate(self, cap: int) -> None:
        if cap != CAP:
            raise ElementsRegistryError(f"cap must be {CAP} (got {cap})")
        if len(self.elements) > CAP:
            raise ElementsRegistryError(
                f"more than {CAP} elements ({len(self.elements)}) — the cap is HARD"
            )
        seen_z: set[int] = set()
        seen_slug: set[str] = set()
        for e in self.elements:
            if not (1 <= e.atomic_number <= CAP):
                raise ElementsRegistryError(
                    f"atomicNumber {e.atomic_number} outside 1..{CAP} ({e.symbol})"
                )
            if e.atomic_number in seen_z:
                raise ElementsRegistryError(f"duplicate atomicNumber {e.atomic_number}")
            seen_z.add(e.atomic_number)
            if e.slug in seen_slug:
                raise ElementsRegistryError(f"duplicate slug {e.slug!r}")
            seen_slug.add(e.slug)
            if e.status not in _VALID_STATUS:
                raise ElementsRegistryError(f"invalid status {e.status!r} for {e.symbol}")
            if e.is_active and not (e.engine_binding is not None and e.engine_binding.is_external):
                # LOCAL active element: og118's runner runs it, so it must carry its
                # own persona on disk. (An EXTERNAL element needs none — the remote
                # engine owns the persona; persona_id is optional and absent means the
                # engine's default persona, e.g. Insult on the insult-runner.)
                if not e.backing_bot_id or not e.persona_prompt_path:
                    raise ElementsRegistryError(
                        f"active element {e.symbol} needs backingBotId + personaPromptPath"
                    )
                if not (ELEMENTS_DIR / e.persona_prompt_path).is_file():
                    raise ElementsRegistryError(
                        f"active element {e.symbol}: persona file missing "
                        f"({e.persona_prompt_path})"
                    )
                if e.persona_core_path:
                    core = FI_PERSONAS_DIR / e.persona_core_path
                    if not core.is_file():
                        raise ElementsRegistryError(
                            f"active element {e.symbol}: shared persona core missing "
                            f"({e.persona_core_path})"
                        )
                    if CONTEXT_MARKER not in core.read_text(encoding="utf-8"):
                        raise ElementsRegistryError(
                            f"active element {e.symbol}: shared core {e.persona_core_path} "
                            f"lacks the {CONTEXT_MARKER} splice marker"
                        )

    def resolve(self, token: str | None) -> Element | None:
        """Find an element by slug, symbol (case-insensitive), atomic number,
        canonical id, or alias. Returns None for an unknown/blank token (the base
        og118 persona handles "no element")."""
        if not token:
            return None
        t = token.strip().lower()
        for e in self.elements:
            if (
                t == e.slug
                or t == e.symbol.lower()
                or t == str(e.atomic_number)
                or t == e.id
                or t in e.aliases
            ):
                return e
        return None

    def persona_path(self, e: Element) -> Path | None:
        if not e.persona_prompt_path:
            return None
        return ELEMENTS_DIR / e.persona_prompt_path

    def core_path(self, e: Element) -> Path | None:
        """The shared persona core (fi-personas) for an element, or None when the
        element's persona_prompt_path is a standalone full persona (PERSONA-SSOT-1)."""
        if not e.persona_core_path:
            return None
        return FI_PERSONAS_DIR / e.persona_core_path

    def composed_persona(self, e: Element) -> str | None:
        """The element's full system prompt (PERSONA-SSOT-1). With a shared core,
        the core's CONTEXT_MARKER is spliced with the element's operative-context
        block (persona_prompt_path), so the character's core is NOT copied per repo.
        Without a core, persona_prompt_path is the whole standalone persona."""
        ppath = self.persona_path(e)
        if ppath is None:
            return None
        context = ppath.read_text(encoding="utf-8")
        cpath = self.core_path(e)
        if cpath is None:
            return context
        return cpath.read_text(encoding="utf-8").replace(CONTEXT_MARKER, context)


@lru_cache(maxsize=1)
def get_registry() -> ElementsRegistry:
    """The process-wide registry (loaded + validated once)."""
    return ElementsRegistry.load()
