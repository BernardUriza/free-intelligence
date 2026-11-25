import * as react from 'react';
import { RefObject } from 'react';
import { CalendarOptions, EventInput } from '@fullcalendar/core';
import FullCalendar from '@fullcalendar/react';
import { DoctorAvailability, WeeklySlot, DateOverride, WeekSchedule, SchedulingRules, AvailabilityError } from '@free-intelligence/core/availability';

/** The stretch of the day a calendar shows, and how finely it is ruled. */
declare const CALENDAR_HOURS: {
    business: {
        slotMinTime: string;
        slotMaxTime: string;
        slotDuration: string;
        slotLabelInterval: string;
    };
    extended: {
        slotMinTime: string;
        slotMaxTime: string;
        slotDuration: string;
        slotLabelInterval: string;
    };
    compact: {
        slotMinTime: string;
        slotMaxTime: string;
        slotDuration: string;
        slotLabelInterval: string;
    };
    clinic: {
        slotMinTime: string;
        slotMaxTime: string;
        slotDuration: string;
        slotLabelInterval: string;
    };
};
type CalendarHours = keyof typeof CALENDAR_HOURS;
declare const CALENDAR_DEFAULTS: {
    initialView: string;
    locale: string;
    headerToolbar: false;
    height: number;
    allDaySlot: false;
    nowIndicator: true;
    eventDisplay: string;
    displayEventEnd: false;
    eventTimeFormat: {
        hour: "2-digit";
        minute: "2-digit";
        hour12: false;
    };
    slotLabelFormat: {
        hour: "numeric";
        minute: "2-digit";
        hour12: false;
    };
    dayHeaderFormat: {
        weekday: "short";
        day: "numeric";
        month: "short";
    };
};

type FiCalendarHandle = FullCalendar;
/** Every FullCalendar option passes through and wins over the house default. */
interface FiCalendarProps extends CalendarOptions {
    hours?: CalendarHours;
    /** `inherit` takes the tokens of the surface around it. */
    theme?: 'dark' | 'light' | 'inherit';
    className?: string;
}
declare const FiCalendar: react.ForwardRefExoticComponent<FiCalendarProps & react.RefAttributes<FullCalendar>>;

interface CalendarNavigation {
    goToNext: () => void;
    goToPrev: () => void;
    goToToday: () => void;
    goToDate: (date: Date) => void;
}
interface UseCalendarNavigationResult {
    calendarRef: RefObject<FiCalendarHandle | null>;
    navigation: CalendarNavigation;
}
declare function useCalendarNavigation(): UseCalendarNavigationResult;

type AvailabilityEventKind = 'available' | 'override' | 'closed' | 'day-off';
interface AvailabilityEventsOptions {
    from: Date;
    days: number;
    availableLabel?: string;
    overrideLabel?: string;
}
interface BusinessHours {
    daysOfWeek: number[];
    startTime: string;
    endTime: string;
}
declare function closedDayEvent({ date, reason }: Pick<DateOverride, 'date' | 'reason'>): EventInput;
declare function availabilityEvents({ weeklySchedule, overrides }: Pick<DoctorAvailability, 'weeklySchedule' | 'overrides'>, { from, days, availableLabel, overrideLabel }: AvailabilityEventsOptions): EventInput[];
declare function businessHours(weeklySchedule: WeeklySlot[]): BusinessHours[];

interface Draft {
    week: WeekSchedule;
    overrides: DateOverride[];
    rules: SchedulingRules;
}
interface AvailabilityForm extends Draft {
    availability: DoctorAvailability;
    errors: AvailabilityError[];
    isValid: boolean;
    isDirty: boolean;
    setDayWorking: (day: number, isWorking: boolean) => void;
    addSlot: (day: number) => void;
    removeSlot: (day: number, index: number) => void;
    updateSlot: (day: number, index: number, changes: Partial<WeeklySlot>) => void;
    addOverride: (override: DateOverride) => void;
    removeOverride: (date: string) => void;
    updateOverride: (date: string, changes: Partial<DateOverride>) => void;
    updateRules: (changes: Partial<SchedulingRules>) => void;
    applyWeek: (weeklySchedule: WeeklySlot[]) => void;
    reset: () => void;
}
declare function useAvailabilityForm(initial?: DoctorAvailability | null): AvailabilityForm;

interface AvailabilityTabProps {
    form: AvailabilityForm;
    disabled?: boolean;
}

type AvailabilityTab = 'weekly' | 'exceptions' | 'rules' | 'templates' | 'preview';
interface AvailabilityEditorProps extends AvailabilityTabProps {
    tabs?: AvailabilityTab[];
    theme?: 'dark' | 'light';
}
declare function AvailabilityEditor({ form, disabled, tabs, theme }: AvailabilityEditorProps): react.JSX.Element;

export { AvailabilityEditor, type AvailabilityEditorProps, type AvailabilityEventKind, type AvailabilityEventsOptions, type AvailabilityForm, type AvailabilityTab, type BusinessHours, CALENDAR_DEFAULTS, CALENDAR_HOURS, type CalendarHours, type CalendarNavigation, FiCalendar, type FiCalendarHandle, type FiCalendarProps, type UseCalendarNavigationResult, availabilityEvents, businessHours, closedDayEvent, useAvailabilityForm, useCalendarNavigation };
