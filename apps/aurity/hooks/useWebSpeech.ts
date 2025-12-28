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
      console.log('[WebSpeech] Started');
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
          console.log('[WebSpeech] Final:', transcript);
          if (onTranscript) {
            onTranscript(transcript, true);
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

    // Track consecutive errors for smart retry
    let consecutiveErrors = 0;
    const MAX_CONSECUTIVE_ERRORS = 3;

    recognition.onerror = (event: any) => {
      // Ignore common non-critical errors
      if (event.error === 'no-speech') {
        return; // Normal silence, don't log
      }

      consecutiveErrors++;

      // Only log first few errors to avoid spam
      if (consecutiveErrors <= MAX_CONSECUTIVE_ERRORS) {
        console.warn(
          `[WebSpeech] Error ${consecutiveErrors}/${MAX_CONSECUTIVE_ERRORS}:`,
          event.error,
          '(using backend transcription)'
        );
      } else if (consecutiveErrors === MAX_CONSECUTIVE_ERRORS + 1) {
        console.warn(
          '[WebSpeech] Too many errors - suppressing further logs. Backend transcription active.'
        );
      }

      setError(event.error);
    };

    recognition.onend = () => {
      setIsListening(false);

      // Auto-restart if not manually stopped (continuous mode)
      if (continuous && !isStoppingRef.current) {
        // Stop auto-restart after too many errors
        if (consecutiveErrors > MAX_CONSECUTIVE_ERRORS) {
          console.warn(
            '[WebSpeech] Auto-restart disabled after multiple failures. Backend transcription active.'
          );
          return;
        }

        // Only log restart on first few attempts
        if (consecutiveErrors <= MAX_CONSECUTIVE_ERRORS) {
          console.log('[WebSpeech] Auto-restarting...');
        }

        try {
          recognition.start();
        } catch (err) {
          if (consecutiveErrors <= MAX_CONSECUTIVE_ERRORS) {
            console.error('[WebSpeech] Restart failed:', err);
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
  }, [isSupported, language, continuous, interimResults, onTranscript]);

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
      recognitionRef.current.start();
      console.log('[WebSpeech] Start requested');
    } catch (err) {
      console.error('[WebSpeech] Start error:', err);
      setError(err instanceof Error ? err.message : 'Error al iniciar Web Speech');
    }
  }, [isSupported]);

  const stopWebSpeech = useCallback(() => {
    if (!recognitionRef.current) return;

    try {
      isStoppingRef.current = true;
      recognitionRef.current.stop();
      setInterimTranscript('');
      console.log('[WebSpeech] Stop requested');
    } catch (err) {
      console.error('[WebSpeech] Stop error:', err);
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
