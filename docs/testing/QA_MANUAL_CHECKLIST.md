# Free Intelligence - Manual QA Checklist

**Version**: 0.2.0
**Sprint**: SPR-2025W44 (Sprint 2)
**Task**: FI-TEST-FEAT-001
**Last Updated**: 2025-10-27

---

## 📋 Purpose

This checklist ensures that all critical system components, policies, and workflows are manually validated before each release or major milestone.

---

## ✅ Pre-Release QA Checklist

### 🔧 Environment Setup
- [ ] Python 3.11+ installed (`python3 --version`)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] Storage directory exists (`mkdir -p storage`)
- [ ] Config file present (`ls config/config.yml`)
- [ ] Logs directory exists (`mkdir -p logs`)
- [ ] Tests directory present (`ls tests/`)
- [ ] Backend modules importable (`python3 -c "import backend"`)

---

### 📦 Module Validation

#### Config Loader (backend/config_loader.py)
- [ ] Loads YAML correctly (`python3 -c "from backend.config_loader import load_config; load_config()"`)
- [ ] Raises ConfigError on missing file
- [ ] Validates required sections (owner, models, storage)
- [ ] Returns dict with expected keys

#### Logger (backend/logger.py)
- [ ] Produces structured JSON logs
- [ ] Includes timestamp in ISO 8601 format
- [ ] Includes America/Mexico_City timezone
- [ ] Writes to logs/app.log
- [ ] Log level configurable (INFO, DEBUG, WARNING, ERROR)

#### Corpus Schema (backend/corpus_schema.py)
- [ ] Initializes HDF5 structure correctly
- [ ] Creates /interactions, /embeddings, /metadata groups
- [ ] Sets metadata attributes (created_at, version, schema_version)
- [ ] Validates corpus structure
- [ ] Prevents duplicate initialization

#### Corpus Operations (backend/corpus_ops.py)
- [ ] Appends interactions without corruption
- [ ] Generates UUID v4 for interaction_id
- [ ] Timestamps use UTC timezone
- [ ] Returns interaction_id on success
- [ ] Reads interactions correctly
- [ ] Get stats returns correct counts

#### Corpus Identity (backend/corpus_identity.py)
- [ ] Generates valid UUID v4 for corpus_id
- [ ] Generates valid SHA256 for owner_hash
- [ ] Adds identity to existing corpus
- [ ] Verifies ownership correctly
- [ ] Returns identity metadata

#### Event Validator (backend/event_validator.py)
- [ ] Validates UPPER_SNAKE_CASE format
- [ ] Accepts canonical events
- [ ] Rejects invalid formats
- [ ] Suggests event names
- [ ] Scans files for events
- [ ] CLI commands work (validate, scan, list)

#### Append-Only Policy (backend/append_only_policy.py)
- [ ] Context manager works correctly
- [ ] Validates write index (new indices only)
- [ ] Validates resize (increase only)
- [ ] Detects truncation in __exit__
- [ ] Raises AppendOnlyViolation on mutation
- [ ] Integrates with corpus_ops

#### Mutation Validator (backend/mutation_validator.py)
- [ ] Detects forbidden function names
- [ ] Scans files with AST
- [ ] Accepts allowed patterns
- [ ] Rejects forbidden patterns
- [ ] CLI validation works
- [ ] Reports violations correctly

#### Audit Logs (backend/audit_logs.py)
- [ ] Initializes /audit_logs/ group
- [ ] Appends audit log entries
- [ ] Hashes payloads + results (SHA256)
- [ ] Filters by operation/user
- [ ] Returns audit stats
- [ ] Auto-init if group missing

#### LLM Audit Policy (backend/llm_audit_policy.py)
- [ ] @require_audit_log decorator works
- [ ] Detects LLM functions via AST
- [ ] Scans files for violations
- [ ] CLI validate command works
- [ ] Excludes false positives
- [ ] Reports violations correctly

#### LLM Router Policy (backend/llm_router_policy.py)
- [ ] Detects forbidden imports (anthropic, openai, etc.)
- [ ] Detects forbidden calls (messages.create, etc.)
- [ ] Scans files with AST
- [ ] CLI validate command works
- [ ] Backend passes validation

#### Export Policy (backend/export_policy.py)
- [ ] Creates export manifest
- [ ] Validates schema (export_id, timestamp, etc.)
- [ ] Computes file hash (SHA256)
- [ ] Validates export (schema + hash match)
- [ ] Load/save manifests
- [ ] CLI commands work

#### Boot Map (backend/boot_map.py)
- [ ] Initializes /system/boot_map/ group
- [ ] Appends boot events
- [ ] Registers core functions
- [ ] Appends health checks
- [ ] Retrieves boot sequence
- [ ] Filters core functions by category
- [ ] Groups health status
- [ ] Returns boot map stats

---

### 🗄️ Data Integrity

#### HDF5 Datasets
- [ ] Interactions dataset is resizable (maxshape=None)
- [ ] Embeddings dataset is resizable
- [ ] Compression enabled (gzip level 4)
- [ ] Chunking enabled (chunks=True)
- [ ] Datasets are not corrupted (h5dump validates)

#### Metadata
- [ ] created_at is ISO 8601 timestamp
- [ ] version is "0.2.0"
- [ ] schema_version is "1"
- [ ] corpus_id is valid UUID v4 (36 chars, 4 dashes)
- [ ] owner_hash is valid SHA256 (64 hex chars)

#### Timestamps
- [ ] All timestamps use timezone-aware format
- [ ] Timezone is America/Mexico_City
- [ ] ISO 8601 format (YYYY-MM-DDTHH:MM:SS.ffffff±HH:MM)

---

### 🛡️ Policy Enforcement

#### Append-Only
- [ ] Cannot modify existing interactions
- [ ] Cannot delete interactions
- [ ] Cannot resize dataset to smaller size
- [ ] Can append new interactions
- [ ] Can read existing interactions
- [ ] AppendOnlyViolation raised on mutation attempt

#### No-Mutation
- [ ] No functions named update_*, delete_*, modify_*
- [ ] No functions named edit_*, change_*, overwrite_*
- [ ] No functions named truncate_*, drop_*, clear_*
- [ ] Validator detects violations
- [ ] Backend passes validation (0 violations)

#### LLM Audit
- [ ] All LLM functions have @require_audit_log
- [ ] LLM functions call append_audit_log()
- [ ] Validator detects missing decorator
- [ ] Backend passes validation (0 violations)

#### LLM Router
- [ ] No direct import of anthropic
- [ ] No direct import of openai, cohere, etc.
- [ ] No direct calls to client.messages.create
- [ ] Validator detects violations
- [ ] Backend passes validation (0 violations)

#### Export
- [ ] All exports have manifests
- [ ] Manifests include export_id (UUID v4)
- [ ] Manifests include timestamp
- [ ] Manifests include data_hash (SHA256)
- [ ] Validation checks schema + hash match

---

### 📊 Audit Trail

#### Audit Logs
- [ ] Every operation logged to /audit_logs/
- [ ] Logs include audit_id (UUID v4)
- [ ] Logs include timestamp (ISO 8601 + TZ)
- [ ] Logs include operation name
- [ ] Logs include user_id
- [ ] Logs include endpoint
- [ ] Logs include payload_hash (SHA256)
- [ ] Logs include result_hash (SHA256)
- [ ] Logs include status (SUCCESS/FAILED/BLOCKED)

#### Audit Stats
- [ ] Total logs count is correct
- [ ] Success count is correct
- [ ] Failed count is correct
- [ ] Blocked count is correct
- [ ] Operation breakdown is correct
- [ ] User breakdown is correct

---

### 🚀 Boot Sequence

#### Boot Events
- [ ] SYSTEM_START tracked
- [ ] CONFIG_LOADED tracked
- [ ] LOGGER_INITIALIZED tracked
- [ ] CORPUS_INITIALIZED tracked
- [ ] AUDIT_LOGS_INITIALIZED tracked
- [ ] BOOT_MAP_INITIALIZED tracked
- [ ] SYSTEM_READY tracked

#### Core Functions
- [ ] load_config registered (priority 1)
- [ ] get_logger registered (priority 2)
- [ ] init_corpus registered (priority 3)
- [ ] validate_corpus registered (priority 4)
- [ ] All functions have category (CORE, DATA, etc.)

#### Health Checks
- [ ] CONFIG check recorded
- [ ] LOGGER check recorded
- [ ] CORPUS check recorded
- [ ] AUDIT_LOGS check recorded
- [ ] All checks have status (OK, WARNING, ERROR, CRITICAL)
- [ ] All checks have duration_ms

---

### ⚡ Performance

#### Interaction Operations
- [ ] Append interaction < 100ms
- [ ] Read interaction < 50ms
- [ ] Get stats < 100ms

#### Corpus Operations
- [ ] Initialize corpus < 500ms
- [ ] Validate corpus < 500ms
- [ ] Verify ownership < 200ms

#### Audit Operations
- [ ] Append audit log < 50ms
- [ ] Get audit stats < 100ms

#### Boot Operations
- [ ] Append boot event < 50ms
- [ ] Register core function < 50ms
- [ ] Append health check < 50ms
- [ ] Get boot map stats < 100ms

#### Bulk Operations
- [ ] 100 interactions < 10s (< 100ms each)
- [ ] 100 audit logs < 5s (< 50ms each)

---

### 🐛 Error Handling

#### Config Errors
- [ ] Missing config.yml raises ConfigError
- [ ] Invalid YAML raises ConfigError
- [ ] Missing required sections raises ConfigError

#### Corpus Errors
- [ ] Missing corpus file raises FileNotFoundError
- [ ] Invalid owner_id raises ValueError
- [ ] Duplicate init raises ValueError
- [ ] Invalid corpus structure fails validation

#### Policy Errors
- [ ] Mutation attempt raises AppendOnlyViolation
- [ ] Invalid event name raises ValidationError
- [ ] Missing @require_audit_log detected
- [ ] Forbidden function name detected
- [ ] Direct LLM API call detected

#### Data Errors
- [ ] Invalid UUID raises ValueError
- [ ] Invalid SHA256 raises ValueError
- [ ] Missing dataset raises KeyError
- [ ] Corrupted HDF5 file raises OSError

---

### 🧪 Test Execution

#### Unit Tests
- [ ] All unit tests pass (259/259)
- [ ] No test failures
- [ ] No test errors
- [ ] No test skips
- [ ] Tests complete in < 5s

#### E2E Tests
- [ ] System initialization test passes
- [ ] Boot sequence test passes
- [ ] Data operations test passes
- [ ] Multiple interactions test passes
- [ ] Policy enforcement test passes
- [ ] Audit logging test passes
- [ ] Performance test passes
- [ ] Corpus integrity test passes

#### Manual Tests
- [ ] Initialize fresh corpus manually
- [ ] Append interaction manually
- [ ] Validate corpus manually
- [ ] Verify ownership manually
- [ ] Inspect HDF5 with h5dump
- [ ] Check logs with tail -f

---

### 📝 Documentation

#### Code Documentation
- [ ] All modules have docstrings
- [ ] All functions have docstrings
- [ ] Docstrings follow Google style
- [ ] Examples provided where helpful

#### User Documentation
- [ ] README.md is up to date
- [ ] CLAUDE.md reflects current state
- [ ] Sprint docs are current
- [ ] Testing guide is complete
- [ ] QA checklist is complete

---

### 🔄 CI/CD

#### Pre-Commit Hooks
- [ ] Hooks installed (./scripts/install_hooks.sh)
- [ ] Append-only validator runs
- [ ] Mutation validator runs
- [ ] LLM audit validator runs
- [ ] LLM router validator runs
- [ ] Event name validator runs
- [ ] Commit message validator runs

#### Sprint Automation
- [ ] Sprint close script works (./scripts/sprint-close.sh)
- [ ] Git tag created correctly
- [ ] Release notes generated
- [ ] Velocity calculated
- [ ] Tests run before close

---

## ✅ Sign-Off

**QA Performed By**: ______________________
**Date**: _____________
**Version Tested**: 0.2.0
**Sprint**: SPR-2025W44

### Results Summary
- [ ] All checks passed
- [ ] Issues found (list below):

**Issues**:
```
(None / List issues here)
```

**Recommendations**:
```
(None / List recommendations here)
```

**Approved for Release**: ☐ Yes ☐ No

**Signature**: ______________________

---

**END OF MANUAL QA CHECKLIST**
