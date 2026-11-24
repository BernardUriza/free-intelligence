"""A source file to clean text. Extraction that loses content raises; nothing is skipped."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

_UNSAFE_CATEGORIES = {"Cf", "Co", "Cs"}


class ExtractError(RuntimeError):
    """A source could not be read whole."""


def strip_invisible(text: str) -> str:
    """NFC text without format, private-use or control characters (zero-width, bidi, tag blocks).

    They carry no meaning for a reader and can carry instructions for a model.
    """
    out = []
    for ch in unicodedata.normalize("NFC", text):
        category = unicodedata.category(ch)
        if ch in "\n\t" or category not in {*_UNSAFE_CATEGORIES, "Cc"}:
            out.append(ch)
        elif category == "Cc":
            out.append(" ")
    return "".join(out)


def _pdf_text(path: Path) -> str:
    from pypdf import PdfReader

    pages = []
    for number, page in enumerate(PdfReader(str(path)).pages, start=1):
        try:
            pages.append((page.extract_text() or "").strip())
        except Exception as e:
            raise ExtractError(f"{path.name}: page {number} could not be read ({type(e).__name__})") from e
    return "\n\n".join(p for p in pages if p)


def _xml_text(path: Path) -> str:
    from defusedxml import DefusedXmlException, ElementTree

    try:
        root = ElementTree.parse(str(path)).getroot()
    except (ElementTree.ParseError, DefusedXmlException) as e:
        raise ExtractError(f"{path.name}: XML does not parse ({e})") from e
    text = " ".join(t.strip() for t in root.itertext() if t and t.strip())
    return re.sub(r"[ \t]{2,}", " ", text).strip()


def extract_text(path: Path) -> str:
    """The clean text of a `.pdf`, `.xml` (JATS), `.txt` or `.md` source."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        raw = _pdf_text(path)
    elif suffix == ".xml":
        raw = _xml_text(path)
    else:
        raw = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return strip_invisible(raw).strip()
