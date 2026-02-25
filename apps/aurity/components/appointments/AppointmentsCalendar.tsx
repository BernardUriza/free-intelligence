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

import { useCallback, useMemo, useEffect } from 'react';
import { createLogger } from '@/lib/internal/logger';
import { SchedulerCore, buildAppointmentSchedulerConfig, initBryntumPatchHook, cleanupBryntumPatchHook } from '@/components/bryntum';

const log = createLogger('AppointmentsCalendar');
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

  // Scheduler instance callback
  onSchedulerReady?: (instance: any) => void;
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
  onSchedulerReady,
}: AppointmentsCalendarProps) {
  // Initialize the Bryntum patch hook with doctor data for working hours validation
  // This connects our isDateInWorkingHours function to the patched Bryntum JS
  useEffect(() => {
    if (doctors.length > 0) {
      initBryntumPatchHook(doctors);
    }
    return () => {
      cleanupBryntumPatchHook();
    };
  }, [doctors]);

  // Build configuration from current state (memoized for stability)
  // NOTE: Blocked time events are now generated as regular events in the config
  // This is a workaround for CSS/JS version mismatch (Card: FI-BRYNTUM-CSS-001)
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
      skipTimeRanges: false, // Generate blocked time events
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

  const handleReady = useCallback((instance: unknown) => {
    onSchedulerReady?.(instance);
  }, [onSchedulerReady]);

  const handleError = useCallback((error: unknown) => {
    log.error('Scheduler error', { error: String(error) });
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
      className="apt-calendar-wrapper"
      style={{ height: 'calc(100vh - 220px)' }}
    />
  );
}
