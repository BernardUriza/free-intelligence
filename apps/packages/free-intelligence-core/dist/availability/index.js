// src/availability/defaults.ts
var AVAILABILITY_VERSION = 1;
var DAYS_OF_WEEK = [
  { value: 0, label: "Domingo", short: "Dom", abbr: "D" },
  { value: 1, label: "Lunes", short: "Lun", abbr: "L" },
  { value: 2, label: "Martes", short: "Mar", abbr: "M" },
  { value: 3, label: "Mi\xE9rcoles", short: "Mi\xE9", abbr: "X" },
  { value: 4, label: "Jueves", short: "Jue", abbr: "J" },
  { value: 5, label: "Viernes", short: "Vie", abbr: "V" },
  { value: 6, label: "S\xE1bado", short: "S\xE1b", abbr: "S" }
];
var WEEKDAYS = [1, 2, 3, 4, 5];
var WEEKEND = [0, 6];
var DEFAULT_WORK_START = "09:00";
var DEFAULT_WORK_END = "18:00";
var DEFAULT_BREAK_START = "13:00";
var DEFAULT_BREAK_END = "14:00";
var SLOT_DURATION_CHOICES = [15, 20, 30, 45, 60];
var DEFAULT_RULES = {
  minSlotDuration: 15,
  maxPatientsPerHour: 4,
  bufferBetweenAppointments: 5
};
var COMMON_EXCEPTION_REASONS = [
  "Vacaciones",
  "D\xEDa festivo",
  "Conferencia",
  "Capacitaci\xF3n",
  "Cita personal",
  "Enfermedad",
  "Emergencia familiar"
];
function emptyAvailability() {
  return { version: AVAILABILITY_VERSION, weeklySchedule: [], overrides: [], rules: { ...DEFAULT_RULES } };
}
var everyDay = (days, ...hours) => days.flatMap((day) => hours.map((slot) => ({ day, ...slot })));
var AVAILABILITY_TEMPLATES = [
  {
    id: "standard-9-5",
    name: "Est\xE1ndar 9-18 (L-V)",
    description: "9:00 - 18:00, lunes a viernes, fines de semana libres",
    weeklySchedule: everyDay(WEEKDAYS, { start: "09:00", end: "18:00" })
  },
  {
    id: "morning-clinic",
    name: "Cl\xEDnica Matutina (L-V)",
    description: "8:00 - 14:00, lunes a viernes",
    weeklySchedule: everyDay(WEEKDAYS, { start: "08:00", end: "14:00" })
  },
  {
    id: "afternoon-clinic",
    name: "Cl\xEDnica Vespertina (L-V)",
    description: "15:00 - 21:00, lunes a viernes",
    weeklySchedule: everyDay(WEEKDAYS, { start: "15:00", end: "21:00" })
  },
  {
    id: "split-shift",
    name: "Turno Partido (L-V)",
    description: "9:00 - 13:00 y 16:00 - 20:00, lunes a viernes",
    weeklySchedule: everyDay(
      WEEKDAYS,
      { start: "09:00", end: "13:00", label: "Ma\xF1ana" },
      { start: "16:00", end: "20:00", label: "Tarde" }
    )
  },
  {
    id: "weekend-doctor",
    name: "Doctor de Fin de Semana",
    description: "10:00 - 14:00, s\xE1bado y domingo",
    weeklySchedule: everyDay(WEEKEND, { start: "10:00", end: "14:00" })
  },
  {
    id: "full-week",
    name: "Semana Completa",
    description: "9:00 - 18:00, todos los d\xEDas",
    weeklySchedule: everyDay([0, ...WEEKDAYS, 6], { start: "09:00", end: "18:00" })
  }
];

// src/availability/time.ts
var MINUTES_PER_DAY = 24 * 60;
var TIME_PATTERN = /^([01]\d|2[0-3]):[0-5]\d$/;
var DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
var twoDigits = (value) => String(value).padStart(2, "0");
function timeToMinutes(time) {
  const [hours, minutes] = time.split(":").map(Number);
  return hours * 60 + minutes;
}
function minutesToTime(minutes) {
  return `${twoDigits(Math.floor(minutes / 60) % 24)}:${twoDigits(minutes % 60)}`;
}
function isValidTime(time) {
  return TIME_PATTERN.test(time);
}
function isEndAfterStart(start, end) {
  return timeToMinutes(end) > timeToMinutes(start);
}
function isValidDate(date) {
  const match = DATE_PATTERN.exec(date);
  if (!match) return false;
  const [year, month, day] = match.slice(1).map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
}
function toCalendarDate(date) {
  return `${date.getFullYear()}-${twoDigits(date.getMonth() + 1)}-${twoDigits(date.getDate())}`;
}

// src/availability/validation.ts
var MIN_SLOT_DURATION = 5;
function problemInHours(start, end) {
  if (!isValidTime(start)) return { type: "invalid_time", message: `Hora de inicio inv\xE1lida: ${start}` };
  if (!isValidTime(end)) return { type: "invalid_time", message: `Hora de fin inv\xE1lida: ${end}` };
  if (!isEndAfterStart(start, end)) {
    return {
      type: "end_before_start",
      message: `La hora de fin (${end}) debe ser posterior a la de inicio (${start})`
    };
  }
  return null;
}
function problemInOverride(override) {
  if (!isValidDate(override.date)) return { type: "invalid_time", message: `Fecha inv\xE1lida: ${override.date}` };
  if (override.fullDayClosed) return null;
  if (!override.start || !override.end) {
    return { type: "invalid_time", message: "Debe especificar hora de inicio y fin, o marcar como d\xEDa libre" };
  }
  return problemInHours(override.start, override.end);
}
function problemsInRules(rules) {
  const errors = [];
  const { breakStart, breakEnd, minSlotDuration, maxPatientsPerHour } = rules;
  if (breakStart && breakEnd) {
    const problem = problemInHours(breakStart, breakEnd);
    if (problem) errors.push({ ...problem, message: `Descanso: ${problem.message}`, severity: "error" });
  } else if (breakStart || breakEnd) {
    errors.push({
      type: "invalid_time",
      message: "Debe especificar tanto inicio como fin del descanso",
      severity: "warning"
    });
  }
  if (minSlotDuration !== void 0 && minSlotDuration < MIN_SLOT_DURATION) {
    errors.push({
      type: "invalid_time",
      message: `La duraci\xF3n m\xEDnima debe ser al menos ${MIN_SLOT_DURATION} minutos`,
      severity: "error"
    });
  }
  if (maxPatientsPerHour !== void 0 && maxPatientsPerHour < 1) {
    errors.push({ type: "invalid_time", message: "Debe permitir al menos 1 paciente por hora", severity: "error" });
  }
  return errors;
}
function slotsOverlap(a, b) {
  return a.day === b.day && timeToMinutes(a.start) < timeToMinutes(b.end) && timeToMinutes(b.start) < timeToMinutes(a.end);
}
function slotsByDay(slots) {
  const days = /* @__PURE__ */ new Map();
  for (const slot of slots) days.set(slot.day, [...days.get(slot.day) ?? [], slot]);
  return days;
}
function problemsInDay(day, slots) {
  const errors = [];
  slots.forEach((slot, slotIndex) => {
    const problem = problemInHours(slot.start, slot.end);
    if (problem) errors.push({ ...problem, day, slotIndex, severity: "error" });
    slots.slice(0, slotIndex).forEach((earlier) => {
      if (!slotsOverlap(earlier, slot)) return;
      errors.push({
        type: "overlap",
        day,
        slotIndex,
        message: `Solapamiento detectado: ${earlier.start}-${earlier.end} y ${slot.start}-${slot.end}`,
        severity: "error"
      });
    });
  });
  return errors;
}
function problemsInOverrides(overrides) {
  const errors = [];
  const seen = /* @__PURE__ */ new Set();
  for (const override of overrides) {
    const { date } = override;
    const problem = problemInOverride(override);
    if (problem) errors.push({ ...problem, date, severity: "error" });
    if (seen.has(date)) {
      errors.push({ type: "duplicate_date", date, message: `Fecha duplicada: ${date}`, severity: "error" });
    }
    seen.add(date);
  }
  return errors;
}
function validateAvailability(availability) {
  const weekly = [...slotsByDay(availability.weeklySchedule)].flatMap(([day, slots]) => problemsInDay(day, slots));
  return [...weekly, ...problemsInOverrides(availability.overrides), ...problemsInRules(availability.rules)];
}
function hasBlockingErrors(errors) {
  return errors.some((error) => error.severity === "error");
}
function findGaps(slots) {
  return [...slotsByDay(slots)].flatMap(([day, daySlots]) => {
    const sorted = [...daySlots].sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));
    return sorted.slice(1).flatMap((next, i) => {
      const previous = sorted[i];
      return isEndAfterStart(previous.end, next.start) ? [{ day, from: previous.end, to: next.start }] : [];
    });
  });
}

// src/availability/week.ts
var GAP_BEFORE_NEW_SLOT = 60;
var NEW_SLOT_LENGTH = 4 * 60;
var SHORTEST_NEW_SLOT = 30;
var LAST_MINUTE = MINUTES_PER_DAY - 1;
function groupByDay(weeklySchedule) {
  return Object.fromEntries(
    DAYS_OF_WEEK.map(({ value }) => {
      const slots = weeklySchedule.filter((slot) => slot.day === value).sort((a, b) => timeToMinutes(a.start) - timeToMinutes(b.start));
      return [value, { isWorking: slots.length > 0, slots }];
    })
  );
}
function availabilityFromWeek(week, overrides, rules) {
  const weeklySchedule = Object.values(week).flatMap((day) => day.isWorking ? day.slots : []);
  return { version: AVAILABILITY_VERSION, weeklySchedule, overrides, rules };
}
function suggestNextSlot(day, existing) {
  const last = existing[existing.length - 1];
  if (!last) return { day, start: DEFAULT_WORK_START, end: DEFAULT_WORK_END };
  const start = timeToMinutes(last.end) + GAP_BEFORE_NEW_SLOT;
  const end = Math.min(start + NEW_SLOT_LENGTH, LAST_MINUTE);
  if (!(end - start >= SHORTEST_NEW_SLOT)) return null;
  return { day, start: minutesToTime(start), end: minutesToTime(end) };
}
function weeklyHours(availability) {
  const minutes = availability.weeklySchedule.reduce(
    (total, slot) => total + timeToMinutes(slot.end) - timeToMinutes(slot.start),
    0
  );
  return minutes / 60;
}
function workingDays(availability) {
  return [...new Set(availability.weeklySchedule.map((slot) => slot.day))].sort();
}
export {
  AVAILABILITY_TEMPLATES,
  AVAILABILITY_VERSION,
  COMMON_EXCEPTION_REASONS,
  DAYS_OF_WEEK,
  DEFAULT_BREAK_END,
  DEFAULT_BREAK_START,
  DEFAULT_RULES,
  DEFAULT_WORK_END,
  DEFAULT_WORK_START,
  MINUTES_PER_DAY,
  SLOT_DURATION_CHOICES,
  WEEKDAYS,
  WEEKEND,
  availabilityFromWeek,
  emptyAvailability,
  findGaps,
  groupByDay,
  hasBlockingErrors,
  isEndAfterStart,
  isValidDate,
  isValidTime,
  minutesToTime,
  slotsOverlap,
  suggestNextSlot,
  timeToMinutes,
  toCalendarDate,
  validateAvailability,
  weeklyHours,
  workingDays
};
//# sourceMappingURL=index.js.map