import * as react_jsx_runtime from 'react/jsx-runtime';
import { TextareaHTMLAttributes } from 'react';

interface ComposerProps {
    /** Current message value */
    message: string;
    /** Is sending message (disables input) */
    loading?: boolean;
    /** Placeholder text */
    placeholder?: string;
    /** Called on every edit */
    onMessageChange: (value: string) => void;
    /** Called on Enter (without Shift) */
    onSend: () => void;
    /** Max rows before the textarea scrolls */
    maxRows?: number;
    /** Class for the outer area wrapper */
    areaClassName?: string;
    /** Class for the AutoResizeTextarea wrapper */
    wrapperClassName?: string;
    /** Class for the <textarea> itself */
    textareaClassName?: string;
}
declare function Composer({ message, loading, placeholder, onMessageChange, onSend, maxRows, areaClassName, wrapperClassName, textareaClassName, }: ComposerProps): react_jsx_runtime.JSX.Element;

interface AutoResizeTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
    /** Max rows before scrolling */
    maxRows?: number;
    /** Show character counter */
    showCounter?: boolean;
    /** Max characters */
    maxLength?: number;
    /** Additional wrapper CSS classes */
    wrapperClassName?: string;
}
declare function AutoResizeTextarea({ value, onChange, maxRows, showCounter, maxLength, wrapperClassName, className, ...props }: AutoResizeTextareaProps): react_jsx_runtime.JSX.Element;

export { AutoResizeTextarea, type AutoResizeTextareaProps, Composer, type ComposerProps };
