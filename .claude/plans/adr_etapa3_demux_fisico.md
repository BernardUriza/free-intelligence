# ADR: Etapa 3 Demux Físico / Runtime Wiring

Status: Accepted
Date: 2026-06-16
Merge: PR #26 / e527080

> Authoring note: redactado vía `/exchange-coagent` (coagent insult-gpt → Claude Code).
> El esqueleto lo propuso el coagent; las claims load-bearing fueron verificadas en
> vivo antes de aceptar (ver sección Validation). La fecha del coagent (2026-06-14)
> se corrigió a la fecha real del merge de PR #26 (2026-06-16T07:29:41Z).

## Context
- Insult dejó de ser tratado como sistema.
- Monorepo demuxeado en personas, host, shared y adapter.
- Etapa 0 ya había estabilizado el data plane (migración a Azure PostgreSQL).
- Etapa 3 cerró boundaries físicos y runtime wiring.

## Decisions

1. Registry/launcher explícito en demux_ai
   - persona selection: explicit > `KHIMERAS_PERSONA` > default insult
   - default histórico preservado, ahora explícito

2. Host/plugin inversion
   - demux_ai resuelve personas por entrypoint string/factory
   - no static imports de personas desde host/gateway/shared

3. AgentRunnerClient en khimeras_shared
   - decisión deliberada para evitar persona→host
   - demux_ai wrapper diferido hasta que cambie el runtime ownership

4. prompts_loader
   - loader genérico en khimeras_shared
   - prompt assets permanecen por-persona

5. composition.py
   - queda interno en cada persona
   - host consume `PersonaAppFactory` / `PersonaApp` contract

6. memory_consolidator
   - split, no move entero
   - core neutral en `khimeras_shared.memory_consolidation`
   - hooks persona-side para siesta/diary/voz
   - safety-cap P0 preservado

7. consolidate_all_users en khimeras_shared por ahora
   - decisión transicional
   - evita persona→host mientras ACA Job siga llamando el trigger histórico
   - `demux_ai/jobs` wrapper queda para etapa futura cuando se repointe ACA Job

## Boundary Locks
- persona→persona: 0
- shared→persona: 0
- gateway→persona: 0
- demux_ai→persona: 0

## Validation

Verified live during ADR authoring (2026-06-16):
- arch boundary suite: 61 passed (`pytest tests/arch/`) — boundaries enforced at 0
- merge commit e527080 confirmado vía `gh pr view 26` (MERGED 2026-06-16T07:29:41Z)
- prod: serving=true / healthy=true / guild_count=1

Passed during PR/CD path before merge, NOT re-run locally during ADR authoring:
- full suite: 1611 passed / 13 skipped
- ruff: clean
- CD: green

## Security audit note
- pip-audit parser ahora distingue inauditables (con `skip_reason`) de vulnerabilidades reales.
- fi-core / fi-runner conda-only no-PyPI quedan saltados como inauditables, no como pass falso.
- cryptography GHSA-537c-gmf6-5ccf y starlette CVEs quedan ignoradas temporalmente con
  justificación y trigger de re-auditoría.
- Exploitability review humana por Bernard pendiente.
- Los ignores NO significan mitigación ni evaluación de no explotabilidad.

## Consequences
- Insult y Alice son personas/plugins.
- demux_ai es host/orquestador.
- discord-bot es adapter/runtime entrypoint.
- khimeras_shared contiene contratos/capabilities neutrales.
- Tier B (juez semántico de facts dedup) sigue congelado.
- ACA Job repoint queda fuera de esta etapa.

## Deferred decisions
- repoint ACA Job a `python -m demux_ai ...`
- optional `demux_ai/jobs` wrapper
- exploitability review de los CVEs de cryptography / starlette
- Tier B semantic judge permanece congelado
