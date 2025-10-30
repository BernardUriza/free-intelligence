# Governance: Trello Artifacts Guard

**Card:** FI-GOV-TOOL-001
**Philosophy:** Done is auditable - without artifacts, Done doesn't exist

## Overview

Automated governance system to ensure no Trello card reaches "Done" without verifiable artifacts.

**Components:**
1. **Butler Automation** (Trello UI) - Auto-checklist + guard rules
2. **CI Guard** (GitHub Actions) - PR validation before merge
3. **Shell Scripts** - Manual validation + bulk operations

---

## Quick Start

### 1. Butler Setup (Trello UI)

Navigate to board automation and create these 3 rules:

**Rule 1: Auto-add Artifacts Checklist**
- Trigger: Card created OR moved to "In Progress"
- Action: Add checklist "Artifacts" with 4 items

**Rule 2: Guard - Block Done**
- Trigger: Card moved to "Done"
- Condition: Checklist "Artifacts" NOT complete
- Actions: Revert to "In Progress" + red label + comment

**Rule 3: Artifacts OK**
- Trigger: Checklist "Artifacts" completed
- Actions: Green label "Artifacts OK" + remove red label

See [butler_rules.yaml](butler_rules.yaml) for detailed configuration.

### 2. GitHub Secrets

Add to repository secrets:
- `TRELLO_API_KEY` - Get from https://trello.com/app-key
- `TRELLO_TOKEN` - Generate with read/write scope

### 3. Branch Protection

Enable in Settings → Branches → main:
- ✅ Require status checks: "Trello Artifacts Guard"

---

## Artifacts Checklist

Every card must have:

1. **📎 URL demo** - Deployment URL or demo video
2. **🔖 Commit/Tag** - Git SHA (short) or version tag (v1.2.3)
3. **📄 Manifest** - manifest.json URL (optional)
4. **📊 Evidence** - Logs, metrics, screenshots, or PR link

---

## Usage

### Manual Validation

```bash
# Test CI guard locally
export TRELLO_KEY="your_key"
export TRELLO_TOKEN="your_token"
export TRELLO_CARD="abc123XY"

./tools/ci_guard_trello.sh
```

### Bulk Operations

```bash
# Source utility functions
source docs/governance/trello_commands.sh

# Audit all Done cards
audit_done_list

# Find cards without artifacts
find_done_without_artifacts

# Check single card
validate_artifacts abc123XY
```

### PR Workflow

1. Complete work on feature branch
2. Ensure Trello card has "Artifacts" checklist complete
3. Create PR with `TRELLO_CARD=<shortLink>` in description
4. CI validates artifacts automatically
5. Merge only if "Trello Artifacts Guard" passes ✅

---

## Validation Patterns

The guard checks for these patterns:

| Artifact | Pattern | Example |
|----------|---------|---------|
| Demo URL | `https?://` | https://demo.example.com |
| Commit SHA | `[0-9a-f]{7,40}` | abc1234 or abc1234567890abcdef |
| Version Tag | `v[0-9]+\.[0-9]+\.[0-9]+` | v1.2.3 |
| Manifest | `manifest\.json` | https://example.com/manifest.json |

---

## Files

```
docs/governance/
├── README.md                  # This file
├── butler_rules.yaml          # Butler automation rules
└── trello_commands.sh         # Shell utility functions

tools/
└── ci_guard_trello.sh         # CI validation script

.github/
├── workflows/
│   └── trello-guard.yml       # GitHub Actions workflow
└── pull_request_template.md  # PR template with TRELLO_CARD field
```

---

## Troubleshooting

**Q: Butler not triggering?**
- Check board automation settings (free tier: 1 command/month limit)
- Test with dummy card first
- Verify checklist name is exactly "Artifacts"

**Q: CI failing even with complete checklist?**
- Ensure "Artifacts OK" label is present (green)
- Run `./tools/ci_guard_trello.sh` locally to debug
- Check patterns in card description/attachments

**Q: Need to bypass guard temporarily?**
- Manually add "Artifacts OK" label: `add_artifacts_ok_label <CARD_ID>`
- Or disable branch protection (not recommended)

---

## Philosophy: AURITY Governance

**Gobernanza ≠ burocracia**
- Minimal friction: Automated checks, no manual approvals
- Maximum evidence: Every Done card has verifiable artifacts
- Humanize the message: Clear errors, actionable instructions

**Done is auditable**
- No artifacts = No Done
- Traceability: demo → commit → manifest → evidence
- Non-repudiation: Butler comments timestamped, CI logs immutable

---

## Next Steps

1. Test Butler rules with dummy card
2. Run first PR with CI guard
3. Enable branch protection
4. Monitor audit logs weekly: `audit_done_list`
5. Adjust patterns if needed (edit `ci_guard_trello.sh`)
