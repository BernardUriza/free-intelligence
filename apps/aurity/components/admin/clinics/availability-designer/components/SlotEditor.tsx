/**
 * SlotEditor - Single time slot editor row
 *
 * Inline editor for a single working time slot with delete action
 */

'use client';

import { Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { TimeRangeInput } from './TimeRangeInput';
import type { WeeklySlot } from '../types';

interface SlotEditorProps {
  slot: WeeklySlot;
  index: number;
  onUpdate: (updates: Partial<WeeklySlot>) => void;
  onRemove: () => void;
  error?: string;
  canRemove?: boolean;
  disabled?: boolean;
}

export function SlotEditor({
  slot,
  index,
  onUpdate,
  onRemove,
  error,
  canRemove = true,
  disabled = false,
}: SlotEditorProps) {
  return (
    <div
      className={`flex items-center gap-2 p-2 rounded-md transition-colors ${
        error ? 'bg-red-500/10' : 'bg-slate-800/30 hover:bg-slate-800/50'
      }`}
    >
      {/* Slot number indicator */}
      <div className="admin-slot-number">
        {index + 1}
      </div>

      {/* Time range */}
      <div className="flex-1">
        <TimeRangeInput
          startTime={slot.start}
          endTime={slot.end}
          onStartChange={(start) => onUpdate({ start })}
          onEndChange={(end) => onUpdate({ end })}
          error={error}
          disabled={disabled}
          showLabels={false}
          compact
        />
      </div>

      {/* Delete button */}
      {canRemove && (
        <Button
          type="button"
          variant="ghost"
          size="sm"
          onClick={onRemove}
          disabled={disabled}
          className="text-slate-500 hover:text-red-400 hover:bg-red-500/10 p-1 h-8 w-8"
          aria-label={`Eliminar horario ${index + 1}`}
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      )}
    </div>
  );
}

export default SlotEditor;
