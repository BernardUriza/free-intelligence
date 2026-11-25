'use client';

import { useId, type ButtonHTMLAttributes, type ReactNode } from 'react';

type ActionTone = 'default' | 'primary' | 'dashed' | 'danger';

interface ActionProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: ActionTone;
}

export function Action({ tone = 'default', ...button }: ActionProps) {
  return <button type="button" className="fi-availability-action" data-tone={tone} {...button} />;
}

interface SwitchProps {
  checked: boolean;
  label: string;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}

export function Switch({ checked, label, onChange, disabled }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      className="fi-availability-switch"
      aria-checked={checked}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange(!checked)}
    />
  );
}

interface ChipProps {
  selected: boolean;
  onSelect: () => void;
  disabled?: boolean;
  children: ReactNode;
}

export function Chip({ selected, onSelect, disabled, children }: ChipProps) {
  return (
    <button type="button" className="fi-availability-chip" aria-pressed={selected} disabled={disabled} onClick={onSelect}>
      {children}
    </button>
  );
}

interface TimeRangeProps {
  label: string;
  start: string;
  end: string;
  onChange: (changes: { start?: string; end?: string }) => void;
  error?: string;
  disabled?: boolean;
}

export function TimeRange({ label, start, end, onChange, error, disabled }: TimeRangeProps) {
  const errorId = useId();
  const shared = {
    type: 'time',
    className: 'fi-availability-field',
    disabled,
    'aria-invalid': Boolean(error),
    'aria-describedby': error ? errorId : undefined,
  } as const;
  return (
    <div className="fi-availability-range">
      <input {...shared} aria-label={`${label}, inicio`} value={start} onChange={(e) => onChange({ start: e.target.value })} />
      <span className="fi-availability-range-dash" aria-hidden="true">—</span>
      <input {...shared} aria-label={`${label}, fin`} value={end} onChange={(e) => onChange({ end: e.target.value })} />
      {error && <ErrorNote id={errorId}>{error}</ErrorNote>}
    </div>
  );
}

interface NumberFieldProps {
  label: string;
  value: number | undefined;
  onChange: (value: number | undefined) => void;
  min: number;
  max: number;
  step?: number;
  placeholder?: string;
  disabled?: boolean;
}

export function NumberField({ label, value, onChange, ...input }: NumberFieldProps) {
  return (
    <label className="fi-availability-labeled">
      {label}
      <input
        type="number"
        className="fi-availability-field"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value === '' ? undefined : Number(e.target.value))}
        {...input}
      />
    </label>
  );
}

export function ErrorNote({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="fi-availability-error" role="alert">
      {children}
    </p>
  );
}

interface TabHeadingProps {
  title: string;
  children: ReactNode;
}

export function TabHeading({ title, children }: TabHeadingProps) {
  return (
    <header className="fi-availability-heading">
      <h3 className="fi-availability-title">{title}</h3>
      <p className="fi-availability-hint">{children}</p>
    </header>
  );
}

export function EmptyState({ title, children }: TabHeadingProps) {
  return (
    <div className="fi-availability-empty">
      <p>{title}</p>
      <p className="fi-availability-hint">{children}</p>
    </div>
  );
}
