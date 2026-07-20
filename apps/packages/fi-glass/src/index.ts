// fi-glass — public surface.
// Phase 1 ships the glass theme (tokens + values). Later phases add the chat
// shell (from aurity) and the agentic UI layer (from insult_ai), all rendered
// as frosted glass surfaces bound to core's event contract.
export { glassTheme } from './theme/glass-theme';

// Plutonio (94): message primitives. Also importable via `fi-glass/messages`.
export * from './messages';

// Americio (95): composer. Also importable via `fi-glass/composer`.
export * from './composer';

// Americio (95): voice presentation. Also importable via `fi-glass/voice`.
export * from './voice';

// Curio (96): cross-surface primitives (touch target, media query, file
// preview, the shared type vocabulary). Also importable via `fi-glass/shell`.
// The ChatWidget orchestrator that used to live here now lives in aurity, its
// only consumer (B3-FIGLASS-SHELL-CONSOLIDATION-1).
export * from './shell';

// Berkelio (97): the AGENTIC surface — the one og118 actually renders.
//
// This barrel used to export the legacy chat orchestrator and NOT this. The
// public front door of the framework advertised the dead system and hid the
// live one; every real consumer had to know to reach past it into the
// `fi-glass/agent` subpath. Fixed here — the subpath keeps working.
export * from './agent';

// Californio (98): configurable optionals. Persona selector is also importable
// via `fi-glass/persona-selector`; SpeakButton ships under `fi-glass/voice`.
export * from './persona-selector';

// The framework's ONE menu (extracted from aurity's toolbar — the SSOT of this
// anatomy). Both the shell toolbar ("⋮") and the composer ("+") render it.
export { ActionMenu, type MenuAction, type ActionMenuProps } from './menu/ActionMenu';
