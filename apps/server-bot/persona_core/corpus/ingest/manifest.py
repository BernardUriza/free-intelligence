"""`manifest.yml`: every source of a persona's corpus, with its provenance.

The files are not versioned (licences, size); the manifest and the lock are. The
lock pins each file's sha256, so what was ingested can be proven later.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath

import yaml

MANIFEST_NAME = "manifest.yml"
LOCK_NAME = "manifest.lock.json"
SUPPORTED_SUFFIXES = {".pdf", ".xml", ".txt", ".md"}
_OWN_FILES = {MANIFEST_NAME, LOCK_NAME, "MANIFEST.md"}
_LICENSE = re.compile(r"[A-Za-z0-9][A-Za-z0-9.+-]*")


class ManifestError(ValueError):
    """The manifest, the lock and the folder do not agree; `problems` lists why."""

    def __init__(self, problems: list[str]):
        self.problems = problems
        super().__init__("\n".join(problems))


@dataclass(frozen=True)
class Source:
    """One declared source. `held` ids live in the store with no local file and are never touched."""

    title: str
    author: str
    year: str
    url: str
    license: str
    retrieved_at: date
    files: tuple[str, ...] = ()
    held: tuple[str, ...] = ()
    why: str = ""
    derived_from: str = ""
    license_note: str = ""


@dataclass(frozen=True)
class Manifest:
    persona_id: str
    title: str
    folder: Path
    sources: tuple[Source, ...]
    notes: str = ""

    def files(self) -> dict[str, Source]:
        """Every file on disk, by its path inside the folder, with the source that declares it."""
        owners: dict[str, Source] = {}
        for path in files_on_disk(self.folder):
            for source in self.sources:
                if any(PurePosixPath(path).full_match(pattern) for pattern in source.files):
                    owners.setdefault(path, source)
        return owners

    @property
    def held_ids(self) -> set[str]:
        return {i for s in self.sources for i in s.held}


def files_on_disk(folder: Path) -> list[str]:
    """The ingestable paths under `folder`: no hidden file, manifest or lock."""
    paths = (p.relative_to(folder) for p in folder.rglob("*") if p.is_file())
    return sorted(
        p.as_posix() for p in paths if p.name not in _OWN_FILES and not any(part.startswith(".") for part in p.parts)
    )


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def document_id(persona_id: str, path: str) -> str:
    """`<persona_id>:<slug>`; a folder keeps its whole name so `v1.2/` and `v1.3/` never collide."""
    rel = PurePosixPath(path)
    parts = [*rel.parts[:-1], rel.stem]
    return f"{persona_id}:" + "-".join(re.sub(r"[ _.]", "-", part.lower()) for part in parts)


def read_manifest(folder: Path, persona_id: str) -> Manifest:
    """The declared sources, without looking at the files."""
    raw = yaml.safe_load((folder / MANIFEST_NAME).read_text(encoding="utf-8"))
    problems, sources = [], []
    for i, entry in enumerate(raw["sources"]):
        entry = {**entry, "files": tuple(entry.get("files", ())), "held": tuple(entry.get("held", ()))}
        try:
            source = Source(**{**entry, "year": str(entry.get("year", ""))})
        except TypeError as e:
            problems.append(f"source {i + 1}: {e}")
            continue
        problems += [f"{source.title!r}: {p}" for p in _source_problems(source)]
        sources.append(source)
    if problems:
        raise ManifestError(problems)
    return Manifest(persona_id, raw["title"], folder, tuple(sources), raw.get("notes", ""))


def _source_problems(source: Source) -> list[str]:
    problems = [f"`{f}` is empty" for f in ("title", "author", "year", "url") if not str(getattr(source, f)).strip()]
    if not _LICENSE.fullmatch(source.license or ""):
        problems.append(f"license {source.license!r} is not an SPDX id or a LicenseRef-")
    if type(source.retrieved_at) is not date:
        problems.append("`retrieved_at` is not a date")
    if not source.files and not source.held:
        problems.append("declares neither `files` nor `held`")
    return problems


def write_lock(manifest: Manifest) -> int:
    """Pin every declared file's sha256; returns how many."""
    _check_coverage(manifest)
    pins = {path: sha256_of(manifest.folder / path) for path in sorted(manifest.files())}
    (manifest.folder / LOCK_NAME).write_text(json.dumps(pins, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return len(pins)


def load_manifest(folder: Path, persona_id: str) -> tuple[Manifest, dict[str, str]]:
    """The manifest and its lock, once both agree with the files on disk."""
    manifest = read_manifest(folder, persona_id)
    _check_coverage(manifest)
    lock: dict[str, str] = json.loads((folder / LOCK_NAME).read_text(encoding="utf-8"))
    files = manifest.files()
    problems = [f"{p}: in the lock but not on this machine" for p in sorted(set(lock) - set(files))]
    problems += [f"{p}: not in the lock" for p in sorted(set(files) - set(lock))]
    problems += [
        f"{p}: changed since it was locked" for p in sorted(set(files) & set(lock)) if sha256_of(folder / p) != lock[p]
    ]
    if problems:
        raise ManifestError(problems)
    return manifest, lock


def _check_coverage(manifest: Manifest) -> None:
    on_disk, owners = files_on_disk(manifest.folder), manifest.files()
    problems = [f"{p}: no source declares it" for p in on_disk if p not in owners]
    problems += [
        f"{p}: unsupported file type" for p in on_disk if PurePosixPath(p).suffix.lower() not in SUPPORTED_SUFFIXES
    ]
    for source in manifest.sources:
        for pattern in source.files:
            if not any(PurePosixPath(p).full_match(pattern) for p in on_disk):
                problems.append(f"{source.title!r}: no file matches {pattern!r}")
    for path in on_disk:
        declaring = [s.title for s in manifest.sources if any(PurePosixPath(path).full_match(f) for f in s.files)]
        if len(declaring) > 1:
            problems.append(f"{path}: declared by {declaring}")
    ids: dict[str, str] = {}
    for path in owners:
        if (other := ids.setdefault(document_id(manifest.persona_id, path), path)) != path:
            problems.append(f"{path}: same document id as {other}")
    problems += [f"{i}: held and also a local file" for i in sorted(manifest.held_ids & set(ids))]
    if problems:
        raise ManifestError(problems)


def render_markdown(manifest: Manifest) -> str:
    """MANIFEST.md's table, generated so it cannot drift from `manifest.yml`."""
    rows = [
        "| " + " | ".join(str(c).replace("|", "\\|") for c in cells) + " |"
        for cells in (
            (
                f"{s.title} — **por qué:** {s.why}" if s.why else s.title,
                s.author,
                s.year,
                s.url + (f" · derivado de {s.derived_from}" if s.derived_from else ""),
                s.license + (f" ({s.license_note})" if s.license_note else ""),
                s.retrieved_at.isoformat(),
                ", ".join([*s.files, *(f"{h} (sólo en la tienda)" for h in s.held)]),
            )
            for s in manifest.sources
        )
    ]
    return "\n".join(
        [
            f"# {manifest.title}",
            "",
            f"Generado desde `{MANIFEST_NAME}` con `python scripts/corpus_sync.py lock --persona {manifest.persona_id}`.",
            "Los archivos no se versionan; su sha256 sí, en el lock.",
            "",
            "| Título | Autor | Año | Origen | Licencia | Obtenido | Archivos |",
            "|---|---|---|---|---|---|---|",
            *rows,
            "",
            *([manifest.notes.strip(), ""] if manifest.notes.strip() else []),
        ]
    )
