/**
 * Availability Designer - Type Definitions
 *
 * Schema for doctor availability stored as JSONB in doctors.working_hours
 */

// =============================================================================
// CORE TYPES
// =============================================================================

/**
 * Weekly time slot - recurring pattern for a specific day
 */
export interface WeeklySlot {
  day: number;        // 0=Sunday, 1=Monday, ..., 6=Saturday (Temporal API format)
  start: string;      // HH:mm (24h format)
  end: string;        // HH:mm (24h format)
  label?: string;     // Optional: "Morning shift", "Afternoon"
}

/**
 * Date-specific override - exception for a particular date
 */
export interface DateOverride {
  date: string;       // YYYY-MM-DD (ISO format)
  start?: string;     // HH:mm - omit if fullDayClosed=true
  end?: string;       // HH:mm
  fullDayClosed: boolean;
  reason?: string;    // "Vacation", "Holiday", "Conference"
}

/**
 * Scheduling rules - automated constraints
 */
export interface SchedulingRules {
  breakStart?: string;                  // HH:mm when break starts
  breakEnd?: string;                    // HH:mm when break ends
  minSlotDuration?: number;             // Minutes (e.g., 15)
  maxPatientsPerHour?: number;          // Capacity limit (e.g., 4)
  bufferBetweenAppointments?: number;   // Minutes between appointments (e.g., 5)
}

/**
 * Complete availability configuration - stored in doctors.working_hours JSONB
 */
export interface DoctorAvailability {
  version: number;                // Schema version (currently 1)
  weeklySchedule: WeeklySlot[];   // Recurring weekly pattern
  overrides: DateOverride[];      // Date-specific exceptions
  rules: SchedulingRules;         // Scheduling constraints
}

// =============================================================================
// VALIDATION TYPES
// =============================================================================

export type ValidationErrorType =
  | 'overlap'           // Two slots overlap on same day
  | 'gap'               // Gap between slots (informational)
  | 'invalid_time'      // Invalid time format
  | 'end_before_start'  // End time is before start time
  | 'exceeds_24h'       // Slot exceeds 24 hours
  | 'duplicate_date'    // Same date appears twice in overrides
  | 'break_outside';    // Break is outside working hours

export interface ValidationError {
  type: ValidationErrorType;
  day?: number;         // Day of week (for weekly errors)
  date?: string;        // Date (for override errors)
  message: string;      // Human-readable message
  severity: 'error' | 'warning';
}

// =============================================================================
// FORM STATE TYPES
// =============================================================================

export interface DaySchedule {
  isWorking: boolean;
  slots: WeeklySlot[];
}

export interface AvailabilityFormState {
  weeklySchedule: Record<number, DaySchedule>; // day -> schedule
  overrides: DateOverride[];
  rules: SchedulingRules;
  isDirty: boolean;
  errors: ValidationError[];
}

// =============================================================================
// PREVIEW TYPES
// =============================================================================

export interface PreviewDay {
  date: Date;
  dayOfWeek: number;
  isOverride: boolean;
  isDayOff: boolean;
  slots: Array<{ start: string; end: string }>;
  breaks: Array<{ start: string; end: string }>;
  totalMinutes: number;
}

export interface PreviewWeek {
  weekStart: Date;
  days: PreviewDay[];
  totalHours: number;
}

// =============================================================================
// TEMPLATE TYPES
// =============================================================================

export interface AvailabilityTemplate {
  id: string;
  name: string;
  description: string;
  availability: DoctorAvailability;
}

// =============================================================================
// LEGACY COMPATIBILITY
// =============================================================================

/**
 * WorkingHour - Format expected by working-hours.resolver.ts
 * Transform DoctorAvailability to this format for Bryntum integration
 */
export interface WorkingHour {
  day?: number;              // 0-6 (Sunday-Saturday)
  start: string;             // HH:mm
  end: string;               // HH:mm
  date?: string;             // YYYY-MM-DD for date-specific override
  fullDayClosed?: boolean;
  reason?: string;
  legacyDerived?: boolean;   // True if derived from work_start_time/work_end_time
}
