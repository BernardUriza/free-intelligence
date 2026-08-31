'use client';

/**
 * fi-glass · a button.
 *
 * The package had none. Every consumer wrote `<button className="og-...-cta">`
 * with its own gradient, which meant the primary action of one surface and the
 * primary action of the next agreed only by accident.
 *
 * `type` defaults to `button`, not `submit`. The HTML default is `submit`, and
 * inside a form that turns every unmarked button into an accidental submit —
 * the bug is silent, common, and lands as a document sent before it was ready.
 */

import { forwardRef, type ButtonHTMLAttributes } from 'react';
import {
  FI_BUTTON_CLASS,
  FI_BUTTON_DANGER_CLASS,
  FI_BUTTON_QUIET_CLASS,
  useFormStyle,
} from './formStyle';

export type ButtonTone = 'primary' | 'quiet' | 'danger';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  tone?: ButtonTone;
}

const TONE: Record<ButtonTone, string> = {
  primary: '',
  quiet: FI_BUTTON_QUIET_CLASS,
  danger: FI_BUTTON_DANGER_CLASS,
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { tone = 'primary', className, type, ...rest },
  ref,
) {
  useFormStyle();
  const classes = [FI_BUTTON_CLASS, TONE[tone], className].filter(Boolean).join(' ');
  return <button ref={ref} type={type ?? 'button'} className={classes} {...rest} />;
});
