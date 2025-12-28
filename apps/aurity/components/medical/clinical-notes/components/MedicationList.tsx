'use client';

import { memo } from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Medication } from '../types';

interface MedicationListProps {
  medications: Medication[];
  onRemove: (index: number) => void;
}

export const MedicationList = memo(function MedicationList({
  medications,
  onRemove,
}: MedicationListProps) {
  if (medications.length === 0) return null;

  return (
    <div className="space-y-2 mb-2" role="list">
      {medications.map((med, idx) => (
        <div
          key={`${med.name}-${idx}`}
          className="bg-slate-900 p-3 rounded-lg border border-slate-600"
          role="listitem"
        >
          <div className="fi-flex-between">
            <div className="grid grid-cols-3 gap-3 flex-1">
              <span className="text-white">{med.name}</span>
              <span className="text-slate-400">{med.dose}</span>
              <span className="text-slate-400">{med.frequency}</span>
            </div>
            <Button
              onClick={() => onRemove(idx)}
              variant="ghost"
              size="sm"
              icon={X}
              className="ml-3 text-slate-400 hover:text-red-400"
              aria-label={`Eliminar ${med.name}`}
            />
          </div>
        </div>
      ))}
    </div>
  );
});
