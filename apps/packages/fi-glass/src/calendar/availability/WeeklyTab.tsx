'use client';

import { DAYS_OF_WEEK, findGaps, suggestNextSlot, type AvailabilityError, type DaySchedule } from '@free-intelligence/core/availability';
import { Action, EmptyState, Switch, TabHeading, TimeRange } from './controls';
import type { AvailabilityTabProps } from './tab';

type Day = (typeof DAYS_OF_WEEK)[number];

interface DayRowProps extends AvailabilityTabProps {
  day: Day;
  schedule: DaySchedule;
  errors: AvailabilityError[];
}

function DayRow({ day, schedule, errors, form, disabled }: DayRowProps) {
  const { isWorking, slots } = schedule;
  return (
    <li className="fi-availability-day" data-working={isWorking} data-invalid={errors.length > 0 || undefined}>
      <div className="fi-availability-row">
        <span className="fi-availability-day-name">{day.label}</span>
        <span className="fi-availability-hint">{isWorking ? 'Activo' : 'Libre'}</span>
        <Switch
          checked={isWorking}
          label={`${day.label}: día de consulta`}
          onChange={(working) => form.setDayWorking(day.value, working)}
          disabled={disabled}
        />
      </div>
      {isWorking && (
        <div className="fi-availability-slots">
          {slots.map((slot, index) => (
            <div key={index} className="fi-availability-row">
              <TimeRange
                label={`${day.label}, horario ${index + 1}`}
                start={slot.start}
                end={slot.end}
                onChange={(changes) => form.updateSlot(day.value, index, changes)}
                error={errors.find((error) => error.slotIndex === index)?.message}
                disabled={disabled}
              />
              {slots.length > 1 && (
                <Action
                  tone="danger"
                  aria-label={`Eliminar ${day.label}, horario ${index + 1}`}
                  onClick={() => form.removeSlot(day.value, index)}
                  disabled={disabled}
                >
                  Quitar
                </Action>
              )}
            </div>
          ))}
          <Action
            tone="dashed"
            onClick={() => form.addSlot(day.value)}
            disabled={disabled || !suggestNextSlot(day.value, slots)}
          >
            Agregar horario
          </Action>
        </div>
      )}
    </li>
  );
}

export function WeeklyTab({ form, disabled }: AvailabilityTabProps) {
  const gaps = findGaps(form.availability.weeklySchedule);
  const isEmpty = form.availability.weeklySchedule.length === 0;
  return (
    <>
      <TabHeading title="Horario semanal">
        El horario que se repite cada semana. Un día puede tener varios bloques, por ejemplo mañana y tarde.
      </TabHeading>
      {isEmpty && <EmptyState title="No hay días de consulta.">Activa al menos un día.</EmptyState>}
      <ul className="fi-availability-list">
        {DAYS_OF_WEEK.map((day) => (
          <DayRow
            key={day.value}
            day={day}
            schedule={form.week[day.value]}
            errors={form.errors.filter((error) => error.day === day.value)}
            form={form}
            disabled={disabled}
          />
        ))}
      </ul>
      {gaps.length > 0 && (
        <div className="fi-availability-note">
          Espacios sin consulta entre horarios:
          <ul className="fi-availability-note-list">
            {gaps.map(({ day, from, to }) => (
              <li key={`${day}-${from}`}>{`${DAYS_OF_WEEK[day].label}: ${from} - ${to}`}</li>
            ))}
          </ul>
        </div>
      )}
    </>
  );
}
