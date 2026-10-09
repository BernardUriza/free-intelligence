/**
 * Tests for the sidebar timestamp locale (B3-OG118-5).
 *
 * The audit showed "Jun 11, 12:18 AM" (browser locale, 12h) inside a fully
 * Spanish UI. shortTime is now pinned to es-MX 24h, independent of the
 * browser/system locale.
 */

import { describe, it, expect } from 'vitest';
import { releaseLabel, shortTime, syncNote } from '../Og118Sidebar';

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

describe('syncNote', () => {
  it('never claims "local" while a signed-in account is still reaching its server', () => {
    expect(syncNote('connecting', false)).not.toMatch(/localmente/);
    expect(syncNote('connecting', true)).toMatch(/Despertando el servidor/);
  });

  it('says where writes land when the account server is unreachable', () => {
    expect(syncNote('unreachable', false)).toMatch(/se guarda en este navegador y se sube al reconectar/);
  });

  it('keeps the cloud and local copy for the settled states', () => {
    expect(syncNote('cloud', false)).toMatch(/Sincronizado en tu cuenta/);
    expect(syncNote('local', false)).toBe('Guardado localmente en este navegador.');
  });
});

describe('releaseLabel', () => {
  it('shows the short commit and the release date in 24h Spanish, short enough to share the header row', () => {
    const out = releaseLabel('48e0ff55d1c2a9b0', '2026-10-09T15:28:00');
    expect(out).toMatch(/^48e0ff5 · /);
    expect(out.toLowerCase()).toContain('oct');
    expect(out.length).toBeLessThanOrEqual(22);
    expect(out).toContain('15:28');
  });

  it('falls back to "dev" with no commit and to the bare version with no date', () => {
    expect(releaseLabel(undefined, undefined)).toBe('dev');
    expect(releaseLabel('48e0ff55', 'garbage')).toBe('48e0ff5');
  });
});
