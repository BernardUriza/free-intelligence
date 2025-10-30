# Microcopys - Free Intelligence

**Card**: FI-UX-STR-001
**Tone**: Technical but friendly, no corporate fluff
**Date**: 2025-10-29

---

## Voice & Tone

**Principles**:
1. **Honest**: No marketing speak. If something failed, say why.
2. **Concise**: 1-2 sentences max. No walls of text.
3. **Technical**: Use correct terms (session, interaction, corpus) but explain when needed.
4. **Empathetic**: Acknowledge user frustration when things go wrong.

**Anti-patterns**:
- ❌ "Oops! Something went wrong 😅"
- ❌ "We're sorry for the inconvenience"
- ❌ "Please try again later"

**Good examples**:
- ✅ "Export failed: Disk 90% full. Free up 2GB or change location."
- ✅ "Session saved. Hash: a3f7d8e2..."
- ✅ "Network timeout after 5s. Retry with longer timeout?"

---

## Onboarding

### Welcome Screen
```
Welcome to Free Intelligence

Local-first knowledge management.
Your data stays on your machine.

[Get Started]
```

### Identity Setup
```
What should we call you?

Email or username (no password needed)

[____________]

This identifies your sessions.
You can change it later.

[Continue]
```

### First Session
```
Your First Session

Sessions group related thoughts.
Think of them as conversation threads.

Session name: [____________]

What's your first thought?
[________________________]
[________________________]

[Create Session]
```

### Export Test
```
Export Your Data

Free Intelligence is local-first.
You can export anytime, in any format.

Let's try exporting your first session.

Format:
◉ JSON (readable, portable)
○ HDF5 (binary, efficient)
○ Markdown (human-readable)

[Export]
```

### Onboarding Complete
```
✅ You're all set!

Your first session is ready.
View it in Timeline or create more.

[Go to Timeline] [New Session]
```

---

## Timeline

### Empty State
```
No sessions yet.

Create your first session to start tracking thoughts.

[+ New Session]
```

### Loading
```
Loading sessions...
```

### Session Card (Collapsed)
```
session_20251029_140530
14 interactions · Last updated 2 hours ago
⭐ Pinned · 🏷️ bug, p0

[Expand] [Export] [Verify]
```

### Session Card (Expanded)
```
session_20251029_140530
Created: 2025-10-29 14:05:30
Updated: 2025-10-29 16:23:15
Interactions: 14
Hash: a3f7d8e2... (verified)

Interactions:
  1. user_message · 14:05
     "Claude Code no muestra todo items"
     [Pin] [Tag] [Copy] [Verify]

  2. extraction_started · 14:05
     {model: "claude-3-5-sonnet-20241022", ...}
     [Pin] [Tag] [Copy] [Verify]

[Collapse] [Export Session] [Delete]
```

---

## Actions

### Pin Success
```
⭐ Pinned

Interaction pinned to top of Timeline.

[Undo]
```

### Tag Added
```
🏷️ Tagged: bug, p0

Tags help filter Timeline.

[Undo]
```

### Copy Success
```
📋 Copied to clipboard

Interaction content copied.
```

### Export Progress
```
Exporting session_20251029_140530...

Generating manifest... ✅
Computing hashes... 🔄 (2/5)
Applying policies... ⏳
Writing to disk... ⏳

ETA: 3 seconds
```

### Export Success
```
✅ Exported!

Saved to: ~/Downloads/session_20251029_140530.json
Hash: a3f7d8e2f9c1...

[View in Finder] [Verify Export]
```

### Verify Success
```
✅ Session verified!

Hash: a3f7d8e2... ✅ Verified
Policy: ✅ Compliant
Audit: ✅ Logged
Redaction: N/A

No tampering detected.

[View in Timeline]
```

### Delete Confirmation
```
⚠️ Delete Session?

This will permanently delete:
• session_20251029_140530
• 14 interactions
• All metadata

This cannot be undone.

[Cancel] [Delete Permanently]
```

### Delete Success
```
🗑️ Session deleted

session_20251029_140530 removed from corpus.

Undo not available (append-only policy).
```

---

## Errors

### Network Timeout
```
⚠️ Network timeout

Request took >5 seconds.

Possible causes:
• LLM API slow
• Large corpus file
• Network congestion

[Retry] [Increase Timeout]
```

### Disk Full
```
⚠️ Export failed

Disk 90% full (8.9GB / 10GB used).

Action needed:
• Free up 2GB space, or
• Change export location

[Free Space] [Change Location]
```

### Invalid Session
```
❌ Session not found

session_20251029_140530 doesn't exist in corpus.

Possible causes:
• Typo in session ID
• Session was deleted
• Corpus file corrupted

[Go to Timeline] [Create New Session]
```

### Hash Mismatch
```
❌ Verification failed

Expected hash: a3f7d8e2...
Actual hash:   f9c12a45...

This indicates tampering or corruption.

[View Details] [Report Issue]
```

### Corpus Locked
```
⚠️ Corpus locked

Another process is writing to corpus.h5.

Wait for operation to complete (~30s).

[Retry] [Force Unlock (Risky)]
```

### LLM API Error
```
⚠️ LLM request failed

Model: claude-3-5-sonnet-20241022
Error: 429 Too Many Requests

Rate limit exceeded. Retry in 60 seconds.

[Retry Now] [Wait 60s]
```

### Policy Violation
```
❌ Policy violation

Action blocked by mutation_policy.yml:

Rule: no_delete_before_30_days
Session age: 12 days (18 days remaining)

Override requires admin approval.

[Cancel] [Request Override]
```

---

## Friday Review

### Friday Notification
```
📅 Friday Review

It's Friday 4pm. Time to reflect.

This week you:
• Created 12 sessions
• Wrote 87 interactions
• Exported 3 times

Want to do a quick review?

[Start Review] [Skip This Week] [Remind Me at 5pm]
```

### Friday Review Form
```
📅 Friday Review

Most active sessions this week:
1. session_20251024_093021 (15 interactions)
2. session_20251027_141207 (12 interactions)
3. session_20251028_163544 (10 interactions)

What went well this week?
[_______________________________]

What could improve?
[_______________________________]

Goals for next week?
[_______________________________]

[Save Reflection] [Skip]
```

### Review Saved
```
✅ Reflection saved

Your Friday review is saved as:
interaction_reflection_20251029_160000

Tagged with: friday-review

[View in Timeline] [Done]
```

---

## Settings

### Identity Changed
```
✅ Identity updated

New identity: bernard@example.com

This affects future sessions.
Existing sessions unchanged.

[OK]
```

### Export Location Changed
```
✅ Export location updated

New location: ~/Documents/exports/

Future exports will save here.

[OK]
```

### Policy Updated
```
✅ Policy updated

mutation_policy.yml changes applied.

Affected rules:
• no_delete_before_30_days → 7_days

[View Policy] [OK]
```

---

## Help & Tooltips

### Session ID (Tooltip)
```
Session ID

Format: session_YYYYMMDD_HHMMSS

Unique identifier for this session.
Used for export, verify, and API calls.
```

### Content Hash (Tooltip)
```
Content Hash

SHA256 hash of interaction content.

Used to verify data integrity.
Any tampering changes the hash.

Format: hex string (64 chars)
```

### Corpus (Tooltip)
```
Corpus

HDF5 file storing all sessions.

Location: storage/corpus.h5
Mode: Append-only (no mutations)

Think of it as your knowledge database.
```

### Append-Only (Tooltip)
```
Append-Only

New data can be added.
Existing data cannot be modified or deleted.

This ensures:
• Data integrity
• Audit trail
• No accidental loss

Deletion requires policy approval.
```

### Policy-as-Code (Tooltip)
```
Policy-as-Code

Rules defined in YAML files.

Examples:
• mutation_policy.yml (what can be modified)
• llm_policy.yml (which models allowed)
• export_policy.yml (redaction rules)

Policies are versioned and auditable.
```

---

## Status Indicators

### Badge: Hash Verified
```
✅ Hash Verified

Content hash matches expected value.
No tampering detected.
```

### Badge: Policy Compliant
```
✅ Policy Compliant

Action follows all policies.
No violations detected.
```

### Badge: Audit Logged
```
✅ Audit Logged

Action recorded in audit trail.
Timestamp: 2025-10-29 16:23:15
```

### Badge: Redaction Applied
```
✅ Redaction Applied

Sensitive fields removed per export policy.
See manifest for details.
```

### Badge: Pending
```
⏳ Pending

Verification in progress...
```

### Badge: Failed
```
❌ Failed

Verification failed.
[View Details]
```

---

## Search

### Search Empty
```
No results for "bug"

Try:
• Check spelling
• Use different keywords
• Remove filters

[Clear Search]
```

### Search Results
```
Found 12 results for "bug"

Showing results from:
• 3 sessions
• 12 interactions

Filter by:
[ ] Pinned only
[ ] Tagged: bug
[ ] Last 7 days

[Clear Filters]
```

---

## Keyboard Shortcuts

### Shortcuts Panel (Cmd+/)
```
Keyboard Shortcuts

Navigation:
Cmd+K    Search
Cmd+N    New Session
Cmd+E    Export

Timeline:
p        Pin/Unpin
t        Tag
c        Copy

Other:
Cmd+/    Toggle shortcuts panel
Esc      Close modal

[Close]
```

---

## Implementation Notes

**File Location**: `apps/aurity/lib/microcopys.ts`

```typescript
export const MICROCOPYS = {
  onboarding: {
    welcome: "Welcome to Free Intelligence\n\nLocal-first knowledge management.\nYour data stays on your machine.",
    identitySetup: "What should we call you?\n\nEmail or username (no password needed)",
    // ...
  },
  timeline: {
    empty: "No sessions yet.\n\nCreate your first session to start tracking thoughts.",
    loading: "Loading sessions...",
    // ...
  },
  errors: {
    networkTimeout: "⚠️ Network timeout\n\nRequest took >5 seconds.",
    diskFull: "⚠️ Export failed\n\nDisk 90% full (8.9GB / 10GB used).",
    // ...
  },
  // ...
}
```

**Usage**:
```tsx
import { MICROCOPYS } from '@/lib/microcopys';

<p>{MICROCOPYS.timeline.empty}</p>
```

---

_"Palabras precisas para interfaces claras."_
