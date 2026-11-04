/**
 * contracts/fixtures/turno-real.sse — a turn captured from the real server.
 *
 * The same bytes the iPhone's harness parses. Fed here in small chunks, the way
 * a network delivers them, through takeSseFrames → fromWireEvent → the reducer:
 * if the server's framing or the contract moves, this goes red before any
 * client does.
 */

import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { applyAgentEvent, initialAgentTurnState } from './state';
import { takeSseFrames } from './sse';
import { fromWireEvent } from './wire-map';
import type { AgentStreamEvent } from './events';

const here = dirname(fileURLToPath(import.meta.url));
const crudo = readFileSync(resolve(here, '../../contracts/fixtures/turno-real.sse'), 'utf8');

function enTrozos(texto: string, tamano: number): string[] {
  const payloads: string[] = [];
  let buffer = '';
  for (let i = 0; i < texto.length; i += tamano) {
    buffer += texto.slice(i, i + tamano);
    const corte = takeSseFrames(buffer);
    payloads.push(...corte.payloads);
    buffer = corte.rest;
  }
  const final = takeSseFrames(buffer + '\n\n');
  payloads.push(...final.payloads);
  return payloads;
}

describe('turno-real.sse', () => {
  it('se corta en los mismos 4 frames llegue como llegue', () => {
    const entero = enTrozos(crudo, crudo.length).map((p) => JSON.parse(p).type);
    const goteado = enTrozos(crudo, 7).map((p) => JSON.parse(p).type);
    expect(entero).toEqual(['open', 'text', 'result', 'done']);
    expect(goteado).toEqual(entero);
  });

  it('reduce al turno que el servidor de verdad contestó', () => {
    const eventos = enTrozos(crudo, 11)
      .map((p) => fromWireEvent(JSON.parse(p)))
      .filter((e): e is AgentStreamEvent => e !== null);
    const estado = eventos.reduce(applyAgentEvent, initialAgentTurnState());
    expect(estado.text).toBe('PONG');
    expect(estado.status).toBe('done');
    expect(estado.meta?.model).toBe('claude-sonnet-4-5');
  });
});
