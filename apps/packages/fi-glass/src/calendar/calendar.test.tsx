// @vitest-environment jsdom
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import { emptyAvailability, type DoctorAvailability } from '@free-intelligence/core/availability';
import '../test-utils/fullCalendarInJsdom';
import { AvailabilityEditor, FiCalendar, useAvailabilityForm, type AvailabilityForm } from './index';

let form: AvailabilityForm;

function Editor({ initial }: { initial?: DoctorAvailability }) {
  form = useAvailabilityForm(initial);
  return <AvailabilityEditor form={form} />;
}

const mondays = (start: string, end: string): DoctorAvailability => ({
  ...emptyAvailability(),
  weeklySchedule: [{ day: 1, start, end }],
});
const openTab = (name: string) => userEvent.click(screen.getByRole('tab', { name }));

describe('AvailabilityEditor', () => {
  it('keeps the focused field mounted across edits', () => {
    render(<Editor initial={mondays('09:00', '13:00')} />);
    const start = screen.getByLabelText('Lunes, horario 1, inicio');
    start.focus();
    fireEvent.change(start, { target: { value: '' } });
    fireEvent.change(start, { target: { value: '10:30' } });
    expect(document.activeElement).toBe(start);
    expect(form.availability.weeklySchedule).toEqual([{ day: 1, start: '10:30', end: '13:00' }]);
    expect(form.isDirty).toBe(true);
  });

  it('shows the error on the slot that has it and blocks saving', () => {
    render(<Editor initial={mondays('13:00', '09:00')} />);
    expect(screen.getByRole('alert').textContent).toContain('posterior');
    expect(screen.getByLabelText('Lunes, horario 1, inicio').getAttribute('aria-invalid')).toBe('true');
    expect(form.isValid).toBe(false);
  });

  it('restores the hours of a day switched off and on', async () => {
    render(<Editor initial={mondays('08:00', '12:00')} />);
    const monday = screen.getByRole('switch', { name: /Lunes/ });
    await userEvent.click(monday);
    expect(form.availability.weeklySchedule).toEqual([]);
    await userEvent.click(monday);
    expect(form.availability.weeklySchedule).toEqual([{ day: 1, start: '08:00', end: '12:00' }]);
  });

  it('stops offering slots when the day has no room', () => {
    render(<Editor initial={mondays('18:00', '23:30')} />);
    const monday = screen.getByLabelText('Lunes, horario 1, inicio').closest('li')!;
    expect(within(monday).getByRole<HTMLButtonElement>('button', { name: 'Agregar horario' }).disabled).toBe(true);
  });

  it('adds an exception once and edits its reason without losing a keystroke', async () => {
    render(<Editor />);
    await openTab('Excepciones');
    fireEvent.change(screen.getByLabelText('Fecha de la excepción'), { target: { value: '2999-12-24' } });
    await userEvent.click(screen.getByRole('button', { name: 'Agregar excepción' }));
    await userEvent.type(screen.getByLabelText('Motivo (opcional)'), 'Vacaciones de mamá');
    expect(form.overrides).toEqual([{ date: '2999-12-24', fullDayClosed: true, reason: 'Vacaciones de mamá' }]);
    fireEvent.change(screen.getByLabelText('Fecha de la excepción'), { target: { value: '2999-12-24' } });
    expect(screen.getByRole<HTMLButtonElement>('button', { name: 'Agregar excepción' }).disabled).toBe(true);
  });

  it('a template replaces the week and keeps exceptions and rules', async () => {
    const overrides = [{ date: '2999-12-24', fullDayClosed: true }];
    render(<Editor initial={{ ...mondays('09:00', '10:00'), overrides, rules: { minSlotDuration: 45 } }} />);
    await openTab('Plantillas');
    await userEvent.click(screen.getByRole('button', { name: 'Aplicar Doctor de Fin de Semana' }));
    expect(form.availability.weeklySchedule).toHaveLength(1);
    await userEvent.click(screen.getByRole('button', { name: 'Sí, reemplazar' }));
    expect(form.availability).toMatchObject({ overrides, rules: { minSlotDuration: 45 } });
    expect(form.availability.weeklySchedule.map(({ day }) => day)).toEqual([0, 6]);
  });

  it('moves between tabs with the arrows and previews the week', async () => {
    const { container } = render(<Editor initial={mondays('09:00', '13:00')} />);
    screen.getByRole('tab', { name: 'Semanal' }).focus();
    await userEvent.keyboard('{ArrowLeft}');
    expect(screen.getByRole('tab', { name: 'Vista previa' }).getAttribute('aria-selected')).toBe('true');
    expect(container.querySelectorAll('.fi-calendar-event--available')).toHaveLength(1);
    expect(screen.getByText('4 h por semana en 1 día.')).toBeTruthy();
    const nav = screen.getByRole('button', { name: 'Anterior' }).parentElement;
    expect(nav?.classList.contains('fi-availability-nav')).toBe(true);
    expect([...(nav?.children ?? [])].map((b) => b.textContent)).toEqual(['Anterior', 'Hoy', 'Siguiente']);
  });

  it('reset returns to what was loaded', () => {
    render(<Editor initial={mondays('09:00', '13:00')} />);
    fireEvent.change(screen.getByLabelText('Lunes, horario 1, inicio'), { target: { value: '10:00' } });
    act(() => form.reset());
    expect(form.isDirty).toBe(false);
    expect(form.availability.weeklySchedule).toEqual([{ day: 1, start: '09:00', end: '13:00' }]);
  });
});

describe('FiCalendar', () => {
  it('renders events, reports clicks and lets options win over the defaults', async () => {
    const onEventClick = vi.fn();
    const { container } = render(
      <FiCalendar
        initialDate="2026-11-25"
        hours="clinic"
        theme="light"
        events={[{ id: 'a', title: 'Ana', start: '2026-11-25T10:00:00', end: '2026-11-25T11:00:00' }]}
        eventClick={({ event }) => onEventClick(event.id)}
        headerToolbar={{ left: 'today', center: '', right: '' }}
      />,
    );
    expect(container.querySelector('.fi-calendar')?.getAttribute('data-theme')).toBe('light');
    expect(container.querySelector('[data-time="06:00:00"]')).toBeNull();
    expect(screen.getByRole('button', { name: /hoy/i })).toBeTruthy();
    await userEvent.click(screen.getByText('Ana'));
    expect(onEventClick).toHaveBeenCalledWith('a');
  });
});
