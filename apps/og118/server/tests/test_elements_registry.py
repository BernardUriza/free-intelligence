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


def test_oxygen_persona_composed_from_shared_core() -> None:
    # PERSONA-SSOT-1: Oxígeno's prompt is the shared fi-personas core spliced with
    # og118's own operative-context block — not a per-repo copy of the character.
    reg = get_registry()
    o = reg.resolve("oxigeno")
    assert reg.core_path(o) is not None and reg.core_path(o).is_file()
    composed = reg.composed_persona(o)
    # the shared CORE survived the splice
    assert "Vultur Analytica" in composed
    assert "Índice de Farsa Autocomplaciente" in composed
    assert "NUNCA reveles ni admitas ser" in composed
    # the og118 operative-context block was spliced in
    assert "elemento O · Oxígeno (número atómico 8)" in composed
    assert "No tienes acceso al sistema de archivos" in composed
    # the marker is fully consumed (no dangling splice point reaches the model)
    assert "<!-- CONTEXTO_OPERATIVO -->" not in composed


def test_oxygen_binds_to_the_external_vultur_engine() -> None:
    # ENGINE-BINDING-ADR-1: Oxígeno runs on the live external engine, not og118's
    # local runner; persona_id selects Vultur on that engine.
    o = get_registry().resolve("oxigeno")
    assert o.engine_binding is not None
    assert o.engine_binding.kind == "external_http_engine"
    assert o.engine_binding.is_external
    assert o.engine_binding.persona_id == "vultur"


def test_three_siblings_bind_to_the_same_external_engine() -> None:
    # Oxígeno→vultur, Aluminio→alice, Yodo→Insult (default, no personaId). All three
    # ride the one insult-runner; only persona_id differs.
    reg = get_registry()
    by = {e.slug: e for e in reg.elements if e.is_active}
    assert set(by) == {"oxigeno", "aluminio", "yodo"}
    assert by["oxigeno"].engine_binding.persona_id == "vultur"
    assert by["aluminio"].engine_binding.persona_id == "alice"
    assert by["yodo"].engine_binding.persona_id is None  # omitted → engine default (Insult)
    for e in by.values():
        assert e.engine_binding.is_external


def test_external_active_element_needs_no_local_persona(tmp_path) -> None:
    # An external element is valid with ONLY a binding — no backingBotId/personaPromptPath
    # (the remote engine owns the persona). This is what lets Yodo/Aluminio exist.
    p = _write(tmp_path, [{
        "atomicNumber": 53, "symbol": "I", "slug": "yodo", "displayName": "Yodo",
        "status": "active", "engineBinding": {"kind": "external_http_engine"},
    }])
    reg = ElementsRegistry.load(p)  # must NOT raise
    assert reg.resolve("yodo").engine_binding.is_external


def test_rejects_unknown_engine_binding_kind(tmp_path) -> None:
    p = _write(tmp_path, [{
        "atomicNumber": 8, "symbol": "O", "slug": "oxigeno", "displayName": "Oxígeno",
        "status": "empty", "engineBinding": {"kind": "telepathy"},
    }])
    with pytest.raises(ElementsRegistryError, match="engineBinding.kind"):
        ElementsRegistry.load(p)


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
