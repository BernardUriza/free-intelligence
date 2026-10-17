/**
 * contracts/agent-turn.vectors.json — the turn machine, as a contract.
 *
 * Each vector is a sequence of WIRE frames and the state both consumers must
 * reach: this reducer (through fromWireEvent) and og118-ios's ChatModel (its
 * harness replays the same file). The JSON is the source; neither language
 * generates it for the other. A vector that fails here is core drifting from
 * the contract, not the contract drifting from core.
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { applyAgentEvent, initialAgentTurnState, type AgentTurnState } from './state';
import { fromWireEvent } from './wire-map';
import type { AgentStreamEvent } from './events';

interface Vector {
  name: string;
  events: unknown[];
  expect: unknown;
}

const here = dirname(fileURLToPath(import.meta.url));
const contrato = JSON.parse(
  readFileSync(resolve(here, '../../contracts/agent-turn.vectors.json'), 'utf8'),
) as { version: number; vectors: Vector[] };

function proyectar(s: AgentTurnState) {
  return {
    text: s.text,
    status: s.status,
    deferred: s.deferred,
    reactions: s.reactions,
    author: s.author ? { id: s.author.id, name: s.author.name } : null,
    plan: s.plan
      ? {
          steps: s.plan.steps.map((p) => ({
            label: p.label,
            status: p.status,
            summary: p.summary ?? null,
            error: p.error ?? null,
            note: p.note ?? null,
          })),
          rejection: s.plan.rejection
            ? {
                reason: s.plan.rejection.reason,
                matched: s.plan.rejection.matched.map((m) => m.label),
                guard: s.plan.rejection.guard,
              }
            : null,
          amended: s.plan.amended ?? null,
          outcome: s.plan.outcome ?? null,
        }
      : null,
  };
}

describe('agent-turn.vectors.json', () => {
  it('declara su versión y al menos un vector', () => {
    expect(contrato.version).toBe(1);
    expect(contrato.vectors.length).toBeGreaterThan(0);
  });

  for (const v of contrato.vectors) {
    it(v.name, () => {
      const eventos = v.events
        .map(fromWireEvent)
        .filter((e): e is AgentStreamEvent => e !== null);
      const estado = eventos.reduce(applyAgentEvent, initialAgentTurnState());
      expect(proyectar(estado)).toEqual(v.expect);
    });
  }
});
