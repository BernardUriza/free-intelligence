/**
 * AudioStateMachine - Manage playback lifecycle
 *
 * States:
 * - initialized: Provider mounted, capabilities being probed
 * - ready: Can accept audio playback requests
 * - playing: Audio actively playing
 * - paused: Playback paused
 * - exhausted: Rate limit hit or quota exceeded
 * - failed: Unrecoverable error (e.g., capability probe failed)
 *
 * Transitions:
 * - initialized → ready (on capability probe success)
 * - initialized → failed (on capability probe failure)
 * - ready → playing (on play request)
 * - playing → paused (on pause)
 * - paused → playing (on resume)
 * - playing → ready (on audio end)
 * - playing → failed (on error)
 * - ready/playing → exhausted (on rate limit)
 *
 * @module AudioStateMachine
 * @see /apps/aurity/docs/audio/STATE_MACHINE.md
 */

import { createLogger } from '@/lib/internal/logger';

const log = createLogger('AudioStateMachine');

export type AudioState =
  | 'initialized'
  | 'ready'
  | 'playing'
  | 'paused'
  | 'exhausted'
  | 'failed';

export type AudioEvent =
  | 'CAPABILITIES_OK'
  | 'CAPABILITIES_FAILED'
  | 'PLAY'
  | 'PAUSE'
  | 'END'
  | 'ERROR'
  | 'RATE_LIMITED';

export interface StateTransition {
  from: AudioState;
  to: AudioState;
  event: AudioEvent;
  guard?: () => boolean; // Optional guard condition
}

/**
 * Valid state transitions
 *
 * Defines all allowed state transitions in the audio playback lifecycle.
 * Transitions without a guard are always allowed.
 */
const TRANSITIONS: StateTransition[] = [
  { from: 'initialized', to: 'ready', event: 'CAPABILITIES_OK' },
  { from: 'initialized', to: 'failed', event: 'CAPABILITIES_FAILED' },
  { from: 'ready', to: 'playing', event: 'PLAY' },
  { from: 'playing', to: 'paused', event: 'PAUSE' },
  { from: 'paused', to: 'playing', event: 'PLAY' },
  { from: 'playing', to: 'ready', event: 'END' },
  { from: 'playing', to: 'failed', event: 'ERROR' },
  { from: 'paused', to: 'ready', event: 'END' },
  { from: 'ready', to: 'exhausted', event: 'RATE_LIMITED' },
  { from: 'playing', to: 'exhausted', event: 'RATE_LIMITED' },
];

/**
 * AudioStateMachine class
 *
 * Manages audio playback state with guarded transitions and event listeners.
 */
export class AudioStateMachine {
  private currentState: AudioState = 'initialized';
  private listeners: Array<(state: AudioState) => void> = [];

  /**
   * Get current state
   *
   * @returns Current AudioState
   */
  getState(): AudioState {
    return this.currentState;
  }

  /**
   * Transition to new state
   *
   * Checks if transition is valid according to TRANSITIONS table.
   * If valid, updates state and notifies listeners.
   *
   * @param event - Event triggering the transition
   * @returns True if transition succeeded, false otherwise
   */
  transition(event: AudioEvent): boolean {
    const validTransition = TRANSITIONS.find(
      t => t.from === this.currentState && t.event === event
    );

    if (!validTransition) {
      log.warn('Invalid transition', { from: this.currentState, event });
      return false;
    }

    // Check guard if present
    if (validTransition.guard && !validTransition.guard()) {
      log.warn('Guard failed', { from: this.currentState, to: validTransition.to });
      return false;
    }

    const previousState = this.currentState;
    this.currentState = validTransition.to;

    // Notify listeners
    this.listeners.forEach(listener => listener(this.currentState));

    return true;
  }

  /**
   * Register state change listener
   *
   * Listener is called whenever state changes.
   *
   * @param listener - Callback function receiving new state
   * @returns Unsubscribe function
   */
  onStateChange(listener: (state: AudioState) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  /**
   * Check if audio can play
   *
   * @returns True if state is 'ready' or 'paused'
   */
  canPlay(): boolean {
    return this.currentState === 'ready' || this.currentState === 'paused';
  }

  /**
   * Check if audio can pause
   *
   * @returns True if state is 'playing'
   */
  canPause(): boolean {
    return this.currentState === 'playing';
  }

  /**
   * Check if state is playable
   *
   * @returns True if audio can be played (ready or paused)
   */
  isPlayable(): boolean {
    return ['ready', 'paused'].includes(this.currentState);
  }
}
