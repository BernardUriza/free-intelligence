'use client';

import { DEFAULT_BREAK_END, DEFAULT_BREAK_START, SLOT_DURATION_CHOICES } from '@free-intelligence/core/availability';
import { Chip, ErrorNote, NumberField, Switch, TabHeading, TimeRange } from './controls';
import type { AvailabilityTabProps } from './tab';

export function RulesTab({ form, disabled }: AvailabilityTabProps) {
  const { rules, updateRules } = form;
  const hasBreak = rules.breakStart !== undefined && rules.breakEnd !== undefined;
  const ruleErrors = form.errors.filter((error) => error.day === undefined && error.date === undefined);

  return (
    <>
      <TabHeading title="Reglas de agenda">Descanso diario, capacidad y duración de las citas.</TabHeading>
      <section className="fi-availability-card">
        <div className="fi-availability-row">
          <span className="fi-availability-day-name">Descanso diario</span>
          <Switch
            checked={hasBreak}
            label="Descanso diario"
            onChange={(on) =>
              updateRules({ breakStart: on ? DEFAULT_BREAK_START : undefined, breakEnd: on ? DEFAULT_BREAK_END : undefined })
            }
            disabled={disabled}
          />
        </div>
        {hasBreak && (
          <TimeRange
            label="Descanso"
            start={rules.breakStart ?? ''}
            end={rules.breakEnd ?? ''}
            onChange={({ start = rules.breakStart, end = rules.breakEnd }) => updateRules({ breakStart: start, breakEnd: end })}
            disabled={disabled}
          />
        )}
      </section>
      <section className="fi-availability-card">
        <span className="fi-availability-day-name">Capacidad</span>
        <div className="fi-availability-columns">
          <NumberField
            label="Máx. pacientes por hora"
            min={1}
            max={20}
            placeholder="Sin límite"
            value={rules.maxPatientsPerHour}
            onChange={(maxPatientsPerHour) => updateRules({ maxPatientsPerHour })}
            disabled={disabled}
          />
          <NumberField
            label="Minutos entre citas"
            min={0}
            max={60}
            step={5}
            placeholder="0"
            value={rules.bufferBetweenAppointments}
            onChange={(bufferBetweenAppointments) => updateRules({ bufferBetweenAppointments })}
            disabled={disabled}
          />
        </div>
      </section>
      <section className="fi-availability-card">
        <span className="fi-availability-day-name">Duración de la cita</span>
        <div className="fi-availability-chips">
          {SLOT_DURATION_CHOICES.map((minutes) => (
            <Chip
              key={minutes}
              selected={rules.minSlotDuration === minutes}
              onSelect={() => updateRules({ minSlotDuration: minutes })}
              disabled={disabled}
            >
              {minutes} min
            </Chip>
          ))}
        </div>
        <NumberField
          label="Otra duración (minutos)"
          min={5}
          max={120}
          step={5}
          value={rules.minSlotDuration}
          onChange={(minSlotDuration) => updateRules({ minSlotDuration })}
          disabled={disabled}
        />
      </section>
      {ruleErrors.map(({ message }) => (
        <ErrorNote key={message}>{message}</ErrorNote>
      ))}
    </>
  );
}
