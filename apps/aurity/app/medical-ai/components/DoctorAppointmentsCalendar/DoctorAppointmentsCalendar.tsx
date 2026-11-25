/**
 * DoctorAppointmentsCalendar
 *
 * Composition root – wires hooks and sub-components together.
 * No business logic lives here; each concern is delegated.
 */

'use client';

import { useRef } from 'react';
import { FiCalendar, businessHours, type FiCalendarHandle } from 'fi-glass/calendar';

import type { DoctorAppointmentsCalendarProps } from './types';
import { useCalendarEvents } from './hooks/useCalendarEvents';
import { useCalendarNavigation } from './hooks/useCalendarNavigation';
import { CalendarHeader } from './components/CalendarHeader';
import { CalendarLegend } from './components/CalendarLegend';
import { DEFAULT_BUSINESS_HOURS } from './constants';

// ============================================================================
// Component
// ============================================================================

export function DoctorAppointmentsCalendar({
  appointments,
  currentDate,
  onDateChange,
  onSelectAppointment,
  onCreateAppointment,
  loading = false,
  availability,
}: DoctorAppointmentsCalendarProps) {
  const calendarRef = useRef<FiCalendarHandle>(null);

  // Derived data
  const weeklyHours = availability?.weeklySchedule.length
    ? businessHours(availability.weeklySchedule)
    : DEFAULT_BUSINESS_HOURS;
  const events = useCalendarEvents(appointments, availability);

  // Navigation & interaction handlers
  const { goToToday, goToPrev, goToNext, handleEventClick, handleDateClick } =
    useCalendarNavigation({
      calendarRef,
      onDateChange,
      onSelectAppointment,
      onCreateAppointment,
    });

  return (
    <div className="flex flex-col h-full">
      <CalendarHeader
        loading={loading}
        onPrev={goToPrev}
        onNext={goToNext}
        onToday={goToToday}
        onNewAppointment={() => onCreateAppointment(new Date())}
      />

      {/* Loading overlay */}
      {loading && (
        <div className="apt-loading-overlay">
          <div className="apt-loading-spinner" />
        </div>
      )}

      {/* Calendar grid */}
      <FiCalendar
        ref={calendarRef}
        className="flex-1 relative"
        hours="clinic"
        height="100%"
        initialDate={currentDate}
        events={events}
        eventClick={handleEventClick}
        dateClick={handleDateClick}
        businessHours={weeklyHours}
      />

      <CalendarLegend />
    </div>
  );
}
