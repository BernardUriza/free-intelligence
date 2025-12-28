/**
 * Free Intelligence - Demo Module
 *
 * Exports for deterministic demo dataset generation.
 *
 * File: lib/demo/index.ts
 * Card: FI-UI-FEAT-207
 * Created: 2025-10-30
 */

export { PRNG } from './prng';
export { DemoAdapter, parseDemoConfig } from './adapter';
export {
  generateDemoDataset,
  generateSessionSummary,
  generateSessionDetail,
  generateManifest,
} from './generator';
export type {
  DemoConfig,
  DemoManifest,
  EventsProfileWeights,
  SpeakerTemplate,
  EventKind,
  TextCorpus,
} from './types';
