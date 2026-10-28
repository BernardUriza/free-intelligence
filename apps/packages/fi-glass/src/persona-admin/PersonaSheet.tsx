'use client';

import { useEffect, type ReactNode } from 'react';
import { FI_PERSONA_ROOT_CLASS, usePersonaAdminStyle } from './personaAdminStyle';

export interface PersonaSheetProps {
  onDismiss: () => void;
  labelledBy: string;
  /** 'center' is a dialog; 'side' a slide-over. Both become a full sheet on mobile. */
  placement?: 'center' | 'side';
  header: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
}

export function PersonaSheet({ onDismiss, labelledBy, placement = 'center', header, footer, children }: PersonaSheetProps) {
  usePersonaAdminStyle();
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onDismiss();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onDismiss]);

  return (
    <div className={`${FI_PERSONA_ROOT_CLASS} fi-persona-overlay`} data-placement={placement}>
      <div className="fi-persona-backdrop" onClick={onDismiss} aria-hidden="true" />
      <div className="fi-persona-sheet" role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
        <div className="fi-persona-sheet-head">{header}</div>
        <div className="fi-persona-sheet-body">{children}</div>
        {footer ? <div className="fi-persona-sheet-foot">{footer}</div> : null}
      </div>
    </div>
  );
}
