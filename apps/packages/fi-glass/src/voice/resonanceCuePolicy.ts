/**
 * resonanceCuePolicy — the pure decision layer for RESONANCE's audio cues.
 *
 * Maps a single FSM transition (previousState, nextState, event) to the cue
 * actions to run. No Web Audio, no timers — so "right cue only on its transition"
 * and "the thinking loop can never hang" are provable with plain assertions.
 *
 * The load-bearing rule: stopLoop(thinking) is derived from LEAVING the thinking
 * state, not from a specific event. That makes it impossible to strand the loop —
 * a barge-in, an agent error, a hangup, or any future transition out of thinking
 * all stop it. stopAll is layered on top for terminal/teardown paths.
 */

import type { ResonanceCallState, ResonanceCallEvent } from './resonanceCallMachine';

export type ResonanceCueName = 'thinking' | 'crystalline' | 'ready';

export type ResonanceCueAction =
  | { type: 'playLoop'; cue: 'thinking' }
  | { type: 'stopLoop'; cue: 'thinking' }
  | { type: 'playOnce'; cue: 'crystalline' | 'ready' }
  | { type: 'stopAll' };

export interface ResonanceCuePolicyInput {
  previousState: ResonanceCallState;
  nextState: ResonanceCallState;
  event: ResonanceCallEvent;
}

export function resonanceCuePolicy(input: ResonanceCuePolicyInput): ResonanceCueAction[] {
  const { previousState, nextState, event } = input;

  // Teardown wins and short-circuits: once the call is ending, silence everything
  // (stopAll also stops the loop), and emit nothing else.
  if (event === 'call.ended' || event === 'error.fatal' || nextState === 'ended') {
    return [{ type: 'stopAll' }];
  }

  const actions: ResonanceCueAction[] = [];

  // Loop lifecycle keyed on STATE membership, not a single event.
  if (previousState !== 'thinking' && nextState === 'thinking') {
    actions.push({ type: 'playLoop', cue: 'thinking' });
  }
  if (previousState === 'thinking' && nextState !== 'thinking') {
    actions.push({ type: 'stopLoop', cue: 'thinking' });
  }

  // One-shots fire only on their exact event.
  if (event === 'user.speech.ended') actions.push({ type: 'playOnce', cue: 'crystalline' });
  if (event === 'assistant.speech.completed') actions.push({ type: 'playOnce', cue: 'ready' });

  return actions;
}
