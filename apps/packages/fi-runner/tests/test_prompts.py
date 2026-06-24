"""Tests for the canonical prompt loader (prompts-as-content-not-code P0)."""

from __future__ import annotations

import os
import time

import pytest

from fi_runner import load_prompt


def test_loads_file_text_stripped(tmp_path) -> None:
    f = tmp_path / "persona.md"
    f.write_text("You are a test companion.\n\n", encoding="utf-8")
    assert load_prompt(f) == "You are a test companion."


def test_hot_reload_on_mtime_change(tmp_path) -> None:
    f = tmp_path / "persona.md"
    f.write_text("first", encoding="utf-8")
    assert load_prompt(f) == "first"

    f.write_text("second", encoding="utf-8")
    os.utime(f, (time.time() + 2, time.time() + 2))
    assert load_prompt(f) == "second"


def test_missing_file_is_hard_error(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        load_prompt(tmp_path / "nope.md")
