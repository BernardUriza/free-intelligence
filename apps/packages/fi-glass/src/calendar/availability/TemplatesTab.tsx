'use client';

import { useState } from 'react';
import { AVAILABILITY_TEMPLATES, type AvailabilityTemplate } from '@free-intelligence/core/availability';
import { Action, TabHeading } from './controls';
import type { AvailabilityTabProps } from './tab';

export function TemplatesTab({ form, disabled }: AvailabilityTabProps) {
  const [pending, setPending] = useState<AvailabilityTemplate | null>(null);
  const hasSchedule = form.availability.weeklySchedule.length > 0;

  const choose = (template: AvailabilityTemplate) =>
    hasSchedule ? setPending(template) : form.applyWeek(template.weeklySchedule);

  const confirm = (template: AvailabilityTemplate) => {
    form.applyWeek(template.weeklySchedule);
    setPending(null);
  };

  return (
    <>
      <TabHeading title="Plantillas">
        Un horario semanal para empezar. Las excepciones y las reglas se conservan.
      </TabHeading>
      {pending && (
        <div className="fi-availability-note" role="alertdialog" aria-label="Reemplazar horario semanal">
          <p>¿Reemplazar el horario semanal con «{pending.name}»?</p>
          <div className="fi-availability-row">
            <Action onClick={() => setPending(null)}>Cancelar</Action>
            <Action tone="primary" onClick={() => confirm(pending)}>Sí, reemplazar</Action>
          </div>
        </div>
      )}
      <ul className="fi-availability-list">
        {AVAILABILITY_TEMPLATES.map((template) => (
          <li key={template.id} className="fi-availability-card">
            <div className="fi-availability-row">
              <div>
                <p className="fi-availability-day-name">{template.name}</p>
                <p className="fi-availability-hint">{template.description}</p>
              </div>
              <Action aria-label={`Aplicar ${template.name}`} onClick={() => choose(template)} disabled={disabled || pending !== null}>
                Aplicar
              </Action>
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
