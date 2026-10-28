'use client';

import type { ButtonHTMLAttributes, ReactNode } from 'react';
import { AlertCircle, Loader2, type LucideIcon } from 'lucide-react';
import { withTouchTarget } from '../shell/touchTarget';
import type { PersonaOption } from './types';

export function FieldLabel({
  htmlFor,
  required,
  icon: Icon,
  children,
}: {
  htmlFor?: string;
  required?: boolean;
  icon?: LucideIcon;
  children: ReactNode;
}) {
  return (
    <label className="fi-persona-label" htmlFor={htmlFor}>
      {Icon ? <Icon size={14} aria-hidden="true" /> : null}
      {children}
      {required ? <span className="fi-persona-required">*</span> : null}
    </label>
  );
}

export function FieldError({ id, error }: { id?: string; error?: string }) {
  if (!error) return null;
  return (
    <p id={id} className="fi-persona-error" role="alert">
      <AlertCircle size={12} aria-hidden="true" />
      {error}
    </p>
  );
}

export function Alert({ children }: { children: ReactNode }) {
  return (
    <p className="fi-persona-alert" role="alert">
      <AlertCircle size={18} aria-hidden="true" />
      <span>{children}</span>
    </p>
  );
}

type Variant = 'default' | 'primary' | 'ghost' | 'danger';

export function PersonaButton({
  variant = 'default',
  icon: Icon,
  loading = false,
  iconOnly = false,
  className,
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  icon?: LucideIcon;
  loading?: boolean;
  iconOnly?: boolean;
}) {
  const LeadIcon = loading ? Loader2 : Icon;
  return (
    <button
      type="button"
      {...rest}
      className={withTouchTarget(className ? `fi-persona-btn ${className}` : 'fi-persona-btn')}
      data-variant={variant}
      data-icon-only={iconOnly ? '' : undefined}
    >
      {LeadIcon ? <LeadIcon size={16} aria-hidden="true" className={loading ? 'fi-persona-spin' : undefined} /> : null}
      {children}
    </button>
  );
}

export function OptionSelect({
  id,
  value,
  options,
  onChange,
  disabled,
  emptyLabel,
  ariaInvalid,
}: {
  id?: string;
  value: string;
  options: readonly PersonaOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  emptyLabel?: string;
  ariaInvalid?: boolean;
}) {
  const known = value === '' || options.some((o) => o.value === value);
  const all: PersonaOption[] = known ? [...options] : [{ value, label: value }, ...options];
  const ungrouped = all.filter((o) => !o.group);
  const groups = [...new Set(all.filter((o) => o.group).map((o) => o.group as string))];
  return (
    <select
      id={id}
      className="fi-persona-input"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      aria-invalid={ariaInvalid || undefined}
    >
      {emptyLabel !== undefined ? <option value="">{emptyLabel}</option> : null}
      {ungrouped.map((o) => (
        <option key={o.value} value={o.value}>
          {o.label}
        </option>
      ))}
      {groups.map((group) => (
        <optgroup key={group} label={group}>
          {all
            .filter((o) => o.group === group)
            .map((o) => (
              <option key={`${group}-${o.value}`} value={o.value}>
                {o.label}
              </option>
            ))}
        </optgroup>
      ))}
    </select>
  );
}
