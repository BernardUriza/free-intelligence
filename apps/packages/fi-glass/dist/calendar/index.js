'use client';

// src/calendar/FiCalendar.tsx
import { forwardRef } from "react";
import esLocale from "@fullcalendar/core/locales/es";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin from "@fullcalendar/interaction";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";

// src/calendar/presets.ts
var CALENDAR_HOURS = {
  business: { slotMinTime: "06:00:00", slotMaxTime: "23:00:00", slotDuration: "01:00:00", slotLabelInterval: "01:00:00" },
  extended: { slotMinTime: "05:00:00", slotMaxTime: "24:00:00", slotDuration: "01:00:00", slotLabelInterval: "01:00:00" },
  compact: { slotMinTime: "07:00:00", slotMaxTime: "22:00:00", slotDuration: "00:30:00", slotLabelInterval: "01:00:00" },
  clinic: { slotMinTime: "07:00:00", slotMaxTime: "21:00:00", slotDuration: "00:30:00", slotLabelInterval: "01:00:00" }
};
var CALENDAR_DEFAULTS = {
  initialView: "timeGridWeek",
  locale: "es",
  headerToolbar: false,
  height: 420,
  allDaySlot: false,
  nowIndicator: true,
  eventDisplay: "block",
  displayEventEnd: false,
  eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
  slotLabelFormat: { hour: "numeric", minute: "2-digit", hour12: false },
  dayHeaderFormat: { weekday: "short", day: "numeric", month: "short" }
};

// src/calendar/FiCalendar.tsx
import { jsx } from "react/jsx-runtime";
var PLUGINS = [timeGridPlugin, dayGridPlugin, interactionPlugin];
var LOCALES = [esLocale];
var FiCalendar = forwardRef(function FiCalendar2({ hours = "business", theme = "dark", className, ...options }, ref) {
  const isClickable = Boolean(options.dateClick || options.selectable);
  return /* @__PURE__ */ jsx(
    "div",
    {
      className: className ? `fi-calendar ${className}` : "fi-calendar",
      "data-theme": theme,
      "data-clickable": isClickable || void 0,
      children: /* @__PURE__ */ jsx(
        FullCalendar,
        {
          ref,
          plugins: PLUGINS,
          locales: LOCALES,
          ...CALENDAR_DEFAULTS,
          ...CALENDAR_HOURS[hours],
          ...options
        }
      )
    }
  );
});

// src/calendar/useCalendarNavigation.ts
import { useMemo, useRef } from "react";
function useCalendarNavigation() {
  const calendarRef = useRef(null);
  const navigation = useMemo(() => {
    const api = () => calendarRef.current?.getApi();
    return {
      goToNext: () => api()?.next(),
      goToPrev: () => api()?.prev(),
      goToToday: () => api()?.today(),
      goToDate: (date) => api()?.gotoDate(date)
    };
  }, []);
  return { calendarRef, navigation };
}

// src/calendar/availabilityEvents.ts
import { toCalendarDate } from "@free-intelligence/core/availability";
var eventClass = (kind) => [`fi-calendar-event--${kind}`];
var wholeDay = (kind, date, reason) => ({
  id: `${kind}-${date}`,
  start: date,
  allDay: true,
  display: "background",
  classNames: eventClass(kind),
  extendedProps: { kind, reason }
});
var block = (kind, date, index, hours, title) => ({
  id: `${kind}-${date}-${index}`,
  title,
  start: `${date}T${hours.start}:00`,
  end: `${date}T${hours.end}:00`,
  classNames: eventClass(kind),
  extendedProps: { kind }
});
function closedDayEvent({ date, reason }) {
  return wholeDay("closed", date, reason);
}
function availabilityEvents({ weeklySchedule, overrides }, { from, days, availableLabel = "Disponible", overrideLabel = "Horario especial" }) {
  const overrideByDate = new Map(overrides.map((override) => [override.date, override]));
  return Array.from({ length: days }, (_, offset) => {
    const day = new Date(from.getFullYear(), from.getMonth(), from.getDate() + offset);
    const date = toCalendarDate(day);
    const override = overrideByDate.get(date);
    if (override?.fullDayClosed) return [closedDayEvent(override)];
    if (override) {
      const { start, end, reason } = override;
      return start && end ? [block("override", date, 0, { start, end }, reason || overrideLabel)] : [];
    }
    const slots = weeklySchedule.filter((slot) => slot.day === day.getDay());
    if (slots.length === 0) return [wholeDay("day-off", date)];
    return slots.map((slot, index) => block("available", date, index, slot, slot.label || availableLabel));
  }).flat();
}
function businessHours(weeklySchedule) {
  return weeklySchedule.map(({ day, start, end }) => ({ daysOfWeek: [day], startTime: start, endTime: end }));
}

// src/calendar/availability/AvailabilityEditor.tsx
import { useId as useId2, useState as useState4 } from "react";

// src/calendar/availability/ExceptionsTab.tsx
import { useState } from "react";
import {
  COMMON_EXCEPTION_REASONS,
  DEFAULT_WORK_END,
  DEFAULT_WORK_START,
  toCalendarDate as toCalendarDate2
} from "@free-intelligence/core/availability";

// src/calendar/availability/controls.tsx
import { useId } from "react";
import { jsx as jsx2, jsxs } from "react/jsx-runtime";
function Action({ tone = "default", ...button }) {
  return /* @__PURE__ */ jsx2("button", { type: "button", className: "fi-availability-action", "data-tone": tone, ...button });
}
function Switch({ checked, label, onChange, disabled }) {
  return /* @__PURE__ */ jsx2(
    "button",
    {
      type: "button",
      role: "switch",
      className: "fi-availability-switch",
      "aria-checked": checked,
      "aria-label": label,
      disabled,
      onClick: () => onChange(!checked)
    }
  );
}
function Chip({ selected, onSelect, disabled, children }) {
  return /* @__PURE__ */ jsx2("button", { type: "button", className: "fi-availability-chip", "aria-pressed": selected, disabled, onClick: onSelect, children });
}
function TimeRange({ label, start, end, onChange, error, disabled }) {
  const errorId = useId();
  const shared = {
    type: "time",
    className: "fi-availability-field",
    disabled,
    "aria-invalid": Boolean(error),
    "aria-describedby": error ? errorId : void 0
  };
  return /* @__PURE__ */ jsxs("div", { className: "fi-availability-range", children: [
    /* @__PURE__ */ jsx2("input", { ...shared, "aria-label": `${label}, inicio`, value: start, onChange: (e) => onChange({ start: e.target.value }) }),
    /* @__PURE__ */ jsx2("span", { className: "fi-availability-range-dash", "aria-hidden": "true", children: "\u2014" }),
    /* @__PURE__ */ jsx2("input", { ...shared, "aria-label": `${label}, fin`, value: end, onChange: (e) => onChange({ end: e.target.value }) }),
    error && /* @__PURE__ */ jsx2(ErrorNote, { id: errorId, children: error })
  ] });
}
function NumberField({ label, value, onChange, ...input }) {
  return /* @__PURE__ */ jsxs("label", { className: "fi-availability-labeled", children: [
    label,
    /* @__PURE__ */ jsx2(
      "input",
      {
        type: "number",
        className: "fi-availability-field",
        value: value ?? "",
        onChange: (e) => onChange(e.target.value === "" ? void 0 : Number(e.target.value)),
        ...input
      }
    )
  ] });
}
function ErrorNote({ id, children }) {
  return /* @__PURE__ */ jsx2("p", { id, className: "fi-availability-error", role: "alert", children });
}
function TabHeading({ title, children }) {
  return /* @__PURE__ */ jsxs("header", { className: "fi-availability-heading", children: [
    /* @__PURE__ */ jsx2("h3", { className: "fi-availability-title", children: title }),
    /* @__PURE__ */ jsx2("p", { className: "fi-availability-hint", children })
  ] });
}
function EmptyState({ title, children }) {
  return /* @__PURE__ */ jsxs("div", { className: "fi-availability-empty", children: [
    /* @__PURE__ */ jsx2("p", { children: title }),
    /* @__PURE__ */ jsx2("p", { className: "fi-availability-hint", children })
  ] });
}

// src/calendar/availability/ExceptionsTab.tsx
import { Fragment, jsx as jsx3, jsxs as jsxs2 } from "react/jsx-runtime";
var formatDate = (date) => (/* @__PURE__ */ new Date(`${date}T12:00:00`)).toLocaleDateString("es-MX", {
  weekday: "short",
  year: "numeric",
  month: "short",
  day: "numeric"
});
var upcomingFirst = (today) => (a, b) => Number(a.date < today) - Number(b.date < today) || a.date.localeCompare(b.date);
function OverrideCard({ override, isPast, form, disabled }) {
  const { date, fullDayClosed, reason = "" } = override;
  const isLocked = disabled || isPast;
  const update = (changes) => form.updateOverride(date, changes);
  const error = form.errors.find((e) => e.date === date);
  const label = formatDate(date);
  return /* @__PURE__ */ jsxs2("li", { className: "fi-availability-card", "data-past": isPast || void 0, "data-invalid": Boolean(error) || void 0, children: [
    /* @__PURE__ */ jsxs2("div", { className: "fi-availability-row", children: [
      /* @__PURE__ */ jsx3("span", { className: "fi-availability-day-name", children: isPast ? `${label} (pasado)` : label }),
      /* @__PURE__ */ jsx3(Action, { tone: "danger", "aria-label": `Eliminar excepci\xF3n del ${label}`, onClick: () => form.removeOverride(date), disabled, children: "Quitar" })
    ] }),
    /* @__PURE__ */ jsxs2("div", { className: "fi-availability-row", children: [
      /* @__PURE__ */ jsx3("span", { className: "fi-availability-hint", children: "D\xEDa completo libre" }),
      /* @__PURE__ */ jsx3(
        Switch,
        {
          checked: fullDayClosed,
          label: `${label}: d\xEDa completo libre`,
          onChange: (closed) => update({
            fullDayClosed: closed,
            start: closed ? void 0 : DEFAULT_WORK_START,
            end: closed ? void 0 : DEFAULT_WORK_END
          }),
          disabled: isLocked
        }
      )
    ] }),
    !fullDayClosed && /* @__PURE__ */ jsx3(TimeRange, { label, start: override.start ?? "", end: override.end ?? "", onChange: update, disabled: isLocked }),
    /* @__PURE__ */ jsx3("div", { className: "fi-availability-chips", children: COMMON_EXCEPTION_REASONS.map((common) => /* @__PURE__ */ jsx3(Chip, { selected: reason === common, onSelect: () => update({ reason: common }), disabled: isLocked, children: common }, common)) }),
    /* @__PURE__ */ jsxs2("label", { className: "fi-availability-labeled", children: [
      "Motivo (opcional)",
      /* @__PURE__ */ jsx3(
        "input",
        {
          type: "text",
          className: "fi-availability-field",
          value: reason,
          onChange: (e) => update({ reason: e.target.value }),
          disabled: isLocked
        }
      )
    ] }),
    error && /* @__PURE__ */ jsx3(ErrorNote, { children: error.message })
  ] });
}
function ExceptionsTab({ form, disabled }) {
  const [newDate, setNewDate] = useState("");
  const today = toCalendarDate2(/* @__PURE__ */ new Date());
  const isTaken = form.overrides.some(({ date }) => date === newDate);
  const addException = () => {
    form.addOverride({ date: newDate, fullDayClosed: true, reason: "" });
    setNewDate("");
  };
  return /* @__PURE__ */ jsxs2(Fragment, { children: [
    /* @__PURE__ */ jsx3(TabHeading, { title: "Excepciones", children: "Fechas en las que el horario cambia: vacaciones, festivos, eventos." }),
    /* @__PURE__ */ jsxs2("div", { className: "fi-availability-row", children: [
      /* @__PURE__ */ jsx3(
        "input",
        {
          type: "date",
          className: "fi-availability-field",
          "aria-label": "Fecha de la excepci\xF3n",
          min: today,
          value: newDate,
          onChange: (e) => setNewDate(e.target.value),
          disabled
        }
      ),
      /* @__PURE__ */ jsx3(Action, { tone: "primary", onClick: addException, disabled: disabled || !newDate || isTaken, children: "Agregar excepci\xF3n" })
    ] }),
    isTaken && /* @__PURE__ */ jsx3(ErrorNote, { children: "Ya existe una excepci\xF3n para esta fecha" }),
    form.overrides.length === 0 && /* @__PURE__ */ jsx3(EmptyState, { title: "No hay excepciones.", children: "El horario semanal aplica sin cambios." }),
    /* @__PURE__ */ jsx3("ul", { className: "fi-availability-list", children: [...form.overrides].sort(upcomingFirst(today)).map((override) => /* @__PURE__ */ jsx3(OverrideCard, { override, isPast: override.date < today, form, disabled }, override.date)) })
  ] });
}

// src/calendar/availability/PreviewTab.tsx
import { useMemo as useMemo2, useState as useState2 } from "react";
import { weeklyHours, workingDays } from "@free-intelligence/core/availability";
import { Fragment as Fragment2, jsx as jsx4, jsxs as jsxs3 } from "react/jsx-runtime";
var DAYS_SHOWN = 7;
var WEEK_TITLE = { left: "title", center: "", right: "" };
var DAY_HEADER = { weekday: "short", day: "numeric" };
var LEGEND = [
  { kind: "available", label: "Disponible" },
  { kind: "override", label: "Horario especial" },
  { kind: "closed", label: "Cerrado" },
  { kind: "day-off", label: "D\xEDa libre" }
];
function PreviewTab({ form }) {
  const { availability } = form;
  const { calendarRef, navigation } = useCalendarNavigation();
  const [from, setFrom] = useState2(() => /* @__PURE__ */ new Date());
  const dayCount = workingDays(availability).length;
  const events = useMemo2(() => availabilityEvents(availability, { from, days: DAYS_SHOWN }), [availability, from]);
  const showWeek = ({ start }) => setFrom(start);
  return /* @__PURE__ */ jsxs3(Fragment2, { children: [
    /* @__PURE__ */ jsx4(TabHeading, { title: "Vista previa", children: `${weeklyHours(availability)} h por semana en ${dayCount} ${dayCount === 1 ? "d\xEDa" : "d\xEDas"}.` }),
    /* @__PURE__ */ jsxs3("div", { className: "fi-availability-row", children: [
      /* @__PURE__ */ jsx4(Action, { onClick: navigation.goToPrev, children: "Anterior" }),
      /* @__PURE__ */ jsx4(Action, { onClick: navigation.goToToday, children: "Hoy" }),
      /* @__PURE__ */ jsx4(Action, { onClick: navigation.goToNext, children: "Siguiente" })
    ] }),
    /* @__PURE__ */ jsx4(
      FiCalendar,
      {
        ref: calendarRef,
        className: "fi-availability-preview",
        theme: "inherit",
        events,
        datesSet: showWeek,
        headerToolbar: WEEK_TITLE,
        dayHeaderFormat: DAY_HEADER
      }
    ),
    /* @__PURE__ */ jsx4("ul", { className: "fi-availability-legend", children: LEGEND.map(({ kind, label }) => /* @__PURE__ */ jsx4("li", { "data-kind": kind, children: label }, kind)) })
  ] });
}

// src/calendar/availability/RulesTab.tsx
import { DEFAULT_BREAK_END, DEFAULT_BREAK_START, SLOT_DURATION_CHOICES } from "@free-intelligence/core/availability";
import { Fragment as Fragment3, jsx as jsx5, jsxs as jsxs4 } from "react/jsx-runtime";
function RulesTab({ form, disabled }) {
  const { rules, updateRules } = form;
  const hasBreak = rules.breakStart !== void 0 && rules.breakEnd !== void 0;
  const ruleErrors = form.errors.filter((error) => error.day === void 0 && error.date === void 0);
  return /* @__PURE__ */ jsxs4(Fragment3, { children: [
    /* @__PURE__ */ jsx5(TabHeading, { title: "Reglas de agenda", children: "Descanso diario, capacidad y duraci\xF3n de las citas." }),
    /* @__PURE__ */ jsxs4("section", { className: "fi-availability-card", children: [
      /* @__PURE__ */ jsxs4("div", { className: "fi-availability-row", children: [
        /* @__PURE__ */ jsx5("span", { className: "fi-availability-day-name", children: "Descanso diario" }),
        /* @__PURE__ */ jsx5(
          Switch,
          {
            checked: hasBreak,
            label: "Descanso diario",
            onChange: (on) => updateRules({ breakStart: on ? DEFAULT_BREAK_START : void 0, breakEnd: on ? DEFAULT_BREAK_END : void 0 }),
            disabled
          }
        )
      ] }),
      hasBreak && /* @__PURE__ */ jsx5(
        TimeRange,
        {
          label: "Descanso",
          start: rules.breakStart ?? "",
          end: rules.breakEnd ?? "",
          onChange: ({ start = rules.breakStart, end = rules.breakEnd }) => updateRules({ breakStart: start, breakEnd: end }),
          disabled
        }
      )
    ] }),
    /* @__PURE__ */ jsxs4("section", { className: "fi-availability-card", children: [
      /* @__PURE__ */ jsx5("span", { className: "fi-availability-day-name", children: "Capacidad" }),
      /* @__PURE__ */ jsxs4("div", { className: "fi-availability-columns", children: [
        /* @__PURE__ */ jsx5(
          NumberField,
          {
            label: "M\xE1x. pacientes por hora",
            min: 1,
            max: 20,
            placeholder: "Sin l\xEDmite",
            value: rules.maxPatientsPerHour,
            onChange: (maxPatientsPerHour) => updateRules({ maxPatientsPerHour }),
            disabled
          }
        ),
        /* @__PURE__ */ jsx5(
          NumberField,
          {
            label: "Minutos entre citas",
            min: 0,
            max: 60,
            step: 5,
            placeholder: "0",
            value: rules.bufferBetweenAppointments,
            onChange: (bufferBetweenAppointments) => updateRules({ bufferBetweenAppointments }),
            disabled
          }
        )
      ] })
    ] }),
    /* @__PURE__ */ jsxs4("section", { className: "fi-availability-card", children: [
      /* @__PURE__ */ jsx5("span", { className: "fi-availability-day-name", children: "Duraci\xF3n de la cita" }),
      /* @__PURE__ */ jsx5("div", { className: "fi-availability-chips", children: SLOT_DURATION_CHOICES.map((minutes) => /* @__PURE__ */ jsxs4(
        Chip,
        {
          selected: rules.minSlotDuration === minutes,
          onSelect: () => updateRules({ minSlotDuration: minutes }),
          disabled,
          children: [
            minutes,
            " min"
          ]
        },
        minutes
      )) }),
      /* @__PURE__ */ jsx5(
        NumberField,
        {
          label: "Otra duraci\xF3n (minutos)",
          min: 5,
          max: 120,
          step: 5,
          value: rules.minSlotDuration,
          onChange: (minSlotDuration) => updateRules({ minSlotDuration }),
          disabled
        }
      )
    ] }),
    ruleErrors.map(({ message }) => /* @__PURE__ */ jsx5(ErrorNote, { children: message }, message))
  ] });
}

// src/calendar/availability/TemplatesTab.tsx
import { useState as useState3 } from "react";
import { AVAILABILITY_TEMPLATES } from "@free-intelligence/core/availability";
import { Fragment as Fragment4, jsx as jsx6, jsxs as jsxs5 } from "react/jsx-runtime";
function TemplatesTab({ form, disabled }) {
  const [pending, setPending] = useState3(null);
  const hasSchedule = form.availability.weeklySchedule.length > 0;
  const choose = (template) => hasSchedule ? setPending(template) : form.applyWeek(template.weeklySchedule);
  const confirm = (template) => {
    form.applyWeek(template.weeklySchedule);
    setPending(null);
  };
  return /* @__PURE__ */ jsxs5(Fragment4, { children: [
    /* @__PURE__ */ jsx6(TabHeading, { title: "Plantillas", children: "Un horario semanal para empezar. Las excepciones y las reglas se conservan." }),
    pending && /* @__PURE__ */ jsxs5("div", { className: "fi-availability-note", role: "alertdialog", "aria-label": "Reemplazar horario semanal", children: [
      /* @__PURE__ */ jsxs5("p", { children: [
        "\xBFReemplazar el horario semanal con \xAB",
        pending.name,
        "\xBB?"
      ] }),
      /* @__PURE__ */ jsxs5("div", { className: "fi-availability-row", children: [
        /* @__PURE__ */ jsx6(Action, { onClick: () => setPending(null), children: "Cancelar" }),
        /* @__PURE__ */ jsx6(Action, { tone: "primary", onClick: () => confirm(pending), children: "S\xED, reemplazar" })
      ] })
    ] }),
    /* @__PURE__ */ jsx6("ul", { className: "fi-availability-list", children: AVAILABILITY_TEMPLATES.map((template) => /* @__PURE__ */ jsx6("li", { className: "fi-availability-card", children: /* @__PURE__ */ jsxs5("div", { className: "fi-availability-row", children: [
      /* @__PURE__ */ jsxs5("div", { children: [
        /* @__PURE__ */ jsx6("p", { className: "fi-availability-day-name", children: template.name }),
        /* @__PURE__ */ jsx6("p", { className: "fi-availability-hint", children: template.description })
      ] }),
      /* @__PURE__ */ jsx6(Action, { "aria-label": `Aplicar ${template.name}`, onClick: () => choose(template), disabled: disabled || pending !== null, children: "Aplicar" })
    ] }) }, template.id)) })
  ] });
}

// src/calendar/availability/WeeklyTab.tsx
import { DAYS_OF_WEEK, findGaps, suggestNextSlot } from "@free-intelligence/core/availability";
import { Fragment as Fragment5, jsx as jsx7, jsxs as jsxs6 } from "react/jsx-runtime";
function DayRow({ day, schedule, errors, form, disabled }) {
  const { isWorking, slots } = schedule;
  return /* @__PURE__ */ jsxs6("li", { className: "fi-availability-day", "data-working": isWorking, "data-invalid": errors.length > 0 || void 0, children: [
    /* @__PURE__ */ jsxs6("div", { className: "fi-availability-row", children: [
      /* @__PURE__ */ jsx7("span", { className: "fi-availability-day-name", children: day.label }),
      /* @__PURE__ */ jsx7("span", { className: "fi-availability-hint", children: isWorking ? "Activo" : "Libre" }),
      /* @__PURE__ */ jsx7(
        Switch,
        {
          checked: isWorking,
          label: `${day.label}: d\xEDa de consulta`,
          onChange: (working) => form.setDayWorking(day.value, working),
          disabled
        }
      )
    ] }),
    isWorking && /* @__PURE__ */ jsxs6("div", { className: "fi-availability-slots", children: [
      slots.map((slot, index) => /* @__PURE__ */ jsxs6("div", { className: "fi-availability-row", children: [
        /* @__PURE__ */ jsx7(
          TimeRange,
          {
            label: `${day.label}, horario ${index + 1}`,
            start: slot.start,
            end: slot.end,
            onChange: (changes) => form.updateSlot(day.value, index, changes),
            error: errors.find((error) => error.slotIndex === index)?.message,
            disabled
          }
        ),
        slots.length > 1 && /* @__PURE__ */ jsx7(
          Action,
          {
            tone: "danger",
            "aria-label": `Eliminar ${day.label}, horario ${index + 1}`,
            onClick: () => form.removeSlot(day.value, index),
            disabled,
            children: "Quitar"
          }
        )
      ] }, index)),
      /* @__PURE__ */ jsx7(
        Action,
        {
          tone: "dashed",
          onClick: () => form.addSlot(day.value),
          disabled: disabled || !suggestNextSlot(day.value, slots),
          children: "Agregar horario"
        }
      )
    ] })
  ] });
}
function WeeklyTab({ form, disabled }) {
  const gaps = findGaps(form.availability.weeklySchedule);
  const isEmpty = form.availability.weeklySchedule.length === 0;
  return /* @__PURE__ */ jsxs6(Fragment5, { children: [
    /* @__PURE__ */ jsx7(TabHeading, { title: "Horario semanal", children: "El horario que se repite cada semana. Un d\xEDa puede tener varios bloques, por ejemplo ma\xF1ana y tarde." }),
    isEmpty && /* @__PURE__ */ jsx7(EmptyState, { title: "No hay d\xEDas de consulta.", children: "Activa al menos un d\xEDa." }),
    /* @__PURE__ */ jsx7("ul", { className: "fi-availability-list", children: DAYS_OF_WEEK.map((day) => /* @__PURE__ */ jsx7(
      DayRow,
      {
        day,
        schedule: form.week[day.value],
        errors: form.errors.filter((error) => error.day === day.value),
        form,
        disabled
      },
      day.value
    )) }),
    gaps.length > 0 && /* @__PURE__ */ jsxs6("div", { className: "fi-availability-note", children: [
      "Espacios sin consulta entre horarios:",
      /* @__PURE__ */ jsx7("ul", { className: "fi-availability-note-list", children: gaps.map(({ day, from, to }) => /* @__PURE__ */ jsx7("li", { children: `${DAYS_OF_WEEK[day].label}: ${from} - ${to}` }, `${day}-${from}`)) })
    ] })
  ] });
}

// src/calendar/availability/AvailabilityEditor.tsx
import { jsx as jsx8, jsxs as jsxs7 } from "react/jsx-runtime";
var TABS = {
  weekly: { label: "Semanal", Panel: WeeklyTab },
  exceptions: { label: "Excepciones", Panel: ExceptionsTab },
  rules: { label: "Reglas", Panel: RulesTab },
  templates: { label: "Plantillas", Panel: TemplatesTab },
  preview: { label: "Vista previa", Panel: PreviewTab }
};
var ALL_TABS = Object.keys(TABS);
var ARROW_STEP = { ArrowRight: 1, ArrowLeft: -1 };
function AvailabilityEditor({ form, disabled, tabs = ALL_TABS, theme = "dark" }) {
  const [active, setActive] = useState4(tabs[0]);
  const id = useId2();
  const tabId = (tab) => `${id}-${tab}`;
  const { Panel } = TABS[active];
  const moveWithArrows = (event) => {
    const step = ARROW_STEP[event.key];
    if (!step) return;
    event.preventDefault();
    const next = tabs[(tabs.indexOf(active) + step + tabs.length) % tabs.length];
    setActive(next);
    document.getElementById(tabId(next))?.focus();
  };
  return /* @__PURE__ */ jsxs7("div", { className: "fi-availability", "data-theme": theme, children: [
    /* @__PURE__ */ jsx8("div", { className: "fi-availability-tabs", role: "tablist", onKeyDown: moveWithArrows, children: tabs.map((tab) => /* @__PURE__ */ jsx8(
      "button",
      {
        id: tabId(tab),
        type: "button",
        role: "tab",
        className: "fi-availability-tab",
        "aria-selected": tab === active,
        "aria-controls": `${id}-panel`,
        tabIndex: tab === active ? 0 : -1,
        onClick: () => setActive(tab),
        children: TABS[tab].label
      },
      tab
    )) }),
    /* @__PURE__ */ jsx8("div", { id: `${id}-panel`, className: "fi-availability-panel", role: "tabpanel", "aria-labelledby": tabId(active), children: /* @__PURE__ */ jsx8(Panel, { form, disabled }) })
  ] });
}

// src/calendar/availability/useAvailabilityForm.ts
import { useMemo as useMemo3, useState as useState5 } from "react";
import {
  DEFAULT_RULES,
  availabilityFromWeek,
  emptyAvailability,
  groupByDay,
  hasBlockingErrors,
  suggestNextSlot as suggestNextSlot2,
  validateAvailability
} from "@free-intelligence/core/availability";
var draftOf = (availability) => ({
  week: groupByDay(availability.weeklySchedule),
  overrides: availability.overrides,
  rules: availability.rules ?? { ...DEFAULT_RULES }
});
var byDate = (a, b) => a.date.localeCompare(b.date);
function useAvailabilityForm(initial) {
  const [draft, setDraft] = useState5(() => draftOf(initial ?? emptyAvailability()));
  const [isDirty, setIsDirty] = useState5(false);
  const availability = useMemo3(() => availabilityFromWeek(draft.week, draft.overrides, draft.rules), [draft]);
  const errors = useMemo3(() => validateAvailability(availability), [availability]);
  const edit = (change) => {
    setDraft((current) => ({ ...current, ...change(current) }));
    setIsDirty(true);
  };
  const editDay = (day, change) => edit(({ week }) => ({ week: { ...week, [day]: change(week[day]) } }));
  return {
    ...draft,
    availability,
    errors,
    isValid: !hasBlockingErrors(errors),
    isDirty,
    setDayWorking: (day, isWorking) => editDay(day, ({ slots }) => {
      const first = isWorking && slots.length === 0 ? suggestNextSlot2(day, []) : null;
      return { isWorking, slots: first ? [first] : slots };
    }),
    addSlot: (day) => editDay(day, (schedule) => {
      const next = suggestNextSlot2(day, schedule.slots);
      return next ? { isWorking: true, slots: [...schedule.slots, next] } : schedule;
    }),
    removeSlot: (day, index) => editDay(day, ({ slots }) => {
      const remaining = slots.filter((_, i) => i !== index);
      return { isWorking: remaining.length > 0, slots: remaining };
    }),
    updateSlot: (day, index, changes) => editDay(day, (schedule) => ({
      ...schedule,
      slots: schedule.slots.map((slot, i) => i === index ? { ...slot, ...changes } : slot)
    })),
    addOverride: (override) => edit(
      ({ overrides }) => overrides.some(({ date }) => date === override.date) ? {} : { overrides: [...overrides, override].sort(byDate) }
    ),
    removeOverride: (date) => edit(({ overrides }) => ({ overrides: overrides.filter((o) => o.date !== date) })),
    updateOverride: (date, changes) => edit(({ overrides }) => ({ overrides: overrides.map((o) => o.date === date ? { ...o, ...changes } : o) })),
    updateRules: (changes) => edit(({ rules }) => ({ rules: { ...rules, ...changes } })),
    applyWeek: (weeklySchedule) => edit(() => ({ week: groupByDay(weeklySchedule) })),
    reset: () => {
      setDraft(draftOf(initial ?? emptyAvailability()));
      setIsDirty(false);
    }
  };
}
export {
  AvailabilityEditor,
  CALENDAR_DEFAULTS,
  CALENDAR_HOURS,
  FiCalendar,
  availabilityEvents,
  businessHours,
  closedDayEvent,
  useAvailabilityForm,
  useCalendarNavigation
};
//# sourceMappingURL=index.js.map