"""`[GIF: tag]` — a persona posts a GIF from its OWN curated catalog.

Discord's GIF picker does not attach anything: it pastes a plain URL into the
message and the client unfurls it (verified 2026-07-23 against Bernard's own
stored messages, and by posting as the bot over REST — both a `tenor.com/view/…`
and a `media.giphy.com/…` URL rendered as GIFs).

So POSTING is trivial. FINDING is the hard part, and it is why this is a catalog
instead of an API call:

- Google shut the Tenor API down on 2026-06-30 and stopped issuing keys in
  January, so the obvious route is simply gone. (`tenor.com/view/…` URLs still
  render — the unfurl scrapes the site, which survived the API.)
- A live provider (Giphy's free tier is 100 req/hour, Klipy is what Discord's
  picker now serves) would work, but hands tone control to a search engine.
- **A model cannot invent these URLs.** The id is an opaque number; asked for
  "a party GIF" it would hallucinate one and post a dead link.

The catalog closes all three: the model emits an INTENT (`[GIF: fiesta]`), never
a URL, and a tag with no entry posts NOTHING. A persona's repertoire is content
in its own voice — `shared/personas/guidance/<persona_id>/gifs.md`, hot-editable
with no redeploy — so Vultur and Frugívoro can share a marker and not a taste.

Catalog lives at `shared/personas/guidance/<persona_id>/gifs/catalog.md`, one
entry per line (`#` comments and blanks ignored):

    fiesta: https://tenor.com/view/dance-maracas-...-gif-8136857277085094799
    nope:   https://media.giphy.com/media/1TOSaJsWtnhe0/giphy.gif
"""

from __future__ import annotations

import re

import structlog

from persona_core.behavior.content import load_guidance

log = structlog.get_logger()

GIF_PATTERN = re.compile(r"\[GIF:\s*([^\]]*)\]", re.IGNORECASE)

# shared/personas/guidance/<persona_id>/gifs/catalog.md — same shape as presets/,
# so the loader, the mtime hot-reload and the "no content = no feature" default
# all come for free.
GIF_CATALOG_KIND = "gifs"
GIF_CATALOG_NAME = "catalog"

# One GIF per turn. The marker is a punchline, not a mood board — and a persona
# that carpet-bombs the channel is the failure mode this cap exists for.
MAX_GIFS_PER_TURN = 1

# Only what Discord actually unfurls as a GIF today. An arbitrary URL from the
# model would be a link-injection surface, so the catalog is allowlisted too.
_ALLOWED_HOSTS = ("tenor.com", "media.giphy.com", "i.giphy.com", "static.klipy.com", "media.klipy.com")


def parse_gif_tags(response: str) -> list[str]:
    """Tags requested by `[GIF: …]` markers, lowercased, in order, deduped."""
    tags: list[str] = []
    for raw in GIF_PATTERN.findall(response or ""):
        tag = raw.strip().lower()
        if tag and tag not in tags:
            tags.append(tag)
    return tags[:MAX_GIFS_PER_TURN]


def strip_gif_markers(response: str) -> str:
    """Remove `[GIF: …]` markers from the text the user sees."""
    return GIF_PATTERN.sub("", response or "").strip()


def load_catalog(persona_id: str) -> dict[str, str]:
    """This persona's `tag → url` catalog, or {} when it has none.

    Malformed lines and non-allowlisted hosts are skipped loudly rather than
    shipped — a broken entry must never become a dead link in the channel.
    """
    raw = load_guidance(persona_id, GIF_CATALOG_KIND, GIF_CATALOG_NAME)
    catalog: dict[str, str] = {}
    for line in (raw or "").splitlines():
        entry = line.strip()
        if not entry or entry.startswith("#"):
            continue
        tag, _, url = entry.partition(":")
        tag, url = tag.strip().lower(), url.strip()
        if not tag or not url.startswith("https://"):
            log.warning("gif_catalog_bad_line", persona_id=persona_id, line=entry[:80])
            continue
        if not any(host in url for host in _ALLOWED_HOSTS):
            log.warning("gif_catalog_host_rejected", persona_id=persona_id, url=url[:80])
            continue
        catalog[tag] = url
    return catalog


def resolve_gifs(persona_id: str, response: str) -> list[str]:
    """URLs to post for this reply — [] when the persona asked for a tag it does
    not have. A miss is silence, never a broken link."""
    tags = parse_gif_tags(response)
    if not tags:
        return []
    catalog = load_catalog(persona_id)
    urls: list[str] = []
    for tag in tags:
        url = catalog.get(tag)
        if url:
            urls.append(url)
        else:
            log.info("gif_tag_unknown", persona_id=persona_id, tag=tag, known=len(catalog))
    return urls


def catalog_block(persona_id: str) -> str | None:
    """The available tags, for the turn's guidance — a persona cannot use a
    repertoire it was never shown, and an unlisted tag posts nothing."""
    catalog = load_catalog(persona_id)
    if not catalog:
        return None
    tags = ", ".join(sorted(catalog))
    return (
        "GIFs disponibles. Para mandar uno, emite [GIF: tag] en cualquier parte de tu "
        "respuesta — el marcador NO se ve, se convierte en el GIF. Solo estos tags "
        f"existen; cualquier otro no manda nada:\n{tags}\n"
        "Úsalo cuando el GIF diga algo que tus palabras no; nunca por rellenar."
    )


__all__ = [
    "GIF_CATALOG_KIND",
    "GIF_CATALOG_NAME",
    "GIF_PATTERN",
    "MAX_GIFS_PER_TURN",
    "catalog_block",
    "load_catalog",
    "parse_gif_tags",
    "resolve_gifs",
    "strip_gif_markers",
]
