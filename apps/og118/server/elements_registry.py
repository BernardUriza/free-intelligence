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

_VALID_STATUS = {"empty", "reserved", "active", "deprecated", "disabled"}


class ElementsRegistryError(ValueError):
    """The registry is malformed or violates an invariant (cap, uniqueness, a
    missing persona file for an active slot). Raised at load time — a broken
    catalog fails fast instead of resolving to a wrong/empty persona at run time."""


@dataclass(frozen=True)
class Element:
    atomic_number: int
    symbol: str
    slug: str
    display_name: str
    status: str
    backing_bot_id: str | None = None
    persona_prompt_path: str | None = None
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


def _to_element(raw: dict) -> Element:
    return Element(
        atomic_number=raw["atomicNumber"],
        symbol=raw["symbol"],
        slug=raw["slug"],
        display_name=raw["displayName"],
        status=raw["status"],
        backing_bot_id=raw.get("backingBotId"),
        persona_prompt_path=raw.get("personaPromptPath"),
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
            if e.is_active:
                if not e.backing_bot_id or not e.persona_prompt_path:
                    raise ElementsRegistryError(
                        f"active element {e.symbol} needs backingBotId + personaPromptPath"
                    )
                if not (ELEMENTS_DIR / e.persona_prompt_path).is_file():
                    raise ElementsRegistryError(
                        f"active element {e.symbol}: persona file missing "
                        f"({e.persona_prompt_path})"
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


@lru_cache(maxsize=1)
def get_registry() -> ElementsRegistry:
    """The process-wide registry (loaded + validated once)."""
    return ElementsRegistry.load()
