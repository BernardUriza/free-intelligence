// @vitest-environment jsdom
/**
 * mensajeDeFalloDeVoz — lo que el usuario LEE cuando una llamada falla.
 *
 * RESONANCE era la única superficie de voz sin banner de error: el composer de
 * un tiro ya enrutaba sus fallos a `setVoiceError`, la llamada no. Un /tts 503
 * (el trío de config ausente) se veía idéntico a un modelo callado. Esta función
 * es la decisión de qué texto sale, y por eso vive separada del glue de I/O.
 */

import { describe, it, expect } from 'vitest';
import { mensajeDeFalloDeVoz } from '../useOg118ResonanceCall';
import { Og118TTSError, Og118STTError } from '../og118VoiceAdapter';

describe('mensajeDeFalloDeVoz', () => {
  it('prefiere el mensaje del adapter — ya viene traducido por status', () => {
    const e = new Og118TTSError('Síntesis de voz no está configurada.', 'TTS_NOT_CONFIGURED', 503);
    expect(mensajeDeFalloDeVoz('tts', e, false)).toBe('Síntesis de voz no está configurada.');
  });

  it('un 401 de STT llega con su propio texto, no con el genérico de fase', () => {
    const e = new Og118STTError('Token de acceso inválido o ausente para STT.', 'STT_UNAUTHORIZED', 401);
    expect(mensajeDeFalloDeVoz('stt', e, false)).toBe('Token de acceso inválido o ausente para STT.');
  });

  it('sin mensaje utilizable cae a la fase — ningún fallo llega mudo', () => {
    for (const phase of ['mic', 'stt', 'agent', 'tts'] as const) {
      expect(mensajeDeFalloDeVoz(phase, undefined, true)).not.toBe('');
    }
    expect(mensajeDeFalloDeVoz('agent', new Error('   '), true))
      .toBe('El agente no pudo responder este turno.');
  });

  it('sólo lo recuperable promete reintento; lo fatal ya colgó', () => {
    expect(mensajeDeFalloDeVoz('tts', null, false)).toContain('Reintentando');
    expect(mensajeDeFalloDeVoz('mic', null, true)).not.toContain('Reintentando');
  });
});
