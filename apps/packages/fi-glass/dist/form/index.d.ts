import * as react from 'react';
import { ReactNode, ButtonHTMLAttributes, InputHTMLAttributes, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react';

interface FieldControlProps {
    id: string;
    'aria-describedby': string | undefined;
    'aria-invalid': boolean | undefined;
    'aria-required': boolean | undefined;
}
interface FieldProps {
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
declare function Field({ label, children, hint, error, required, className }: FieldProps): react.JSX.Element;

type ButtonTone = 'primary' | 'quiet' | 'danger';
interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    tone?: ButtonTone;
}
declare const Button: react.ForwardRefExoticComponent<ButtonProps & react.RefAttributes<HTMLButtonElement>>;

type TextInputProps = InputHTMLAttributes<HTMLInputElement>;
declare const TextInput: react.ForwardRefExoticComponent<TextInputProps & react.RefAttributes<HTMLInputElement>>;
type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement>;
declare const TextArea: react.ForwardRefExoticComponent<TextAreaProps & react.RefAttributes<HTMLTextAreaElement>>;
interface SelectOption {
    value: string;
    label: string;
    disabled?: boolean;
}
interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
    options: SelectOption[];
    /** Rendered as a disabled first entry. Omit it when a value is always set. */
    placeholder?: string;
}
declare const Select: react.ForwardRefExoticComponent<SelectProps & react.RefAttributes<HTMLSelectElement>>;
interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
    label: ReactNode;
    wrapperClassName?: string;
}
declare const Checkbox: react.ForwardRefExoticComponent<CheckboxProps & react.RefAttributes<HTMLInputElement>>;
interface FieldGridProps {
    children: ReactNode;
    /** Minimum column width before the grid reflows. Default 12rem. */
    minColumn?: string;
    className?: string;
}
declare function FieldGrid({ children, minColumn, className }: FieldGridProps): react.JSX.Element;
interface FormActionsProps {
    children: ReactNode;
    className?: string;
}
declare function FormActions({ children, className }: FormActionsProps): react.JSX.Element;

declare const FI_FIELD_CLASS = "fi-field";
declare const FI_FIELD_LABEL_CLASS = "fi-field-label";
declare const FI_FIELD_CONTROL_CLASS = "fi-field-control";
declare const FI_FIELD_HINT_CLASS = "fi-field-hint";
declare const FI_FIELD_ERROR_CLASS = "fi-field-error";
declare const FI_FIELD_GRID_CLASS = "fi-field-grid";
declare const FI_CHECKBOX_CLASS = "fi-field-checkbox";
declare const FI_CHECKBOX_LABEL_CLASS = "fi-field-checkbox-label";
declare const FI_FORM_ACTIONS_CLASS = "fi-form-actions";
declare const FI_BUTTON_CLASS = "fi-button";
declare const FI_BUTTON_QUIET_CLASS = "fi-button-quiet";
declare const FI_BUTTON_DANGER_CLASS = "fi-button-danger";
/** Inject the idempotent form stylesheet (no-op on the server / if already present). */
declare function ensureFormStyle(): void;
/** Ensure the form stylesheet is present for the lifetime of the component. */
declare function useFormStyle(): void;

export { Button, type ButtonProps, type ButtonTone, Checkbox, type CheckboxProps, FI_BUTTON_CLASS, FI_BUTTON_DANGER_CLASS, FI_BUTTON_QUIET_CLASS, FI_CHECKBOX_CLASS, FI_CHECKBOX_LABEL_CLASS, FI_FIELD_CLASS, FI_FIELD_CONTROL_CLASS, FI_FIELD_ERROR_CLASS, FI_FIELD_GRID_CLASS, FI_FIELD_HINT_CLASS, FI_FIELD_LABEL_CLASS, FI_FORM_ACTIONS_CLASS, Field, type FieldControlProps, FieldGrid, type FieldGridProps, type FieldProps, FormActions, type FormActionsProps, Select, type SelectOption, type SelectProps, TextArea, type TextAreaProps, TextInput, type TextInputProps, ensureFormStyle, useFormStyle };
