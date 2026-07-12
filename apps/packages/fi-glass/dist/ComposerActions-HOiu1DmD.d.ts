import * as react from 'react';
import { ReactNode } from 'react';

interface MenuAction {
    /** Stable id (also the React key). */
    id: string;
    /** What the user reads ("Adjuntar archivo"). */
    label: string;
    icon?: ReactNode;
    onSelect: () => void;
    disabled?: boolean;
    /**
     * Dress for THIS item — aurity paints its destructive and dev-tool entries
     * differently (`chat-dropdown-item-danger`, the amber curl one). Falls back to
     * the menu's `itemClassName`.
     */
    className?: string;
    /** Rule above the item (aurity's `chat-dropdown-divider`). */
    dividerBefore?: boolean;
    /**
     * Class on a wrapper around the item — aurity gates two entries to the compact
     * layout with `@md:hidden` (they have their own buttons when there is room).
     */
    wrapperClassName?: string;
}
interface ActionMenuProps {
    actions: MenuAction[];
    /** The trigger's content — aurity passes `⋮`, the composer passes `+`. */
    trigger: ReactNode;
    /** aria-label/title of the trigger. */
    triggerLabel: string;
    triggerClassName?: string;
    /** Inline dress for the trigger (unstyled consumers). Deliberately unannotated:
     *  CI resolves two csstype versions and a typed CSSProperties clashes. */
    triggerStyle?: Record<string, unknown>;
    disabled?: boolean;
    /** Dress for the dropdown. aurity passes `chat-dropdown`. */
    menuClassName?: string;
    /** Dress for each item. aurity passes `chat-dropdown-item`. */
    itemClassName?: string;
    /** Dress for a divider. aurity passes `chat-dropdown-divider`. */
    dividerClassName?: string;
    /** Marks the trigger for tests/consumers (e.g. `data-fi-composer-actions`). */
    triggerAttribute?: string;
}
declare function ActionMenu({ actions, trigger, triggerLabel, triggerClassName, triggerStyle, disabled, menuClassName, itemClassName, dividerClassName, triggerAttribute, }: ActionMenuProps): react.JSX.Element | null;

type ComposerAction = MenuAction;
interface ComposerActionsProps {
    actions: ComposerAction[];
    /** Disable the trigger (a turn is streaming, the composer is disabled). */
    disabled?: boolean;
    /** aria-label/title of the trigger. Default: "Añadir". */
    label?: string;
    className?: string;
    iconClassName?: string;
    menuClassName?: string;
    itemClassName?: string;
}
declare function ComposerActions({ actions, disabled, label, className, iconClassName, menuClassName, itemClassName, }: ComposerActionsProps): react.JSX.Element;

export { ActionMenu as A, ComposerActions as C, type MenuAction as M, type ActionMenuProps as a, type ComposerAction as b, type ComposerActionsProps as c };
