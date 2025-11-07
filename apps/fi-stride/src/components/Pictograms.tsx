/**
 * T21 Pictograms - Emoji-based visual cues for common actions
 * AC: Pictogramas simples para acciones (play, pausa, stop, check)
 */

import React from 'react';

export const Pictograms = {
  PLAY: '▶️',
  PAUSE: '⏸️',
  STOP: '⏹️',
  CHECK: '✅',
  CLOSE: '✕',
  HEART: '❤️',
  SMILE_GOOD: '😊',
  SMILE_OK: '😐',
  SMILE_TIRED: '😴',
  STAR: '⭐',
  FIRE: '🔥',
  MEDAL: '🏅',
  TROPHY: '🏆',
  THUMBS_UP: '👍',
  BREATHING: '🌬️',
  RESET: '🔄',
  INFO: 'ℹ️',
  WARNING: '⚠️',
  ALERT: '🚨',
} as const;

interface PictogramProps {
  icon: keyof typeof Pictograms;
  size?: 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  animated?: boolean;
  ariaLabel?: string;
}

export const Pictogram: React.FC<PictogramProps> = ({
  icon,
  size = 'md',
  animated = false,
  ariaLabel,
}) => {
  const sizeClasses = {
    sm: 'text-2xl',
    md: 'text-4xl',
    lg: 'text-5xl',
    xl: 'text-6xl',
    '2xl': 'text-8xl',
  };

  return (
    <span
      className={`inline-block transition-transform duration-200 ${
        animated ? 'animate-bounce' : ''
      } ${sizeClasses[size]}`}
      role="img"
      aria-label={ariaLabel || icon}
    >
      {Pictograms[icon]}
    </span>
  );
};
