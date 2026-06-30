"""Backcompat re-export — the canonical prompt loader lives in ``fi_core.prompts``.

Per the playbook P0 ``prompts-as-content-not-code`` there is ONE loader for the
whole fi stack. It lives in fi-core (the lowest, dep-free layer) so fi-core
itself can load its own prompts WITHOUT importing fi-runner — the layer boundary
forbids that upward dependency (``fi_runner`` imports ``fi_core``, never the
reverse). fi-runner keeps ``load_prompt`` importable here so existing consumers
(e.g. og118: ``from fi_runner import load_prompt``) keep working unchanged.
"""

from __future__ import annotations

from fi_core.prompts import load_prompt

__all__ = ["load_prompt"]
