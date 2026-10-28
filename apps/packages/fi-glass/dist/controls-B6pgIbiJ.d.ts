import * as react from 'react';
import { ReactNode, ButtonHTMLAttributes, Ref } from 'react';
import { LucideIcon } from 'lucide-react';

type AdminButtonVariant = 'default' | 'primary' | 'ghost' | 'danger';
type AdminButtonTone = 'danger' | 'on' | 'off' | 'secondary';
type AdminButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
    variant?: AdminButtonVariant;
    tone?: AdminButtonTone;
    icon?: LucideIcon;
    loading?: boolean;
    iconOnly?: boolean;
};
declare function AdminButton({ variant, tone, icon: Icon, loading, iconOnly, className, children, ...rest }: AdminButtonProps): react.JSX.Element;
declare function AdminAlert({ children, action }: {
    children: ReactNode;
    action?: ReactNode;
}): react.JSX.Element;
interface AdminSheetProps {
    onDismiss: () => void;
    labelledBy: string;
    /** 'center' is a dialog; 'side' a slide-over. Both become a full sheet on mobile. */
    placement?: 'center' | 'side';
    /** The module's root class, so its own fields and cards style inside the sheet. */
    className?: string;
    header: ReactNode;
    footer?: ReactNode;
    bodyRef?: Ref<HTMLDivElement>;
    children: ReactNode;
}
declare function AdminSheet({ onDismiss, labelledBy, placement, className, header, footer, bodyRef, children, }: AdminSheetProps): react.JSX.Element;

export { AdminAlert as A, AdminButton as a, AdminSheet as b, type AdminButtonProps as c, type AdminButtonTone as d, type AdminButtonVariant as e, type AdminSheetProps as f };
