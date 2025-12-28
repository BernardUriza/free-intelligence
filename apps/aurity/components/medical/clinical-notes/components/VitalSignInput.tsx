'use client';

import { memo } from 'react';
import type { LucideIcon } from 'lucide-react';

interface VitalSignInputProps {
  icon: LucideIcon;
  iconColor: string;
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
  unit?: string;
  type?: 'text' | 'number';
  step?: string;
  inputWidth?: string;
}

export const VitalSignInput = memo(function VitalSignInput({
  icon: Icon,
  iconColor,
  label,
  value,
  onChange,
  placeholder,
  unit,
  type = 'number',
  step,
  inputWidth = 'w-14',
}: VitalSignInputProps) {
  const borderColor = iconColor.replace('text-', 'border-').replace('-400', '-500');
  const ringColor = iconColor.replace('text-', 'ring-').replace('-400', '-500/50');

  return (
    <div
      className={`bg-slate-900 p-3 rounded-lg border border-slate-600 hover:${borderColor} transition-colors`}
    >
      <div className="fi-flex-gap mb-2">
        <Icon className={`h-4 w-4 ${iconColor}`} aria-hidden="true" />
        <span className="fi-text-xs">{label}</span>
      </div>
      <div
        className={`flex items-center gap-1 bg-slate-800/50 px-2 py-1 rounded border border-slate-700 hover:${borderColor} focus-within:${borderColor} focus-within:ring-1 focus-within:${ringColor}`}
      >
        <input
          type={type}
          step={step}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`${inputWidth} bg-transparent text-white text-lg font-semibold border-none outline-none`}
          aria-label={label}
        />
        {unit && <span className="text-slate-400 text-sm">{unit}</span>}
      </div>
    </div>
  );
});
