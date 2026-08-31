'use client';

/**
 * fi-glass · the controls a `Field` wraps.
 *
 * Each one is a thin dress over the native element, on purpose: the native
 * `<input>`, `<textarea>` and `<select>` already carry the keyboard, the
 * autofill, the mobile keyboards and the form semantics that a hand-rolled
 * replacement spends years failing to reproduce. What the package adds is the
 * skin and the touch target, nothing else — so every native prop passes through.
 */

import {
  forwardRef,
  useId,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from 'react';
import {
  FI_CHECKBOX_CLASS,
  FI_CHECKBOX_LABEL_CLASS,
  FI_FIELD_CONTROL_CLASS,
  FI_FIELD_GRID_CLASS,
  FI_FORM_ACTIONS_CLASS,
  useFormStyle,
} from './formStyle';

function join(...parts: (string | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

export type TextInputProps = InputHTMLAttributes<HTMLInputElement>;

export const TextInput = forwardRef<HTMLInputElement, TextInputProps>(
  function TextInput({ className, ...rest }, ref) {
    useFormStyle();
    return <input ref={ref} className={join(FI_FIELD_CONTROL_CLASS, className)} {...rest} />;
  },
);

export type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;

export const TextArea = forwardRef<HTMLTextAreaElement, TextAreaProps>(
  function TextArea({ className, ...rest }, ref) {
    useFormStyle();
    return <textarea ref={ref} className={join(FI_FIELD_CONTROL_CLASS, className)} {...rest} />;
  },
);

export interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  options: SelectOption[];
  /** Rendered as a disabled first entry. Omit it when a value is always set. */
  placeholder?: string;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  function Select({ options, placeholder, className, ...rest }, ref) {
    useFormStyle();
    return (
      <select ref={ref} className={join(FI_FIELD_CONTROL_CLASS, className)} {...rest}>
        {placeholder ? (
          <option value="" disabled>
            {placeholder}
          </option>
        ) : null}
        {options.map((o) => (
          <option key={o.value} value={o.value} disabled={o.disabled}>
            {o.label}
          </option>
        ))}
      </select>
    );
  },
);

export interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  label: ReactNode;
  wrapperClassName?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  function Checkbox({ label, wrapperClassName, className, id, ...rest }, ref) {
    useFormStyle();
    const auto = useId();
    const inputId = id ?? auto;
    return (
      <div className={join(FI_CHECKBOX_CLASS, wrapperClassName)}>
        <input ref={ref} id={inputId} type="checkbox" className={className} {...rest} />
        <label className={FI_CHECKBOX_LABEL_CLASS} htmlFor={inputId}>
          {label}
        </label>
      </div>
    );
  },
);

export interface FieldGridProps {
  children: ReactNode;
  /** Minimum column width before the grid reflows. Default 12rem. */
  minColumn?: string;
  className?: string;
}

export function FieldGrid({ children, minColumn, className }: FieldGridProps) {
  useFormStyle();
  return (
    <div
      className={join(FI_FIELD_GRID_CLASS, className)}
      style={minColumn ? ({ '--fi-field-min': minColumn } as Record<string, string>) : undefined}
    >
      {children}
    </div>
  );
}

export interface FormActionsProps {
  children: ReactNode;
  className?: string;
}

export function FormActions({ children, className }: FormActionsProps) {
  useFormStyle();
  return <div className={join(FI_FORM_ACTIONS_CLASS, className)}>{children}</div>;
}
