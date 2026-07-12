import * as react from 'react';
import { ReactNode } from 'react';

interface ComposerAction {
    /** Stable id (also the React key). */
    id: string;
    /** What the user reads in the menu ("Adjuntar imagen"). */
    label: string;
    /** Leading icon. */
    icon?: ReactNode;
    onSelect: () => void;
    disabled?: boolean;
}
interface ComposerActionsProps {
    actions: ComposerAction[];
    /** Disable the whole trigger (streaming, composer disabled). */
    disabled?: boolean;
    /** aria-label/title of the trigger. Default: "Añadir". */
    label?: string;
    className?: string;
    iconClassName?: string;
    menuClassName?: string;
    itemClassName?: string;
}
declare function ComposerActions({ actions, disabled, label, className, iconClassName, menuClassName, itemClassName, }: ComposerActionsProps): react.JSX.Element | null;

export { ComposerActions as C, type ComposerAction as a, type ComposerActionsProps as b };
