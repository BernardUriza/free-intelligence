"""fi_runner.packs re-exports fi-core's persona packs, so a thin consumer never
imports fi-core directly. These tests pin: the re-export works, each symbol is
the SAME object as fi-core's, and no public pack is missing (parity, no drift).
"""

from __future__ import annotations

import inspect

import fi_core.persona.packs as fc_packs

from fi_runner import packs


def _public_pack_names(mod) -> set[str]:  # noqa: ANN001
    """Public names that are actual packs — exclude dunders, imported modules
    (e.g. ``re``), and the ``from __future__`` ``annotations`` feature."""
    names: set[str] = set()
    for n in dir(mod):
        if n.startswith("_") or n == "annotations":
            continue
        if inspect.ismodule(getattr(mod, n)):
            continue
        names.add(n)
    return names


def test_import_from_fi_runner_works():
    # The acceptance-criteria smoke: the three named packs resolve via fi-runner.
    assert packs.MARKDOWN_DRIFT and packs.DEFAULT_BILINGUAL and packs.GENERIC_REINFORCEMENT


def test_every_fi_core_pack_is_reexported_and_identical():
    for name in _public_pack_names(fc_packs):
        assert hasattr(packs, name), f"fi_runner.packs is missing {name!r}"
        assert getattr(packs, name) is getattr(fc_packs, name), f"{name!r} is not the same object"


def test_all_has_exact_parity_with_fi_core_no_drift():
    # If fi-core adds/removes a public pack, this fails so the re-export stays honest.
    assert set(packs.__all__) == _public_pack_names(fc_packs)


def test_no_private_or_module_leaked_into_all():
    for name in packs.__all__:
        assert not name.startswith("_")
        assert not inspect.ismodule(getattr(packs, name))
