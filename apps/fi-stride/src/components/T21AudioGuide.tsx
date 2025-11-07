/**
 * T21AudioGuide - Text-to-speech utility for accessible instructions
 * AC: Audio-guía en /t21/* rutas (locución clara)
 * Uses Web Speech API for browser-native TTS
 */

import React, { useState, useRef } from 'react';
import { Pictogram } from './Pictograms';

interface T21AudioGuideProps {
  text: string;
  autoPlay?: boolean;
  rate?: number; // 0.5 - 2.0, default 1.0
  pitch?: number; // 0.5 - 2.0, default 1.0
  lang?: string; // 'es-ES', 'en-US', etc.
}

export const T21AudioGuide: React.FC<T21AudioGuideProps> = ({
  text,
  autoPlay = false,
  rate = 0.9, // Slower than normal for clarity
  pitch = 1.0,
  lang = 'es-ES',
}) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null);

  const speak = () => {
    if (!('speechSynthesis' in window)) {
      console.error('Web Speech API not supported');
      return;
    }

    // Cancel any ongoing speech
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = rate;
    utterance.pitch = pitch;

    utterance.onstart = () => setIsPlaying(true);
    utterance.onend = () => setIsPlaying(false);
    utterance.onerror = () => setIsPlaying(false);

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  const stop = () => {
    window.speechSynthesis.cancel();
    setIsPlaying(false);
  };

  React.useEffect(() => {
    if (autoPlay) {
      speak();
    }
    return () => {
      window.speechSynthesis.cancel();
    };
  }, [text, autoPlay, rate, pitch, lang]);

  return (
    <div className="flex items-center gap-2">
      <button
        onClick={isPlaying ? stop : speak}
        className="bg-purple-700 hover:bg-purple-800 text-white px-4 py-3 rounded-lg
                   font-bold uppercase text-lg focus:outline-2 focus:outline-offset-2
                   focus:outline-white transition-all duration-200"
        aria-label={isPlaying ? 'Detener lectura' : 'Leer en voz alta'}
      >
        <Pictogram icon={isPlaying ? 'PAUSE' : 'PLAY'} size="md" />
      </button>
      <span className="text-sm text-gray-600">
        {isPlaying ? 'Leyendo...' : 'Toca para escuchar'}
      </span>
    </div>
  );
};

/**
 * Hook: useAudioGuide
 * Manage audio guide state globally
 */
export const useAudioGuide = () => {
  const [isSpeaking, setIsSpeaking] = useState(false);

  const speak = (text: string, lang = 'es-ES', rate = 0.9) => {
    if (!('speechSynthesis' in window)) {
      console.error('Web Speech API not supported');
      return;
    }

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = lang;
    utterance.rate = rate;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const stop = () => {
    window.speechSynthesis.cancel();
    setIsSpeaking(false);
  };

  return { speak, stop, isSpeaking };
};
