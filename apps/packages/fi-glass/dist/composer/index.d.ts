import * as react from 'react';
import { CSSProperties, TextareaHTMLAttributes } from 'react';

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
    /** Inline style for the input wrapper (e.g. flex-grow so it fills the area). */
    wrapperStyle?: CSSProperties;
    /** Class for the <textarea> itself */
    textareaClassName?: string;
}
declare function Composer({ message, loading, placeholder, onMessageChange, onSend, maxRows, areaClassName, wrapperClassName, wrapperStyle, textareaClassName, }: ComposerProps): react.JSX.Element;

interface AutoResizeTextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
    /** Max rows before scrolling */
    maxRows?: number;
    /** Show character counter */
    showCounter?: boolean;
    /** Max characters */
    maxLength?: number;
    /** Additional wrapper CSS classes */
    wrapperClassName?: string;
    /**
     * Inline style for the wrapper div. Lets the Composer/surface own the input's
     * layout (e.g. `flex: 1 1 0%` so it fills a flex composer) WITHOUT a consumer
     * reaching into the internal `.relative` wrapper from CSS.
     */
    wrapperStyle?: CSSProperties;
}
declare function AutoResizeTextarea({ value, onChange, maxRows, showCounter, maxLength, wrapperClassName, wrapperStyle, className, ...props }: AutoResizeTextareaProps): react.JSX.Element;

export { AutoResizeTextarea, type AutoResizeTextareaProps, Composer, type ComposerProps };
