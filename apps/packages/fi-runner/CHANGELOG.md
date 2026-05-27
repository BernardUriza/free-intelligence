# Changelog — fi-runner

All notable changes to **fi-runner** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Policy:

- **PATCH** (`0.x.y` → `0.x.y+1`): backwards-compatible bug fixes; no public-API change.
- **MINOR** (`0.x.y` → `0.x+1.0`): backwards-compatible feature additions; new backends, new capability factories, new guards.
- **MAJOR** (`x.y.z` → `x+1.0.0`): breaking changes to public API (`Runner`, `AgentBackend`, `ToolPolicy`, capability factory signatures, guard contracts).

Pre-1.0 (`0.x.y`): no backwards-compat shims required. Stability promise applies at 1.0.0.

`fi-runner` depends on `fi-core>=0.24,<0.25`. When fi-core bumps to a new minor, fi-runner also gets a release that bumps the pin.

---

## [Unreleased]

(Add entries here as work lands on `dev`.)

---

## [0.17.1] — 2026-05-26

### Added

- P1+P2 robustness hardening (PR #168, merged 2026-05-26):
  - **R5** — `FlowNarrator.max_inflight_narrations: int = 8`; `schedule_narration` emits `narration_dropped` event when pool at cap. Prevents narrator task-set from growing unbounded under slow-narrator + burst-turn scenarios.
  - **R7** — `MCPServerSpec.__post_init__` lint warning when `command` is `sh`/`bash`/`zsh` (full path OR basename). Shell-wrapped commands hide the child PID from the harness's tracker → zombie risk.
  - **R8** — `_TRACKER` alias in `fi_core.task_tracker.mcp_server` replaced with module-level `__getattr__` (PEP 562) that delegates to the live `_registry._TRACKER`. Existing internal tests unaffected.
  - **R10** — `Runner.run_stream` post-stream pipeline wrapped in `try/except` that emits `stream_postprocess_error`; final `yield {"type":"result"...}` is OUTSIDE the guarded block, so the consumer ALWAYS receives a result event even if the pipeline crashes.
  - **R11** — `Runner.install_signal_handlers()` opt-in helper. Registers SIGTERM/SIGINT via `loop.add_signal_handler`; emits `runner_signal_received` + calls `aclose()`. Catches `NotImplementedError` on Windows.
  - **R13** — `_TTLStore.values()/.items()` return `list(...)` snapshots so a future async-lock migration won't race purge against iteration.
  - **R14** — `Runner.pre_emit_append: bool = False` (write-ahead variant of conversation_store append). Append body extracted to a single `_append_to_store(phase=…)` helper.
- mcp pin bumped: `mcp>=1.27,<2` (RFC 8707 OAuth + StreamableHTTP timeout).
- New `narration_dropped`, `stream_postprocess_error`, `runner_signal_received`, `runner_shutdown_error`, `runner_signal_install_skipped`, `conversation_store_error` events.

### Changed

- `Runner` constructor adds `pre_emit_append: bool = False`. Default behavior unchanged.

### Documentation

- `capabilities.py` module docstring + `task_tracker()` factory warn about MCP stdio one-client-per-server bottleneck under multi-tenant fan-out. HTTP variant deferred until second-consumer trigger.

---

## [0.17.0]

Internal milestone (no published artifact). See git log for details.

---

## [0.15.0] — last anaconda.org publish

Tag at which the anaconda.org channel was last updated. Drift from 0.15.0 to 0.17.1 corresponds to PR #168 (P1+P2 robustness) plus the eval-set work in fi-core 0.24.x.

[Unreleased]: https://github.com/BernardUriza/free-intelligence/compare/fi-runner-v0.17.1...HEAD
[0.17.1]: https://github.com/BernardUriza/free-intelligence/releases/tag/fi-runner-v0.17.1
[0.17.0]: internal
[0.15.0]: https://anaconda.org/bernardurizaorozco/fi-runner/0.15.0
