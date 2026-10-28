'use client';

import { useEffect, type ButtonHTMLAttributes, type ReactNode, type Ref } from 'react';
import { AlertCircle, Loader2, type LucideIcon } from 'lucide-react';
import { withTouchTarget } from '../shell/touchTarget';
import { useAdminKitStyle } from './adminKitStyle';

export type AdminButtonVariant = 'default' | 'primary' | 'ghost' | 'danger';
export type AdminButtonTone = 'danger' | 'on' | 'off' | 'secondary';

export type AdminButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: AdminButtonVariant;
  tone?: AdminButtonTone;
  icon?: LucideIcon;
  loading?: boolean;
  iconOnly?: boolean;
};

export function AdminButton({
  variant = 'default',
  tone,
  icon: Icon,
  loading = false,
  iconOnly = false,
  className,
  children,
  ...rest
}: AdminButtonProps) {
  useAdminKitStyle();
  const LeadIcon = loading ? Loader2 : Icon;
  return (
    <button
      type="button"
      {...rest}
      className={withTouchTarget(className ? `fi-admin-btn ${className}` : 'fi-admin-btn')}
      data-variant={variant}
      data-tone={tone}
      data-icon-only={iconOnly ? '' : undefined}
    >
      {LeadIcon ? <LeadIcon size={16} aria-hidden="true" className={loading ? 'fi-admin-spin' : undefined} /> : null}
      {children}
    </button>
  );
}

export function AdminAlert({ children, action }: { children: ReactNode; action?: ReactNode }) {
  useAdminKitStyle();
  return (
    <div className="fi-admin-alert" role="alert">
      <AlertCircle size={18} aria-hidden="true" />
      <span>{children}</span>
      {action}
    </div>
  );
}

export interface AdminSheetProps {
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

export function AdminSheet({
  onDismiss,
  labelledBy,
  placement = 'center',
  className,
  header,
  footer,
  bodyRef,
  children,
}: AdminSheetProps) {
  useAdminKitStyle();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onDismiss]);

  return (
    <div className={className ? `fi-admin-overlay ${className}` : 'fi-admin-overlay'} data-placement={placement}>
      <div className="fi-admin-backdrop" onClick={onDismiss} aria-hidden="true" />
      <div className="fi-admin-sheet" role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
        <div className="fi-admin-sheet-head">{header}</div>
        <div className="fi-admin-sheet-body" ref={bodyRef}>
          {children}
        </div>
        {footer ? <div className="fi-admin-sheet-foot">{footer}</div> : null}
      </div>
    </div>
  );
}
