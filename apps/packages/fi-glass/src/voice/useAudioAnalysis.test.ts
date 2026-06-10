import { describe, it, expect } from 'vitest';
import { frequencyDataToBands } from './useAudioAnalysis';

describe('frequencyDataToBands', () => {
  it('returns exactly bandCount entries', () => {
    const data = new Uint8Array(128).fill(100);
    expect(frequencyDataToBands(data, 24, 1)).toHaveLength(24);
    expect(frequencyDataToBands(data, 8, 1)).toHaveLength(8);
  });

  it('normalizes 0-255 byte data into 0..1 (no gain)', () => {
    const data = new Uint8Array(128).fill(255);
    const bands = frequencyDataToBands(data, 4, 1);
    // Full-scale bins → ~1.0 per band (within the usable range).
    bands.forEach((b) => expect(b).toBeCloseTo(1, 5));
  });

  it('maps mid-level data proportionally', () => {
    const data = new Uint8Array(128).fill(128);
    const bands = frequencyDataToBands(data, 4, 1);
    bands.forEach((b) => expect(b).toBeCloseTo(128 / 255, 2));
  });

  it('applies gain and clamps to a 1.0 ceiling', () => {
    const data = new Uint8Array(128).fill(128); // ~0.5 raw
    const bands = frequencyDataToBands(data, 4, 2.5); // 0.5 * 2.5 = 1.25 → clamp
    bands.forEach((b) => expect(b).toBe(1));
  });

  it('produces a varying spectrum, not one flat value', () => {
    // Energy concentrated in low bins → low bands hot, high bands cold.
    const data = new Uint8Array(128).fill(0);
    for (let i = 0; i < 16; i++) data[i] = 255;
    const bands = frequencyDataToBands(data, 8, 1);
    expect(bands[0]).toBeGreaterThan(bands[bands.length - 1]);
  });

  it('returns zeros for empty data', () => {
    expect(frequencyDataToBands(new Uint8Array(0), 4, 1)).toEqual([0, 0, 0, 0]);
  });

  it('returns an empty array for non-positive bandCount', () => {
    expect(frequencyDataToBands(new Uint8Array(128).fill(100), 0, 1)).toEqual([]);
  });
});
