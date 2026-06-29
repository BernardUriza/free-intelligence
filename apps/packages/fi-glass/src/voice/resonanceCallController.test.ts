import { describe, it, expect, vi } from 'vitest';

import { createResonanceCallController } from './resonanceCallController';
import type { ResonanceDriver } from './resonanceEffects';

function mockDriver(): ResonanceDriver {
  return {
    openMic: vi.fn(),
    beginTranscribe: vi.fn(),
    invokeAgent: vi.fn(),
    speak: vi.fn(),
    stopSpeaking: vi.fn(),
    holdSilence: vi.fn(),
    fadeAndHangup: vi.fn(),
    endCall: vi.fn(),
  };
}

describe('resonanceCallController', () => {
  it('starts idle and only opens the mic on startCall', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    expect(c.state()).toBe('idle');
    expect(driver.openMic).not.toHaveBeenCalled();
    c.startCall();
    expect(c.state()).toBe('listening');
    expect(driver.openMic).toHaveBeenCalledTimes(1);
  });

  it('drives a full happy turn: mic -> STT -> agent -> speak -> auto-resume', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    c.startCall();
    c.userSpeechEnded();              // listening -> transcribing
    expect(driver.beginTranscribe).toHaveBeenCalledTimes(1);
    c.sttCompleted('hola americio');  // transcribing -> thinking
    expect(c.lastTranscript()).toBe('hola americio');
    expect(driver.invokeAgent).toHaveBeenCalledTimes(1);
    c.assistantTurnReady('hola, te escucho'); // thinking -> speaking
    expect(c.lastAssistantText()).toBe('hola, te escucho');
    expect(driver.speak).toHaveBeenCalledTimes(1);
    c.ttsCompleted();                 // speaking -> silence_hold
    expect(driver.holdSilence).toHaveBeenCalledTimes(1);
    c.silenceResume();                // silence_hold -> listening
    expect(c.state()).toBe('listening');
    expect(driver.openMic).toHaveBeenCalledTimes(2); // initial + auto-resume
  });

  it('barge-in: interrupt() cuts TTS first, then re-opens the mic', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    // get into speaking
    c.startCall();
    c.userSpeechEnded();
    c.sttCompleted('x');
    c.assistantTurnReady('respuesta larga');
    expect(c.state()).toBe('speaking');

    const order: string[] = [];
    (driver.stopSpeaking as ReturnType<typeof vi.fn>).mockImplementation(() => order.push('stop'));
    (driver.openMic as ReturnType<typeof vi.fn>).mockImplementation(() => order.push('mic'));

    c.interrupt();
    expect(c.state()).toBe('listening');
    expect(order).toEqual(['stop', 'mic']); // cut FIRST, then capture
  });

  it('interrupt() is a no-op when not speaking', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    c.startCall(); // listening
    c.interrupt();
    expect(driver.stopSpeaking).not.toHaveBeenCalled();
    expect(c.state()).toBe('listening');
  });

  it('sleep hangup: silence_hold -> sleepDecay -> endCall reaches ended', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    c.startCall();
    c.userSpeechEnded();
    c.sttCompleted('x');
    c.assistantTurnReady('y');
    c.ttsCompleted();          // silence_hold
    c.sleepDecay();            // sleep_decay -> fade_and_hangup
    expect(driver.fadeAndHangup).toHaveBeenCalledTimes(1);
    c.endCall();               // ended -> end_call
    expect(c.state()).toBe('ended');
    expect(driver.endCall).toHaveBeenCalledTimes(1);
  });

  it('endCall from any state hangs up, and ended ignores further signals', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    c.startCall();
    c.endCall();
    expect(c.state()).toBe('ended');
    c.startCall();             // ignored
    c.userSpeechStarted();     // ignored
    expect(c.state()).toBe('ended');
  });

  it('failRecoverable from transcribing recovers to listening (STT hiccup)', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    c.startCall();
    c.userSpeechEnded();           // transcribing
    expect(c.state()).toBe('transcribing');
    c.failRecoverable();           // -> listening (re-opens mic)
    expect(c.state()).toBe('listening');
    expect(driver.openMic).toHaveBeenCalledTimes(2);
  });

  it('failFatal hangs up the call (mic lost)', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    c.startCall();
    c.failFatal();
    expect(c.state()).toBe('ended');
    expect(driver.endCall).toHaveBeenCalledTimes(1);
  });

  it('failRecoverable is a no-op before a call starts', () => {
    const driver = mockDriver();
    const c = createResonanceCallController(driver);
    c.failRecoverable();
    expect(c.state()).toBe('idle');
  });

  it('emits onState / onEvent observers and records the event log', () => {
    const driver = mockDriver();
    const states: string[] = [];
    const events: string[] = [];
    const c = createResonanceCallController(driver, {
      onState: (s) => states.push(s),
      onEvent: (e) => events.push(e),
    });
    c.startCall();
    c.userSpeechEnded();
    expect(states).toEqual(['listening', 'transcribing']);
    expect(events).toEqual(['call.started', 'user.speech.ended']);
    expect(c.events()).toEqual(['call.started', 'user.speech.ended']);
  });
});
