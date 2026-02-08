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
import { api } from '@/lib/api/client';
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
    <div className="aplay-pulsing-dots">
      <span className="aplay-pulsing-dot-1" />
      <span className="aplay-pulsing-dot-2" />
      <span className="aplay-pulsing-dot-3" />
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
    <div className="aplay-voice-selector">
      <Button onClick={() => setIsOpen(!isOpen)} className="fi-dropdown-trigger" title="Cambiar voz" variant="ghost" size="sm" type="button">
        <span className="aplay-voice-label">Voz:</span>
        <span className="aplay-voice-highlight">{getVoiceDisplayName(currentVoice)}</span>
        <ChevronDown className={isOpen ? 'aplay-chevron-open' : 'aplay-chevron'} />
      </Button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="aplay-dropdown-backdrop"
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
                    className={voiceOption.value === currentVoice ? 'aplay-voice-option-active' : 'aplay-voice-option'}
                    variant="ghost"
                    size="sm"
                    type="button"
                  >
                    <span>{voiceOption.label}</span>
                    {voiceOption.value === currentVoice && (
                      <Check className="aplay-check-icon fi-text-purple" strokeWidth={2} aria-hidden="true" />
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
        className="aplay-bar"
      >
        {/* Loading state - horizontal bar */}
        {isLoading && (
          <div className="aplay-loading-row">
            <div className="aplay-loading-icon">
              <PulsingDot />
            </div>
            <span className="aplay-loading-text">Generando audio...</span>
            <span className="aplay-loading-voice">Voz: {voiceName}</span>
            <div className="aplay-spacer" />
            <Button
              onClick={handleClose}
              className="aplay-btn-close"
              aria-label="Cancelar"
              variant="ghost"
              size="sm"
              type="button"
            >
              <X className="aplay-icon-sm" />
            </Button>
          </div>
        )}

        {/* Player controls - horizontal bar layout */}
        {!isLoading && audioUrl && (
          <div className="aplay-controls">
            {/* Left: Voice indicator - matches header icon style */}
            <div className="aplay-voice-group">
              <div className={isUserMessage ? 'aplay-voice-indicator-user' : 'aplay-voice-indicator'}>
                {isUserMessage ? (
                  <User className="aplay-voice-icon-user" />
                ) : (
                  <Volume2 className="aplay-voice-icon-ai" />
                )}
              </div>
              {/* For user messages: show voice selector dropdown */}
              {isUserMessage && onChangeVoice ? (
                <VoiceSelector
                  currentVoice={currentVoice}
                  onSelect={onChangeVoice}
                />
              ) : (
                <span className="aplay-voice-name fi-text-xs-medium">{voiceName}</span>
              )}
            </div>

            {/* Skip back -10s */}
            <Button
              onClick={skipBackward}
              disabled={currentTime === 0}
              className="aplay-btn-skip"
              title="Retroceder 10s"
              variant="ghost"
              size="sm"
              type="button"
            >
              <svg className="aplay-skip-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0019 16V8a1 1 0 00-1.6-.8l-5.334 4zM4.066 11.2a1 1 0 000 1.6l5.334 4A1 1 0 0011 16V8a1 1 0 00-1.6-.8l-5.334 4z" />
              </svg>
              <span>10s</span>
            </Button>

            {/* Play/Pause - white/20 like header icons */}
            <Button
              onClick={togglePlay}
              className="aplay-btn-play"
              aria-label={isPlaying ? 'Pausar' : 'Reproducir'}
              variant="ghost"
              size="lg"
              type="button"
            >
              {isPlaying ? (
                <Pause className="fi-icon-md" strokeWidth={2.5} />
              ) : (
                <Play className="fi-icon-md aplay-play-offset" strokeWidth={2.5} />
              )}
            </Button>

            {/* Skip forward +10s */}
            <Button
              onClick={skipForward}
              disabled={currentTime >= duration}
              className="aplay-btn-skip"
              title="Adelantar 10s"
              variant="ghost"
              size="sm"
              type="button"
            >
              <span>10s</span>
              <svg className="aplay-skip-icon" fill="currentColor" viewBox="0 0 24 24">
                <path d="M11.933 12.8a1 1 0 000-1.6L6.6 7.2A1 1 0 005 8v8a1 1 0 001.6.8l5.333-4zM19.933 12.8a1 1 0 000-1.6l-5.333-4A1 1 0 0013 8v8a1 1 0 001.6.8l5.333-4z" />
              </svg>
            </Button>

            {/* Time display */}
            <span className="aplay-time">
              {formatTime(currentTime)}
            </span>

            {/* Seek bar - takes remaining space */}
            <div className="aplay-seek">
              {/* Track background */}
              <div className="aplay-seek-track">
                {/* Progress fill - white for consistency */}
                <div
                  className="aplay-seek-fill"
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
                className="aplay-seek-input"
              />
              {/* Thumb - appears on hover */}
              <div
                className="aplay-seek-thumb"
                style={{ left: `calc(${progressPercent}% - 6px)` }}
              />
            </div>

            {/* Duration */}
            <span className="aplay-duration">
              {formatTime(duration)}
            </span>

            {/* Close button - matches header button style */}
            <Button
              onClick={handleClose}
              className="aplay-btn-close"
              aria-label="Cerrar"
              title="Cerrar"
              variant="ghost"
              size="sm"
              type="button"
            >
              <X className="aplay-icon-md" />
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
      const blob = await api.blob(`${ROUTES.tts}/synthesize`, { text, voice: voiceValue, speed: 1.0 });
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (error) {
      await reportAudioError(error, 'AudioPlayer:TTS');
      setIsOpen(false);
    } finally {
      setIsLoading(false);
    }
  }, [getVoiceDisplayName]);

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
      const blob = await api.blob(`${ROUTES.tts}/synthesize`, { text: currentText, voice: newVoiceValue, speed: 1.0 });
      const url = URL.createObjectURL(blob);
      setAudioUrl(url);
    } catch (error) {
      await reportAudioError(error, 'AudioPlayer:VoiceChange');
    } finally {
      setIsLoading(false);
    }
  }, [currentText, audioUrl, getVoiceDisplayName]);

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
