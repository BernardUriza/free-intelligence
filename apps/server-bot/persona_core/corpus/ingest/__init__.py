"""Declarative corpus ingest: a manifest says what a persona's corpus holds, `sync` makes it so.

- ``manifest``: `manifest.yml` + `manifest.lock.json`, validated against the folder.
- ``extract``: a source file to clean text.
- ``documents``: text to chunks that fit the embedder's window.
- ``plan``: what to add, replace and delete, and the reasons to refuse.
- ``apply``: embed and write it in one transaction.
"""
