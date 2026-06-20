# Backlog — discord-bot

Roadmap / feature ideas que NO son reglas de comportamiento (esas viven en
`.claude/rules/`). Un item por archivo. Regla padre: `backlog-handling.md`
en el engineering-playbook.

| Item | Status | Hook |
|---|---|---|
| [rename `discord-bot` → `server-bot`](rename-discord-bot-to-server-bot.md) | Proposed | el sistema ya no es solo Discord cognitivo; rename del repo/sistema (NO de la plomería de Discord) cuando exista el host del demux |
| [ML-stack CVE tax](ml-stack-cve-audit.md) | Proposed | `sentence-transformers`→torch/transformers (embeddings, EN USO) arrastra un CVE tax perpetuo sin fix upstream; mitigado con ignore-list justificado en ci.yml. Root: migrar embeddings a Azure OpenAI (mata el tax + aligera la imagen). Fork arquitectura+costo de Bernard |
| [LLM shadow router token bloat](llm-shadow-router-token-bloat.md) | Done (token bloat) | fix LOCAL `DirectAzureLLMRouter` desplegado + medido en prod: 9509→115 tokens (−98.8%). Shadow ON/direct (rev 169). A.2.2 report corrido (4/4 missing_vultur, 0 false, N chico). Gap empty-input arreglado (v4.21.84). Next: A.2.3 ≥50 direct calls → luego cutover gpt-4.1 (NO-GO hoy). Upstream fi_runner chat backend = mejora canónica separada, sin urgencia |
