/**
 * useWebSpeech Hook
 *
 * Provides instant transcription using Web Speech API (browser native).
 * Use as fallback for instant preview while Whisper processes in background.
 *
 * Features:
 * - Instant transcription (no backend latency)
 * - Continuous recognition with auto-restart
 * - Language detection (es-MX, en-US)
 * - Interim results for real-time feedback
 *
 * @example
 * const { startWebSpeech, stopWebSpeech, isListening, interimTranscript } =
 *   useWebSpeech({
 *     onTranscript: (text) => console.log('Final:', text),
 *     language: 'es-MX'
 *   });
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('WebSpeech');

interface UseWebSpeechConfig {
  onTranscript?: (transcript: string, isFinal: boolean) => void;
  language?: string;
  continuous?: boolean;
  interimResults?: boolean;
}

interface UseWebSpeechReturn {
  isListening: boolean;
  interimTranscript: string;
  error: string | null;
  isSupported: boolean;
  startWebSpeech: () => void;
  stopWebSpeech: () => void;
}

export function useWebSpeech(config: UseWebSpeechConfig = {}): UseWebSpeechReturn {
  const {
    onTranscript,
    language = 'es-MX',
    continuous = true,
    interimResults = true,
  } = config;

  const [isListening, setIsListening] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState('');
  const [error, setError] = useState<string | null>(null);
  const recognitionRef = useRef<any>(null);
  const isStoppingRef = useRef(false);

  // Fix: Use refs to persist state across effect re-runs and avoid dependency array issues
  const consecutiveErrorsRef = useRef(0);
  const onTranscriptRef = useRef(onTranscript);

  // Keep onTranscript ref updated without triggering effect re-run
  useEffect(() => {
    onTranscriptRef.current = onTranscript;
  }, [onTranscript]);

  // Check browser support
  const isSupported =
    typeof window !== 'undefined' &&
    ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window);

  // Initialize recognition
  useEffect(() => {
    if (!isSupported) return;

    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    const recognition = new SpeechRecognition();
    recognition.continuous = continuous;
    recognition.interimResults = interimResults;
    recognition.lang = language;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
      log.debug('Started');
      setIsListening(true);
      setError(null);
    };

    recognition.onresult = (event: any) => {
      let interim = '';
      let final = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const result = event.results[i];
        const transcript = result[0].transcript;

        if (result.isFinal) {
          final += transcript + ' ';
          log.debug('Final transcript received');
          // Use ref to avoid stale closure and dependency array issues
          if (onTranscriptRef.current) {
            onTranscriptRef.current(transcript, true);
          }
        } else {
          interim += transcript;
        }
      }

      if (interim) {
        setInterimTranscript(interim);
      } else if (final) {
        setInterimTranscript('');
      }
    };

    // Use ref to persist error count across effect re-runs (fixes infinite loop bug)
    const MAX_CONSECUTIVE_ERRORS = 3;

    recognition.onerror = (event: any) => {
      // Ignore common non-critical errors
      if (event.error === 'no-speech') {
        return; // Normal silence, don't log
      }

      consecutiveErrorsRef.current++;

      // Only log first few errors to avoid spam
      if (consecutiveErrorsRef.current <= MAX_CONSECUTIVE_ERRORS) {
        log.warn('Recognition error (using backend transcription)', {
          attempt: consecutiveErrorsRef.current,
          error: event.error,
        });
      } else if (consecutiveErrorsRef.current === MAX_CONSECUTIVE_ERRORS + 1) {
        log.warn('Too many errors, suppressing further logs');
      }

      setError(event.error);
    };

    recognition.onend = () => {
      setIsListening(false);

      // Auto-restart if not manually stopped (continuous mode)
      if (continuous && !isStoppingRef.current) {
        // Stop auto-restart after too many errors
        if (consecutiveErrorsRef.current > MAX_CONSECUTIVE_ERRORS) {
          log.warn('Auto-restart disabled after multiple failures');
          return;
        }

        try {
          recognition.start();
        } catch (err) {
          if (consecutiveErrorsRef.current <= MAX_CONSECUTIVE_ERRORS) {
            log.error('Restart failed', { error: String(err) });
          }
        }
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop();
        } catch {
          // Ignore errors on cleanup
        }
      }
    };
    // Note: onTranscript intentionally excluded - we use onTranscriptRef to avoid effect thrashing
  }, [isSupported, language, continuous, interimResults]);

  const startWebSpeech = useCallback(() => {
    if (!isSupported) {
      setError('Web Speech API no soportada en este navegador');
      return;
    }

    if (!recognitionRef.current) {
      setError('Recognition not initialized');
      return;
    }

    try {
      isStoppingRef.current = false;
      consecutiveErrorsRef.current = 0; // Reset error counter on manual start
      recognitionRef.current.start();
    } catch (err) {
      log.error('Start error', { error: String(err) });
      setError(err instanceof Error ? err.message : 'Error al iniciar Web Speech');
    }
  }, [isSupported]);

  const stopWebSpeech = useCallback(() => {
    if (!recognitionRef.current) return;

    try {
      isStoppingRef.current = true;
      recognitionRef.current.stop();
      setInterimTranscript('');
    } catch (err) {
      log.error('Stop error', { error: String(err) });
    }
  }, []);

  return {
    isListening,
    interimTranscript,
    error,
    isSupported,
    startWebSpeech,
    stopWebSpeech,
  };
}
