# B3-FIGLASS-SHELL-PRIMITIVES-AUDIT-1 — read-only audit of og118 `globals.css`

Status: Done (audit only — no behavior touched)
Produced: 2026-06-24 by Claude (via `/exchange-coagent`, coagent-ordered)
Parent: [[b3-figlass-shell-primitives]] · Gate: security surface CLEAR (2026-06-24)

## Scope

Read-only classification of every `og-*` selector in
`apps/og118/web/app/globals.css` (486 LOC, 47 unique class selectors) into
{reusable layout, reusable interaction state, product semantic, branding/token,
dead/legacy}, each mapped to the component that applies it and to a proposed
fi-glass primitive. **No CSS moved, no component changed.** This is the
classification step before the incremental extraction PRs (1A → 1D).

## The line (restated, then proven below)

**Rises to fi-glass** — the *anatomy* of a sidebar/resource shell: rail layout,
section (header + action + empty-state + list), row/item (selected/hover/active,
title/subtitle/meta slots, inline-rename affordance, destructive action revealed
on hover/touch with the coarse-pointer fallback), composer action rail + slots.
**Stays in og118** — the *meaning*: what a Project is, conversations, the corpus,
Auth0, voice, the privacy copy, and every brand color (emerald, the gradients).
fi-glass renders a resource list with actions; og118 decides those resources are
projects/conversations and what they do.

## The un-fakeable proof

`.og-chat-item` and `.og-project-item` are structurally identical: both `flex`
row, same padding/`border-radius`/transparent border, same `.is-active`
(emerald-tint bg + border), same `:hover` bg lift, same delete button at
`opacity:0` revealed by `:hover` AND by `@media (pointer: coarse)`. Two consumers
of the SAME skeleton, hand-written twice. That is the framework-leak (Art. 6) the
extraction repays — and it confirms the item primitive is real, not a chat-item
disguised as a project-item.

## Inventory — selector → component → CSS role → class → target primitive

### Composer (Og118AgentChat.tsx) — 5 selectors
| selector | CSS role | class | target |
|---|---|---|---|
| `og-composer-box:focus-within` | focus ring affordance | **reusable interaction** | `ComposerBox` focus state (token-tinted) |
| `og-composer-area` | textarea-area padding | **reusable layout** | `ComposerToolbar` / area slot |
| `og-composer-controls` | controls-row padding | **reusable layout** | `ComposerActionRail` |
| `og-send-btn` | flex/disabled/hover *structure* | **reusable interaction** | `ComposerPrimaryAction` slot |
| `og-send-btn` gradient + `og-send-icon` color | emerald gradient | **branding/token** | stays og118 (token) |

### Sidebar rail + conversation list (Og118Sidebar.tsx) — 14 selectors
| selector | CSS role | class | target |
|---|---|---|---|
| `og-sidebar` | rail container (border-right + backdrop) | **reusable layout** | `AgentSidebarRail` |
| `og-sidebar-head` | section header row | **reusable layout** | `AgentSidebarSection` header |
| `og-sidebar-title` | header label | **reusable layout** | section title slot |
| `og-sidebar-new` | header action button *structure* | **reusable layout** + token color | `ItemActionSlot` (header) |
| `og-sidebar-list` | scroll list | **reusable layout** | section list |
| `og-chat-item` | row (flex/pad/radius) | **reusable layout** | `AgentSidebarItem` |
| `og-chat-item.is-active` | selected state | **reusable interaction** | item `selected` (token tint) |
| `og-chat-item:hover` | hover lift | **reusable interaction** | item hover |
| `og-chat-item-main` | title+meta column | **reusable layout** | item body slot |
| `og-chat-item-title` | title ellipsis | **reusable layout** | item title slot |
| `og-chat-item-preview` | subtitle ellipsis | **reusable layout** | item subtitle slot |
| `og-chat-item-time` | meta line | **reusable layout** | item meta slot |
| `og-chat-item-del` (+coarse) | destructive, reveal on hover/touch | **reusable interaction** | `DestructiveActionSlot` |
| `og-chat-item-rename-btn` (+coarse) | edit affordance reveal | **reusable interaction** | `EditableResourceItem` trigger |
| `og-chat-item-rename` | inline edit input | **reusable interaction** | `EditableResourceItem` input |
| `og-sidebar-privacy` | privacy copy | **product semantic** | stays og118 |

### Projects section (Og118ProjectsSection.tsx) — 9 selectors
| selector | CSS role | class | target |
|---|---|---|---|
| `og-projects` | section container | **reusable layout** | `AgentSidebarSection` (resource variant) |
| `og-projects-head` | header row | **reusable layout** | `AgentSidebarSection` header |
| `og-projects-title` | header label | **reusable layout** | section title slot |
| `og-projects-new` | header action *structure* | **reusable layout** + token | `ItemActionSlot` (header) |
| `og-projects-empty` | empty state | **reusable layout** | `ResourceListEmptyState` |
| `og-projects-list` | scroll list (max-height) | **reusable layout** | section list |
| `og-project-item` (+ is-active/hover) | row — TWIN of `og-chat-item` | **reusable layout+interaction** | `AgentResourceItem` (= `AgentSidebarItem`) |
| `og-project-item-name` | name ellipsis | **reusable layout** | item title slot |
| `og-project-item-del` (+coarse) | destructive reveal | **reusable interaction** | `DestructiveActionSlot` |
| ("Projects"/upload/corpus meaning) | — | **product semantic** | stays og118 |

### Auth banner (Og118AuthBanner.tsx) — 5 selectors
| selector | class | target |
|---|---|---|
| `og-auth-banner` + `-label/-row/-input/-save` | **product semantic** (Auth0) + danger token | stays og118 — generic form-banner shell could extract LATER, not now (auth is clearly product) |

### Voice (Og118VoiceErrorBanner.tsx + useOg118VoiceComposer.tsx) — 8 selectors
| selector | class | target |
|---|---|---|
| `og-voice-bar` | **reusable layout** (above-composer slot) — low priority | `ComposerAboveSlot` (candidate) |
| `og-voice-player/-progress/-visualizer/-bar-bar` | **product semantic** (voice) — content via existing RichAudioPlayer/AudioVisualizer primitives | stays og118 (layout/color only) |
| `og-voice-error-banner/-text/-dismiss` | **reusable interaction** (dismissable notice) — low priority | `DismissableBanner` (candidate) |

### Mic (useOg118VoiceComposer.tsx) — 5 selectors
| selector | class | target |
|---|---|---|
| `og-mic-slot button` / `og-mic-btn` / `og-durable-mic` | **product semantic** (voice) + branding color — already consumes fi-glass `ComposerMicSlot` | stays og118 (color/layout override) |
| `og-mic-saving` / `og-mic-saving-spinner` | **product semantic** | stays og118 |

### Misc — 1 selector
| selector | class | target |
|---|---|---|
| `og-loading` | **reusable layout** (centered state) — trivial | `AgentLoadingState` (low priority) |

### Tokens (`:root` + `body.glass-chat`)
`--og-bg-*`, `--og-accent*`, `--og-danger*`, `--og-warning*`, the
`glass-chat` re-tints → **branding/token**, stay in og118 (this is the correct
consumer-owns-brand pattern already; B3-FIGLASS-13).

### Dead/legacy
No dead *families* found — every `og-*` family is applied by a live component.
Per-selector dead check (individual unused rules) deferred to each extraction PR,
where "every PR must REDUCE og118 CSS" makes a leftover obvious.

## Tally
- **Reusable (layout + interaction): ~30 selectors** across sidebar/section/item/
  composer — the extraction target.
- **Product semantic: ~12** (auth, voice content, mic, privacy copy, Projects meaning).
- **Branding/token: ~8** (the `:root` vars + gradients + per-button accent color).
- **Dead: 0 families.**

## Incremental PR plan (coagent's cut, validated by this inventory)

Every PR must REDUCE og118 CSS, gain a token-themed fi-glass primitive, and keep
slate/paper able to use it with zero og118 knowledge. Order:

- **1A — `AgentSidebarItem` + `EditableResourceItem` + `ItemActionSlot` + `DestructiveActionSlot`.**
  Canary: og118 conversation list (the `og-chat-item*` family, INCLUDING the
  `#283` rename affordance which is already sitting in the consumer). Highest
  value: the rename PR just sedimented the inline-edit CSS here.
- **1B — Projects section adopts the SAME item.** Canary: `og-project-item*`
  re-points at `AgentResourceItem`. Proves the item isn't chat-specific (the twin
  proof above becomes a shared primitive).
- **1C — `AgentSidebarSection`** (header + action + empty-state + list spacing +
  responsive). Both `og-sidebar-head`/`og-projects-head` collapse into it.
- **1D — composer slots** (`ComposerActionRail` + `ComposerPrimaryAction` + focus
  state). Lower priority; only if it doesn't drag in voice.

NOT in this arc: auth banner (product), voice content (product), Projects/corpus
meaning (product), the `AgentRoster`/`PersonaSelector` (Elements, separate). The
identity-scoped-store docs (`B3-FIGLASS-IDENTITY-STORES-DOCS-1`) are the next P1,
not mixed in here.

## Owner decision (Bernard's)
Greenlight to open **1A** (the conversation-list item primitive) is the only
gate left — the security blocker is gone. Recommended first because `#283`
already created the pressure on `ConversationListItem`/rename.
