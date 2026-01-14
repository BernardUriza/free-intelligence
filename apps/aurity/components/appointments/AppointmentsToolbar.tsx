/**
 * Appointments Toolbar Component
 * Card: FI-CHECKIN-005 (Phase 2)
 *
 * Medical appointments calendar toolbar with:
 * - Clinic selector
 * - View mode switcher (Day/Week/Month)
 * - Date navigation
 * - Refresh and new appointment actions
 */

import { ChevronLeft, ChevronRight, Plus, RefreshCw, ZoomIn, ZoomOut, ArrowLeft, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from '@/components/ui/select';
import type { AppointmentViewMode } from '@/components/bryntum/config/appointment-presets.config';
import { APPOINTMENT_VIEW_PRESETS } from '@/components/bryntum/config/appointment-presets.config';

interface Clinic {
  clinic_id: string;
  name: string;
}

interface AppointmentsToolbarProps {
  // Clinic selection
  clinics: Clinic[];
  selectedClinic: string;
  onClinicChange: (clinicId: string) => void;

  // View mode
  viewMode: AppointmentViewMode;
  onViewModeChange: (mode: AppointmentViewMode) => void;

  // Navigation
  onNavigateDate: (direction: 'prev' | 'next') => void;
  onGoToToday: () => void;

  // Zoom controls
  onZoomIn?: () => void;
  onZoomOut?: () => void;
  zoomLevel?: number;
  minZoomLevel?: number;
  maxZoomLevel?: number;

  // Horizontal scroll navigation
  onScrollLeft?: () => void;
  onScrollRight?: () => void;

  // Actions
  onRefresh: () => void;
  onNewAppointment: () => void;

  // Display helpers
  dateDisplayText: string;
}

export function AppointmentsToolbar({
  clinics,
  selectedClinic,
  onClinicChange,
  viewMode,
  onViewModeChange,
  onNavigateDate,
  onGoToToday,
  onZoomIn,
  onZoomOut,
  zoomLevel,
  minZoomLevel = 5,
  maxZoomLevel = 14,
  onScrollLeft,
  onScrollRight,
  onRefresh,
  onNewAppointment,
  dateDisplayText,
}: AppointmentsToolbarProps) {
  return (
    <div className="fi-flex-gap-md">
      {/* Clinic Selector */}
      <Select value={selectedClinic} onValueChange={onClinicChange}>
        <SelectTrigger className="w-48">
          <SelectValue placeholder="Seleccionar clínica" />
        </SelectTrigger>
        <SelectContent>
          {clinics.map((clinic) => (
            <SelectItem key={clinic.clinic_id} value={clinic.clinic_id}>
              {clinic.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      {/* View Mode Selector */}
      <div className="flex items-center bg-slate-800 rounded-lg p-0.5">
        {(Object.keys(APPOINTMENT_VIEW_PRESETS) as AppointmentViewMode[]).map((mode) => {
          const config = APPOINTMENT_VIEW_PRESETS[mode];
          const Icon = config.icon;
          const isActive = viewMode === mode;
          return (
            <button
              key={mode}
              onClick={() => onViewModeChange(mode)}
              className={`flex items-center gap-1 px-2 py-1 rounded fi-text-xs-medium transition-colors ${
                isActive
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'text-slate-400 hover:bg-slate-700 hover:text-slate-200'
              }`}
              title={config.label}
            >
              <Icon className="h-3.5 w-3.5" />
              <span className="hidden lg:inline">{config.label}</span>
            </button>
          );
        })}
      </div>

      {/* Date Navigation */}
      <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-0.5">
        <Button
          onClick={() => onNavigateDate('prev')}
          variant="ghost"
          size="sm"
          icon={ChevronLeft}
          aria-label="Día anterior"
        />
        <Button
          onClick={onGoToToday}
          variant="ghost"
          size="sm"
          className="fi-text"
        >
          Hoy
        </Button>
        <span className="px-2 py-1 fi-text-xs-medium min-w-[120px] text-center text-slate-200">
          {dateDisplayText}
        </span>
        <Button
          onClick={() => onNavigateDate('next')}
          variant="ghost"
          size="sm"
          icon={ChevronRight}
          aria-label="Día siguiente"
        />
      </div>

      {/* Zoom Controls */}
      {(onZoomIn || onZoomOut) && (
        <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-0.5">
          <Button
            onClick={onZoomOut}
            variant="ghost"
            size="sm"
            icon={ZoomOut}
            disabled={zoomLevel === undefined || zoomLevel <= minZoomLevel}
            aria-label="Alejar"
          />
          <span className="px-2 fi-text-xs-medium text-slate-200 min-w-[40px] text-center">
            {zoomLevel !== undefined ? `${zoomLevel}` : '-'}
          </span>
          <Button
            onClick={onZoomIn}
            variant="ghost"
            size="sm"
            icon={ZoomIn}
            disabled={zoomLevel !== undefined && zoomLevel >= maxZoomLevel}
            aria-label="Acercar"
          />
        </div>
      )}

      {/* Horizontal Scroll Navigation */}
      {(onScrollLeft || onScrollRight) && (
        <div className="flex items-center gap-1 bg-slate-800 rounded-lg p-0.5">
          <Button
            onClick={onScrollLeft}
            variant="ghost"
            size="sm"
            icon={ArrowLeft}
            aria-label="Scroll izquierda"
            title="Scroll izquierda (horas anteriores)"
          />
          <Button
            onClick={onScrollRight}
            variant="ghost"
            size="sm"
            icon={ArrowRight}
            aria-label="Scroll derecha"
            title="Scroll derecha (horas siguientes)"
          />
        </div>
      )}

      {/* Refresh */}
      <Button
        onClick={onRefresh}
        variant="ghost"
        size="sm"
        icon={RefreshCw}
        aria-label="Actualizar"
      />

      {/* New Appointment */}
      <Button
        onClick={onNewAppointment}
        variant="cyan"
        size="sm"
        icon={Plus}
      >
        Nueva Cita
      </Button>
    </div>
  );
}
