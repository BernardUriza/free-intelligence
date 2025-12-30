/**
 * TimeRangeInput - Start/End time picker pair
 *
 * Compact time range selector with validation feedback
 */

'use client';

import { useId } from 'react';
import { Input } from '@/components/ui/input';
import { AlertCircle } from 'lucide-react';

interface TimeRangeInputProps {
  startTime: string;
  endTime: string;
  onStartChange: (time: string) => void;
  onEndChange: (time: string) => void;
  error?: string;
  disabled?: boolean;
  showLabels?: boolean;
  compact?: boolean;
}

export function TimeRangeInput({
  startTime,
  endTime,
  onStartChange,
  onEndChange,
  error,
  disabled = false,
  showLabels = true,
  compact = false,
}: TimeRangeInputProps) {
  const id = useId();

  return (
    <div className={`flex items-center gap-2 ${compact ? '' : 'flex-wrap'}`}>
      <div className={compact ? '' : 'flex-1 min-w-[100px]'}>
        {showLabels && (
          <label
            htmlFor={`${id}-start`}
            className="block text-xs text-slate-500 mb-1"
          >
            Inicio
          </label>
        )}
        <Input
          id={`${id}-start`}
          type="time"
          value={startTime}
          onChange={(e) => onStartChange(e.target.value)}
          disabled={disabled}
          className={`${compact ? 'w-24 text-sm' : 'w-full'} ${
            error ? 'border-red-500 focus:ring-red-500' : ''
          }`}
          aria-invalid={!!error}
          aria-describedby={error ? `${id}-error` : undefined}
        />
      </div>

      <span className={`text-slate-500 ${showLabels ? 'mt-5' : ''}`}>—</span>

      <div className={compact ? '' : 'flex-1 min-w-[100px]'}>
        {showLabels && (
          <label
            htmlFor={`${id}-end`}
            className="block text-xs text-slate-500 mb-1"
          >
            Fin
          </label>
        )}
        <Input
          id={`${id}-end`}
          type="time"
          value={endTime}
          onChange={(e) => onEndChange(e.target.value)}
          disabled={disabled}
          className={`${compact ? 'w-24 text-sm' : 'w-full'} ${
            error ? 'border-red-500 focus:ring-red-500' : ''
          }`}
          aria-invalid={!!error}
        />
      </div>

      {error && (
        <div
          id={`${id}-error`}
          className="flex items-center gap-1 text-red-400 text-xs mt-1 w-full"
          role="alert"
        >
          <AlertCircle className="w-3 h-3 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}

export default TimeRangeInput;
