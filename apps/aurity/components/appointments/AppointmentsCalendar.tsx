/**
 * Appointments Calendar Component - UNIFIED CORE
 * Card: FI-BRYNTUM-UNIFY-001
 *
 * Medical appointments scheduler using unified Bryntum architecture.
 * 
 * Architecture:
 * - Uses SchedulerCore + buildAppointmentSchedulerConfig
 * - Single source of truth for Bryntum lifecycle
 * - No duplicate CSS/JS loads
 * - StrictMode-safe initialization
 * - Async finalize pattern for API calls
 * 
 * Refactored: 2025-12-11
 */

'use client';

import { useCallback, useMemo } from 'react';
import { SchedulerCore, buildAppointmentSchedulerConfig } from '@/components/bryntum';
import { APPOINTMENT_VIEW_PRESETS, type AppointmentViewMode } from '@/components/bryntum/config/appointment-presets.config';
import { type Doctor, type Appointment } from '@/components/bryntum/utils/appointment-transform.utils';

interface AppointmentsCalendarProps {
  // Data
  doctors: Doctor[];
  appointments: Appointment[];
  
  // View state
  viewMode: AppointmentViewMode;
  currentDate: Date;
  
  // API callbacks
  onEventDrop?: (eventData: {
    appointment_id: string;
    scheduled_at: string;
    doctor_id: string;
  }) => Promise<void>;
  onEventResize?: (eventData: {
    appointment_id: string;
    estimated_duration: number;
  }) => Promise<void>;
  onEventEdit?: (eventData: {
    appointment_id: string;
    scheduled_at?: string;
    estimated_duration?: number;
    doctor_id?: string;
    status?: string;
    reason?: string;
    notes?: string;
  }) => Promise<void>;
  onEventClick?: (appointment: Appointment) => void;
  onScheduleClick?: (date: Date, doctorId: string, endDate?: Date | null) => void;
}

export function AppointmentsCalendar({
  doctors,
  appointments,
  viewMode,
  currentDate,
  onEventDrop,
  onEventResize,
  onEventEdit,
  onEventClick,
  onScheduleClick,
}: AppointmentsCalendarProps) {
  // Build configuration from current state (memoized for stability)
  const getConfig = useCallback(() => {
    return buildAppointmentSchedulerConfig({
      viewMode,
      currentDate,
      doctors,
      appointments,
      onEventDrop,
      onEventResize,
      onEventEdit,
      onEventClick,
      onScheduleClick,
    });
  }, [
    viewMode,
    currentDate,
    doctors,
    appointments,
    onEventDrop,
    onEventResize,
    onEventEdit,
    onEventClick,
    onScheduleClick,
  ]);

  // Calculate time window for batched updates
  const timeWindow = useMemo(() => {
    const viewConfig = APPOINTMENT_VIEW_PRESETS[viewMode];
    const { start, end } = viewConfig.getDateRange(currentDate);
    return { startDate: start, endDate: end };
  }, [viewMode, currentDate]);

  const handleReady = useCallback((instance: any) => {
    console.log('[AppointmentsCalendar] Scheduler ready:', instance);
  }, []);

  const handleError = useCallback((error: unknown) => {
    console.error('[AppointmentsCalendar] Scheduler error:', error);
  }, []);

  // ============================================================================
  // Render
  // ============================================================================

  return (
    <SchedulerCore
      getConfig={getConfig}
      timeWindow={timeWindow}
      onReady={handleReady}
      onError={handleError}
      className="bg-slate-900 rounded-lg shadow-lg border border-slate-700"
      style={{ height: 'calc(100vh - 220px)' }}
    />
  );
}
