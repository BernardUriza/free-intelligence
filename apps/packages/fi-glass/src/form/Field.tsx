'use client';

/**
 * fi-glass · one labelled control.
 *
 * The whole point of this component is the wiring a hand-written `<input>`
 * almost never gets right: the label points at the control, the hint and the
 * error are announced with it through `aria-describedby`, and an invalid field
 * says so to a screen reader and not only in red. Those three connections are
 * why a form primitive exists at all — the border colour is the least of it.
 *
 * It renders its control through a child function so it stays honest about what
 * it does NOT own: the value, the change handler and the element type belong to
 * the consumer. `Field` owns the label, the ids and the announcement.
 */

import { useId, type ReactNode } from 'react';
import {
  FI_FIELD_CLASS,
  FI_FIELD_ERROR_CLASS,
  FI_FIELD_HINT_CLASS,
  FI_FIELD_LABEL_CLASS,
  useFormStyle,
} from './formStyle';

export interface FieldControlProps {
  id: string;
  'aria-describedby': string | undefined;
  'aria-invalid': boolean | undefined;
  'aria-required': boolean | undefined;
}

export interface FieldProps {
  label: ReactNode;
  /** Receives the ids and aria state to spread onto the control. */
  children: (control: FieldControlProps) => ReactNode;
  /** Guidance shown under the control. Announced with it. */
  hint?: ReactNode;
  /** When present the control is marked invalid and this is announced. */
  error?: ReactNode;
  /** Marks the control required, visually and for assistive tech. */
  required?: boolean;
  className?: string;
}

export function Field({ label, children, hint, error, required, className }: FieldProps) {
  useFormStyle();
  const base = useId();
  const controlId = `${base}-control`;
  const hintId = hint ? `${base}-hint` : undefined;
  const errorId = error ? `${base}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(' ') || undefined;

  return (
    <div className={className ? `${FI_FIELD_CLASS} ${className}` : FI_FIELD_CLASS}>
      {/* The asterisk is drawn by CSS from `data-required`, not rendered as a
          node. Inside the label it becomes part of the label's TEXT, and every
          consumer test that asks for `getByLabelText('Nombre')` then fails on a
          decoration. Real assistive tech reads `aria-required` on the control;
          the mark is for eyes only, and CSS is where eyes-only things belong. */}
      <label
        className={FI_FIELD_LABEL_CLASS}
        htmlFor={controlId}
        data-required={required || undefined}
      >
        {label}
      </label>
      {children({
        id: controlId,
        'aria-describedby': describedBy,
        'aria-invalid': error ? true : undefined,
        'aria-required': required || undefined,
      })}
      {hint ? (
        <span className={FI_FIELD_HINT_CLASS} id={hintId}>
          {hint}
        </span>
      ) : null}
      {/* `role="alert"` and not just red text: an error nobody is told about is
          an error only sighted users have. */}
      {error ? (
        <span className={FI_FIELD_ERROR_CLASS} id={errorId} role="alert">
          {error}
        </span>
      ) : null}
    </div>
  );
}
