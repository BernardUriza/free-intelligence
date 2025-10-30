# AURITY System Overview

**AURITY** = **A**dvanced **U**niversal **R**eliable **I**ntelligence for **T**elemedicine **Y**ield

Not branding. Computational contract.

## Semantic Expansion

- **Advanced** → modular, self-extending under policy control
- **Universal** → unifies every data domain (EHR, imaging, audio, lab) into one causal ledger
- **Reliable** → deterministic, hash-anchored, idempotent
- **Intelligence** → adaptive reasoning layer (LLM middleware) bound by provenance
- **for Telemedicine Yield** → purpose clause: measurable outcomes in clinical workflows

## System Invariants

1. **Integridad**: SHA256 + tamaño + append-only ledger. Sin ediciones silenciosas.
2. **Reproducibilidad**: Toda respuesta guarda agent_id, prompt_template_v, policy_snapshot_id, source_ids[], answer_hash.
3. **Soberanía PHI**: Procesamiento on-prem (NAS). Egreso deny-by-default.
4. **Una sola voz**: Plantilla versionada (determinística) + políticas → misma pregunta + mismo estado = misma respuesta + provenance.
5. **Auditoría viva**: Timeline causal, métricas (p95 ingest <2s), export con manifiestos firmados.

## Architecture

```
Fuentes → Collectors (SMB/HL7/FHIR/RTSP) → Ingestor NAS (SHA256 + append-only JSONL/.h5)
  → Normalizador (PII guardrails + policy-as-code)
  → Almacenamiento (Btrfs WORM lógico + blobs + manifiestos)
  → Indexación (Qdrant + Timeline causal)
  → LLM Router (plantillas determinísticas: Claude/GPT/Ollama)
  → API FastAPI (/provenance /query /export)
  → UI AURITY (React: Sessions + Timeline + Evidencias)
  → Auditoría (SHA re-check, Prom/Grafana)
```

## Reference

- Config: `config/fi.policy.yaml`, `config/agent.yaml`, `config/sources.yaml`
- Observability: `observability/error_budgets.yaml`
- Policy: `docs/policy/identity_contract.md`
- Telemedicine: `docs/telemedicine/yield_metrics.md`
