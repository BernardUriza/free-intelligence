/**
 * resonanceCueController — applies resonanceCuePolicy decisions to a CuePlayer,
 * with the guarantees Web Audio alone can't give: playLoop is idempotent (one
 * thinking source, never two), playOnce dedupes by eventId (a re-render of the
 * same transition can't double-fire), and stopAll is safe to call any number of
 * times. The controller knows the policy; the player only knows Web Audio.
 *
 * Lifecycle: one controller per call session (startCall makes/reset()s it). On
 * teardown the wrapper calls stopAll() — and the policy also emits stopAll on the
 * terminal transition — so no cue can outlive the call.
 */

import { resonanceCuePolicy, type ResonanceCueName } from './resonanceCuePolicy';
import type { ResonanceCallState, ResonanceCallEvent } from './resonanceCallMachine';

export interface ResonanceCuePlayer {
  playOnce: (cue: 'crystalline' | 'ready') => void;
  playLoop: (cue: 'thinking') => void;
  stopLoop: (cue: 'thinking') => void;
  stopAll: () => void;
}

export interface ResonanceCueController {
  /** Apply one FSM transition's cues. eventId dedupes one-shots across re-renders. */
  applyTransition: (
    input: { previousState: ResonanceCallState; nextState: ResonanceCallState; event: ResonanceCallEvent },
    eventId?: string,
  ) => void;
  stopAll: () => void;
  reset: () => void;
}

export function createResonanceCueController(player: ResonanceCuePlayer): ResonanceCueController {
  const activeLoops = new Set<ResonanceCueName>();
  const playedOneShots = new Set<string>();

  function stopAll() {
    player.stopAll();
    activeLoops.clear();
  }

  function reset() {
    activeLoops.clear();
    playedOneShots.clear();
  }

  function applyTransition(
    input: { previousState: ResonanceCallState; nextState: ResonanceCallState; event: ResonanceCallEvent },
    eventId?: string,
  ) {
    for (const action of resonanceCuePolicy(input)) {
      switch (action.type) {
        case 'playLoop':
          if (!activeLoops.has(action.cue)) {
            activeLoops.add(action.cue);
            player.playLoop(action.cue);
          }
          break;
        case 'stopLoop':
          if (activeLoops.has(action.cue)) {
            activeLoops.delete(action.cue);
            player.stopLoop(action.cue);
          }
          break;
        case 'playOnce': {
          const key = eventId ? `${eventId}:${action.cue}` : undefined;
          if (key && playedOneShots.has(key)) break;
          if (key) playedOneShots.add(key);
          player.playOnce(action.cue);
          break;
        }
        case 'stopAll':
          stopAll();
          break;
      }
    }
  }

  return { applyTransition, stopAll, reset };
}
