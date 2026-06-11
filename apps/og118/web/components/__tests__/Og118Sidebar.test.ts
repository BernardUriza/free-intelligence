/**
 * Tests for the sidebar timestamp locale (B3-OG118-5).
 *
 * The audit showed "Jun 11, 12:18 AM" (browser locale, 12h) inside a fully
 * Spanish UI. shortTime is now pinned to es-MX 24h, independent of the
 * browser/system locale.
 */

import { describe, it, expect } from 'vitest';
import { shortTime } from '../Og118Sidebar';

describe('shortTime', () => {
  it('formats in Spanish (es-MX), not the browser locale', () => {
    const out = shortTime('2026-06-11T00:18:00');
    // Spanish month abbreviation, no English "Jun 11"-style ordering artifacts.
    expect(out.toLowerCase()).toContain('jun');
    expect(out).not.toMatch(/AM|PM/i);
  });

  it('uses a 24h clock (no AM/PM, midnight hour rendered as 00)', () => {
    const out = shortTime('2026-06-11T00:18:00');
    expect(out).toContain('00:18');
  });

  it('renders an afternoon hour without AM/PM', () => {
    const out = shortTime('2026-06-11T15:05:00');
    expect(out).toContain('15:05');
    expect(out).not.toMatch(/AM|PM/i);
  });

  it('returns empty string for an invalid date', () => {
    expect(shortTime('garbage')).toBe('');
  });
});
