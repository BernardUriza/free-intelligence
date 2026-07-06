# Backlog — discord-bot

Roadmap / feature ideas que NO son reglas de comportamiento (esas viven en
`.claude/rules/`). Un item por archivo. Regla padre: `backlog-handling.md`
en el engineering-playbook. Items Done se retiran del folder (limpieza
2026-07-05); su historia vive en git.

| Item | Status | Hook |
|---|---|---|
| [rename `discord-bot` → `server-bot`](rename-discord-bot-to-server-bot.md) | Proposed | el sistema ya no es solo Discord cognitivo; rename del repo/sistema (NO de la plomería de Discord) cuando exista el host del demux |
| [ML-stack CVE tax](ml-stack-cve-audit.md) | Proposed | `sentence-transformers`→torch/transformers (embeddings, EN USO) arrastra un CVE tax perpetuo sin fix upstream; mitigado con ignore-list justificado en ci.yml. Root: migrar embeddings a Azure OpenAI (mata el tax + aligera la imagen). Fork arquitectura+costo de Bernard |
| [LLM shadow router token bloat](llm-shadow-router-token-bloat.md) | Done (token bloat); cutover PENDIENTE | fix `DirectAzureLLMRouter` desplegado + medido (9509→115 tokens). Lo vivo del item: A.2.3 ≥50 direct calls → cutover gpt-4.1 (NO-GO hoy: 26% divergencia, falsos positivos peli/Netflix→vultur) |

- [Frugívoro persona](frugivoro-persona.md) — In progress. Persona LIVE en prod (registry + gateway, v4.21.115); pendiente el corpus RAG de erudición (`__corpus_vegan__`) y el benchmark ético vs el GPT competidor.
- [Cross-turn durable research jobs](cross-turn-research-jobs.md) — Proposed (2026-07-05). @mention → ack ya → worker durable corre el job multi-step → postea la respuesta al canal después. Async-real que NO encaja en og118 (stateless) pero SÍ aquí. Reusa el molde `reminders` (tabla + drain loop + retry) + `/v1/turn`; slice = tabla `research_jobs` + repo + `@tasks.loop`. GO del primer slice = Bernard.
- [Renombrar Frugi → Fruggy](rename-frugi-to-fruggy.md) — Proposed (2026-07-05). Alias/display de la persona Frugívoro: "frugi" → "Fruggy". Slice en `shared/personas/registry.py` + grep total del nombre; forks del owner: ¿rename completo (display + username Discord) o solo alias, y ¿muere `frugi` como legacy?
- [Renombrar `vultur-gateway` → `persona-gateway`](rename-vultur-gateway-to-persona-gateway.md) — Proposed (2026-07-05). El CA hospeda a TODOS los siblings, el nombre miente (verificado: sigue `vultur-gateway` en Azure). Molde: el rename insult-runner→persona-runner. Atom de Bernard: GO por el blip ~30s.

## Retirados (Done, 2026-07-05 — historia en git)

- addressed_to_sibling over-suppression — Done v4.21.113 `783b00d`; cross-talk @frugi E2E-verificado (`7a1f6d2`).
- runner no dispara invoke_alice → marcador `[INVITE:]` — Done v4.21.114 `3f871a5`, E2E verificado.
- mover runner a `persona_runner/` top-level — Done v4.21.118 `19db105`.
