/**
 * useAudioRecording - Audio recording state machine hook
 *
 * Extracts MediaRecorder API logic from ConversationCapture
 * Handles: recording, pause, resume, stop, audio level monitoring
 *
 * Created: 2025-11-15
 * Part of: ConversationCapture decomposition refactoring
 */

import { useState, useRef, useCallback } from 'react';

export interface AudioRecordingState {
  isRecording: boolean;
  isPaused: boolean;
  audioLevel: number;
  isSilent: boolean;
  mediaRecorder: MediaRecorder | null;
  audioStream: MediaStream | null;
}

export interface UseAudioRecordingReturn {
  // State
  isRecording: boolean;
  isPaused: boolean;
  audioLevel: number;
  isSilent: boolean;

  // Actions
  startRecording: () => Promise<void>;
  pauseRecording: () => void;
  resumeRecording: () => void;
  stopRecording: () => Promise<Blob | null>;

  // Refs (for advanced usage)
  mediaRecorderRef: React.MutableRefObject<MediaRecorder | null>;
  audioStreamRef: React.MutableRefObject<MediaStream | null>;
}

export interface UseAudioRecordingOptions {
  onDataAvailable?: (blob: Blob) => void;
  onAudioLevelChange?: (level: number, isSilent: boolean) => void;
  mimeType?: string;
  audioBitsPerSecond?: number;
  timeslice?: number; // How often to fire ondataavailable (ms)
}

export function useAudioRecording(
  options: UseAudioRecordingOptions = {}
): UseAudioRecordingReturn {
  const {
    onDataAvailable,
    onAudioLevelChange,
    mimeType = 'audio/webm;codecs=opus',
    audioBitsPerSecond = 128000,
    timeslice,
  } = options;

  // State
  const [isRecording, setIsRecording] = useState(false);
  const [isPaused, setIsPaused] = useState(false);
  const [audioLevel, setAudioLevel] = useState(0);
  const [isSilent, setIsSilent] = useState(true);

  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const animationFrameRef = useRef<number | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  // Audio level monitoring
  const monitorAudioLevel = useCallback(() => {
    if (!analyserRef.current) return;

    const analyser = analyserRef.current;
    const dataArray = new Uint8Array(analyser.frequencyBinCount);

    const updateLevel = () => {
      analyser.getByteFrequencyData(dataArray);

      // Calculate RMS (Root Mean Square) for accurate level
      const rms = Math.sqrt(
        dataArray.reduce((sum, value) => sum + value * value, 0) / dataArray.length
      );

      const normalizedLevel = Math.min(rms / 128, 1); // Normalize to 0-1
      const silent = normalizedLevel < 0.01; // Silence threshold

      setAudioLevel(normalizedLevel);
      setIsSilent(silent);

      if (onAudioLevelChange) {
        onAudioLevelChange(normalizedLevel, silent);
      }

      animationFrameRef.current = requestAnimationFrame(updateLevel);
    };

    updateLevel();
  }, [onAudioLevelChange]);

  // Start recording
  const startRecording = useCallback(async () => {
    try {
      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      audioStreamRef.current = stream;

      // Setup audio analysis
      const audioContext = new AudioContext();
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;

      const source = audioContext.createMediaStreamSource(stream);
      source.connect(analyser);

      audioContextRef.current = audioContext;
      analyserRef.current = analyser;

      // Start monitoring audio levels
      monitorAudioLevel();

      // Create MediaRecorder
      const recorder = new MediaRecorder(stream, {
        mimeType,
        audioBitsPerSecond,
      });

      recordedChunksRef.current = [];

      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          recordedChunksRef.current.push(event.data);

          if (onDataAvailable) {
            onDataAvailable(event.data);
          }
        }
      };

      recorder.start(timeslice);
      mediaRecorderRef.current = recorder;

      setIsRecording(true);
      setIsPaused(false);

      console.log('[AudioRecording] Started recording');
    } catch (error) {
      console.error('[AudioRecording] Failed to start:', error);
      throw error;
    }
  }, [mimeType, audioBitsPerSecond, timeslice, onDataAvailable, monitorAudioLevel]);

  // Pause recording
  const pauseRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.pause();
      setIsPaused(true);
      console.log('[AudioRecording] Paused');
    }
  }, []);

  // Resume recording
  const resumeRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'paused') {
      mediaRecorderRef.current.resume();
      setIsPaused(false);
      console.log('[AudioRecording] Resumed');
    }
  }, []);

  // Stop recording
  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;

      if (!recorder) {
        resolve(null);
        return;
      }

      recorder.onstop = () => {
        const blob = new Blob(recordedChunksRef.current, { type: mimeType });
        console.log('[AudioRecording] Stopped, blob size:', blob.size);

        // Cleanup
        if (animationFrameRef.current) {
          cancelAnimationFrame(animationFrameRef.current);
        }

        if (audioStreamRef.current) {
          audioStreamRef.current.getTracks().forEach((track) => track.stop());
        }

        if (audioContextRef.current) {
          audioContextRef.current.close();
        }

        setIsRecording(false);
        setIsPaused(false);
        setAudioLevel(0);
        setIsSilent(true);

        mediaRecorderRef.current = null;
        audioStreamRef.current = null;
        audioContextRef.current = null;
        analyserRef.current = null;
        recordedChunksRef.current = [];

        resolve(blob);
      };

      recorder.stop();
    });
  }, [mimeType]);

  return {
    isRecording,
    isPaused,
    audioLevel,
    isSilent,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    mediaRecorderRef,
    audioStreamRef,
  };
}
