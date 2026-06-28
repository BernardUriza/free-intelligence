"""OG118-ELEMENTS-ADR-1 — the finite 118-slot persona registry.

Two layers: the real shipped registry (118 slots, Oxígeno active + its persona
.md exists) and the invariants that make the cap HARD and the catalog trustworthy
(cap, uniqueness, an active slot must have a real persona file). A broken catalog
must fail at LOAD, never resolve to a wrong/empty persona at run time.
"""

from __future__ import annotations

import json

import pytest

from elements_registry import (
    CAP,
    ElementsRegistry,
    ElementsRegistryError,
    get_registry,
)


def test_shipped_registry_has_exactly_118_and_oxygen_active() -> None:
    reg = get_registry()
    assert len(reg.elements) == 118
    o = reg.resolve("oxigeno")
    assert o is not None and o.is_active
    assert o.atomic_number == 8 and o.symbol == "O"
    assert o.backing_bot_id == "vultur-bot"
    # the active slot's persona file really exists (load-time invariant held)
    assert reg.persona_path(o) is not None and reg.persona_path(o).is_file()


def test_canonical_id_and_label_use_atomic_number_pk() -> None:
    o = get_registry().resolve("oxigeno")
    assert o.id == "element-008-o-oxigeno"
    assert o.display_label == "8 · O · Oxígeno"


def test_resolve_by_every_token_form() -> None:
    reg = get_registry()
    for token in ("oxigeno", "O", "o", "8", "element-008-o-oxigeno", "o1", "oxygen", "vultur"):
        el = reg.resolve(token)
        assert el is not None and el.symbol == "O", token


def test_resolve_unknown_or_blank_is_none() -> None:
    reg = get_registry()
    assert reg.resolve("119") is None
    assert reg.resolve("nonsense") is None
    assert reg.resolve(None) is None
    assert reg.resolve("") is None


def test_oganesson_is_reserved_not_active() -> None:
    og = get_registry().resolve("og")
    assert og is not None and og.atomic_number == 118 and og.status == "reserved"


def _write(tmp_path, elements, cap=CAP):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"version": 1, "cap": cap, "elements": elements}), encoding="utf-8")
    return p


def test_rejects_more_than_118() -> None:
    bad = [{"atomicNumber": i, "symbol": f"X{i}", "slug": f"x{i}", "displayName": f"X{i}", "status": "empty"} for i in range(1, 120)]
    # 119 entries — over the hard cap
    import tempfile, pathlib
    d = pathlib.Path(tempfile.mkdtemp())
    p = _write(d, bad)
    with pytest.raises(ElementsRegistryError, match="cap is HARD|more than"):
        ElementsRegistry.load(p)


def test_rejects_atomic_number_out_of_range(tmp_path) -> None:
    p = _write(tmp_path, [{"atomicNumber": 119, "symbol": "Zz", "slug": "zz", "displayName": "Zz", "status": "empty"}])
    with pytest.raises(ElementsRegistryError, match="outside"):
        ElementsRegistry.load(p)


def test_rejects_duplicate_atomic_number(tmp_path) -> None:
    p = _write(tmp_path, [
        {"atomicNumber": 1, "symbol": "H", "slug": "h", "displayName": "H", "status": "empty"},
        {"atomicNumber": 1, "symbol": "He", "slug": "he", "displayName": "He", "status": "empty"},
    ])
    with pytest.raises(ElementsRegistryError, match="duplicate atomicNumber"):
        ElementsRegistry.load(p)


def test_active_element_without_persona_file_fails(tmp_path) -> None:
    p = _write(tmp_path, [{
        "atomicNumber": 8, "symbol": "O", "slug": "oxigeno", "displayName": "Oxígeno",
        "status": "active", "backingBotId": "vultur-bot", "personaPromptPath": "personas/missing.md",
    }])
    with pytest.raises(ElementsRegistryError, match="persona file missing"):
        ElementsRegistry.load(p)
