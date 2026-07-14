import * as react from 'react';
import { ClipboardEventHandler, CSSProperties, Ref, TextareaHTMLAttributes, ReactNode } from 'react';
import { MessageImage } from '@free-intelligence/core';
export { b as ComposerAction, C as ComposerActions, c as ComposerActionsProps } from '../ComposerActions-HOiu1DmD.js';

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
    /**
     * Paste hook on the textarea (OG118-IMAGE-UPLOAD-1): the surface intercepts
     * pasted image files here (calling `preventDefault` itself); plain-text paste
     * is untouched. Omit for the previous behavior.
     */
    onPaste?: ClipboardEventHandler<HTMLTextAreaElement>;
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
declare function Composer({ message, loading, disabled, placeholder, onMessageChange, onSend, onPaste, maxRows, areaClassName, wrapperClassName, wrapperStyle, textareaClassName, id, name, textareaRef, }: ComposerProps): react.JSX.Element;

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
    /** Accessible label for the compact-mode rail disclosure toggle
     * (CONV-MOBILE-RECLAIM-1). Only rendered when `footerStart` is filled. */
    railToggleLabel?: string;
}
declare function ComposerFrame({ children, header, footer, footerStart, className, style, headerClassName, footerClassName, footerStyle, footerStartClassName, railToggleLabel, }: ComposerFrameProps): react.JSX.Element;

/** Media types the pipeline accepts end-to-end (mirrors the server allowlist). */
declare const COMPOSER_IMAGE_MEDIA_TYPES: readonly ["image/jpeg", "image/png", "image/webp", "image/gif"];
/** Picker filter string for the file input. */
declare const COMPOSER_IMAGE_ACCEPT: string;
/** Default maximum images per message (mirrors the server cap). */
declare const DEFAULT_MAX_IMAGES = 4;
/** One attached image, preview-ready (`dataUrl`) and wire-ready (`data`). */
interface ComposerImageDraft extends MessageImage {
    /** Stable id for chip rendering/removal. */
    id: string;
    /** `data:<mediaType>;base64,<data>` — feed straight into an <img src>. */
    dataUrl: string;
    /** Original file name (chip title/alt). */
    name: string;
}
interface UseComposerImagesOptions {
    /** Max images attachable to one message. Default {@link DEFAULT_MAX_IMAGES}. */
    maxImages?: number;
    /** Surfaced with a human-readable message when a file is rejected. */
    onError?: (message: string) => void;
}
interface ComposerImages {
    /** The images currently attached to the message being composed. */
    drafts: ComposerImageDraft[];
    /** Validate + encode picked/dropped/pasted files into drafts. */
    addFiles: (files: Iterable<File>) => Promise<void>;
    /** Detach one image. */
    remove: (id: string) => void;
    /** Detach all (called by the surface after a send). */
    clear: () => void;
    /** The drafts as wire-ready MessageImages. */
    toMessageImages: () => MessageImage[];
    /** Extract + add image files from a paste event. True if any were taken. */
    handlePaste: (event: {
        clipboardData: DataTransfer | null;
    }) => boolean;
}
declare function useComposerImages(options?: UseComposerImagesOptions): ComposerImages;

interface ComposerImageChipsProps {
    drafts: ComposerImageDraft[];
    onRemove: (id: string) => void;
    /** Disable removal (e.g. while a turn streams). */
    disabled?: boolean;
    className?: string;
    /** aria-label template for a chip's remove button. Default: "Quitar imagen". */
    removeLabel?: string;
}
declare function ComposerImageChips({ drafts, onRemove, disabled, className, removeLabel, }: ComposerImageChipsProps): react.JSX.Element | null;
interface ImagePicker {
    /** Render this anywhere inside the composer — it is the hidden file input. */
    input: ReactNode;
    /** Open the OS file picker (wire it to a ComposerAction's onSelect). */
    open: () => void;
}
/**
 * The image file-picker as a CAPABILITY, not a button: it hands back the hidden
 * input to render and an `open()` for whatever affordance invokes it — today the
 * shared "+" menu (ComposerActions).
 */
declare function useImagePicker(onFiles: (files: File[]) => void): ImagePicker;

export { AutoResizeTextarea, type AutoResizeTextareaProps, COMPOSER_IMAGE_ACCEPT, COMPOSER_IMAGE_MEDIA_TYPES, Composer, ComposerFrame, type ComposerFrameProps, ComposerImageChips, type ComposerImageChipsProps, type ComposerImageDraft, type ComposerImages, type ComposerProps, DEFAULT_MAX_IMAGES, type ImagePicker, type UseComposerImagesOptions, ensureComposerFrameStyle, useComposerFrameStyle, useComposerImages, useImagePicker };
