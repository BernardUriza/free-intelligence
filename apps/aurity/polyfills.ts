// @ts-nocheck - Temporal polyfill types may vary by version
import { Temporal } from '@js-temporal/polyfill';

// Ensure Temporal is available across both server and client before any date logic runs.
// Install global Temporal polyfill
if (typeof globalThis !== 'undefined' && !(globalThis as Record<string, unknown>).Temporal) {
  (globalThis as Record<string, unknown>).Temporal = Temporal;
}
