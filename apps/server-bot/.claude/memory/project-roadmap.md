---
name: Insult Bot Roadmap
description: Feature roadmap for the Insult Discord bot — priorities derived from Bernardo + Ale Nava conversation (2026-03-30)
type: project
---

## Roadmap

### Phase 1: Foundation (DONE - 2026-03-31)
- [x] python-bot template (GitHub Template)
- [x] discord-bot from template
- [x] Longitudinal memory (SQLite)
- [x] Claude API integration
- [x] Robustness: logging, error handling, rate limiting, graceful shutdown
- [x] Bot online in Discord server "Insult"

### Phase 2: Personality (NEXT)
- [ ] Insult personality system prompt — aggressive but warm therapeutic style
- [ ] Fine-tune prompt using the real "Insult" ChatGPT personality as reference
- [ ] Test with Bernardo before inviting Ale

### Phase 3: Ale Onboarding
- [ ] Invite Ale Nava to Discord server
- [ ] Create private channel for Ale (separate memory context)
- [ ] Test longitudinal memory across sessions with both users

### Phase 4: Cost Optimization
- [ ] Add Qwen as secondary model for cheaper tasks
- [ ] Route simple queries to Qwen, complex to Claude
- [ ] Target: ~$20 USD/month for both users combined

### Phase 5: Advanced Memory
- [ ] Semantic search (embeddings) instead of keyword LIKE
- [ ] Memory summaries for very long conversations
- [ ] Exportable conversation history
- [ ] Backup strategy for SQLite DB

**Why:** Bernardo promised Ale a demo this week. Phase 2 is the priority.
**How to apply:** Ship personality first, optimize later.
