import * as react from 'react';
import { CSSProperties, Ref, TextareaHTMLAttributes, ReactNode } from 'react';

interface ComposerProps {
    /** Current message value */
    message: string;
    /**
     * A turn is streaming. Blocks SUBMIT (Enter is a no-op) so a second turn
     * can't fire, but NEVER blocks editing — the user keeps typing the next
     * message while the assistant responds (ChatGPT parity, B3-FIGLASS-COMPOSER-FOCUS-1).
     */
    loading?: boolean;
    /**
     * Genuinely disable EDITING (auth blocked, readonly, quota/capacity, terminal
     * error) — this is the only state that sets the <textarea> disabled and lets
     * the browser drop focus. Streaming is `loading`, not `disabled`.
     */
    disabled?: boolean;
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
declare function Composer({ message, loading, disabled, placeholder, onMessageChange, onSend, maxRows, areaClassName, wrapperClassName, wrapperStyle, textareaClassName, id, name, textareaRef, }: ComposerProps): react.JSX.Element;

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

/** Inject the idempotent composer-frame stylesheet (no-op on the server / if already present). */
declare function ensureComposerFrameStyle(): void;
/** Ensure the composer-frame stylesheet is present for the lifetime of the component. */
declare function useComposerFrameStyle(): void;
interface ComposerFrameProps {
    /** The body — the textarea row. Rendered directly (no wrapper element). */
    children: ReactNode;
    /** Optional header slot — previews/drafts above the body (e.g. an audio draft). */
    header?: ReactNode;
    /** Optional footer slot — the controls row below the body (chips, mic, send). */
    footer?: ReactNode;
    /**
     * Optional footer LEFT rail — tool chips (model/persona, attach, call). Claims
     * the left with `margin-right: auto`; omit it and the footer is unchanged.
     */
    footerStart?: ReactNode;
    /** Class for the single container (the consumer's frosted box preset). */
    className?: string;
    style?: CSSProperties;
    headerClassName?: string;
    footerClassName?: string;
    footerStyle?: CSSProperties;
    footerStartClassName?: string;
}
declare function ComposerFrame({ children, header, footer, footerStart, className, style, headerClassName, footerClassName, footerStyle, footerStartClassName, }: ComposerFrameProps): react.JSX.Element;

export { AutoResizeTextarea, type AutoResizeTextareaProps, Composer, ComposerFrame, type ComposerFrameProps, type ComposerProps, ensureComposerFrameStyle, useComposerFrameStyle };
