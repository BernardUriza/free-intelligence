import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

import { createOg118ElementStore } from '../og118ElementStore';

const READ = {
  slug: 'radon',
  displayName: 'Radón',
  description: 'Gases nobles, sin más.',
  aliases: ['rn-bot'],
  provider: 'codex',
  model: 'gpt-6-astra',
  dna: 'Eres Radón.',
  version: 7,
};

let calls: { url: string; method: string; body?: unknown }[];

beforeEach(() => {
  calls = [];
  vi.stubGlobal('fetch', async (url: string, init: RequestInit = {}) => {
    const method = init.method ?? 'GET';
    calls.push({ url, method, body: init.body ? JSON.parse(String(init.body)) : undefined });
    const json = (status: number, body: unknown) =>
      ({ ok: status < 400, status, json: async () => body }) as Response;
    if (url.endsWith('/elements/slots')) return json(200, { canCreate: true, slots: [], editable: ['radon'] });
    if (url.endsWith('/elements') && method === 'GET')
      return json(200, {
        elements: [
          { slug: 'oxigeno', displayName: 'Oxígeno', engine: 'Vultur' },
          { slug: 'radon', displayName: 'Radón', description: 'Gases nobles, sin más.', engine: 'codex' },
        ],
      });
    if (url.endsWith('/elements') && method === 'POST')
      return json(422, { detail: [{ msg: 'String should have at most 500 characters' }] });
    if (url.endsWith('/persona')) return json(200, READ);
    if (method === 'DELETE') return { ok: true, status: 204, json: async () => ({}) } as Response;
    if (url.endsWith('/test')) return json(200, { output: 'Rn.', latency_ms: 812 });
    return json(200, { slug: 'radon', personaVersion: 8 });
  });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

const store = (aliases = 'Rn-Bot, gas') =>
  createOg118ElementStore({
    slot: () => ({ atomicNumber: 86, symbol: 'Rn', slug: 'radon', displayName: 'Radón' }),
    aliases: () => aliases.split(',').map((a) => a.trim()),
  });

describe('og118 element store', () => {
  it('lists only the elements this account made from the UI', async () => {
    expect((await store().list()).map((p) => p.id)).toEqual(['radon']);
  });

  it('creates on the chosen slot with its aliases and engine, and shows the server reason', async () => {
    await expect(
      store().create({ id: 'radon', name: 'Radón', description: 'x'.repeat(501), system_prompt: 'Eres Radón.', model: 'codex' }),
    ).rejects.toThrow('String should have at most 500 characters');
    expect(calls.at(-1)?.body).toMatchObject({
      atomicNumber: 86,
      personaId: 'radon',
      aliases: ['Rn-Bot', 'gas'],
      provider: 'codex',
      model: 'gpt-6-astra',
      dna: 'Eres Radón.',
    });
  });

  it('an edit keeps the aliases and the engine it did not touch', async () => {
    const s = store();
    expect((await s.get('radon')).model).toBe('codex');
    await s.update('radon', { system_prompt: 'Eres Radón, más callado.' });
    const put = calls.find((c) => c.method === 'PUT');
    expect(put?.body).toEqual({
      displayName: 'Radón',
      description: 'Gases nobles, sin más.',
      aliases: ['rn-bot'],
      provider: 'codex',
      model: 'gpt-6-astra',
      dna: 'Eres Radón, más callado.',
    });
  });

  it('deletes and probes through the element routes', async () => {
    const s = store();
    await s.remove('radon');
    expect(await s.test('radon', 'hola')).toEqual({ output: 'Rn.', latency_ms: 812 });
    expect(calls.map((c) => `${c.method} ${c.url.replace(/^.*?(\/elements)/, '$1')}`)).toEqual([
      'DELETE /elements/radon',
      'POST /elements/radon/test',
    ]);
  });
});
