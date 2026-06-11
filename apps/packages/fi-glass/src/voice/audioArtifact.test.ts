// @vitest-environment node
import { describe, it, expect } from 'vitest';
import {
  makeArtifactId,
  isPending,
  isTerminal,
  artifactLabel,
  formatArtifactSize,
  formatArtifactDuration,
  type AudioArtifact,
} from './audioArtifact';

const BASE: AudioArtifact = {
  id: 'a1',
  mime: 'audio/wav',
  size: 1024,
  createdAt: '2026-06-11T00:00:00.000Z',
  updatedAt: '2026-06-11T00:00:00.000Z',
  state: 'queued',
};

describe('makeArtifactId', () => {
  it('produces unique ids', () => {
    const ids = new Set(Array.from({ length: 100 }, makeArtifactId));
    expect(ids.size).toBe(100);
  });
  it('starts with audio-', () => {
    expect(makeArtifactId()).toMatch(/^audio-\d+-[a-z0-9]+$/);
  });
});

describe('isPending / isTerminal', () => {
  const terminal: AudioArtifact['state'][] = ['transcribed', 'deleted'];
  const pending: AudioArtifact['state'][] = [
    'recording', 'paused', 'saved', 'queued', 'uploading', 'transcribing', 'failed',
  ];

  for (const s of pending) {
    it(`isPending(${s}) = true`, () => {
      expect(isPending({ ...BASE, state: s })).toBe(true);
    });
    it(`isTerminal(${s}) = false`, () => {
      expect(isTerminal({ ...BASE, state: s })).toBe(false);
    });
  }
  for (const s of terminal) {
    it(`isPending(${s}) = false`, () => {
      expect(isPending({ ...BASE, state: s })).toBe(false);
    });
    it(`isTerminal(${s}) = true`, () => {
      expect(isTerminal({ ...BASE, state: s })).toBe(true);
    });
  }
});

describe('artifactLabel', () => {
  it('returns Spanish label for every state', () => {
    const states: AudioArtifact['state'][] = [
      'recording', 'paused', 'saved', 'queued', 'uploading',
      'transcribing', 'transcribed', 'failed', 'deleted',
    ];
    for (const s of states) {
      const label = artifactLabel(s);
      expect(label).toBeTruthy();
      expect(typeof label).toBe('string');
    }
  });
});

describe('formatArtifactSize', () => {
  it('bytes < 1KB', () => expect(formatArtifactSize(512)).toBe('512 B'));
  it('bytes in KB range', () => expect(formatArtifactSize(2048)).toBe('2.0 KB'));
  it('bytes in MB range', () => expect(formatArtifactSize(2 * 1024 * 1024)).toBe('2.0 MB'));
});

describe('formatArtifactDuration', () => {
  it('undefined → --:--', () => expect(formatArtifactDuration(undefined)).toBe('--:--'));
  it('0 → --:-- (treated as no duration)', () => expect(formatArtifactDuration(0)).toBe('--:--'));
  it('90s → 01:30', () => expect(formatArtifactDuration(90_000)).toBe('01:30'));
  it('3600s → 60:00', () => expect(formatArtifactDuration(3_600_000)).toBe('60:00'));
});
