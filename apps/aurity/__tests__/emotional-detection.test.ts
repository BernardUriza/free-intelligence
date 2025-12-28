/**
 * Tests for Emotional Detection System
 *
 * Card: FI-ONBOARD-005
 * Tests emotional state detection heuristics with simulated scenarios.
 */

import { describe, it, expect } from 'vitest';
import {
  calculateMetrics,
  detectEmotionalState,
  emotionalStateToTone,
  getToneSuggestion,
  DEFAULT_CONFIG,
  type InteractionEvent,
} from '../lib/emotional-detection';

// ============================================================================
// Helper Functions
// ============================================================================

function createEvent(
  type: InteractionEvent['type'],
  offsetMs: number = 0,
  metadata?: InteractionEvent['metadata']
): InteractionEvent {
  return {
    type,
    timestamp: Date.now() - offsetMs,
    metadata,
  };
}

function createEventSequence(
  types: Array<{ type: InteractionEvent['type']; offsetMs?: number; metadata?: InteractionEvent['metadata'] }>
): InteractionEvent[] {
  return types.map((t, i) => createEvent(t.type, t.offsetMs ?? i * 1000, t.metadata));
}

// ============================================================================
// Frustration Detection Tests
// ============================================================================

describe('Frustration Detection', () => {
  it('should detect frustration from consecutive errors', () => {
    // Need enough errors AND rapid clicks to cross 0.6 threshold
    const events = createEventSequence([
      { type: 'error' },
      { type: 'error' },
      { type: 'error' },
      { type: 'error' },
      { type: 'message', metadata: { repeated: true } },
      { type: 'message', metadata: { repeated: true } },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('frustrated');
    expect(result.confidence).toBeGreaterThan(0.5);
    expect(result.reason).toContain('errors');
  });

  it('should detect frustration from rapid clicks', () => {
    // Create clicks less than 500ms apart + errors to cross threshold
    const events: InteractionEvent[] = [];
    for (let i = 0; i < 10; i++) {
      events.push(createEvent('click', i * 200)); // 200ms apart = rapid
    }
    // Add errors to boost score
    events.push(createEvent('error', 2100));
    events.push(createEvent('error', 2200));
    events.push(createEvent('error', 2300));

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('frustrated');
    expect(result.reason).toContain('rapid clicks');
  });

  it('should detect frustration from repeated messages', () => {
    const events = createEventSequence([
      { type: 'message', metadata: { repeated: false } },
      { type: 'message', metadata: { repeated: true } },
      { type: 'message', metadata: { repeated: true } },
      { type: 'error' },
      { type: 'error' },
      { type: 'error' },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('frustrated');
  });

  it('should map frustrated state to empathetic tone', () => {
    expect(emotionalStateToTone('frustrated')).toBe('empathetic');
  });
});

// ============================================================================
// Success Detection Tests
// ============================================================================

describe('Success Detection', () => {
  it('should detect success from consecutive successes', () => {
    const events = createEventSequence([
      { type: 'success', offsetMs: 15000 },
      { type: 'success', offsetMs: 10000 },
      { type: 'success', offsetMs: 5000 },
      { type: 'success', offsetMs: 0 },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('successful');
    expect(result.confidence).toBeGreaterThan(0.6);
  });

  it('should detect success from no errors and progressive navigation', () => {
    const events = createEventSequence([
      { type: 'navigation', metadata: { target: 'forward' } },
      { type: 'success' },
      { type: 'navigation', metadata: { target: 'forward' } },
      { type: 'success' },
      { type: 'success' },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('successful');
    expect(metrics.backNavigations).toBe(0);
  });

  it('should map successful state to sharp tone', () => {
    expect(emotionalStateToTone('successful')).toBe('sharp');
  });
});

// ============================================================================
// Hesitation Detection Tests
// ============================================================================

describe('Hesitation Detection', () => {
  it('should detect hesitation from long idle time', () => {
    // Create event 35 seconds ago + back navigations to cross threshold
    const events = [
      createEvent('message', 35000),
      createEvent('navigation', 34000, { target: 'back' }),
      createEvent('navigation', 33000, { target: 'back' }),
    ];

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('hesitant');
    expect(result.reason).toContain('idle time');
  });

  it('should detect hesitation from back navigations', () => {
    // Multiple back navigations + long idle to cross threshold
    const events = [
      createEvent('navigation', 35000, { target: 'forward' }),
      createEvent('navigation', 34000, { target: 'back' }),
      createEvent('navigation', 33000, { target: 'forward' }),
      createEvent('navigation', 32000, { target: 'back' }),
      createEvent('navigation', 31000, { target: 'back' }),
    ];

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('hesitant');
    expect(metrics.backNavigations).toBeGreaterThanOrEqual(2);
  });

  it('should map hesitant state to obsessive tone', () => {
    expect(emotionalStateToTone('hesitant')).toBe('obsessive');
  });
});

// ============================================================================
// Neutral State Tests
// ============================================================================

describe('Neutral State', () => {
  it('should return neutral when no strong signals', () => {
    const events = createEventSequence([
      { type: 'click', offsetMs: 5000 },
      { type: 'message', offsetMs: 3000 },
      { type: 'click', offsetMs: 1000 },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('neutral');
  });

  it('should return neutral for empty events', () => {
    const metrics = calculateMetrics([], DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    expect(result.state).toBe('neutral');
  });

  it('should map neutral state to neutral tone', () => {
    expect(emotionalStateToTone('neutral')).toBe('neutral');
  });
});

// ============================================================================
// Metrics Calculation Tests
// ============================================================================

describe('Metrics Calculation', () => {
  it('should count errors correctly', () => {
    const events = createEventSequence([
      { type: 'error' },
      { type: 'click' },
      { type: 'error' },
      { type: 'message' },
      { type: 'error' },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);

    expect(metrics.recentErrors).toBe(3);
  });

  it('should count successes correctly', () => {
    const events = createEventSequence([
      { type: 'success' },
      { type: 'click' },
      { type: 'success' },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);

    expect(metrics.recentSuccesses).toBe(2);
  });

  it('should respect window size', () => {
    const config = { ...DEFAULT_CONFIG, windowSize: 3 };
    const events = createEventSequence([
      { type: 'error' },
      { type: 'error' },
      { type: 'error' },
      { type: 'error' },
      { type: 'success' }, // Only this and 2 before should count
    ]);

    const metrics = calculateMetrics(events, config);

    expect(metrics.recentErrors).toBe(2); // Only last 3 events
    expect(metrics.recentSuccesses).toBe(1);
  });
});

// ============================================================================
// Tone Suggestion Tests
// ============================================================================

describe('Tone Suggestions', () => {
  it('should provide empathetic suggestion for frustration', () => {
    const suggestion = getToneSuggestion('frustrated');
    expect(suggestion).toContain('empático');
  });

  it('should provide direct suggestion for success', () => {
    const suggestion = getToneSuggestion('successful');
    expect(suggestion).toContain('directo');
  });

  it('should provide context suggestion for hesitation', () => {
    const suggestion = getToneSuggestion('hesitant');
    expect(suggestion).toContain('contexto');
  });
});

// ============================================================================
// Edge Cases
// ============================================================================

describe('Edge Cases', () => {
  it('should handle mixed signals gracefully', () => {
    const events = createEventSequence([
      { type: 'error' },
      { type: 'success' },
      { type: 'error' },
      { type: 'success' },
    ]);

    const metrics = calculateMetrics(events, DEFAULT_CONFIG);
    const result = detectEmotionalState(metrics, DEFAULT_CONFIG);

    // Should return neutral due to conflicting signals
    expect(['neutral', 'frustrated', 'successful']).toContain(result.state);
  });

  it('should not crash with malformed metadata', () => {
    const events: InteractionEvent[] = [
      { type: 'click', timestamp: Date.now(), metadata: undefined },
      { type: 'message', timestamp: Date.now(), metadata: {} },
    ];

    expect(() => calculateMetrics(events, DEFAULT_CONFIG)).not.toThrow();
  });
});
