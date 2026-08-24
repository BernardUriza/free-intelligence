"""AireCorpusClient — the project corpus, served by AIRE instead of a local file.

A drop-in peer of :class:`fi_runner.rag_store.RagStoreClient`: same method names,
same return shapes, so a consumer swaps it in at its dependency seam and every call
site stays untouched. That sameness is the point — the two differ only in WHERE the
documents live, and a consumer choosing between them should not have to care about
anything else.

Why it exists (2026-08-24): AIRE's `rag_store` tool let the MODEL search a corpus in
AIRE's Postgres, but a consumer's upload endpoint is server code and had nothing to
call, so it kept writing to a local store nothing on that route read. The corpus the
agent searched was always empty, and og118 answered a user that their working upload
had failed. Half a data path is worse than none — see aire-server backlog #47, which
is the door this speaks to.

The scoping is AIRE's: the door derives the shelf from the casita's `@base`, so the
`project` this client addresses is the consumer's BASE casita, and `corpus_id` names
one project inside it. Nothing about which shelf is reachable crosses this wire.

Retrieval is Postgres full-text — it matches on WORDS, not on meaning. `similarity`
in a search hit therefore carries `ts_rank`, which orders results honestly but is not
a cosine distance and must not be rendered as a percentage of anything.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class AireCorpusError(RuntimeError):
    """The corpus door refused or was unreachable. Raised rather than swallowed:
    a consumer that answers as if the documents were consulted, when they were
    not, is the exact failure this module was built to end."""


class AireCorpusClient:
    """The corpus surface, over AIRE's HTTP door."""

    def __init__(self, project: str | None = None, *, gate_url: str | None = None,
                 auth_token: str | None = None, timeout: float = 30.0) -> None:
        self.project = project or os.environ.get("OG118_AIRE_PROJECT", "og118")
        self.gate_url = (gate_url or os.environ.get("AIRE_GATE_URL", "")).rstrip("/")
        self.auth_token = (auth_token or os.environ.get("AIRE_AUTH_TOKEN", "")
                           or os.environ.get("AIRE_CANARY_TOKEN", ""))
        self.timeout = timeout
        self._client: Any = None

    def _http(self) -> Any:
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _url(self, corpus_id: str, *parts: str) -> str:
        """The door's URL for this corpus. `parts` extend past `/documents`; with
        none, it is the collection itself."""
        tail = "/".join(("documents", *parts))
        return f"{self.gate_url}/projects/{self.project}/corpus/{corpus_id}/{tail}"

    async def _call(self, method: str, url: str, **kwargs: Any) -> Any:
        if not self.gate_url or not self.auth_token:
            raise AireCorpusError("AIRE corpus door not configured (AIRE_GATE_URL / AIRE_AUTH_TOKEN)")
        res = await self._http().request(
            method, url, headers={"Authorization": f"Bearer {self.auth_token}"}, **kwargs)
        if res.status_code >= 400:
            raise AireCorpusError(f"AIRE corpus {res.status_code}: {res.text[:200]}")
        return res.json()

    async def ingest(self, corpus_id: str, doc_id: str, text: str, **_kwargs: Any) -> int:
        """Store a document, replacing any earlier version under the same `doc_id`.
        Returns the chunk count, so a caller can still refuse a document that
        indexed to nothing. Extra keyword arguments (fi-core's `min_chunk_size`
        and friends) are accepted and ignored: the chunking is AIRE's."""
        out = await self._call("POST", self._url(corpus_id),
                               json={"doc_id": doc_id, "text": text})
        return int(out.get("chunks", 0))

    async def ingest_text_file(self, corpus_id: str, path: str | Path, *,
                               doc_id: str | None = None, **kwargs: Any) -> int:
        p = Path(path)
        return await self.ingest(corpus_id, doc_id or p.name, p.read_text(encoding="utf-8"), **kwargs)

    async def search(self, corpus_id: str, query: str, *, top_k: int = 5,
                     filters: dict | None = None) -> list[dict]:
        """Hits as `{"text", "similarity", "doc_id"}`. `filters` has no counterpart
        on this door and is REFUSED rather than dropped: silently returning
        unfiltered results is how a caller ends up trusting a narrowing that never
        happened."""
        if filters:
            raise AireCorpusError("the AIRE corpus door takes no filters")
        hits = await self._call("GET", self._url(corpus_id, "search"),
                                params={"q": query, "top_k": top_k})
        return [{"text": h["text"], "similarity": h["score"], "doc_id": h["doc_id"]} for h in hits]

    async def list_documents(self, corpus_id: str) -> list[dict]:
        out = await self._call("GET", self._url(corpus_id))
        return [{"doc_id": d["doc_id"], "chunk_count": d["chunks"],
                 "status": "indexed", "attributes": {}} for d in out["documents"]]

    async def delete_document(self, corpus_id: str, doc_id: str) -> bool:
        out = await self._call("DELETE", self._url(corpus_id, doc_id))
        return int(out.get("chunks_removed", 0)) > 0

    async def delete_corpus(self, corpus_id: str) -> int:
        url = f"{self.gate_url}/projects/{self.project}/corpus/{corpus_id}"
        return int((await self._call("DELETE", url)).get("chunks_removed", 0))

    async def stats(self, corpus_id: str) -> dict:
        cap = (await self._call("GET", self._url(corpus_id)))["capacity"]
        return {"n_docs": cap["docs"], "n_chunks": cap["chunks"], "bytes": cap["bytes"]}

    def quota(self) -> dict:
        """No per-corpus ceiling on this door. `None` means UNLIMITED and a consumer
        must render it as "no cap" — never as a percentage of an invented number.
        What DOES bound the corpus is `AIRE_DB_CEILING_MB`, which alarms on the
        database as a whole rather than refusing one project's upload."""
        return {"max_docs": None, "max_bytes": None}

    async def aclose(self) -> None:
        if self._client is not None:
            try:
                await self._client.aclose()
            finally:
                self._client = None
