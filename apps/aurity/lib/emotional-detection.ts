/**
 * Emotional Detection System for Free Intelligence
 *
 * Detects user emotional states through behavioral patterns:
 * - Frustration: Repeated messages, rapid clicks, consecutive errors
 * - Success: Correct quiz completion, advancing without help
 * - Hesitation: Prolonged time on phase, going back, hover without click
 *
 * Privacy-first: All data stored in LocalStorage, never sent to backend.
 *
 * Card: FI-ONBOARD-005
 * Author: Bernard Uriza Orozco
 */

// ============================================================================
// Types
// ============================================================================

export type EmotionalState = 'neutral' | 'frustrated' | 'successful' | 'hesitant';

export interface InteractionEvent {
  type: 'click' | 'message' | 'error' | 'success' | 'hover' | 'navigation' | 'idle';
  timestamp: number;
  metadata?: {
    target?: string;
    duration?: number;
    repeated?: boolean;
    phase?: string;
  };
}

export interface EmotionalMetrics {
  /** Number of errors in last N interactions */
  recentErrors: number;
  /** Number of successes in last N interactions */
  recentSuccesses: number;
  /** Average time between messages (ms) */
  avgMessageInterval: number;
  /** Number of repeated messages */
  repeatedMessages: number;
  /** Time spent on current phase (ms) */
  phaseTime: number;
  /** Number of back navigations */
  backNavigations: number;
  /** Rapid clicks (< 500ms apart) */
  rapidClicks: number;
  /** Idle time without interaction (ms) */
  idleTime: number;
}

export interface EmotionalDetectionConfig {
  /** Window size for recent interactions */
  windowSize: number;
  /** Threshold for frustration detection (errors) */
  frustrationErrorThreshold: number;
  /** Threshold for frustration detection (rapid clicks) */
  frustrationClickThreshold: number;
  /** Threshold for success detection */
  successThreshold: number;
  /** Threshold for hesitation (idle time in ms) */
  hesitationIdleThreshold: number;
  /** Threshold for hesitation (back navigations) */
  hesitationBackThreshold: number;
  /** Minimum confidence to change state */
  confidenceThreshold: number;
}

// ============================================================================
// Default Configuration
// ============================================================================

export const DEFAULT_CONFIG: EmotionalDetectionConfig = {
  windowSize: 20,
  frustrationErrorThreshold: 3,
  frustrationClickThreshold: 5,
  successThreshold: 3,
  hesitationIdleThreshold: 30000, // 30 seconds
  hesitationBackThreshold: 2,
  confidenceThreshold: 0.6,
};

// ============================================================================
// Storage Keys
// ============================================================================

import { createLogger } from '@/lib/internal/logger';

const emotionLog = createLogger('EmotionalDetection');

const STORAGE_KEY = 'fi_emotional_events';
const STATE_KEY = 'fi_emotional_state';
const METRICS_KEY = 'fi_emotional_metrics';

// ============================================================================
// Core Detection Logic
// ============================================================================

/**
 * Calculate emotional metrics from interaction events
 */
export function calculateMetrics(
  events: InteractionEvent[],
  config: EmotionalDetectionConfig = DEFAULT_CONFIG
): EmotionalMetrics {
  const now = Date.now();
  const recentEvents = events.slice(-config.windowSize);

  // Count errors and successes
  const recentErrors = recentEvents.filter((e) => e.type === 'error').length;
  const recentSuccesses = recentEvents.filter((e) => e.type === 'success').length;

  // Calculate message intervals
  const messageEvents = recentEvents.filter((e) => e.type === 'message');
  let avgMessageInterval = 0;
  if (messageEvents.length > 1) {
    const intervals: number[] = [];
    for (let i = 1; i < messageEvents.length; i++) {
      intervals.push(messageEvents[i].timestamp - messageEvents[i - 1].timestamp);
    }
    avgMessageInterval = intervals.reduce((a, b) => a + b, 0) / intervals.length;
  }

  // Count repeated messages
  const repeatedMessages = recentEvents.filter(
    (e) => e.type === 'message' && e.metadata?.repeated
  ).length;

  // Calculate phase time
  const phaseEvents = recentEvents.filter((e) => e.metadata?.phase);
  const phaseTime = phaseEvents.length > 0 ? now - phaseEvents[0].timestamp : 0;

  // Count back navigations
  const backNavigations = recentEvents.filter(
    (e) => e.type === 'navigation' && e.metadata?.target === 'back'
  ).length;

  // Count rapid clicks
  const clickEvents = recentEvents.filter((e) => e.type === 'click');
  let rapidClicks = 0;
  for (let i = 1; i < clickEvents.length; i++) {
    if (clickEvents[i].timestamp - clickEvents[i - 1].timestamp < 500) {
      rapidClicks++;
    }
  }

  // Calculate idle time
  const lastEvent = recentEvents[recentEvents.length - 1];
  const idleTime = lastEvent ? now - lastEvent.timestamp : 0;

  return {
    recentErrors,
    recentSuccesses,
    avgMessageInterval,
    repeatedMessages,
    phaseTime,
    backNavigations,
    rapidClicks,
    idleTime,
  };
}

/**
 * Detect emotional state from metrics with confidence score
 */
export function detectEmotionalState(
  metrics: EmotionalMetrics,
  config: EmotionalDetectionConfig = DEFAULT_CONFIG
): { state: EmotionalState; confidence: number; reason: string } {
  // Calculate confidence scores for each state
  const frustrationScore = calculateFrustrationScore(metrics, config);
  const successScore = calculateSuccessScore(metrics, config);
  const hesitationScore = calculateHesitationScore(metrics, config);

  // Find the highest score
  const scores = [
    { state: 'frustrated' as EmotionalState, score: frustrationScore.score, reason: frustrationScore.reason },
    { state: 'successful' as EmotionalState, score: successScore.score, reason: successScore.reason },
    { state: 'hesitant' as EmotionalState, score: hesitationScore.score, reason: hesitationScore.reason },
  ];

  const highest = scores.reduce((a, b) => (a.score > b.score ? a : b));

  // Return neutral if no strong signal
  if (highest.score < config.confidenceThreshold) {
    return { state: 'neutral', confidence: 1 - highest.score, reason: 'No strong emotional signal detected' };
  }

  return { state: highest.state, confidence: highest.score, reason: highest.reason };
}

/**
 * Calculate frustration score (0-1)
 */
function calculateFrustrationScore(
  metrics: EmotionalMetrics,
  config: EmotionalDetectionConfig
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  // Consecutive errors
  if (metrics.recentErrors >= config.frustrationErrorThreshold) {
    score += 0.4;
    reasons.push(`${metrics.recentErrors} consecutive errors`);
  }

  // Rapid clicks
  if (metrics.rapidClicks >= config.frustrationClickThreshold) {
    score += 0.3;
    reasons.push(`${metrics.rapidClicks} rapid clicks`);
  }

  // Repeated messages
  if (metrics.repeatedMessages >= 2) {
    score += 0.2;
    reasons.push(`${metrics.repeatedMessages} repeated messages`);
  }

  // Fast message interval (< 2 seconds)
  if (metrics.avgMessageInterval > 0 && metrics.avgMessageInterval < 2000) {
    score += 0.1;
    reasons.push('Very fast message rate');
  }

  return { score: Math.min(score, 1), reason: reasons.join(', ') || 'Low frustration indicators' };
}

/**
 * Calculate success score (0-1)
 */
function calculateSuccessScore(
  metrics: EmotionalMetrics,
  config: EmotionalDetectionConfig
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  // Recent successes
  if (metrics.recentSuccesses >= config.successThreshold) {
    score += 0.5;
    reasons.push(`${metrics.recentSuccesses} recent successes`);
  }

  // No errors
  if (metrics.recentErrors === 0) {
    score += 0.2;
    reasons.push('No recent errors');
  }

  // Steady pace (not too fast, not too slow)
  if (metrics.avgMessageInterval >= 3000 && metrics.avgMessageInterval <= 15000) {
    score += 0.2;
    reasons.push('Steady interaction pace');
  }

  // No back navigations
  if (metrics.backNavigations === 0) {
    score += 0.1;
    reasons.push('Progressive navigation');
  }

  return { score: Math.min(score, 1), reason: reasons.join(', ') || 'Low success indicators' };
}

/**
 * Calculate hesitation score (0-1)
 */
function calculateHesitationScore(
  metrics: EmotionalMetrics,
  config: EmotionalDetectionConfig
): { score: number; reason: string } {
  let score = 0;
  const reasons: string[] = [];

  // Long idle time
  if (metrics.idleTime >= config.hesitationIdleThreshold) {
    score += 0.4;
    reasons.push(`${Math.round(metrics.idleTime / 1000)}s idle time`);
  }

  // Back navigations
  if (metrics.backNavigations >= config.hesitationBackThreshold) {
    score += 0.3;
    reasons.push(`${metrics.backNavigations} back navigations`);
  }

  // Long phase time without progress
  if (metrics.phaseTime > 60000 && metrics.recentSuccesses === 0) {
    score += 0.2;
    reasons.push('Stuck on current phase');
  }

  // Slow message rate (> 30 seconds between messages)
  if (metrics.avgMessageInterval > 30000) {
    score += 0.1;
    reasons.push('Very slow interaction pace');
  }

  return { score: Math.min(score, 1), reason: reasons.join(', ') || 'Low hesitation indicators' };
}

// ============================================================================
// LocalStorage Persistence (Privacy-First)
// ============================================================================

/**
 * Save interaction event to LocalStorage
 */
export function saveEvent(event: InteractionEvent): void {
  if (typeof window === 'undefined') return;

  try {
    const events = getEvents();
    events.push(event);

    // Keep only last 100 events to prevent storage bloat
    const trimmedEvents = events.slice(-100);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmedEvents));
  } catch (error) {
    emotionLog.warn('Failed to save event', { error: String(error) });
  }
}

/**
 * Get all stored events
 */
export function getEvents(): InteractionEvent[] {
  if (typeof window === 'undefined') return [];

  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch (error) {
    emotionLog.warn('Failed to get events', { error: String(error) });
    return [];
  }
}

/**
 * Clear all stored events
 */
export function clearEvents(): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(STATE_KEY);
    localStorage.removeItem(METRICS_KEY);
  } catch (error) {
    emotionLog.warn('Failed to clear events', { error: String(error) });
  }
}

/**
 * Save current emotional state
 */
export function saveState(state: EmotionalState): void {
  if (typeof window === 'undefined') return;

  try {
    localStorage.setItem(STATE_KEY, state);
  } catch (error) {
    emotionLog.warn('Failed to save state', { error: String(error) });
  }
}

/**
 * Get last saved emotional state
 */
export function getState(): EmotionalState {
  if (typeof window === 'undefined') return 'neutral';

  try {
    return (localStorage.getItem(STATE_KEY) as EmotionalState) || 'neutral';
  } catch {
    return 'neutral';
  }
}

// ============================================================================
// Tone Mapping
// ============================================================================

import type { FITone } from '@aurity-standalone/types/assistant';

/**
 * Map emotional state to FI tone
 */
export function emotionalStateToTone(state: EmotionalState): FITone {
  switch (state) {
    case 'frustrated':
      return 'empathetic';
    case 'successful':
      return 'sharp';
    case 'hesitant':
      return 'obsessive';
    case 'neutral':
    default:
      return 'neutral';
  }
}

/**
 * Get tone suggestion message for FI
 */
export function getToneSuggestion(state: EmotionalState): string {
  switch (state) {
    case 'frustrated':
      return 'El usuario parece frustrado. Usa un tono empático y ofrece ayuda adicional.';
    case 'successful':
      return 'El usuario está teniendo éxito. Mantén un tono directo y eficiente.';
    case 'hesitant':
      return 'El usuario parece dudar. Ofrece más contexto y explicaciones detalladas.';
    case 'neutral':
    default:
      return 'Interacción normal. Usa el tono estándar.';
  }
}
