import * as react from 'react';
import { CSSProperties, Ref, TextareaHTMLAttributes } from 'react';

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
    /**
     * Optional stable id for the inner <textarea> (B3-FIGLASS-A11Y-1). Omit it and
     * the textarea self-generates an accessible default — pass one only when the
     * app needs a predictable handle (label `for=`, autofill, tests).
     */
    id?: string;
    /** Optional stable name for the inner <textarea> (B3-FIGLASS-A11Y-1). */
    name?: string;
    /**
     * Typed ref to the inner <textarea> (B3-FIGLASS-10) so the owner can manage
     * focus (e.g. refocus after dictation/send/stream) without touching DOM
     * internals.
     */
    textareaRef?: Ref<HTMLTextAreaElement>;
}
declare function Composer({ message, loading, placeholder, onMessageChange, onSend, maxRows, areaClassName, wrapperClassName, wrapperStyle, textareaClassName, id, name, textareaRef, }: ComposerProps): react.JSX.Element;

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
/**
 * Forwards its ref to the inner <textarea> (B3-FIGLASS-10) so an owner (e.g. the
 * conversation surface) can manage focus through a TYPED handle instead of
 * reaching into this component's internal DOM.
 */
declare const AutoResizeTextarea: react.ForwardRefExoticComponent<AutoResizeTextareaProps & react.RefAttributes<HTMLTextAreaElement>>;

export { AutoResizeTextarea, type AutoResizeTextareaProps, Composer, type ComposerProps };
