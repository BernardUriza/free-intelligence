#!/usr/bin/env python3
"""Synthesize RESONANCE's two UI sound cues from scratch (numpy additive synthesis).

- crystalline.wav : one-shot chime on user.speech.ended (end-of-speech).
  Inharmonic bell partials (1 : 2.76 : 5.40 : 8.93) + fast exponential decay = glass.
- thinking.wav    : subtle loop while the assistant is thinking; stop() on the
  response interrupts it. Soft low sine, amplitude envelope hits 0 at both ends
  so the loop is seamless (no click), regardless of carrier phase.

Run: python3 generate-resonance-cues.py   (writes WAV to ../public/sounds/, then
mp3 via ffmpeg if available). numpy only; no scipy/soundfile needed.
"""
import os
import subprocess
import wave

import numpy as np

SR = 44100
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "sounds")


def write_wav(path: str, samples: np.ndarray) -> None:
    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(path, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def soft_attack(env: np.ndarray, ms: float = 5.0) -> np.ndarray:
    n = max(1, int(SR * ms / 1000))
    env = env.copy()
    env[:n] *= np.linspace(0.0, 1.0, n)
    return env


def crystalline(dur: float = 0.7, f0: float = 880.0) -> np.ndarray:
    t = np.linspace(0.0, dur, int(SR * dur), endpoint=False)
    partials = [(1.0, 1.0), (2.76, 0.55), (5.40, 0.28), (8.93, 0.13)]  # bell ratios
    sig = sum(amp * np.sin(2 * np.pi * f0 * ratio * t) for ratio, amp in partials)
    env = soft_attack(np.exp(-t * 6.0))  # bright, fast glassy decay
    return sig * env * 0.42


def ready(note_dur: float = 0.14) -> np.ndarray:
    # "Your turn — mic is open." Warm HARMONIC two-note RISE (C5 -> G5), the
    # opposite gesture to the bright falling inharmonic crystalline, so Bernard
    # can tell "I finished" (crystalline) from "your turn now" (this one).
    def note(freq: float) -> np.ndarray:
        t = np.linspace(0.0, note_dur, int(SR * note_dur), endpoint=False)
        sig = np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2 * t)
        env = np.sin(np.pi * t / note_dur) ** 1.5  # soft in/out, ends at 0
        return sig * env
    return np.concatenate([note(523.25), note(783.99)]) * 0.3  # C5 -> G5


def thinking(dur: float = 1.2, f: float = 174.61) -> np.ndarray:
    # Two gentle "breaths" per loop. env(0)==env(dur)==0 -> seamless, click-free.
    t = np.linspace(0.0, dur, int(SR * dur), endpoint=False)
    breaths = np.sin(np.pi * (t / dur) * 2.0) ** 2  # 2 raised bumps, zero at ends
    carrier = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)
    return carrier * breaths * 0.12  # subtle


def to_mp3(wav_path: str) -> bool:
    mp3_path = wav_path[:-4] + ".mp3"
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", wav_path, "-codec:a", "libmp3lame", "-q:a", "4", mp3_path],
            check=True, capture_output=True,
        )
        return True
    except Exception as e:  # ffmpeg missing or failed -> WAV is enough for Web Audio
        print(f"  (mp3 skipped: {e})")
        return False


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    for name, samples in (("crystalline", crystalline()), ("thinking", thinking()), ("ready", ready())):
        wav = os.path.join(OUT, f"{name}.wav")
        write_wav(wav, samples)
        mp3 = to_mp3(wav)
        print(f"{name}: {wav}{'  + .mp3' if mp3 else ''}  ({len(samples)/SR:.2f}s)")


if __name__ == "__main__":
    main()
