# Orphan Feature Files - Pending Integration

These files exist but are not imported by any production code.
They may be unfinished features from previous sprints.

## Status: REVIEW NEEDED

| File | Lines | Sprint | Decision Needed |
|------|-------|--------|-----------------|
| `config/mock_loader.py` | 90 | Unknown | Keep/Delete? |
| `infrastructure/common/boot_map.py` | 439 | FI-DATA-FEAT-003 | Integrate/Archive? |
| `infrastructure/common/buffered_writer.py` | 424 | FI-DATA-FEAT-002 | Integrate/Archive? |
| `infrastructure/config/base_config.py` | 87 | Unknown | Merge into config/? |
| `schemas/api/kpis_middleware.py` | 99 | Unknown | Integrate/Delete? |
| `schemas/domain/backup.py` | 614 | FI-SEC-FEAT-001 | Integrate/Archive? |
| `schemas/llm/decision_mw.py` | 407 | Unknown | Integrate/Delete? |
| `security/lan_guard.py` | 149 | FI-SEC-FEAT-002 | Integrate/Delete? |
| `repositories/hdf5_audio_chunk_repository.py` | 253 | Unknown | Integrate/Delete? |

**Total:** ~2,562 lines of potentially dead code

## Action Items

1. Review each file with product owner
2. If feature is still needed → integrate into codebase
3. If feature is deprecated → archive or delete
4. Update this file when decisions are made

---
Generated: 2026-02-02
