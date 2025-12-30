/**
 * FullCalendar Presets Configuration
 *
 * Pre-configured settings for different calendar use cases
 */

import type {
  CalendarConfig,
  TimeSlotConfig,
  CalendarViewConfig,
  CalendarThemeConfig,
  EventStyleConfig,
  CalendarEventCategory,
} from '../types/calendar.types';

// ============================================================================
// Time Slot Presets
// ============================================================================

export const TIME_SLOT_PRESETS: Record<string, TimeSlotConfig> = {
  /** Standard business hours (6am - 11pm) */
  business: {
    minTime: '06:00:00',
    maxTime: '23:00:00',
    slotDuration: '01:00:00',
    slotLabelInterval: '01:00:00',
  },
  /** Extended hours (5am - midnight) */
  extended: {
    minTime: '05:00:00',
    maxTime: '24:00:00',
    slotDuration: '01:00:00',
    slotLabelInterval: '01:00:00',
  },
  /** Compact view with 30-min slots */
  compact: {
    minTime: '07:00:00',
    maxTime: '22:00:00',
    slotDuration: '00:30:00',
    slotLabelInterval: '01:00:00',
  },
  /** Medical clinic hours (7am - 9pm) */
  clinic: {
    minTime: '07:00:00',
    maxTime: '21:00:00',
    slotDuration: '00:30:00',
    slotLabelInterval: '01:00:00',
  },
};

// ============================================================================
// View Presets
// ============================================================================

export const VIEW_PRESETS: Record<string, CalendarViewConfig> = {
  /** Weekly view without header toolbar */
  weeklyNoHeader: {
    initialView: 'timeGridWeek',
    headerToolbar: false,
    height: 420,
    locale: 'es',
  },
  /** Weekly view with navigation */
  weeklyWithNav: {
    initialView: 'timeGridWeek',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: 'timeGridWeek,timeGridDay',
    },
    height: 500,
    locale: 'es',
  },
  /** Daily detail view */
  daily: {
    initialView: 'timeGridDay',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: '',
    },
    height: 600,
    locale: 'es',
  },
  /** Monthly overview */
  monthly: {
    initialView: 'dayGridMonth',
    headerToolbar: {
      left: 'prev,next today',
      center: 'title',
      right: '',
    },
    height: 'auto',
    locale: 'es',
  },
};

// ============================================================================
// Theme Presets
// ============================================================================

export const THEME_PRESETS: Record<string, CalendarThemeConfig> = {
  /** Dark theme matching Aurity design system */
  dark: {
    borderColor: 'rgb(51 65 85)',
    pageBgColor: 'rgb(15 23 42 / 0.5)',
    neutralBgColor: 'rgb(30 41 59 / 0.5)',
    todayBgColor: 'rgb(99 102 241 / 0.1)',
    nowIndicatorColor: 'rgb(99 102 241)',
  },
  /** Light theme */
  light: {
    borderColor: 'rgb(226 232 240)',
    pageBgColor: 'rgb(255 255 255)',
    neutralBgColor: 'rgb(248 250 252)',
    todayBgColor: 'rgb(99 102 241 / 0.1)',
    nowIndicatorColor: 'rgb(99 102 241)',
  },
};

// ============================================================================
// Event Style Presets
// ============================================================================

export const EVENT_STYLES: Record<CalendarEventCategory, EventStyleConfig> = {
  /** Normal availability - indigo */
  available: {
    backgroundColor: 'rgba(99, 102, 241, 0.3)',
    borderColor: 'rgba(99, 102, 241, 0.6)',
    textColor: '#a5b4fc',
  },
  /** Override/exception - orange */
  override: {
    backgroundColor: 'rgba(249, 115, 22, 0.3)',
    borderColor: 'rgba(249, 115, 22, 0.6)',
    textColor: '#fdba74',
  },
  /** Full day closed - red */
  closed: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    textColor: '#fca5a5',
  },
  /** Day off - gray */
  dayOff: {
    backgroundColor: 'rgba(100, 116, 139, 0.1)',
    borderColor: 'rgba(100, 116, 139, 0.2)',
    textColor: '#94a3b8',
  },
};

// ============================================================================
// Combined Config Presets
// ============================================================================

/**
 * Complete preset configurations for common use cases
 */
export const CALENDAR_PRESETS: Record<string, CalendarConfig> = {
  /** Availability preview (used in AvailabilityDesigner) */
  availabilityPreview: {
    timeSlot: TIME_SLOT_PRESETS.business,
    view: VIEW_PRESETS.weeklyNoHeader,
    theme: THEME_PRESETS.dark,
    eventStyles: EVENT_STYLES,
  },
  /** Doctor schedule viewer */
  doctorSchedule: {
    timeSlot: TIME_SLOT_PRESETS.clinic,
    view: VIEW_PRESETS.weeklyWithNav,
    theme: THEME_PRESETS.dark,
    eventStyles: EVENT_STYLES,
  },
  /** Appointment booking view */
  appointmentBooking: {
    timeSlot: TIME_SLOT_PRESETS.compact,
    view: VIEW_PRESETS.daily,
    theme: THEME_PRESETS.dark,
    eventStyles: EVENT_STYLES,
  },
};

// ============================================================================
// Date/Time Format Presets
// ============================================================================

export const TIME_FORMAT = {
  /** 24-hour format: 09:00 */
  h24: {
    hour: '2-digit' as const,
    minute: '2-digit' as const,
    hour12: false,
  },
  /** 12-hour format: 9:00 AM */
  h12: {
    hour: 'numeric' as const,
    minute: '2-digit' as const,
    hour12: true,
  },
};

export const DAY_HEADER_FORMAT = {
  /** Short: Lun 23 */
  short: {
    weekday: 'short' as const,
    day: 'numeric' as const,
  },
  /** Medium: Lun 23 Dic */
  medium: {
    weekday: 'short' as const,
    day: 'numeric' as const,
    month: 'short' as const,
  },
  /** Long: Lunes, 23 de Diciembre */
  long: {
    weekday: 'long' as const,
    day: 'numeric' as const,
    month: 'long' as const,
  },
};

export const SLOT_LABEL_FORMAT = {
  /** Simple: 9:00 */
  simple: {
    hour: 'numeric' as const,
    minute: '2-digit' as const,
    meridiem: false,
    hour12: false,
  },
  /** With meridiem: 9:00 AM */
  meridiem: {
    hour: 'numeric' as const,
    minute: '2-digit' as const,
    meridiem: 'short' as const,
    hour12: true,
  },
};
