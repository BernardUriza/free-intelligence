/**
 * "Actualizado hace 6 días" — og118's words (FIGLASS-PROJECTS-PAGE-1).
 *
 * fi-glass's cards take an already-formatted node precisely so the language
 * lives in the consumer. The case that earns a test is the BAD input: a missing
 * or unparseable timestamp must render nothing, because the naive alternative
 * (`new Date(x).toLocaleString()`) puts "Invalid Date" on a card.
 */

import { describe, expect, it } from 'vitest';
import { relativeTime } from '../og118RelativeTime';

const NOW = Date.parse('2026-08-22T12:00:00Z');

describe('relativeTime', () => {
  it('returns null for a missing timestamp instead of a phrase about 1970', () => {
    expect(relativeTime(undefined, NOW)).toBeNull();
    expect(relativeTime('', NOW)).toBeNull();
  });

  it('returns null for an unparseable timestamp instead of "Invalid Date"', () => {
    expect(relativeTime('no-soy-una-fecha', NOW)).toBeNull();
  });

  it('collapses the last few seconds into a phrase, not "hace 0 segundos"', () => {
    expect(relativeTime('2026-08-22T11:59:50Z', NOW)).toBe('hace un momento');
  });

  it('says days for a timestamp days old', () => {
    expect(relativeTime('2026-08-16T12:00:00Z', NOW)).toContain('6');
  });

  it('uses the natural word instead of "hace 1 día"', () => {
    expect(relativeTime('2026-08-21T12:00:00Z', NOW)).toBe('ayer');
  });

  it('handles a future timestamp (a clock skew) without throwing', () => {
    expect(relativeTime('2026-08-23T12:00:00Z', NOW)).toBe('mañana');
  });
});
