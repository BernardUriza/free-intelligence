'use client';

import { memo } from 'react';
import type { LucideIcon } from 'lucide-react';

/** Static lookup: iconColor → { card, input, icon } CSS classes */
const VITAL_VARIANTS: Record<string, { card: string; input: string; icon: string }> = {
  'text-red-400':    { card: 'med-vital-card-red',   input: 'med-vital-input-red',   icon: 'text-red-400' },
  'text-cyan-400':   { card: 'med-vital-card-cyan',  input: 'med-vital-input-cyan',  icon: 'text-cyan-400' },
  'fi-text-primary': { card: 'med-vital-card-blue',  input: 'med-vital-input-blue',  icon: 'fi-text-primary' },
  'fi-text-green':   { card: 'med-vital-card-green', input: 'med-vital-input-green', icon: 'fi-text-green' },
};

const DEFAULT_VARIANT = VITAL_VARIANTS['text-red-400'];

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
  const variant = VITAL_VARIANTS[iconColor] ?? DEFAULT_VARIANT;

  return (
    <div className={variant.card}>
      <div className="fi-flex-gap mb-2">
        <Icon className={`h-4 w-4 ${variant.icon}`} aria-hidden="true" />
        <span className="fi-text-xs">{label}</span>
      </div>
      <div className={variant.input}>
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
