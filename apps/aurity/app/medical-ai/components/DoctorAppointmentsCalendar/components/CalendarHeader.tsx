/**
 * CalendarHeader
 *
 * Navigation bar: title, prev/next/today, "Nueva Cita" button.
 */

'use client';

import { ChevronLeft, ChevronRight, Calendar, Plus } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface CalendarHeaderProps {
  loading: boolean;
  onPrev: () => void;
  onNext: () => void;
  onToday: () => void;
  onNewAppointment: () => void;
}

export function CalendarHeader({
  loading,
  onPrev,
  onNext,
  onToday,
  onNewAppointment,
}: CalendarHeaderProps) {
  return (
    <div className="flex items-center justify-between mb-4 px-2">
      <div className="flex items-center gap-2">
        <Calendar className="w-5 h-5 text-slate-400" />
        <h2 className="text-lg font-semibold text-white">Mis Citas</h2>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onPrev} disabled={loading}>
          <ChevronLeft className="w-4 h-4" />
        </Button>
        <Button variant="secondary" size="sm" onClick={onToday} disabled={loading}>
          Hoy
        </Button>
        <Button variant="ghost" size="sm" onClick={onNext} disabled={loading}>
          <ChevronRight className="w-4 h-4" />
        </Button>
      </div>

      <Button variant="primary" size="sm" onClick={onNewAppointment} icon={Plus}>
        Nueva Cita
      </Button>
    </div>
  );
}
