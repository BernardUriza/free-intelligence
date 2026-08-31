import * as react from 'react';
import { ReactNode } from 'react';

type CalloutTone = 'neutral' | 'danger' | 'warning' | 'success';
interface CalloutProps {
    children: ReactNode;
    tone?: CalloutTone;
    title?: ReactNode;
    /**
     * Announce it the moment it appears. Default: `true` for `danger`.
     * A wrong value the reader is never told about is the failure this guards.
     */
    live?: boolean;
    className?: string;
}
declare function Callout({ children, tone, title, live, className }: CalloutProps): react.JSX.Element;
interface CalloutListProps {
    /** Rendered in the given order, always. Empty renders nothing at all. */
    items: ReactNode[];
    tone?: CalloutTone;
    title?: ReactNode;
    live?: boolean;
    className?: string;
}
declare function CalloutList({ items, tone, title, live, className }: CalloutListProps): react.JSX.Element | null;

declare const FI_CALLOUT_CLASS = "fi-callout";
declare const FI_CALLOUT_TITLE_CLASS = "fi-callout-title";
declare const FI_CALLOUT_BODY_CLASS = "fi-callout-body";
declare const FI_CALLOUT_LIST_CLASS = "fi-callout-list";
/** Inject the idempotent feedback stylesheet (no-op on the server / if already present). */
declare function ensureFeedbackStyle(): void;
/** Ensure the feedback stylesheet is present for the lifetime of the component. */
declare function useFeedbackStyle(): void;

export { Callout, CalloutList, type CalloutListProps, type CalloutProps, type CalloutTone, FI_CALLOUT_BODY_CLASS, FI_CALLOUT_CLASS, FI_CALLOUT_LIST_CLASS, FI_CALLOUT_TITLE_CLASS, ensureFeedbackStyle, useFeedbackStyle };
