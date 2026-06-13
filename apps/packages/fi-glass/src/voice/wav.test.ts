/**
 * mergeWavBlobs (B3-VOICE-FIGLASS-18) — WAV segment splicing contract.
 *
 * Segmented pause stops the recorder at each pause, so a session is N complete
 * WAVs that must splice into ONE playable/transcribable WAV. Pinned here:
 *  - single segment passes through untouched (no parse, no copy);
 *  - merged output = one canonical header + concatenated PCM, with correct
 *    RIFF/data sizes (what makes the duration readout real, not "--:--");
 *  - mismatched formats and non-WAV input throw instead of splicing garbage.
 */

import { describe, it, expect } from 'vitest';
import { mergeWavBlobs } from './wav';

/** Minimal canonical PCM WAV: 44-byte header + the given samples. */
function makeWav(
  pcm: number[],
  { sampleRate = 16000, channels = 1, bits = 16 } = {},
): Blob {
  const header = new ArrayBuffer(44);
  const view = new DataView(header);
  const writeFourCC = (offset: number, s: string) => {
    for (let i = 0; i < 4; i++) view.setUint8(offset + i, s.charCodeAt(i));
  };
  const data = new Uint8Array(pcm);
  writeFourCC(0, 'RIFF');
  view.setUint32(4, 36 + data.byteLength, true);
  writeFourCC(8, 'WAVE');
  writeFourCC(12, 'fmt ');
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, (sampleRate * channels * bits) / 8, true);
  view.setUint16(32, (channels * bits) / 8, true);
  view.setUint16(34, bits, true);
  writeFourCC(36, 'data');
  view.setUint32(40, data.byteLength, true);
  return new Blob([header, data], { type: 'audio/wav' });
}

async function parseOut(blob: Blob) {
  const buf = await blob.arrayBuffer();
  const view = new DataView(buf);
  return {
    riff: String.fromCharCode(view.getUint8(0), view.getUint8(1), view.getUint8(2), view.getUint8(3)),
    riffSize: view.getUint32(4, true),
    sampleRate: view.getUint32(24, true),
    dataSize: view.getUint32(40, true),
    data: [...new Uint8Array(buf.slice(44))],
  };
}

describe('mergeWavBlobs', () => {
  it('returns a single segment as-is (identity, no re-encode)', async () => {
    const wav = makeWav([1, 2, 3, 4]);
    const merged = await mergeWavBlobs([wav]);
    expect(merged).toBe(wav);
  });

  it('splices two segments into one WAV with concatenated PCM', async () => {
    const merged = await mergeWavBlobs([makeWav([1, 2, 3, 4]), makeWav([5, 6])]);
    const out = await parseOut(merged);
    expect(out.riff).toBe('RIFF');
    expect(out.data).toEqual([1, 2, 3, 4, 5, 6]);
    expect(out.dataSize).toBe(6);
    expect(out.riffSize).toBe(36 + 6);
    expect(merged.type).toBe('audio/wav');
  });

  it('preserves the format of the first segment', async () => {
    const merged = await mergeWavBlobs([makeWav([1, 2]), makeWav([3, 4])]);
    const out = await parseOut(merged);
    expect(out.sampleRate).toBe(16000);
  });

  it('splices three segments in order', async () => {
    const merged = await mergeWavBlobs([
      makeWav([10, 11]),
      makeWav([20]),
      makeWav([30, 31, 32]),
    ]);
    const out = await parseOut(merged);
    expect(out.data).toEqual([10, 11, 20, 30, 31, 32]);
  });

  it('throws on mismatched sample rates instead of splicing garbage', async () => {
    await expect(
      mergeWavBlobs([makeWav([1, 2]), makeWav([3, 4], { sampleRate: 44100 })]),
    ).rejects.toThrow(/mismatched/i);
  });

  it('throws on non-WAV input', async () => {
    await expect(
      mergeWavBlobs([new Blob(['not a wav']), makeWav([1, 2])]),
    ).rejects.toThrow(/RIFF/i);
  });

  it('throws on an empty segment list', async () => {
    await expect(mergeWavBlobs([])).rejects.toThrow(/No WAV segments/i);
  });
});
