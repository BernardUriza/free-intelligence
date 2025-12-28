/**
 * useAudioAnalysis Hook
 *
 * Analiza el nivel de audio en tiempo real usando Web Audio API.
 * Incluye detección de silencio y control de ganancia.
 * Extraído de ConversationCapture durante refactoring incremental.
 *
 * @example
 * const { audioLevel, isSilent } = useAudioAnalysis(stream, {
 *   silenceThreshold: 5,
 *   gain: 2.5,
 *   isActive: isRecording
 * });
 */

import { useState, useRef, useEffect } from 'react';
import { AUDIO_CONFIG } from '@/lib/audio/constants';

interface AudioAnalysisConfig {
  silenceThreshold?: number;
  gain?: number;
  isActive: boolean;
}

interface UseAudioAnalysisReturn {
  audioLevel: number;
  isSilent: boolean;
}

export function useAudioAnalysis(
  stream: MediaStream | null,
  config: AudioAnalysisConfig
): UseAudioAnalysisReturn {
  const {
    silenceThreshold = AUDIO_CONFIG.SILENCE_THRESHOLD,
    gain = AUDIO_CONFIG.AUDIO_GAIN,
    isActive,
  } = config;

  const [audioLevel, setAudioLevel] = useState(0);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const animationFrameRef = useRef<number | null>(null);

  // Calculate if audio is below silence threshold
  const isSilent = audioLevel < silenceThreshold;

  // Real-time audio level analysis using Web Audio API
  useEffect(() => {
    if (!stream || !isActive) {
      setAudioLevel(0);
      return;
    }

    // Create AudioContext and Analyser
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const gainNode = audioContext.createGain();
    const source = audioContext.createMediaStreamSource(stream);

    // Configure gain for low-volume microphones
    gainNode.gain.value = gain;

    // Configure analyser for real-time response
    analyser.fftSize = 256;
    analyser.smoothingTimeConstant = 0.8;

    // Audio routing: source → gain → analyser
    source.connect(gainNode);
    gainNode.connect(analyser);

    audioContextRef.current = audioContext;
    analyserRef.current = analyser;

    console.log(
      `[Audio Setup] Gain: ${gain}x, Silence threshold: ${silenceThreshold}/255 (${Math.round((silenceThreshold / 255) * 100)}%)`
    );

    // Audio analysis loop
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateLevel = () => {
      if (!analyserRef.current) return;

      analyserRef.current.getByteFrequencyData(dataArray);

      // Calculate average level (0-255 range)
      const average = dataArray.reduce((a, b) => a + b, 0) / dataArray.length;
      setAudioLevel(average);

      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };

    updateLevel();

    // Cleanup function
    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [stream, isActive, gain, silenceThreshold]);

  return { audioLevel, isSilent };
}
