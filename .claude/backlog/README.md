# Backlog — discord-bot

Roadmap / feature ideas que NO son reglas de comportamiento (esas viven en
`.claude/rules/`). Un item por archivo. Regla padre: `backlog-handling.md`
en el engineering-playbook.

| Item | Status | Hook |
|---|---|---|
| [rename `discord-bot` → `server-bot`](rename-discord-bot-to-server-bot.md) | Proposed | el sistema ya no es solo Discord cognitivo; rename del repo/sistema (NO de la plomería de Discord) cuando exista el host del demux |
| [LLM shadow router token bloat](llm-shadow-router-token-bloat.md) | Proposed | `codex exec` agéntico manda ~9.4k tokens de harness para clasificar a una palabra; fix = backend Azure-chat directo (no el CLI). NO bloqueante: A.2 gated off. Hacerlo antes de re-encender A.2 |
