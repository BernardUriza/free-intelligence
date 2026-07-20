/**
 * durableRecordingMachine — which recording state may legally follow which, and
 * whether the queue has room to record at all.
 *
 * A pure (state, event) -> state reducer with zero React, MediaRecorder, stream
 * or IndexedDB dependency — the same shape as its sibling
 * {@link ./resonanceCallMachine}, which exists for exactly this reason: keeping
 * the machine pure is what makes the flows verifiable without mocking audio I/O.
 *
 * WHY (B3-VOICE-RECORDER-MACHINE-1): `useDurableRecording` transitioned the
 * artifact by calling `updateArtifact({ state: '…' })` from five different
 * callbacks (start, pause, resume, stop, cancel). There was no table, so no
 * transition was illegal: `resume` after a stop had settled, or a second `pause`
 * racing the in-flight one, would happily write a state the recorder could not
 * honour. The recorder holds the user's ONLY copy of what they just said — a
 * silently-illegal transition there costs audio that exists nowhere else.
 *
 * The blobs, streams and timers stay in the hook. What lives here is the part
 * that is decidable from data alone.
 */

import type { AudioArtifact, AudioArtifactState, AudioQueuePolicy } from './audioArtifact';
import { isPending } from './audioArtifact';

/**
 * What the USER (or the transport) asks the recorder to do. Distinct from the
 * artifact's state: `pause.requested` is the ask, `paused` is the result.
 */
export type RecordingEvent =
  | 'record.started'
  | 'pause.requested'
  | 'resume.requested'
  | 'stop.requested'
  | 'stop.settled'
  | 'cancel.requested'
  | 'error.raised';

/** States a live recording session can occupy. The rest are post-capture. */
const ACTIVE: readonly AudioArtifactState[] = ['recording', 'paused', 'stopping'];

const TRANSITIONS: Partial<
  Record<AudioArtifactState, Partial<Record<RecordingEvent, AudioArtifactState>>>
> = {
  recording: {
    'pause.requested': 'paused',
    'stop.requested': 'stopping',
  },
  paused: {
    'resume.requested': 'recording',
    'stop.requested': 'stopping',
  },
  // The async stop (RecordRTC flush + IndexedDB write, ~500ms) is NOT
  // interruptible: a pause or resume arriving mid-flight must be ignored, not
  // applied, or the segment the flush is collecting is lost.
  stopping: {
    'stop.settled': 'queued',
  },
};

/** True while a capture session is live (recording, paused, or flushing). */
export function isRecordingActive(state: AudioArtifactState): boolean {
  return ACTIVE.includes(state);
}

/**
 * Pure reducer: the next recording state, or the current one when the event is
 * not legal from here. Never throws — an illegal ask is a no-op, because the
 * caller is a UI button the user may double-tap.
 */
export function recordingReducer(
  state: AudioArtifactState,
  event: RecordingEvent,
): AudioArtifactState {
  // A cancel or an error terminates from ANY live state; from a settled one they
  // are meaningless and leave it alone.
  if (event === 'cancel.requested') return isRecordingActive(state) ? 'deleted' : state;
  if (event === 'error.raised') return isRecordingActive(state) ? 'failed' : state;
  if (event === 'record.started') return state === 'recording' ? state : 'recording';
  return TRANSITIONS[state]?.[event] ?? state;
}

/** True when `event` would actually move the machine — for disabling a control. */
export function canRecordingTransition(
  state: AudioArtifactState,
  event: RecordingEvent,
): boolean {
  return recordingReducer(state, event) !== state;
}

/**
 * Whether the durable queue is full. Extracted from the effect that had it
 * inline behind `store.list()`, so the policy is decidable — and testable —
 * without an IndexedDB round-trip.
 *
 * Counts only PENDING artifacts: an archived or deleted one still occupies
 * IndexedDB but must not block a new recording.
 */
export function isQueueAtCapacity(
  artifacts: readonly AudioArtifact[],
  policy: AudioQueuePolicy,
): boolean {
  const pending = artifacts.filter(isPending);
  const totalBytes = pending.reduce((sum, a) => sum + a.size, 0);
  return pending.length >= policy.maxItems || totalBytes >= policy.maxBytes;
}
