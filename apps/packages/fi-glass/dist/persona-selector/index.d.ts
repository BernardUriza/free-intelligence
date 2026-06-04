import * as react_jsx_runtime from 'react/jsx-runtime';
import { ReactNode } from 'react';

interface PersonaSlotContext {
    /** Whether the persona this slot renders is the selected one. */
    selected: boolean;
}
interface PersonaSelectorProps<T> {
    /** Available personas (opaque to fi-glass). */
    personas: T[];
    /** Currently selected persona id. */
    selected: string;
    /** Called with the chosen persona id. */
    onSelect: (personaId: string) => void;
    /** How to read the stable id off a persona. */
    getPersonaId: (persona: T) => string;
    /** Loading state — renders renderLoading() (or a minimal default). */
    loading?: boolean;
    /** The persona label shown in the option row. */
    getPersonaLabel?: (persona: T) => ReactNode;
    /** Optional description line under the label. */
    getPersonaDescription?: (persona: T) => ReactNode;
    /** Leading icon for the option row. Receives `{ selected }` for state color. */
    renderPersonaIcon?: (persona: T, ctx: PersonaSlotContext) => ReactNode;
    /** Badge (e.g. model · voice) for the option row. */
    renderPersonaBadge?: (persona: T, ctx: PersonaSlotContext) => ReactNode;
    /** Metadata chips row (e.g. temp / tokens). */
    renderPersonaMeta?: (persona: T) => ReactNode;
    /** The trigger's inner content (before the chevron). Defaults to placeholder. */
    renderTriggerValue?: (selected: T | undefined, isOpen: boolean) => ReactNode;
    /** Dropdown header (e.g. title + count). */
    renderHeader?: (ctx: {
        count: number;
    }) => ReactNode;
    /** Dropdown footer (e.g. an "edit personas" link). `close()` shuts the menu. */
    renderFooter?: (ctx: {
        close: () => void;
    }) => ReactNode;
    /** Loading-state renderer (default: minimal text). */
    renderLoading?: () => ReactNode;
    /** Trigger content when nothing is selected and no renderTriggerValue given. */
    placeholder?: ReactNode;
    /** Root wrapper class. */
    className?: string;
    /** Trigger button class — pass the exact legacy string for byte-identical look. */
    triggerClassName?: string;
    /** Extra class appended to the portalled content panel. */
    contentClassName?: string;
    /** Accessible label for the trigger. */
    ariaLabel?: string;
}
declare function PersonaSelector<T>({ personas, selected, onSelect, getPersonaId, loading, getPersonaLabel, getPersonaDescription, renderPersonaIcon, renderPersonaBadge, renderPersonaMeta, renderTriggerValue, renderHeader, renderFooter, renderLoading, placeholder, className, triggerClassName, contentClassName, ariaLabel, }: PersonaSelectorProps<T>): react_jsx_runtime.JSX.Element;

export { PersonaSelector, type PersonaSelectorProps, type PersonaSlotContext };
