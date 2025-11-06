import React from 'react';
import { useAccessibility } from './AccessibilityContext';

interface RPEScaleProps {
  value: number;
  onChange: (value: number) => void;
  label?: string;
  description?: string;
  variant?: 'inline' | 'grid';
}

const RPE_LABELS = {
  0: { emoji: '😴', label: 'Descansado', description: 'Sin esfuerzo' },
  1: { emoji: '😊', label: 'Muy Fácil', description: 'Conversación cómoda' },
  2: { emoji: '😐', label: 'Fácil', description: 'Respiración normal' },
  3: { emoji: '🙂', label: 'Moderado', description: 'Respiración rítmica' },
  4: { emoji: '😤', label: 'Difícil', description: 'Difícil hablar' },
  5: { emoji: '😫', label: 'Muy Difícil', description: 'No puedo hablar' },
};

export function RPEScale({
  value,
  onChange,
  label = 'Esfuerzo Percibido',
  description,
  variant = 'grid',
}: RPEScaleProps) {
  const { settings, speak } = useAccessibility();

  const handleSelect = (level: number) => {
    onChange(level);
    if (settings.enableTextToSpeech) {
      speak(`${RPE_LABELS[level as keyof typeof RPE_LABELS].label}`);
    }
  };

  if (variant === 'inline') {
    return (
      <div className="flex flex-col gap-3">
        {label && (
          <label className="text-base font-semibold">
            {label}
            {description && <div className="text-sm text-slate-400">{description}</div>}
          </label>
        )}
        <div className="flex gap-2 flex-wrap">
          {Object.entries(RPE_LABELS).map(([level, data]) => (
            <button
              key={level}
              onClick={() => handleSelect(Number(level))}
              className={`flex flex-col items-center gap-1 p-2 rounded-lg transition-all ${
                value === Number(level) ? 'bg-blue-500 ring-2 ring-blue-400 scale-110' : 'bg-slate-700 hover:bg-slate-600'
              }`}
              aria-selected={value === Number(level)}
              aria-label={`${data.label}: ${data.description}`}
            >
              <span className="text-2xl">{data.emoji}</span>
              <span className="text-xs text-center">{level}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {label && (
        <label className="text-lg font-semibold">
          {label}
          {description && <div className="text-sm text-slate-400">{description}</div>}
        </label>
      )}
      <div className="grid grid-cols-3 gap-3 md:grid-cols-6">
        {Object.entries(RPE_LABELS).map(([level, data]) => (
          <button
            key={level}
            onClick={() => handleSelect(Number(level))}
            className={`flex flex-col items-center gap-2 p-3 rounded-lg transition-all focus:outline-none focus:ring-2 focus:ring-blue-400 ${
              value === Number(level)
                ? 'bg-blue-500 ring-2 ring-blue-400'
                : 'bg-slate-700 hover:bg-slate-600'
            }`}
            aria-selected={value === Number(level)}
            aria-label={`${data.label}: ${data.description}`}
          >
            <span className="text-3xl md:text-4xl">{data.emoji}</span>
            <span className="text-xs font-semibold text-center">{level}</span>
            <span className="text-xs text-center hidden md:block">{data.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
