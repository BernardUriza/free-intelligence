/**
 * Unit tests for the NEW reducer branches added in core v1.1.0 — the plan
 * revision & lifecycle events (step_noted / plan_amended / plan_cancelled /
 * plan_completed / plan_failed) and 'cancelled' in step_done.
 *
 * Why these exist now (and Berkelio's original branches did not get unit tests):
 * those were battle-tested logic we MOVED, validated end-to-end via og118. These
 * five branches are NEW logic that never ran, and a normal agentic turn does NOT
 * reliably exercise them — og118 could run a hundred times without a single
 * plan_cancelled/replan/note. The e2e can't be trusted to hit them; a unit test
 * drives the event deterministically and asserts the resulting state. This is
 * the safety net a substrate reducer consumed by multiple apps must have.
 */

import { describe, it, expect } from 'vitest';
import {
  applyAgentEvent,
  initialAgentTurnState,
  type AgentTurnState,
} from './state';
import type { AgentStreamEvent } from './events';

/** Fold a sequence of events from a fresh turn into final state. */
function run(...events: AgentStreamEvent[]): AgentTurnState {
  return events.reduce(applyAgentEvent, initialAgentTurnState());
}

const plan3: AgentStreamEvent = { type: 'plan', steps: ['a', 'b', 'c'] };

describe('step_done — cancelled status (#5)', () => {
  it('attaches error (not summary) for cancelled', () => {
    const s = run(plan3, {
      type: 'step_done',
      index: 1,
      status: 'cancelled',
      error: 'user aborted',
    });
    expect(s.plan!.steps[1].status).toBe('cancelled');
    expect(s.plan!.steps[1].error).toBe('user aborted');
    expect(s.plan!.steps[1].summary).toBeUndefined();
  });

  it('regression: done still attaches summary, failed still attaches error', () => {
    const s = run(
      plan3,
      { type: 'step_done', index: 0, status: 'done', summary: 'ok' },
      { type: 'step_done', index: 1, status: 'failed', error: 'boom' }
    );
    expect(s.plan!.steps[0].status).toBe('done');
    expect(s.plan!.steps[0].summary).toBe('ok');
    expect(s.plan!.steps[0].error).toBeUndefined();
    expect(s.plan!.steps[1].status).toBe('failed');
    expect(s.plan!.steps[1].error).toBe('boom');
    expect(s.plan!.steps[1].summary).toBeUndefined();
  });
});

describe('step_noted', () => {
  it('annotates exactly step N without touching status', () => {
    const s = run(plan3, { type: 'step_noted', index: 1, note: 'careful here' });
    expect(s.plan!.steps[1].note).toBe('careful here');
    expect(s.plan!.steps[1].status).toBe('pending'); // unchanged
    expect(s.plan!.steps[0].note).toBeUndefined(); // no bleed
    expect(s.plan!.steps[2].note).toBeUndefined();
  });

  it('out-of-bounds index leaves the plan untouched', () => {
    const s = run(plan3, { type: 'step_noted', index: 9, note: 'nope' });
    expect(s.plan!.steps.every((st) => st.note === undefined)).toBe(true);
  });

  it('no plan → passthrough (no crash, no plan invented)', () => {
    const s = run({ type: 'step_noted', index: 0, note: 'x' });
    expect(s.plan).toBeNull();
  });
});

describe('plan_amended — flag set, then cleared by a fresh plan', () => {
  it("set to 'replan'", () => {
    const s = run(plan3, { type: 'plan_amended', action: 'replan' });
    expect(s.plan!.amended).toBe('replan');
  });

  it("set to 'insert'", () => {
    const s = run(plan3, { type: 'plan_amended', action: 'insert' });
    expect(s.plan!.amended).toBe('insert');
  });

  it('a fresh plan event clears amended and reseeds steps', () => {
    const s = run(
      plan3,
      { type: 'plan_amended', action: 'replan' },
      { type: 'plan', steps: ['x', 'y'] } // the replan's real steps arrive here
    );
    expect(s.plan!.amended).toBeNull();
    expect(s.plan!.outcome).toBeNull();
    expect(s.plan!.steps.map((st) => st.label)).toEqual(['x', 'y']);
    expect(s.plan!.steps.every((st) => st.status === 'pending')).toBe(true);
  });

  it('no plan → passthrough', () => {
    const s = run({ type: 'plan_amended', action: 'insert' });
    expect(s.plan).toBeNull();
  });
});

describe('plan_cancelled — order-safe sweep vs result', () => {
  it('cancel BEFORE result: open steps become cancelled and result cannot un-cancel them', () => {
    const s = run(
      plan3,
      { type: 'step_done', index: 0, status: 'done', summary: 'ok' },
      { type: 'plan_cancelled', reason: 'abort' }, // sweeps steps 1,2 (pending) → cancelled
      { type: 'result', text: 'stopped' } // close-out sweep only touches pending/running
    );
    expect(s.plan!.steps[0].status).toBe('done'); // already settled, untouched
    expect(s.plan!.steps[1].status).toBe('cancelled'); // cancel won; result did NOT mark done
    expect(s.plan!.steps[2].status).toBe('cancelled');
    expect(s.plan!.outcome).toBe('cancelled');
    expect(s.status).toBe('done'); // result still settles the turn
  });

  it('cancel AFTER result: late cancel records plan outcome but cannot retro-cancel already-settled steps', () => {
    const s = run(
      plan3,
      { type: 'step_done', index: 0, status: 'done', summary: 'ok' },
      { type: 'result', text: 'done' }, // close-out sweeps steps 1,2 (pending) → done
      { type: 'plan_cancelled', reason: 'late' } // sweep finds nothing open
    );
    expect(s.plan!.steps[0].status).toBe('done');
    expect(s.plan!.steps[1].status).toBe('done'); // result settled them first; cancel can't undo completed work
    expect(s.plan!.steps[2].status).toBe('done');
    expect(s.plan!.outcome).toBe('cancelled'); // plan-level cancellation still recorded
  });

  it('no plan → passthrough', () => {
    const s = run({ type: 'plan_cancelled', reason: 'x' });
    expect(s.plan).toBeNull();
  });
});

describe('plan_completed / plan_failed — stamp outcome, never lie about step statuses', () => {
  it('plan_completed stamps outcome, leaves settled steps as-is', () => {
    const s = run(
      plan3,
      { type: 'step_done', index: 0, status: 'done' },
      { type: 'step_done', index: 1, status: 'done' },
      { type: 'step_done', index: 2, status: 'done' },
      { type: 'plan_completed', completedCount: 3, failedCount: 0, cancelledCount: 0 }
    );
    expect(s.plan!.outcome).toBe('completed');
    expect(s.plan!.steps.every((st) => st.status === 'done')).toBe(true);
  });

  it('plan_failed keeps a done step done (a failed plan can still have completed steps)', () => {
    const s = run(
      plan3,
      { type: 'step_done', index: 0, status: 'done', summary: 'ok' },
      { type: 'step_done', index: 1, status: 'failed', error: 'boom' },
      { type: 'plan_failed', completedCount: 1, failedCount: 1, cancelledCount: 0 }
    );
    expect(s.plan!.outcome).toBe('failed');
    expect(s.plan!.steps[0].status).toBe('done'); // NOT forced to failed
    expect(s.plan!.steps[1].status).toBe('failed');
  });

  it('wire counts are NOT stored as derivable state (only outcome is stamped)', () => {
    const s = run(plan3, {
      type: 'plan_completed',
      completedCount: 3,
      failedCount: 0,
      cancelledCount: 0,
    });
    // counts are derivable from steps[].status — the reduced plan carries no count field.
    expect(Object.keys(s.plan!)).not.toContain('counts');
    expect(s.plan!.outcome).toBe('completed');
  });

  it('no plan → passthrough', () => {
    expect(run({ type: 'plan_completed' }).plan).toBeNull();
    expect(run({ type: 'plan_failed' }).plan).toBeNull();
  });
});

describe('author — the backend names WHO answers', () => {
  it('starts anonymous: a fresh turn has no speaker yet', () => {
    expect(initialAgentTurnState().author).toBeNull();
  });

  it('binds the announced speaker to the turn', () => {
    const s = run({
      type: 'author',
      author: { id: 'element-053-i-yodo', name: 'Yodo', symbol: 'I', engine: 'Insult' },
    });
    expect(s.author).toEqual({
      id: 'element-053-i-yodo',
      name: 'Yodo',
      symbol: 'I',
      engine: 'Insult',
    });
  });

  it('survives the rest of the turn (text, plan, result)', () => {
    const s = run(
      { type: 'author', author: { id: 'yodo', name: 'Yodo' } },
      plan3,
      { type: 'text', delta: 'hola' },
      { type: 'result', text: 'hola' },
    );
    expect(s.author?.name).toBe('Yodo');
    expect(s.status).toBe('done');
  });
});
