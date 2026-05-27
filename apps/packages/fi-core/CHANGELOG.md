# Changelog

All notable changes to `fi-core` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Policy:
- **PATCH**: backwards-compatible bug fixes; no public-API change.
- **MINOR**: backwards-compatible additions; new protocols, new extra, new MCP tool.
- **MAJOR**: breaking changes to Protocols, function signatures, or removed extras.

Pre-1.0 (`0.x.y`): no backwards-compat shims required. Stability promise applies at 1.0.0.

## [Unreleased]

(Add entries here as work lands on `dev`.)

## [0.24.4] — 2026-05-26

Brought to anaconda.org as part of the platform-engineer release pass after the channel had drifted to **0.9.1** while the source was at 0.24.4 — gap of 15 minor versions across 9 months of internal-only work.

### Added
- Proclítico reflexive forms in `PSYCH_CRITICAL_SYMPTOMS` and `PSYCH_CRITICAL_PATTERNS` (`se quiere matar`, `se quiere ahorcar`, `va a matarse`, `intenta suicidarse`, etc.). Spanish allows splitting the reflexive pronoun from the verb; substring matching now catches both forms.
- `fi_core.cognitive.urgency._strip_negations` — regex pre-pass over the input that removes clauses scoped to a negation cue (`niega`/`descarta`/`no presenta`/`sin (?!embargo)`/`denies`/`rules out`/...). Scope: cue → next sentence terminator OR opposing conjunction (`pero`, `sin embargo`, `mas`, `aunque`). Comma is intentionally NOT a clause break.
- Cross-encoder reranker (`fi-core[rerank]`): BAAI/bge-reranker-v2-m3, Apache-2.0, multilingual.
- Long-term memory primitives (`fi-core[memory]`): `PgMemoryStore` + `FactConsolidator` (Mem0-style retention).
- `task_tracker` v2: 11 MCP tools, DAG step deps, terminal-state immutability, TTL eviction, replanning, cancellation, note-step append, `list_plans`, `PlanGuard` integration in fi-runner.

### Changed
- `PSYCH_CRITICAL_SYMPTOMS` / `PSYCH_CRITICAL_PATTERNS` expanded to include 3rd-person + infinitive crisis markers (`quitarse la vida`, `ahorcarse`, `quiere morir`, `planea suicidarse`, etc.). Closes recall regressions on eval cases t04 (1st→3rd person) and t07 (vocab gap for `ahorcarse`).
- `GENERIC_AI_DISCLOSURE_ES` adds "inteligencia artificial" / "IA" patterns (closes d04 eval trap).
- `OpenAI`/`Anthropic` vendor patterns scoped to identity-claim contexts (`made/created/built/trained by`, `I'm (from) OpenAI`, `OpenAI's assistant`) instead of bare `\bOpenAI\b` (closes d11 false-positive trap).
- `mcp>=1.27,<2` pin (RFC 8707 OAuth resource validation + StreamableHTTP idle timeout).
- `fi_core.task_tracker.mcp_server._TRACKER` alias replaced with module-level `__getattr__` (PEP 562) delegating to the live `_registry._TRACKER`. Eliminates the stale-at-import-time reference.
- `_TTLStore.values()/.items()` return `list(...)` snapshots instead of dict views (defensive against future async-lock migration).
- `__init__.py` docstring rewritten: more comprehensive sub-package map, install-extras matrix, dropped the "AURITY + Insult" mention (fi-core is contract-generic).

### Eval impact (vs baseline sha 7bc3f1cd, 38 hand-labeled cases)
- Triage F1: 0.769 → **1.000** (+0.231); recall 0.714 → 1.000.
- Antidrift F1: 0.750 → **1.000** (+0.250); multi-class accuracy 0.750 → **1.000**.

## [0.9.1 — 0.24.3]

These intermediate versions were never published to anaconda.org (the channel was stuck at 0.9.1 while `dev` advanced). Highlights of the period:

- `fi_core.rag` end-to-end: `StoreBackedRetriever` + `search_documents` MCP tool.
- `fi_core.persona.mcp_server` standalone: anti-drift detectors callable from any MCP client.
- `fi_core.cognitive` clinical state machine + urgency classifier + SOAP commit gate.
- `fi_core.task_tracker` v1 → v2 rewrite (gaps catalogued in the fi-runner-task-tracker-v2 memory).
- Multiple safety hardening passes (env whitelist, RLock removal, gather logging, conversation_store guards).

For per-commit detail, browse the git history between tags `fi-core-v0.9.1` and `fi-core-v0.24.3` (when they get created) in https://github.com/BernardUriza/free-intelligence/commits/main/apps/packages/fi-core.

## [0.8.0] — 2026-05-22

### Added
- `fi_core.cognitive` — clinical cognitive-flow primitives extracted from the
  Redux-Claude medical flow (zero-dep core; YAML preset loading via the new
  `cognitive` extra):
  - `presets` / `loader` / `types` — 7 medical prompt presets as typed `CognitivePreset`.
  - `state_machine` — the clinical consultation FSM (14 states + transition table).
  - `urgency` — gravity scoring / triage (1-10 score, modifiers, widow-maker override).
  - `extraction` — extraction iteration loop (completeness %, max 5 iterations, focus).
  - `soap` — SOAP progression (section weights, NOM-004 compliance, commit gate).
  - `events` — Redux→domain-event mapping (`EventType`, `ReduxEventAdapter`, audit hash).
- `cognitive` optional extra (`pyyaml`).

### Changed
- AURITY backend now sources its prompt presets from `fi_core.cognitive`
  (single source of truth); the duplicated YAMLs and the legacy `yaml_provider`
  were removed.

## [0.7.0] — 2026-05-19

### Added

- **`fi_core.memory`** — sixth sub-package: long-term, principal-scoped
  atomic-fact memory. Consolidates the production-validated patterns
  from discord-bot's ``insult/core/memory/repositories/facts.py`` (with
  ``user_id`` generalized to ``principal_id``). Sibling of
  ``fi_core.stores``, not extension: a fact is an atomic unit, not a
  chunk of a document, so they share design language without literal
  Protocol inheritance.

- `fi_core.memory.protocols` — runtime-checkable ``MemoryStore``
  Protocol. Five capability clusters: CRUD (``get_facts``,
  ``save_facts``, ``add_fact``), soft-delete + retention
  (``soft_delete_fact``, ``purge_soft_deleted``, ``count_live``),
  search (``semantic_search``), consolidation
  (``apply_consolidation_plan``), and lifecycle (``init_schema``,
  ``close``).

- `fi_core.memory.types` — ``Fact`` dataclass (frozen, slots),
  ``FactSource`` enum (AUTO / MANUAL / AGENT — same three-tier
  provenance that protects manually curated facts from being wiped by
  auto re-extraction), ``ConsolidationOp`` audit row, and
  ``ConsolidationReport`` rollup with ``counts_by_op()``.

- `fi_core.memory.retention` — ``RetentionPolicy`` Protocol +
  three concrete impls. ``Default90d`` ships discord-bot's
  production-tuned 90-day soft-delete window (``SOFT_DELETE_RETENTION_SECONDS``).
  ``FixedWindow`` for custom durations. ``NeverPurge`` for audit-grade
  stores where soft-delete is the terminal state.

- `fi_core.memory.stores.pgvector_memory.PgMemoryStore` — production
  Postgres + pgvector impl extracted from ``FactsRepository``.
  Self-managing asyncpg pool (mirrors ``PgVectorChunkStore`` shape, not
  discord-bot's ``BaseRepository`` + ``ConnectionManager`` separation
  which only makes sense for multi-table facades). Optional injected
  ``Embedder`` for vector-backed semantic search; falls back to
  ordered-by-recency when absent. Same codec-registration-before-pool
  pattern used in ``PgVectorChunkStore`` to avoid the asyncpg "unknown
  type: vector" pitfall. Schema: ``principal_facts`` table +
  ``fact_consolidation_log`` audit table, both with full DDL +
  indexes shipped via ``init_schema()``.

- `fi_core.memory.consolidator.FactConsolidator` — high-level
  Mem0-style orchestrator. Wraps the three primitives that already
  exist (``MemoryStore`` + ``persona.mcp_server.build_consolidation_prompt``
  + ``parse_consolidation_result``). Shape B per
  ``memory:[[mcp-shape-b-canonical]]``: server builds prompt + parser,
  caller's ``llm_call`` callable executes the LLM. Returns
  ``ConsolidationReport`` with ops + counts + duration + error
  capture; never raises. ``dry_run`` synthesizes the audit trail
  without touching the store — useful for offline eval and CLI diff
  surfaces.

### Changed

- `pyproject.toml`: new ``[memory]`` optional extra
  (``asyncpg>=0.30``, ``pgvector>=0.4`` — same deps as
  ``stores-pgvector`` but named separately so the install intent is
  explicit at the caller site). ``[all]`` and ``[dev]`` already pull
  these via ``stores-pgvector``.

- `fi_core/__init__.py`: lists the new ``fi_core.memory`` path.

- `fi_core.memory.types.ConsolidationReport`: dataclass is NOT frozen
  (the orchestrator mutates it across the consolidation lifecycle —
  appending ops, recording errors, finalizing duration). All other
  types in the module remain frozen+slots.

### Honest extraction notes

- **PgMemoryStore is a direct extraction** of discord-bot's
  ``FactsRepository`` (the source file is ~310 LOC; the fi-core impl
  is ~370 LOC after collapsing the ``ConnectionManager`` separation,
  generalizing ``user_id`` to ``principal_id``, accepting an optional
  injected ``Embedder``, and inlining the audit-log writes that
  previously crossed the ``vectors`` module boundary). SQL shape and
  the soft-delete-then-reinsert UPDATE pattern are byte-identical to
  the production schema.
- **FactConsolidator orchestration logic** is the runner half of
  discord-bot's ``memory_consolidator.py`` (cleaned of Discord
  dataclasses + telemetry-routing logic). The Shape B contract with
  ``fi_core.persona.mcp_server`` is preserved unchanged.
- **Retention windows** mirror the production constant
  ``SOFT_DELETE_RETENTION_SECONDS = 90 * 86400``.

### Coverage

- 40 new tests: 6 types + 7 retention + 13 consolidator (in-memory
  mock store) + 14 PgMemoryStore (against ephemeral PG via
  pytest-postgresql).
- Full suite: 205 passing + 3 skipped (CUDA-gated on Mac runner).
  0 regressions vs 0.6.0.

### Narrative

V2 preserved: ``fi_core.memory`` ships consolidation of code that
**already passed the production filter** in two consumers (discord-bot
Insult since v3.6.0; AURITY medical RAG since 2026-Q1). It is not new
design. The same Shape B integration with ``persona.mcp_server`` that
discord-bot already uses in production is what consumers of
``FactConsolidator`` consume here — no behavioral regression, just a
narrower contract surface.

## [0.6.0] — 2026-05-19

### Added

- **`fi_core.training`** — fifth sub-package: training pipes for
  building small LMs on top of what the production stores already
  write. All sub-modules require the new ``[training]`` extra (torch +
  tiktoken + tokenizers). The base ``fi-core`` install still does NOT
  pull these.
- `fi_core.training.protocols` — runtime-checkable Protocols
  ``DatasetReader``, ``Tokenizer``, ``GenerationModel``, ``Trainer``.
  Re-exported from ``fi_core.training`` for direct ``from fi_core.training
  import DatasetReader`` use.
- `fi_core.training.datasets.HDF5DatasetReader` and
  `fi_core.training.datasets.PgVectorDatasetReader` — stream ``Chunk``
  instances out of an ``HDF5ChunkStore`` / ``PgVectorChunkStore``
  respectively. The reader takes a constructed store (not a path or
  DSN) so the caller controls lifecycle.
- `fi_core.training.tokenizers.TiktokenTokenizer` — thin wrapper over
  OpenAI's ``tiktoken`` library. Default encoding ``cl100k_base`` (the
  GPT-4 vocab, 100,277 tokens). Use with the ``tiny_gpt_30m`` preset.
- `fi_core.training.tokenizers.BPETokenizer` — wraps HuggingFace's
  ``tokenizers`` library (fast Rust BPE trainer). Static ``train``
  classmethod for fitting a corpus-specific BPE; ``save`` / ``load``
  for persistence. Default special tokens: ``<pad>``, ``<unk>``,
  ``<bos>``, ``<eos>``. Use with the ``tiny_gpt_5m`` preset.
- `fi_core.training.models.TinyGPT` + ``GPTConfig`` — compact
  decoder-only Transformer (karpathy-style minGPT): pre-LayerNorm
  blocks, tied embedding ↔ unembedding, GELU activations, causal
  self-attention via ``F.scaled_dot_product_attention`` (PyTorch ≥2.0
  picks flash-attention automatically on supported GPUs). ``forward``
  takes optional ``targets`` and returns ``(logits, loss)``.
  ``generate`` does autoregressive sampling with temperature, top-k,
  top-p (nucleus), and repetition penalty — logic adapted from
  Robo-Poet's ``src/legacy/robo-poet-pytorch/src/generation/generate.py``.
  ``configure_optimizers`` returns AdamW with the standard
  decay / nodecay parameter split.
- `fi_core.training.models.presets` — factory functions
  ``tiny_gpt_5m`` (8K vocab, ~5M params) and ``tiny_gpt_30m``
  (cl100k_base, ~30M params). Both use 6 layers × 8 heads × 256
  hidden, 256-token context, dropout 0.1.
- `fi_core.training.trainers.PyTorchTrainer` — config-driven training
  loop. Adapted from Robo-Poet's
  ``src/legacy/robo-poet-pytorch/src/training/train.py``. Changes:
  GPU-only (fails fast with a clear ``RuntimeError`` on no CUDA — no
  CPU or MPS path), config-driven optimizer (``optimizer_cls`` +
  ``optimizer_kwargs``, default falls back to
  ``model.configure_optimizers`` if available), TensorBoard stripped
  in favor of structlog events, ``torch.amp.GradScaler('cuda')`` API.
  Features mixed precision, gradient accumulation, linear warmup →
  cosine decay LR schedule, gradient clipping, best-loss checkpoint
  tracking, early stopping.

### Changed

- `pyproject.toml`: new ``[training]`` optional extra
  (``torch>=2.0``, ``tiktoken>=0.7``, ``tokenizers>=0.20``). ``[all]``
  and ``[dev]`` updated.
- `fi_core/__init__.py`: lists the new ``fi_core.training`` path.

### Narrative

V2 preserved: training is a utility surface, NOT a closed loop. The
patterns shipped by ``fi_core.persona`` are NOT derived from any
corpus a consumer trains on with this module — they remain
human-distilled from production failure modes. ``fi_core.training``
ships the pipes (read chunks that ``fi_core.stores`` wrote, tokenize,
embed, run a small GPT loop); the closed loop, if a consumer wants
one, is their assembly.

### Honest reuse notes

- ``TinyGPT`` model code was written for fi-core (Robo-Poet referenced
  a ``models.gpt_model`` that never existed in the repo — Bernard's
  comment ``tu PyTorch existe; tu loop no`` was literal: only the
  trainer was real).
- ``PyTorchTrainer`` is a near-verbatim adaptation of Robo-Poet's
  ``GPTTrainer`` class, with the changes documented above.
- Generation sampling (temperature / top-k / top-p / repetition
  penalty) is adapted from Robo-Poet's ``TextGenerator``.
- Tokenizers are thin wrappers over ``tiktoken`` and HuggingFace
  ``tokenizers`` — no point reinventing what those libraries already
  do well.

## [0.5.1] — 2026-05-19

### Added

- `fi_core.persona.mcp_server.build_consolidation_prompt(facts, max_tokens_hint)`
  and `fi_core.persona.mcp_server.parse_consolidation_result(raw_response, facts)`
  — Shape B tools (per the canonical MCP pattern: server returns
  prompt + parser, NEVER executes LLM). Mem0-style judge consolidation
  ported verbatim from discord-bot's `insult/core/memory_consolidator.py`.
  Pairs so any consumer (insult-runner via Claude Code SDK + OAuth Max,
  AURITY's curator, fi-monitor) can run the judge call with its own
  credentials. The system prompt is byte-identical to discord-bot's
  `insult/prompts/memory_consolidator_judge.md`. Parser strips markdown
  fences, validates op shape against the input facts list, backfills
  implicit NOOPs for ids the judge omitted (never silently lose a row).
- `fi_core.persona.MCP_SERVER_NAME` and `fi_core.persona.MCP_TOOLS` —
  explicit MCP contract constants that v0.4.0 forgot to export. Lists
  all 7 tools (5 from 0.4.0 + 2 new consolidation tools). Re-exported
  from `fi_core.persona` so consumers can do
  `from fi_core.persona import MCP_SERVER_NAME, MCP_TOOLS` without
  digging into `mcp_server` internals. This closes the gap that forced
  discord-bot's `scripts/sync_capabilities.py` to AST-walk
  `mcp_server.py` as a fallback in 0.4.0.

### Notes

- 0.5.0 shipped to GitHub + anaconda.org before these two persona
  additions landed on `main`. 0.5.1 is a fast follow that bundles the
  consolidation tools + MCP contract constants into the same release
  cycle; nothing else changed (same pgvector store, same embedders).
  Downstream consumers should target `fi-core>=0.5.1` to unlock the
  consolidation pair and the explicit `MCP_TOOLS` discovery path.

## [0.5.0] — 2026-05-19

### Added

- `fi_core.stores.pgvector.PgVectorChunkStore` — second reference
  `DocumentChunkStore` implementation, backed by Postgres + pgvector.
  Designed for multi-tenant chat substrates that need concurrent writes,
  relational filters mixed with vector similarity, and transactional
  consistency. IVFFlat index (`lists=100`) by default; documented HNSW
  migration cue for >1M chunks per namespace. Codec registration is
  done via one-shot bare connection BEFORE pool construction (avoids
  the asyncpg "unknown type: vector" failure mode). 7 new tests using
  pytest-postgresql's ephemeral PG fixture.
- `fi_core.embeddings.azure_openai.AzureOpenAIEmbedder` — first
  reference `Embedder` implementation. Wraps Azure OpenAI's embeddings
  API via the openai SDK's `AsyncAzureOpenAI` client. Constructor takes
  explicit config (api_key, endpoint, deployment, api_version, dim) —
  NO env-var reading inside the package; caller's job to source
  credentials. Default `dim=1536` (text-embedding-ada-002 /
  text-embedding-3-small), parameterizable to 3072 for
  text-embedding-3-large. 14 new tests with mocked SDK calls — no
  network access in CI.
- `fi_core.embeddings.sentence_transformers.SentenceTransformersEmbedder` —
  second reference `Embedder` implementation. Loads a local
  sentence-transformers model into the host process (CPU by default;
  GPU via `device=` parameter, with auto-detect ladder
  `cuda > mps > cpu` when `device=None`). Lazy-load on first `embed()`
  call (model is NOT loaded at `__init__`). `model.encode` runs through
  `asyncio.to_thread` so it does not block the event loop. Default
  model `sentence-transformers/all-MiniLM-L6-v2` (384-dim, matches
  AURITY's fi-monitor GPU service). 8 new tests including a
  `@pytest.mark.slow` real-model load + encode test.

### Changed

- `fi_core/__init__.py` updated to list the four new sub-package paths.
- `pyproject.toml`: new optional extras `stores-pgvector` (asyncpg +
  pgvector), `embeddings-azure` (openai), `embeddings-st`
  (sentence-transformers + torch). `[all]` and `[dev]` updated to
  bundle all five extras. Default `numpy` and `mcp` upper bounds also
  formalized in `[stores-hdf5]` and `[mcp]` (matching the conda recipe).
- `[tool.pytest.ini_options]` registers a `slow` marker for the heavy
  sentence-transformers real-model test, eliminating
  PytestUnknownMarkWarning at collection.

### Honest extraction notes

- `AzureOpenAIEmbedder` was a clean extraction from discord-bot's
  `insult/core/deep_memory.py` (lines 48-129). Stripped env-var
  reading, promoted dim to a constructor arg, added eager validation.
- `SentenceTransformersEmbedder` is "inspired by" not "extracted from"
  AURITY. AURITY's `monitor_client.py` is a thin HTTP client to a
  Cloudflare-tunneled GPU service; no `MonitorClientEmbedder` class
  exists. The fi-core implementation is a clean local-process
  equivalent modeled on `fi-monitor/rag_service/main.py:71` (the
  actual SentenceTransformer instantiation point in the free-
  intelligence monorepo).
- `PgVectorChunkStore` is "inspired by" not "extracted from"
  discord-bot's `deep_memory.py`. The discord-bot module is heavily
  Discord-domain (hardcoded `user_id` column, closed CHECK constraint
  on source_type, md5-based chunk dedupe, no document concept). The
  fi-core implementation preserves the schema shape, cosine query
  pattern, and IVFFlat index choice, but drops Discord-specific
  concepts and adds the full document-lifecycle layer needed by
  the `DocumentChunkStore` Protocol.

### Coverage

- 29 new tests (14 azure + 8 sentence-transformers + 7 pgvector).
- Full suite: 124 passing in 8.87s. 0 regressions.

## [0.4.0] — 2026-05-19

### Added

- `fi_core.persona.mcp_server` — MCP (Model Context Protocol) server
  exposing the persona detectors as tools that any MCP-compatible AI
  (Claude Code, Cursor, Anthropic API with MCP enabled) can call
  directly, without depending on `fi-core` as a Python package in
  its own process.
- Five tools shipped on the server:
  - `list_packs()` — discovery of atomic + composite packs with
    severity, language, and pattern count metadata.
  - `check_drift(text, packs)` — detect persona drift with matches
    grouped by severity tier (break / soft_drift / clarification_dump).
  - `sanitize_response(text, packs)` — last-resort sentence-level
    cleanup for break-severity matches.
  - `get_reinforcement(pack_name)` — return the reinforcement string
    associated with a pack. Auto-maps `clarification_dump_*` to
    `CONTEXT_REINFORCEMENT`, everything else to `GENERIC_REINFORCEMENT`.
  - `validate_and_retry_prompt(response, system_prompt, packs)` —
    one-shot atomic loop. The killer-feature tool: validates the
    response, decides per-severity whether retry is needed, and
    returns the reinforced system prompt if so. Zero client-side
    orchestration; the AI does not need a state machine.
- Composite packs (`default_bilingual`, `all_ai_disclosure`, etc.) now
  expand to their atomic components when processed by the MCP server,
  preserving per-pattern severity tier end-to-end. A hard break inside
  `default_bilingual` is routed through the break-tier detector, not
  the soft-drift one.
- 21 new tests in `test_persona_mcp.py` covering all five tools, the
  atomic-vs-composite expansion contract, unknown-pack graceful
  fallback, severity-precedence rules, and the no-retry-on-soft-drift
  decision rule.

### Changed

- `fi-core` now ships an optional `[mcp]` extra (depends on `mcp>=1.4`).
  Install as `pip install 'fi-core[mcp]'` to enable the server.
- Anaconda conda recipe `meta.yaml` keeps `mcp` as a non-required
  dependency since the base package remains usable without it; the
  conda-forge submission will declare it as optional output.

### Install + register

```bash
pip install 'fi-core[mcp]'
claude mcp add fi-core-persona -- python -m fi_core.persona.mcp_server
```

After registration, any MCP client (Claude Code, Cursor) can invoke the
five tools directly. The killer use case is the meta-validation loop:
the AI checks its own output for persona drift via `validate_and_retry_prompt`
before sending the response to the user, and retries with the right
reinforcement automatically if drift is detected.

## [0.3.0] — 2026-05-19

### Added

- `fi_core.rag.DocumentChunkStore` Protocol — explicit interface for
  persistent chunk storage, decoupled from any specific backend.
- `fi_core.stores.hdf5.HDF5ChunkStore` — first concrete implementation
  of `DocumentChunkStore`, backed by HDF5 via `h5py`. Supports both
  async and sync APIs.
- New type module surface:
  - `ChunkWithEmbedding` — chunk text + its vector representation.
  - `DocumentMetadata` — document-level metadata associated with a
    chunk set.
  - `DocumentRecord` — combined record returned by store lookups.
- Optional install group `stores-hdf5` (pulls `h5py>=3.10`, `numpy>=1.24`).
- 34 new tests covering the HDF5 store and the protocol contract.

### Notes

- The core package remains zero-dependency. HDF5 is opt-in via
  `pip install fi-core[stores-hdf5]`.

## [0.2.0] — 2026-05-19

### Added

- `fi_core.persona` — character-integrity / anti-drift module
  extracted from the production Insult Discord bot.
- Three detector classes:
  - `BreakDetector` — hard identity leaks (retry-worthy).
  - `AntiPatternMonitor` — soft drift toward assistant tone (log only).
  - `ClarificationDumpDetector` — bot punting the task back at the
    user despite having context (retry with context cue).
- `sanitize()` — last-resort sentence-level cleanup when retries fail.
- `DetectionResult` dataclass — frozen value type with `clean`
  convenience flag and `severity` field for telemetry routing.
- 14 built-in pattern packs covering:
  - AI identity disclosure (`GENERIC_AI_DISCLOSURE_EN`, `..._ES`).
  - Assistant tone (`ASSISTANT_TONE_EN`, `..._ES`).
  - Therapy-speak (`THERAPY_SPEAK_EN`, `..._ES`).
  - Summarizing (`SUMMARIZING`).
  - Stage directions / roleplay drift (`STAGE_DIRECTIONS`).
  - Markdown formatting drift (`MARKDOWN_DRIFT`).
  - Moralizing (`MORALIZING_EN`, `..._ES`).
  - Over-validation (`OVER_VALIDATION_EN`, `..._ES`).
  - Clarification dump (`CLARIFICATION_DUMP_ES`).
- Convenience composite packs: `ALL_AI_DISCLOSURE`,
  `ALL_ASSISTANT_TONE`, `ALL_THERAPY_SPEAK`, `ALL_MORALIZING`,
  `ALL_OVER_VALIDATION`, `DEFAULT_EN`, `DEFAULT_ES`,
  `DEFAULT_BILINGUAL`.
- Reinforcement strings: `GENERIC_REINFORCEMENT`,
  `CONTEXT_REINFORCEMENT`, `IDENTITY_REINFORCEMENT_SUFFIX`.
- 31 new tests pinning the detector contracts and pack invariants
  (e.g. all packs contain only compiled `re.Pattern` objects, default
  composites equal the concatenation of their sources).

### Notes

- All persona detection is deterministic regex — zero LLM calls at
  detection time, zero embeddings, zero training data required.
- Bilingual EN+ES patterns are first-class peers, not afterthoughts.
- Persona-specific patterns stay in the consumer's codebase; the
  library only ships patterns that generalize across personas.

## [0.1.0] — 2026-05-19

### Added

- Initial release.
- `fi_core.rag` — chunking algorithm extracted verbatim from the
  AURITY `document_service` production code.
  - Three strategies: paragraph-aware, sentence-aware, fixed-size.
  - `ChunkingStrategy` enum and `ChunkConfig` dataclass.
  - `chunk_document(text, strategy, config) -> list[str]` entry point.
- `Embedder` Protocol — async `embed(text) -> list[float]` contract
  for any embedding backend (sentence-transformers, Azure OpenAI
  ada-002, etc.).
- `ChunkStore` Protocol — first-pass storage contract (later superseded
  by `DocumentChunkStore` in 0.3.0).
- `Chunk` and `RetrievedChunk` dataclasses for typed chunk values.
- 9 tests covering chunking behavior across strategies and edge cases.

### Notes

- Zero runtime dependencies. The package targets Python 3.12+.
- Intended consumers at extraction time: AURITY (on-prem medical) and
  the Insult Discord bot (Azure-native conversational).

[0.3.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.3.0
[0.2.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.2.0
[0.1.0]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-core-v0.1.0
