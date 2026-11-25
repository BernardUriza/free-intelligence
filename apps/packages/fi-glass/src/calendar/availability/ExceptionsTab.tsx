'use client';

import { useState } from 'react';
import {
  COMMON_EXCEPTION_REASONS,
  DEFAULT_WORK_END,
  DEFAULT_WORK_START,
  toCalendarDate,
  type DateOverride,
} from '@free-intelligence/core/availability';
import { Action, Chip, EmptyState, ErrorNote, Switch, TabHeading, TimeRange } from './controls';
import type { AvailabilityTabProps } from './tab';

const formatDate = (date: string) =>
  new Date(`${date}T12:00:00`).toLocaleDateString('es-MX', {
    weekday: 'short',
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

const upcomingFirst = (today: string) => (a: DateOverride, b: DateOverride) =>
  Number(a.date < today) - Number(b.date < today) || a.date.localeCompare(b.date);

interface OverrideCardProps extends AvailabilityTabProps {
  override: DateOverride;
  isPast: boolean;
}

function OverrideCard({ override, isPast, form, disabled }: OverrideCardProps) {
  const { date, fullDayClosed, reason = '' } = override;
  const isLocked = disabled || isPast;
  const update = (changes: Partial<DateOverride>) => form.updateOverride(date, changes);
  const error = form.errors.find((e) => e.date === date);
  const label = formatDate(date);

  return (
    <li className="fi-availability-card" data-past={isPast || undefined} data-invalid={Boolean(error) || undefined}>
      <div className="fi-availability-row">
        <span className="fi-availability-day-name">{isPast ? `${label} (pasado)` : label}</span>
        <Action tone="danger" aria-label={`Eliminar excepción del ${label}`} onClick={() => form.removeOverride(date)} disabled={disabled}>
          Quitar
        </Action>
      </div>
      <div className="fi-availability-row">
        <span className="fi-availability-hint">Día completo libre</span>
        <Switch
          checked={fullDayClosed}
          label={`${label}: día completo libre`}
          onChange={(closed) =>
            update({
              fullDayClosed: closed,
              start: closed ? undefined : DEFAULT_WORK_START,
              end: closed ? undefined : DEFAULT_WORK_END,
            })
          }
          disabled={isLocked}
        />
      </div>
      {!fullDayClosed && (
        <TimeRange label={label} start={override.start ?? ''} end={override.end ?? ''} onChange={update} disabled={isLocked} />
      )}
      <div className="fi-availability-chips">
        {COMMON_EXCEPTION_REASONS.map((common) => (
          <Chip key={common} selected={reason === common} onSelect={() => update({ reason: common })} disabled={isLocked}>
            {common}
          </Chip>
        ))}
      </div>
      <label className="fi-availability-labeled">
        Motivo (opcional)
        <input
          type="text"
          className="fi-availability-field"
          value={reason}
          onChange={(e) => update({ reason: e.target.value })}
          disabled={isLocked}
        />
      </label>
      {error && <ErrorNote>{error.message}</ErrorNote>}
    </li>
  );
}

export function ExceptionsTab({ form, disabled }: AvailabilityTabProps) {
  const [newDate, setNewDate] = useState('');
  const today = toCalendarDate(new Date());
  const isTaken = form.overrides.some(({ date }) => date === newDate);

  const addException = () => {
    form.addOverride({ date: newDate, fullDayClosed: true, reason: '' });
    setNewDate('');
  };

  return (
    <>
      <TabHeading title="Excepciones">Fechas en las que el horario cambia: vacaciones, festivos, eventos.</TabHeading>
      <div className="fi-availability-row">
        <input
          type="date"
          className="fi-availability-field"
          aria-label="Fecha de la excepción"
          min={today}
          value={newDate}
          onChange={(e) => setNewDate(e.target.value)}
          disabled={disabled}
        />
        <Action tone="primary" onClick={addException} disabled={disabled || !newDate || isTaken}>
          Agregar excepción
        </Action>
      </div>
      {isTaken && <ErrorNote>Ya existe una excepción para esta fecha</ErrorNote>}
      {form.overrides.length === 0 && (
        <EmptyState title="No hay excepciones.">El horario semanal aplica sin cambios.</EmptyState>
      )}
      <ul className="fi-availability-list">
        {[...form.overrides].sort(upcomingFirst(today)).map((override) => (
          <OverrideCard key={override.date} override={override} isPast={override.date < today} form={form} disabled={disabled} />
        ))}
      </ul>
    </>
  );
}
