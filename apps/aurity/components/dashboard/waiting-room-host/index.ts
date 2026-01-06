/**
 * WaitingRoomHost - Waiting Room Display System
 *
 * SOLID Architecture:
 * - types.ts: Interface definitions
 * - services/: API and caching logic
 * - hooks/: State management
 * - components/: Presentational subcomponents
 * - WaitingRoomHost.tsx: Main orchestrator
 */

// Main component
export { WaitingRoomHost } from './WaitingRoomHost';

// Types
export type {
  ContentItem,
  ClinicSlide,
  WaitingRoomHostProps,
  WidgetType,
} from './types';

// Hook (for advanced usage)
export { useWaitingRoomContent } from './hooks/useWaitingRoomContent';

// Services (for advanced usage)
export {
  fetchContentSeeds,
  fetchDynamicTip,
  fetchDynamicTrivia,
  buildMediaUrl,
} from './services/content-api';

export { ContentCache, contentCache } from './services/content-cache';

// Subcomponents (for custom compositions)
export { AvatarIndicator } from './components/AvatarIndicator';
export { ContentRenderer } from './components/ContentRenderer';
export { ProgressIndicator } from './components/ProgressIndicator';
export { InteractiveHint } from './components/InteractiveHint';
export { ClinicFooter } from './components/ClinicFooter';
