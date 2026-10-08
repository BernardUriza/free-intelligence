# Artifact Delivery Rules

How to hand files to the user. Bernard comes from Windows, finds Finder
painful, and frequently needs to SHARE or UPLOAD generated artifacts
(ADRs, reports, exports) — often into a file picker like ChatGPT's upload
dialog.

## Never bury a user-facing artifact in a hidden folder

Dot-folders (`.claude/`, `.github/`, anything starting with `.`) are
**invisible to Finder and to every file picker** (ChatGPT upload, "attach
file", Open dialogs). If you write a document the user will need to open,
share, or upload, do NOT leave it ONLY in a hidden folder.

- Keep the **canonical project copy** where convention dictates
  (e.g. `.claude/plans/` for ADRs) **AND** drop a **shareable copy** in a
  visible location: `~/Desktop/` (best for file pickers) or the repo root.
- Two copies is fine — say which is which, and offer to keep them in sync
  if the user edits the shared one.

## Default to PROACTIVE delivery — don't make Bernard navigate Finder

When you create or reference a file Bernard will need, **hand it to him
directly** instead of telling him a path to go hunt:

- `open <file>` — pops it on screen in the default app.
- `cat <file> | pbcopy` — loads it into the clipboard so he just hits
  Cmd+V wherever he needs it (e.g. pasting an ADR straight into ChatGPT).
- `cp <file> ~/Desktop/` — puts it where a file picker will find it.

The right move when he says "I can't find X" is to run `open`/`pbcopy`/`cp`
for him, not to recite a path. You are his remote control for Finder; he
should not have to memorize macOS shortcuts.

## Why this rule exists

2026-06-06: an ADR (`khimeras_demux_destilado.md`) was written only to
`.claude/plans/`. Bernard couldn't find it in Finder, and ChatGPT's file
picker couldn't see it either — `.claude` is hidden. He was (rightly)
frustrated: "lo pusiste en una carpeta oculta... que estupidez." Coming
from Windows, fighting Finder's hidden folders and ephemeral
`Cmd+Shift+G` address bar is exactly the friction to design away. The fix
was a `~/Desktop/` copy + `pbcopy`. Bake that in: anything meant to leave
the repo gets a visible copy and proactive `open`/`pbcopy` delivery.
