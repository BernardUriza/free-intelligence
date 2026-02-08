'use client';

/**
 * AudioPlayer - Ultra-Modern Floating Audio Player
 *
 * Design inspired by:
 * - ChatGPT Read Aloud (floating player concept)
 * - Spotify (dark theme, green accents → amber for AURITY)
 * - Apple Music (glassmorphism, blur effects)
 * - Dribbble trends (gradients, micro-interactions)
 *
 * Features:
 * - Glassmorphism with backdrop-blur
 * - Skip buttons with visible time labels (-10s, +10s)
 * - Interactive seek bar with gradient
 * - Smooth micro-interactions (hover, active states)
 * - Pulsing dot loader (not spinner)
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import React from 'react';
import { Play, Pause, X, Volume2, ChevronDown, User, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { VOICE_GROUPS } from '@aurity-standalone/types/voices';
import { reportAudioError } from '@/lib/audio/ErrorPolicy';
import { getBackendUrl } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

type VoiceChangeHandler = (voice: string) => void;

export interface AudioPlayerProps {
  audioUrl: string | null;
  isLoading: boolean;
  voiceName?: string;
  isUserMessage?: boolean;
  currentVoice?: string;
  onClose: () => void;
  onChangeVoice?: VoiceChangeHandler;
}

/**
 * Pulsing dot loading indicator - grows and shrinks smoothly
 */
function PulsingDot() {
  return (
    <div className="flex items-center justify-center gap-1">
      <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse-dot" />
      <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse-dot-delay-1" />
      <span className="w-1.5 h-1.5 bg-white rounded-full animate-pulse-dot-delay-2" />
    </div>
  );
}

/**
 * Format seconds to mm:ss
 */
function formatTime(seconds: number): string {
  if (!isFinite(seconds) || isNaN(seconds)) return '0:00';
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Voice selector dropdown for user messages
function VoiceSelector({
  currentVoice,
  onSelect
}: {
  currentVoice: string;
  onSelect: VoiceChangeHandler;
}) {
  const [isOpen, setIsOpen] = useState(false);

  // Get current voice display name
  const getVoiceDisplayName = (voiceId: string): string => {
    for (const group of VOICE_GROUPS) {
      const foundVoice = group.voices.find(v => v.value === voiceId);
      if (foundVoice) return foundVoice.label.split(' ')[0]; // Just the name part
    }
    const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
    return match ? match[1] : voiceId;
  };

  return (
    <div className="relative">
      <Button onClick={() => setIsOpen(!isOpen)} className="fi-dropdown-trigger" title="Cambiar voz" variant="ghost" size="sm" type="button">
        <span className="hidden sm:inline">Voz:</span>
        <span className="text-purple-200">{getVoiceDisplayName(currentVoice)}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </Button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="fi-dropdown-menu">
            {VOICE_GROUPS.map((group) => (
              <div key={group.label}>
                <div className="fi-dropdown-group-header">
                  {group.label}
                </div>
                {group.voices.map((voiceOption) => (
                  <Button
                    key={`${voiceOption.provider}-${voiceOption.value}`}
                    onClick={() => {
                      onSelect(voiceOption.value);
                      setIsOpen(false);
                    }}
                    className={`w-full px-3 py-2 text-left text-sm flex items-center justify-between ${voiceOption.value === currentVoice ? 'bg-purple-500/20 text-purple-200' : 'text-white'}`}
                    variant="ghost"
                    size="sm"
                    type="button"
                  >
                    <span>{voiceOption.label}</span>
                    {voiceOption.value === currentVoice && (
                      <Check className="w-3 h-3 fi-text-purple" strokeWidth={2} aria-hidden="true" />
                    )}
                  </Button>
                ))}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

export function AudioPlayer({
  audioUrl,
  isLoading,
  voiceName = 'nova',
  isUserMessage = false,
  currentVoice = 'nova',
  onClose,
  onChangeVoice,
}: AudioPlayerProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isDragging, setIsDragging] = useState(false);

  // Create audio element when URL changes
  useEffect(() => {
    if (!audioUrl) return;

    const audio = new Audio(audioUrl);
    audioRef.current = audio;

    const handleLoadedMetadata = () => setDuration(audio.duration);
    const handleTimeUpdate = () => {
      if (!isDragging) setCurrentTime(audio.currentTime);
    };
    const handleEnded = () => {
      setIsPlaying(false);
      setCurrentTime(0);
    };
    const handlePlay = () => setIsPlaying(true);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('ended', handleEnded);
    audio.addEventListener('play', handlePlay);
    audio.addEventListener('pause', handlePause);

    // Auto-play when loaded
    audio.play().catch(err => reportAudioError(err, 'AudioPlayer'));

    return () => {
      audio.pause();
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('ended', handleEnded);
      audio.removeEventListener('play', handlePlay);
      audio.removeEventListener('pause', handlePause);
      URL.revokeObjectURL(audioUrl);
    };
  }, [audioUrl, isDragging]);

  const togglePlay = useCallback(() => {
    if (!audioRef.current) return;
    if (isPlaying) {
      audioRef.current.pause();
    } else {
      audioRef.current.play();
    }
  }, [isPlaying]);

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (audioRef.current) {
      audioRef.current.currentTime = time;
    }
  }, []);

  const skipBackward = useCallback(() => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.max(0, audioRef.current.currentTime - 10);
  }, []);

  const skipForward = useCallback(() => {
    if (!audioRef.current) return;
    audioRef.current.currentTime = Math.min(duration, audioRef.current.currentTime + 10);
  }, [duration]);

  const handleClose = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
    }
    onClose();
  }, [onClose]);

  // Progress percentage for gradient
  const progressPercent = duration > 0 ? (currentTime / duration) * 100 : 0;

  return (
    <>
      {/* Full-width top bar - matches app header gradient */}
      <div
        className="
          fixed top-0 left-0 right-0 z-50
          ${gradients.primaryStrong}
          backdrop-blur-xl
          border-b border-white/20
          shadow-lg shadow-purple-900/30
          animate-slide-down
        "
      >
        {/* Loading state - horizontal bar */}
        {isLoading && (
          <div className="flex items-center gap-4 px-4 py-3">
            <div className="w-8 h-8 bg-white/20 rounded-full flex items-center justify-center">
              <PulsingDot />
            </div>
            <span className="text-white text-sm font-medium">Generando audio...</span>
            <span className="text-purple-200 text-xs">Voz: {voiceName}</span>
            <div className="flex-1" />
            <Button
              onClick={handleClose}
              className="p-1 rounded text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Cancelar"
              variant="ghost"
              size="sm"
              type="button"
            >
              <X className="w-4 h-4" />
            </Button>
          </div>
        )}

        {/* Player controls - horizontal bar layout */}
        {!isLoading && audioUrl && (
          <div className="flex items-center gap-3 px-4 py-2">
            {/* Left: Voice indicator - matches header icon style */}
            <div className="flex items-center gap-2 min-w-0">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isUserMessage ? 'bg-amber-500/30' : 'bg-white/20'}`}>
                {isUserMessage ? (
                  <User className="w-4 h-4 text-amber-200" />
                ) : (
                  <Volume2 className="w-4 h-4 text-white" />
                )}
              </div>
              {/* For user messages: show voice selector dropdown */}
              {isUserMessage && onChangeVoice ? (
                <VoiceSelector
                  currentVoice={currentVoice}
                  onSelect={onChangeVoice}
                />
              ) : (
                <span className="text-purple-200 fi-text-xs-medium truncate hidden sm:block">{voiceName}</span>
              )}
            </div>

            {/* Skip back -10s */}
            <Button
              onClick={skipBackward}
              disabled={currentTime === 0}
              className="flex items-center gap-1 px-2 py-1 rounded text-white/70 hover:text-white hover:bg-white/10 text-xs font-semibold transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="Retroceder 10s"
              variant="ghost"
              size="sm"
              type="button"
            >
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.334 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
              </svg>
              <span>10s</span>
            </Button>

            {/* Play/Pause - white/20 like header icons */}
            <Button
              onClick={togglePlay}
              className="bg-white/20 hover:bg-white/30 rounded-full w-10 h-10 flex items-center justify-center text-white transition-colors hover:scale-105 active:scale-95"
              aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
              variant="ghost"
              size="lg"
              type="button"
            >
              {isPlaying ? (
                <Pause className="fi-icon-md" strokeWidth={2.5} />
              ) : (
                <Play className="fi-icon-md ml-0.5" strokeWidth={2.5} />
              )}
            </Button>

            {/* Skip forward +10s */}
            <Button
              onClick={skipForward}
              disabled={currentTime >= duration}
              className="flex items-center gap-1 px-2 py-1 rounded text-white/70 hover:text-white hover:bg-white/10 text-xs font-semibold transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
              title="Adelantar 10s"
              variant="ghost"
              size="sm"
              type="button"
            >
              <span>10s</span>
              <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
              </svg>
            </Button>

            {/* Time display */}
            <span className="text-white/80 text-xs font-mono tabular-nums">
              {formatTime(currentTime)}
            </span>

            {/* Seek bar - takes remaining space */}
            <div className="flex-1 relative h-1 group cursor-pointer min-w-[80px]">
              {/* Track background */}
              <div className="absolute inset-0 bg-white/30 rounded-full overflow-hidden">
                {/* Progress fill - white for consistency */}
                <div
                  className="h-full bg-white rounded-full transition-all duration-75"
                  style={{ width: `${progressPercent}%` }}
                />
              </div>
              {/* Range input */}
              <input
                type="range"
                min={0}
                max={duration || 100}
                value={currentTime}
                onChange={handleSeek}
                onMouseDown={() => setIsDragging(true)}
                onMouseUp={() => setIsDragging(false)}
                onTouchStart={() => setIsDragging(true)}
                onTouchEnd={() => setIsDragging(false)}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
              />
              {/* Thumb - appears on hover */}
              <div
                className="
                  absolute top-1/2 -translate-y-1/2
                  w-3 h-3 rounded-full
                  bg-white shadow-md
                  pointer-events-none
                  opacity-0 group-hover:opacity-100
                  transition-opacity
                "
                style={{ left: `calc(${progressPercent}% - 6px)` }}
              />
            </div>

            {/* Duration */}
            <span className="text-white/50 text-xs font-mono tabular-nums">
              {formatTime(duration)}
            </span>

            {/* Close button - matches header button style */}
            <Button
              onClick={handleClose}
              className="p-1 rounded text-white/70 hover:text-white hover:bg-white/10 transition-colors"
              aria-label="Cerrar"
              title="Cerrar"
              variant="ghost"
              size="sm"
              type="button"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        )}
      </div>
    </>
  );
}

/**
 * Hook to manage audio player state
 */
export function useAudioPlayer() {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const [voiceName, setVoiceName] = useState('nova');
  const [isUserMessage, setIsUserMessage] = useState(false);
  const [currentVoice, setCurrentVoice] = useState('nova');
  const [currentText, setCurrentText] = useState('');

  const BACKEND_URL = getBackendUrl();

  // Helper to extract display name from voice ID
  const getVoiceDisplayName = useCallback((voiceId: string): string => {
    // Check in VOICE_GROUPS first
    for (const group of VOICE_GROUPS) {
      const foundVoice = group.voices.find(v => v.value === voiceId);
      if (foundVoice) return foundVoice.label.split(' ')[0];
    }
    // Fallback: extract from Azure-style name
    const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
    return match ? match[1] : voiceId;
  }, []);

  const generateAudio = useCallback(async (text: string, voiceValue: string = 'nova', isUser: boolean = false) => {
    // Store state for potential voice changes
    setCurrentText(text);
    setCurrentVoice(voiceValue);
    setIsUserMessage(isUser);
    setVoiceName(getVoiceDisplayName(voiceValue));

    setIsOpen(true);
    setIsLoading(true);
    setAudioUrl(null);

    try {
      const response = await fetch(`${BACKEND_URL}${ROUTES.tts}/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, voice: voiceValue, speed: 1.0 }),
      });

      if (!response.ok) {
        throw new Error(`TTS failed: ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (error) {
      await reportAudioError(error, 'AudioPlayer:TTS');
      setIsOpen(false);
    } finally {
      setIsLoading(false);
    }
  }, [BACKEND_URL, getVoiceDisplayName]);

  // Handle voice change for user messages - regenerate audio with new voice
  const changeVoice = useCallback(async (newVoiceValue: string) => {
    if (!currentText) return;

    setCurrentVoice(newVoiceValue);
    setVoiceName(getVoiceDisplayName(newVoiceValue));
    setIsLoading(true);

    // Revoke old URL
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    setAudioUrl(null);

    try {
      const response = await fetch(`${BACKEND_URL}${ROUTES.tts}/synthesize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: currentText, voice: newVoiceValue, speed: 1.0 }),
      });

      if (!response.ok) {
        throw new Error(`TTS failed: ${response.status}`);
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (error) {
      await reportAudioError(error, 'AudioPlayer:VoiceChange');
    } finally {
      setIsLoading(false);
    }
  }, [BACKEND_URL, currentText, audioUrl, getVoiceDisplayName]);

  const close = useCallback(() => {
    setIsOpen(false);
    setAudioUrl(null);
    setIsLoading(false);
    setCurrentText('');
    setIsUserMessage(false);
  }, []);

  return {
    isOpen,
    isLoading,
    audioUrl,
    voiceName,
    isUserMessage,
    currentVoice,
    currentText,
    generateAudio,
    changeVoice,
    close,
  };
}
