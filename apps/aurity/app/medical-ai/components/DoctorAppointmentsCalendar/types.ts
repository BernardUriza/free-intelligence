/**
 * DoctorAppointmentsCalendar - Type Definitions
 *
 * Single Responsibility: all types consumed by the calendar module.
 */

import type { Appointment } from '@/components/bryntum/utils/appointment-transform.utils';
import type { DoctorAvailability } from '@/components/admin/clinics/availability-designer/types';

// ============================================================================
// Props
// ============================================================================

export interface DoctorAppointmentsCalendarProps {
  appointments: Appointment[];
  currentDate: Date;
  onDateChange: (date: Date) => void;
  onSelectAppointment: (appointment: Appointment) => void;
  onCreateAppointment: (date: Date) => void;
  loading?: boolean;
  /** Doctor's availability - used to derive business-hours & closed days */
  availability?: DoctorAvailability | null;
}

// ============================================================================
// Internal
// ============================================================================

export interface StatusColor {
  bg: string;
  border: string;
  text: string;
}
