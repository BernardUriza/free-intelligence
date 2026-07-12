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

// Curio (96): chat shell. Also importable via `fi-glass/shell`.
export * from './shell';

// Californio (98): configurable optionals. Persona selector is also importable
// via `fi-glass/persona-selector`; SpeakButton ships under `fi-glass/voice`.
export * from './persona-selector';

// The framework's ONE menu (extracted from aurity's toolbar — the SSOT of this
// anatomy). Both the shell toolbar ("⋮") and the composer ("+") render it.
export { ActionMenu, type MenuAction, type ActionMenuProps } from './menu/ActionMenu';
