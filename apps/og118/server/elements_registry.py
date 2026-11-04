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
import os
import tempfile
import threading
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

CAP = 118
ELEMENTS_DIR = Path(__file__).parent / "elements"
REGISTRY_PATH = ELEMENTS_DIR / "elements.registry.json"
# OG118-ELEMENTOS-ALTA (2026-10-28): slots claimed from the UI, without a deploy.
# The image's catalog stays the base; the overlay on the Azure Files volume only
# turns an EMPTY slot active and binds it to a persona the runner already holds.
_OVERLAY_LOCK = threading.Lock()


def overlay_path() -> Path:
    default = Path(os.getenv("FI_RAG_STORE_PATH", "/opt/fi/data/fi_rag_store.h5")).parent / "elements.overlay.json"
    return Path(os.getenv("OG118_ELEMENTS_OVERLAY_PATH", str(default)))
# PERSONA-SSOT-2 (2026-09-10, decisión de Bernard): el prompt de un elemento vive
# en discord-bot y en ningún otro lado. og118 NO guarda personajes: elige el
# elemento y el runner de allá pone la voz, igual que Yodo con `insult.md`. Por eso
# aquí no hay ni ruta de persona ni marcador de empalme — un elemento sin motor
# externo no puede estar activo, y el catálogo lo rechaza al cargar.
#
# La razón es medida, no estética: cuando og118 guardaba su propia copia, el core
# de Vultur tenía 96 líneas y la copia viva de discord-bot 205, con 87 que sólo
# existían allá. Un personaje en dos repos se separa solo.

_VALID_STATUS = {"empty", "reserved", "active", "deprecated", "disabled"}


class ElementsRegistryError(ValueError):
    """The registry is malformed or violates an invariant (cap, uniqueness, a
    missing persona file for an active slot). Raised at load time — a broken
    catalog fails fast instead of resolving to a wrong/empty persona at run time."""


# Una sola forma de correr un elemento. `local_runner_persona` y
# `shared_persona_prompt` se borraron con PERSONA-SSOT-2: nombraban una capacidad
# que og118 ya no tiene.
_ENGINE_KINDS = {"external_http_engine"}

# Human labels for the engine/persona that answers an element, shown as the
# selector's engine chip (OG118-ELEMENTS-COMPOSER-SWITCH-1). Keyed by persona_id;
# unknown ids fall back to capitalize(). These are UI labels, never prompts.
_ENGINE_LABELS = {"vultur": "Vultur", "alice": "ALICE", "insult": "Insult", "astra": "Astra"}


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
    # Cómo corre este elemento. Siempre un motor externo si está activo
    # (PERSONA-SSOT-2); `persona_id` ausente = la persona por default del motor,
    # que es Insult.
    engine_binding: EngineBinding | None = None
    aliases: tuple[str, ...] = ()
    # One-line, human-facing summary of the element's persona for the selector
    # panel (OG118-ELEMENTS-COMPOSER-SWITCH-1). Content, not a model prompt.
    description: str | None = None

    @property
    def id(self) -> str:
        """Canonical id: ``element-008-o-oxigeno`` (atomic number is the PK, D2)."""
        return f"element-{self.atomic_number:03d}-{self.symbol.lower()}-{self.slug}"

    @property
    def display_label(self) -> str:
        return f"{self.atomic_number} · {self.symbol} · {self.display_name}"

    @property
    def engine_label(self) -> str | None:
        """The human label of the engine/persona answering this element (Vultur /
        ALICE / Insult), or None for the local base. An external element without a
        persona_id defaults to the runner's Insult persona."""
        eb = self.engine_binding
        if eb is None:
            return None
        if eb.persona_id:
            return _ENGINE_LABELS.get(eb.persona_id, eb.persona_id.capitalize())
        return _ENGINE_LABELS["insult"]

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
        engine_binding=_to_engine_binding(raw.get("engineBinding")),
        aliases=tuple(raw.get("aliases", ())),
        description=raw.get("description"),
    )


@dataclass(frozen=True)
class ElementsRegistry:
    elements: tuple[Element, ...]

    @classmethod
    def load(cls, path: Path = REGISTRY_PATH, overlay: Path | None = None) -> "ElementsRegistry":
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
        for claim in _read_overlay(overlay):
            reg = reg.with_claim(claim)
        return reg

    def with_claim(self, claim: dict) -> "ElementsRegistry":
        """This catalog with one EMPTY slot turned active on an external persona.
        Refuses a taken slot, an unknown slot, or an alias another element owns."""
        z = claim.get("atomicNumber")
        persona_id = claim.get("personaId")
        slot = next((e for e in self.elements if e.atomic_number == z), None)
        if slot is None:
            raise ElementsRegistryError(f"no slot {z!r}")
        if slot.status != "empty":
            raise ElementsRegistryError(f"slot {z} ({slot.symbol}) is {slot.status}, not empty")
        if not persona_id:
            raise ElementsRegistryError("a claim needs a personaId")
        aliases = tuple(a.strip().lower() for a in claim.get("aliases", ()) if a.strip())
        for a in aliases:
            owner = self.resolve(a)
            if owner is not None and owner.atomic_number != z:
                raise ElementsRegistryError(f"alias {a!r} already names {owner.symbol}")
        claimed = replace(
            slot,
            status="active",
            display_name=claim.get("displayName") or slot.display_name,
            description=claim.get("description"),
            aliases=aliases,
            engine_binding=EngineBinding(kind="external_http_engine", persona_id=persona_id),
        )
        return ElementsRegistry(elements=tuple(claimed if e is slot else e for e in self.elements))

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
            external = e.engine_binding is not None and e.engine_binding.is_external
            if e.is_active and not external:
                # PERSONA-SSOT-2: og118 no hospeda personajes. Un elemento activo sin
                # motor externo no tendría de dónde sacar su voz, así que el catálogo
                # se niega a cargar en vez de contestar con la persona base y hacer
                # pasar por Plutonio a un asistente genérico.
                raise ElementsRegistryError(
                    f"active element {e.symbol} must declare an external engineBinding — "
                    f"og118 no longer hosts element personas (PERSONA-SSOT-2); the prompt "
                    f"lives in discord-bot's persona-runner"
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


def _read_overlay(path: Path | None) -> list[dict]:
    if path is None or not path.exists():
        return []
    try:
        return list(json.loads(path.read_text(encoding="utf-8")).get("claims", []))
    except json.JSONDecodeError as e:
        raise ElementsRegistryError(f"overlay is not valid JSON: {e}") from e


def _write_overlay(path: Path, claims: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".elements.overlay.")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump({"claims": claims}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    get_registry.cache_clear()


def _registry_with(claims: list[dict]) -> ElementsRegistry:
    reg = ElementsRegistry.load()
    for claim in claims:
        reg = reg.with_claim(claim)
    return reg


def claim_for(atomic_number: int, path: Path | None = None) -> dict | None:
    """The overlay claim that activated a slot, or None for an image element."""
    return next((c for c in _read_overlay(path or overlay_path()) if c.get("atomicNumber") == atomic_number), None)


def claim_slot(claim: dict, path: Path | None = None) -> Element:
    """Append a claim to the overlay (validated against the live catalog first)
    and return the element it activated. The catalog cache is dropped on success."""
    path = path or overlay_path()
    with _OVERLAY_LOCK:
        claimed = get_registry().with_claim(claim)
        _write_overlay(path, [*_read_overlay(path), claim])
    return next(e for e in claimed.elements if e.atomic_number == claim["atomicNumber"])


def replace_claim(claim: dict, path: Path | None = None) -> Element:
    """Edit a claimed slot in place: same slot, same persona id, new name, text or aliases."""
    path = path or overlay_path()
    z = claim["atomicNumber"]
    with _OVERLAY_LOCK:
        others = [c for c in _read_overlay(path) if c.get("atomicNumber") != z]
        if len(others) == len(_read_overlay(path)):
            raise ElementsRegistryError(f"slot {z} was not claimed from the UI")
        claimed = _registry_with(others).with_claim(claim)
        _write_overlay(path, [*others, claim])
    return next(e for e in claimed.elements if e.atomic_number == z)


def release_slot(atomic_number: int, path: Path | None = None) -> dict:
    """Empty a claimed slot again and return the claim it held."""
    path = path or overlay_path()
    with _OVERLAY_LOCK:
        claims = _read_overlay(path)
        held = next((c for c in claims if c.get("atomicNumber") == atomic_number), None)
        if held is None:
            raise ElementsRegistryError(f"slot {atomic_number} was not claimed from the UI")
        _write_overlay(path, [c for c in claims if c is not held])
    return held


@lru_cache(maxsize=1)
def get_registry() -> ElementsRegistry:
    """The process-wide registry: the image's catalog plus the volume's claims."""
    return ElementsRegistry.load(overlay=overlay_path())
