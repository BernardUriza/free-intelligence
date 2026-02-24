/**
 * DoctorAppointmentsCalendar
 *
 * Composition root – wires hooks and sub-components together.
 * No business logic lives here; each concern is delegated.
 */

'use client';

import { useRef } from 'react';
import FullCalendar from '@fullcalendar/react';
import timeGridPlugin from '@fullcalendar/timegrid';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import {
  TIME_SLOT_PRESETS,
  THEME_PRESETS,
  TIME_FORMAT,
  DAY_HEADER_FORMAT,
  SLOT_LABEL_FORMAT,
} from '@/components/fullcalendar/config/calendar-presets.config';

import type { DoctorAppointmentsCalendarProps } from './types';
import { useBusinessHours } from './hooks/useBusinessHours';
import { useCalendarEvents } from './hooks/useCalendarEvents';
import { useCalendarNavigation } from './hooks/useCalendarNavigation';
import { CalendarHeader } from './components/CalendarHeader';
import { CalendarLegend } from './components/CalendarLegend';
import { CalendarStyles } from './components/CalendarStyles';

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
  const calendarRef = useRef<FullCalendar>(null);

  // Derived data
  const businessHours = useBusinessHours(availability);
  const events = useCalendarEvents(appointments, availability);

  // Navigation & interaction handlers
  const { goToToday, goToPrev, goToNext, handleEventClick, handleDateClick } =
    useCalendarNavigation({
      calendarRef,
      onDateChange,
      onSelectAppointment,
      onCreateAppointment,
    });

  const timeConfig = TIME_SLOT_PRESETS.clinic;
  const themeConfig = THEME_PRESETS.dark;

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
      <div className="flex-1 relative fc-dark-theme">
        <FullCalendar
          ref={calendarRef}
          plugins={[timeGridPlugin, dayGridPlugin, interactionPlugin]}
          initialView="timeGridWeek"
          initialDate={currentDate}
          locale="es"
          headerToolbar={false}
          height="100%"
          slotMinTime={timeConfig.minTime}
          slotMaxTime={timeConfig.maxTime}
          slotDuration={timeConfig.slotDuration}
          slotLabelInterval={timeConfig.slotLabelInterval}
          slotLabelFormat={SLOT_LABEL_FORMAT.simple}
          dayHeaderFormat={DAY_HEADER_FORMAT.medium}
          allDaySlot={false}
          nowIndicator={true}
          events={events}
          eventDisplay="block"
          displayEventTime={true}
          displayEventEnd={false}
          eventTimeFormat={TIME_FORMAT.h24}
          selectable={false}
          editable={false}
          eventClick={handleEventClick}
          dateClick={handleDateClick}
          businessHours={businessHours}
        />

        <CalendarStyles theme={themeConfig} />
      </div>

      <CalendarLegend />
    </div>
  );
}
