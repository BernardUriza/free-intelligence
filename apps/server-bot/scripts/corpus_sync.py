"""Make a persona's corpus match its manifest: add, replace and delete whole documents.

    python scripts/corpus_sync.py lock  --persona frugivoro   # pin the files' sha256, write MANIFEST.md
    python scripts/corpus_sync.py plan  --persona frugivoro   # what would change; exit 1 if refused
    python scripts/corpus_sync.py apply --persona frugivoro   # change it, in one transaction

`--max-deletes N` accepts N deletions over the limit in rules.yml; `--namespace X`
aims at a shadow namespace. Needs POSTGRES_URL except for `lock`. Run
`corpus_eval.py --check` after an `apply`.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from persona_core.corpus.ingest import apply as ingest_apply  # noqa: E402
from persona_core.corpus.ingest.documents import build_document  # noqa: E402
from persona_core.corpus.ingest.manifest import (  # noqa: E402
    ManifestError,
    load_manifest,
    read_manifest,
    render_markdown,
    write_lock,
)
from persona_core.corpus.ingest.plan import SyncPlan, compute_plan, describe  # noqa: E402
from persona_core.corpus.pg_rag import embedding_model, encode, get_corpus_embedder  # noqa: E402
from persona_core.corpus.rules import load_rules  # noqa: E402
from shared.personas.registry import PERSONAS  # noqa: E402

CORPUS_ROOT = ROOT / "data" / "corpus"


def lock(persona_id: str) -> int:
    manifest = read_manifest(CORPUS_ROOT / persona_id, persona_id)
    pinned = write_lock(manifest)
    (manifest.folder / "MANIFEST.md").write_text(render_markdown(manifest), encoding="utf-8")
    print(f"{persona_id}: {pinned} files pinned")
    return 0


async def build_plan(persona_id: str, namespace: str, store, max_deletes: int | None) -> SyncPlan:
    manifest, pins = load_manifest(CORPUS_ROOT / persona_id, persona_id)
    rules = load_rules().ingest
    model = await embedding_model()
    embedder = get_corpus_embedder()

    def count_tokens(text: str) -> int:
        return embedder.count_tokens(embedder.passage_prefix + text)

    documents = [
        build_document(manifest, path, source, pins[path], rules, count_tokens, model)
        for path, source in manifest.files().items()
    ]
    return compute_plan(
        documents,
        await ingest_apply.stored_documents(store, namespace),
        held_ids=manifest.held_ids,
        max_delete_ratio=rules.max_delete_ratio,
        max_deletes=max_deletes,
    )


async def sync(args: argparse.Namespace, namespace: str, dsn: str) -> int:
    store = ingest_apply.corpus_store(dsn)
    try:
        if args.command == "apply":
            await store.init_schema()
        plan = await build_plan(args.persona, namespace, store, args.max_deletes)
        print(f"{args.persona} → {namespace}\n{describe(plan)}")
        if plan.refusals:
            return 1
        if args.command == "plan" or plan.empty:
            return 0
        result = await ingest_apply.apply_plan(
            store,
            namespace,
            plan,
            embed=lambda text: encode(text, role="passage"),
            progress=lambda done, total: print(f"  embedded {done}/{total}", flush=True) if done % 50 == 0 else None,
        )
        print(f"applied: {result.upserted} written, {result.deleted} deleted, {result.chunks} chunks")
        return 0
    finally:
        await store.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("command", choices=("lock", "plan", "apply"))
    parser.add_argument("--persona", required=True, choices=sorted(p for p, d in PERSONAS.items() if d.corpus_namespace))
    parser.add_argument("--namespace", help="a shadow namespace instead of the persona's")
    parser.add_argument("--max-deletes", type=int)
    args = parser.parse_args()
    try:
        if args.command == "lock":
            return lock(args.persona)
        dsn = os.environ.get("POSTGRES_URL")
        if not dsn:
            parser.error("POSTGRES_URL is not set")
        return asyncio.run(sync(args, args.namespace or PERSONAS[args.persona].corpus_namespace, dsn))
    except ManifestError as e:
        print("\n".join(f"REFUSED: {p}" for p in e.problems), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
