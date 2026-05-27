# Contributing to fi-core

`fi-core` is the shared primitives library for the Free Intelligence ecosystem. RAG chunking, embedders, document stores, persona / anti-drift, training pipes, long-term memory, clinical cognitive primitives — all of it lives here, behind optional-dependency extras so the bare install pulls zero external libs.

Consumers (`fi-runner`-based agents, MCP servers, downstream apps) DEPEND on `fi-core`. fi-core does NOT depend back on them.

---

## Dev setup

```bash
cd apps/packages/fi-core
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

`[dev]` pulls every extra. For a leaner setup install only the extras you're working on (`pip install -e ".[rag,stores-hdf5]"` etc.).

---

## Where the code lives

```
fi_core/
├── __init__.py            # __version__ only; submodules load on demand
├── rag/                   # chunking + Embedder / ChunkStore protocols (dep-free)
├── stores/
│   ├── hdf5.py            # HDF5 reference store (extras: stores-hdf5)
│   └── pgvector.py        # Postgres + pgvector store (extras: stores-pgvector)
├── embeddings/
│   ├── azure_openai.py    # Azure OpenAI embedder (extras: embeddings-azure)
│   └── sentence_transformers.py  # local ST embedder (extras: embeddings-st)
├── persona/               # anti-drift detectors + pattern packs (dep-free)
│   └── mcp_server.py      # MCP exposing detectors (extras: mcp)
├── cognitive/             # clinical primitives: urgency, SOAP, FSM, presets
│   ├── urgency.py         # gravity scoring + negation handling
│   ├── domains.py         # PSYCHIATRY + CARDIOLOGY vocabularies
│   ├── state_machine.py
│   ├── soap.py
│   ├── events.py          # Redux→domain-event mapping
│   ├── extraction.py
│   └── mcp_server.py      # MCP server (extras: mcp)
├── task_tracker/          # agent plan-tracking; v2 11-tool MCP surface
│   ├── tracker.py         # core TaskTracker (dep-free)
│   └── mcp_server.py      # MCP tools (extras: mcp)
├── memory/                # long-term fact memory (extras: memory)
└── training/              # TinyGPT + PyTorchTrainer (extras: training)
```

Every sub-package follows the same shape: dep-free primitives at the root, heavy SDK calls behind an optional extra.

---

## The zero-dep core rule

`pip install fi-core` (no extras) must NEVER pull anything beyond stdlib. Specifically:

- `import fi_core` MUST work without h5py, torch, openai, asyncpg, pgvector, etc.
- `import fi_core.rag` MUST work without an embedder backend; only the Protocols.
- Concrete implementations (`HDF5ChunkStore`, `AzureOpenAIEmbedder`, etc.) MUST live in modules that ONLY get imported under their extra (`fi_core.stores.hdf5` requires `[stores-hdf5]`).

If you find yourself adding `import torch` to `fi_core/rag/__init__.py`, STOP. The library must remain consumable as a tiny protocols-only install.

---

## Adding a new extra

1. Add a sub-package under `fi_core/` with the implementation. Import its SDK dep INSIDE functions or at module top-level (the latter only if the entire submodule requires the dep).
2. Declare the extra in `pyproject.toml`:
   ```toml
   [project.optional-dependencies]
   my-extra = ["my-sdk>=1.0"]
   ```
3. Update `__init__.py` docstring + `README.md` "extras matrix" with one-liner.
4. Add a test under `tests/test_<extra>.py` that imports the extra-gated module + smokes it.
5. Update the `all` and `dev` extras to include the new SDK.

---

## PR conventions

- **Conventional Commits**: `feat:`, `fix:`, `refactor:`, `chore:`, `docs:`, `test:`.
- **One concern per PR**: never mix packaging + logic; never combine extras additions with implementation refactors of a different submodule.
- **Tests required** for new public surface (Protocol additions, new factories).
- **Type-clean**: `mypy` / `pyright` should pass; `py.typed` ships so downstream relies on these types.
- **English** in docs and comments.

---

## Release process

See [`RELEASE.md`](RELEASE.md). Releases are tag-driven (`fi-core-vX.Y.Z`). The Golden Rule: external-user smoke test from a CLEAN conda env BEFORE cutting a tag. If anything fails, fix the package or README BEFORE the release ships.

`fi-runner` PINS `fi-core>=0.24,<0.25` so MINOR bumps to fi-core require a matching fi-runner release; PATCH bumps are absorbed automatically.

---

## License

MIT.
