# Free Intelligence - Event Naming Convention

**Version**: 1.0
**Status**: Active
**Task**: FI-API-FEAT-001

---

## 📋 Convention: `[AREA]_[ENTITY]_[ACTION_PAST]`

All system events MUST follow this pattern:

```
FORMAT: <AREA>_<ENTITY>_<ACTION_PAST_PARTICIPLE>
EXAMPLE: CORPUS_IDENTITY_ADDED
         CONFIG_LOADED
         INTERACTION_APPENDED
```

### Components

1. **AREA** (Optional): System area or domain
   - `CORPUS`, `CONFIG`, `LOGGER`, `EMBEDDING`, `INTERACTION`, `SESSION`
   - Use when entity name alone is ambiguous

2. **ENTITY**: The primary noun/resource
   - `IDENTITY`, `SCHEMA`, `CONFIG`, `STATS`, `OWNERSHIP`
   - Should be singular

3. **ACTION_PAST_PARTICIPLE**: Past tense verb
   - `ADDED`, `LOADED`, `INITIALIZED`, `RETRIEVED`, `VERIFIED`
   - `FAILED`, `PASSED`, `APPENDED`, `CREATED`, `UPDATED`
   - Always past participle (implies completed action)

### Format Rules

- **Case**: `UPPER_SNAKE_CASE` only
- **Separators**: Single underscore `_` between components
- **Length**: Maximum 50 characters (readability)
- **Clarity**: Prefer clarity over brevity

---

## ✅ Canonical Event List

### Corpus Events

| Event Name | Level | Description |
|------------|-------|-------------|
| `CORPUS_INITIALIZED` | INFO | Corpus HDF5 file created with schema |
| `CORPUS_INIT_FAILED` | ERROR | Corpus initialization failed |
| `CORPUS_VALIDATION_PASSED` | INFO | Schema validation successful |
| `CORPUS_VALIDATION_FAILED` | WARNING | Schema validation found errors |
| `CORPUS_STATS_RETRIEVED` | INFO | Statistics read from corpus |
| `CORPUS_STATS_FAILED` | ERROR | Failed to retrieve statistics |

### Identity Events

| Event Name | Level | Description |
|------------|-------|-------------|
| `CORPUS_IDENTITY_ADDED` | INFO | Identity (corpus_id + owner_hash) added |
| `CORPUS_IDENTITY_ADD_FAILED` | ERROR | Failed to add identity |
| `CORPUS_IDENTITY_RETRIEVED` | INFO | Identity metadata retrieved |
| `CORPUS_IDENTITY_RETRIEVAL_FAILED` | ERROR | Failed to retrieve identity |
| `CORPUS_IDENTITY_NOT_SET` | INFO | Corpus has no identity |
| `CORPUS_OWNERSHIP_VERIFIED` | INFO | Ownership hash verification passed |
| `CORPUS_OWNERSHIP_MISMATCH` | WARNING | Ownership verification failed |
| `CORPUS_VERIFICATION_ERROR` | ERROR | Error during ownership verification |

### Interaction Events

| Event Name | Level | Description |
|------------|-------|-------------|
| `INTERACTION_APPENDED` | INFO | Interaction added to corpus |
| `INTERACTION_APPEND_FAILED` | ERROR | Failed to append interaction |
| `INTERACTIONS_READ` | INFO | Interactions read from corpus |
| `INTERACTIONS_READ_FAILED` | ERROR | Failed to read interactions |

### Embedding Events

| Event Name | Level | Description |
|------------|-------|-------------|
| `EMBEDDING_APPENDED` | INFO | Vector embedding added to corpus |
| `EMBEDDING_APPEND_FAILED` | ERROR | Failed to append embedding |

### Config Events

| Event Name | Level | Description |
|------------|-------|-------------|
| `CONFIG_LOADED` | INFO | Configuration loaded from YAML |
| `CONFIG_LOAD_FAILED` | ERROR | Failed to load configuration |
| `CONFIG_VALIDATION_FAILED` | ERROR | Configuration validation failed |

### Logger Events

| Event Name | Level | Description |
|------------|-------|-------------|
| `LOGGER_INITIALIZED` | INFO | Structured logger initialized |
| `LOGGER_INIT_FAILED` | ERROR | Failed to initialize logger |

---

## 🔍 Validation Rules

### Must Pass

- ✅ All uppercase letters
- ✅ Only alphanumeric + underscores
- ✅ Ends with past participle verb
- ✅ No consecutive underscores
- ✅ No leading/trailing underscores
- ✅ Maximum 50 characters

### Common Past Participles

**Success/Completion:**
- `INITIALIZED`, `CREATED`, `ADDED`, `UPDATED`, `DELETED`
- `LOADED`, `SAVED`, `RETRIEVED`, `APPENDED`
- `VERIFIED`, `VALIDATED`, `PASSED`
- `STARTED`, `STOPPED`, `COMPLETED`

**Failure:**
- `FAILED` (general failure)
- `MISMATCH` (comparison failed)
- `NOT_FOUND`, `NOT_SET`
- `REJECTED`, `BLOCKED`

---

## ❌ Anti-Patterns (DO NOT USE)

### Wrong Tense
```python
# ❌ BAD: Present tense
logger.info("corpus_initialize")
logger.info("interaction_append")

# ✅ GOOD: Past participle
logger.info("CORPUS_INITIALIZED")
logger.info("INTERACTION_APPENDED")
```

### Inconsistent Case
```python
# ❌ BAD: Mixed case
logger.info("Corpus_initialized")
logger.info("corpus_Initialized")

# ✅ GOOD: All uppercase
logger.info("CORPUS_INITIALIZED")
```

### Vague Names
```python
# ❌ BAD: Too generic
logger.info("DONE")
logger.info("SUCCESS")
logger.info("ERROR")

# ✅ GOOD: Specific entity + action
logger.info("CORPUS_INITIALIZED")
logger.info("IDENTITY_VERIFIED")
logger.info("CONFIG_LOAD_FAILED")
```

### Redundant Prefixes
```python
# ❌ BAD: Redundant "event_"
logger.info("EVENT_CORPUS_INITIALIZED")

# ✅ GOOD: Direct entity
logger.info("CORPUS_INITIALIZED")
```

---

## 🧪 Examples

### Corpus Operations
```python
# Initialization
logger.info("CORPUS_INITIALIZED", path=corpus_path, corpus_id=id)
logger.error("CORPUS_INIT_FAILED", error=str(e))

# Validation
logger.info("CORPUS_VALIDATION_PASSED", path=corpus_path)
logger.warning("CORPUS_VALIDATION_FAILED", errors=errors)

# Statistics
logger.info("CORPUS_STATS_RETRIEVED", interactions=100, embeddings=100)
logger.error("CORPUS_STATS_FAILED", error=str(e))
```

### Identity Operations
```python
# Add identity
logger.info("CORPUS_IDENTITY_ADDED", corpus_id=id, owner_hash=hash[:16])
logger.error("CORPUS_IDENTITY_ADD_FAILED", error=str(e))

# Verify ownership
logger.info("CORPUS_OWNERSHIP_VERIFIED", path=path)
logger.warning("CORPUS_OWNERSHIP_MISMATCH", path=path)
```

### Data Operations
```python
# Append
logger.info("INTERACTION_APPENDED", interaction_id=id, tokens=150)
logger.info("EMBEDDING_APPENDED", interaction_id=id, vector_dim=768)

# Read
logger.info("INTERACTIONS_READ", count=10, limit=50)
logger.error("INTERACTIONS_READ_FAILED", error=str(e))
```

---

## 🔄 Migration Guide

### Legacy → New Convention

| Legacy Event | New Convention | Reason |
|--------------|----------------|--------|
| `corpus_init_failed` | `CORPUS_INIT_FAILED` | Case consistency |
| `interaction_appended` | `INTERACTION_APPENDED` | Case consistency |
| `logger_initialized` | `LOGGER_INITIALIZED` | Case consistency |
| `corpus_identity_add_failed` | `CORPUS_IDENTITY_ADD_FAILED` | Case consistency |

**Note**: All existing events already follow the verb+past pattern, only case needs updating.

---

## 📝 Adding New Events

1. **Choose entity**: What resource/component is affected?
2. **Choose action**: What happened? (past tense)
3. **Add area prefix** (if needed for clarity)
4. **Validate**: Run through validation rules
5. **Add to canonical list** (this document)
6. **Write test case**

### Template
```python
# Good pattern
logger.info(
    "ENTITY_ACTION_PAST",
    key_context_1=value1,
    key_context_2=value2
)

# Example
logger.info(
    "CORPUS_EXPORTED",
    format="markdown",
    path="/exports/corpus_20251025.md",
    interactions=100
)
```

---

## 🛠️ Enforcement

- **Validator**: `backend/event_validator.py` (validates event names)
- **Tests**: `tests/test_event_validator.py` (100% coverage required)
- **CI/CD**: Event validation runs on every commit
- **Documentation**: This file must be updated for new events

---

**Last Updated**: 2025-10-25
**Owner**: Bernard Uriza Orozco
**Review Cycle**: Every sprint or when new event areas added
