/**
 * The recorder machine, exercised without MediaRecorder, streams or IndexedDB.
 *
 * These are the transitions that used to be implicit in the ORDER of five
 * `updateArtifact` calls scattered across the hook — which meant no transition
 * could be illegal, and a double-tapped button could write a state the recorder
 * could not honour.
 */

import { describe, it, expect } from 'vitest';
import {
  recordingReducer,
  canRecordingTransition,
  isRecordingActive,
  isQueueAtCapacity,
} from './durableRecordingMachine';
import { AUDIO_QUEUE_DEFAULTS } from './audioArtifact';
import type { AudioArtifact, AudioArtifactState } from './audioArtifact';

const artifact = (state: AudioArtifactState, size = 1): AudioArtifact =>
  ({
    id: `a-${Math.abs(size)}-${state}`,
    mime: 'audio/wav',
    size,
    state,
    durationMs: 1000,
    createdAt: '2026-01-01T00:00:00.000Z',
    updatedAt: '2026-01-01T00:00:00.000Z',
  }) as AudioArtifact;

describe('the legal recording flow', () => {
  it('record -> pause -> resume -> stop -> queued', () => {
    let s: AudioArtifactState = recordingReducer('queued', 'record.started');
    expect(s).toBe('recording');
    s = recordingReducer(s, 'pause.requested');
    expect(s).toBe('paused');
    s = recordingReducer(s, 'resume.requested');
    expect(s).toBe('recording');
    s = recordingReducer(s, 'stop.requested');
    expect(s).toBe('stopping');
    s = recordingReducer(s, 'stop.settled');
    expect(s).toBe('queued');
  });

  it('can stop straight from paused without resuming first', () => {
    expect(recordingReducer('paused', 'stop.requested')).toBe('stopping');
  });
});

describe('illegal asks are no-ops, never state corruption', () => {
  it('the async stop is NOT interruptible — pause/resume mid-flush are ignored', () => {
    // The flush is collecting the final segment; applying either of these would
    // lose audio that exists nowhere else.
    expect(recordingReducer('stopping', 'pause.requested')).toBe('stopping');
    expect(recordingReducer('stopping', 'resume.requested')).toBe('stopping');
  });

  it('a double-tapped pause does not fall through to another state', () => {
    const once = recordingReducer('recording', 'pause.requested');
    expect(recordingReducer(once, 'pause.requested')).toBe('paused');
  });

  it('resume is meaningless while already recording', () => {
    expect(recordingReducer('recording', 'resume.requested')).toBe('recording');
  });

  it('a settled artifact cannot be resumed back to life', () => {
    for (const settled of ['queued', 'archived', 'transcribed', 'failed'] as const) {
      expect(recordingReducer(settled, 'resume.requested')).toBe(settled);
      expect(recordingReducer(settled, 'pause.requested')).toBe(settled);
    }
  });

  it('cancel and error terminate from any LIVE state and no other', () => {
    for (const live of ['recording', 'paused', 'stopping'] as const) {
      expect(recordingReducer(live, 'cancel.requested')).toBe('deleted');
      expect(recordingReducer(live, 'error.raised')).toBe('failed');
    }
    // A queued artifact is already the user's; cancelling a recording must not
    // reach back and delete it.
    expect(recordingReducer('queued', 'cancel.requested')).toBe('queued');
    expect(recordingReducer('archived', 'error.raised')).toBe('archived');
  });
});

describe('canRecordingTransition drives control state', () => {
  it('reports exactly whether the event would move the machine', () => {
    expect(canRecordingTransition('recording', 'pause.requested')).toBe(true);
    expect(canRecordingTransition('stopping', 'pause.requested')).toBe(false);
    expect(canRecordingTransition('queued', 'stop.requested')).toBe(false);
  });
});

describe('isRecordingActive', () => {
  it('covers the live states and excludes the settled ones', () => {
    const live: AudioArtifactState[] = ['recording', 'paused', 'stopping'];
    const settled: AudioArtifactState[] = ['queued', 'archived', 'failed', 'deleted'];
    expect(live.every(isRecordingActive)).toBe(true);
    expect(settled.some(isRecordingActive)).toBe(false);
  });
});

describe('queue capacity, without an IndexedDB round-trip', () => {
  const policy = { ...AUDIO_QUEUE_DEFAULTS, maxItems: 3, maxBytes: 1000 };

  it('is not at capacity below both limits', () => {
    expect(isQueueAtCapacity([artifact('queued', 10)], policy)).toBe(false);
  });

  it('trips on the item count', () => {
    const three = [artifact('queued', 1), artifact('queued', 2), artifact('queued', 3)];
    expect(isQueueAtCapacity(three, policy)).toBe(true);
  });

  it('trips on total bytes even with room in the count', () => {
    expect(isQueueAtCapacity([artifact('queued', 1000)], policy)).toBe(true);
  });

  it('ignores non-pending artifacts — archived audio must not block a recording', () => {
    const settled = [artifact('archived', 900), artifact('deleted', 900)];
    expect(isQueueAtCapacity(settled, policy)).toBe(false);
  });

  it('an empty queue is never at capacity', () => {
    expect(isQueueAtCapacity([], policy)).toBe(false);
  });
});
