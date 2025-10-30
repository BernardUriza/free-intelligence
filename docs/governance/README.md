# Governance: Trello Artifacts Guard

**Card:** FI-GOV-TOOL-001
**Philosophy:** Done is auditable - without artifacts, Done doesn't exist

## Quick Start

1. **Butler** (Trello UI): Configure 3 rules from `butler_rules.yaml`
2. **GitHub Secrets**: Add `TRELLO_API_KEY` + `TRELLO_TOKEN`
3. **Branch Protection**: Require "Trello Artifacts Guard" status check

## Files

- `butler_rules.yaml` - Butler automation rules (YAML config)
- `trello_commands.sh` - Shell utilities for manual validation
- `tools/ci_guard_trello.sh` - CI validation script
- `.github/workflows/trello-guard.yml` - GitHub Actions workflow
- `.github/pull_request_template.md` - PR template

## Usage

```bash
# Test CI guard
export TRELLO_CARD=abc123XY
./tools/ci_guard_trello.sh

# Audit Done list
source docs/governance/trello_commands.sh
audit_done_list
```

## Full Documentation

See [docs/archive/GOVERNANCE_GUARD.md](../archive/GOVERNANCE_GUARD.md) for complete setup instructions, patterns, troubleshooting, and philosophy.
