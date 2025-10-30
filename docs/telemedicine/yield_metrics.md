# Telemedicine Yield Metrics

## Purpose Clause

AURITY exists para **measurable outcomes in clinical workflows**.

No es gestión documental genérica. Es optimización de rendimiento clínico.

## Core Metrics

### Ingestion Performance
- **p95 ingest latency**: <2000ms (target per `observability/error_budgets.yaml`)
- **Objects with verified SHA256**: 100% (integrity guarantee)

### Clinical Workflow
- **Time to first response** (triage → LLM answer): <5s p95
- **Answer with citations**: 100% (provenance mandatory)
- **Redaction completeness**: 0 PHI leaks (PII guardrails)

### System Reliability
- **Uptime**: 99.9% (LAN-only, on-prem)
- **Export success rate**: 100% (manifests + hashes)
- **Audit trail completeness**: 100% append-only

## Yield Definition

**Yield** = capacidad de convertir caos informacional en respuestas accionables con provenance completo.

Ejemplo:
- Input: 50 PDFs + 20 HL7 messages + 10 audios
- Output: "Paciente X, 12/08, decisión: alta. Fuentes: [doc_001.pdf, msg_007.hl7]. Hash: sha256:abc..."

## Measurement

Ver: `observability/error_budgets.yaml` (SLOs y alertas Prometheus)

Dashboard Grafana:
- Timeline API latency (p50/p95/p99)
- Ingestion throughput (objects/min)
- LLM router metrics (tokens, cost, latency)
- SHA256 verification rate

## Compliance

- **WORM lógico**: Btrfs snapshots + append-only ledger
- **Audit logs**: 90-day retention (`config/fi.policy.yaml`)
- **Export policy**: Manifests with SHA256 validation
