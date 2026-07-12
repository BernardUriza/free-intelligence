'use client';

/**
 * fi-glass · ComposerActions — the "+" that opens what you can attach.
 *
 * ONE trigger for every "add something to this turn" capability, instead of one
 * icon button per capability. og118 grew an `ImagePlus` button the day it gained
 * vision; aurity had already grown a `⋮` overflow with "Adjuntar archivo" inside
 * — two composers, two ad-hoc affordances, in a framework whose whole point is
 * that the shell is shared. A composer with N capabilities does not want N
 * buttons crowding the rail: it wants the ChatGPT "+".
 *
 * The menu opens UPWARD (the composer sits at the bottom of the viewport) and is
 * dismissed by Escape, by an outside click, or by choosing an action. Consumers
 * inject the actions; the framework owns the affordance.
 */

import { useEffect, useRef, useState, type ReactNode } from 'react';
import { Plus } from 'lucide-react';

export interface ComposerAction {
  /** Stable id (also the React key). */
  id: string;
  /** What the user reads in the menu ("Adjuntar imagen"). */
  label: string;
  /** Leading icon. */
  icon?: ReactNode;
  onSelect: () => void;
  disabled?: boolean;
}

export interface ComposerActionsProps {
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

export function ComposerActions({
  actions,
  disabled = false,
  label = 'Añadir',
  className,
  iconClassName,
  menuClassName,
  itemClassName,
}: ComposerActionsProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    const onClick = (e: MouseEvent) => {
      if (!rootRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onClick);
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onClick);
    };
  }, [open]);

  if (actions.length === 0) return null;

  return (
    <div ref={rootRef} style={{ position: 'relative', display: 'inline-flex' }}>
      <button
        type="button"
        aria-label={label}
        title={label}
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className={`fi-touch-target ${className ?? ''}`.trim()}
        data-fi-composer-actions=""
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'transparent',
          border: 'none',
          cursor: disabled ? 'default' : 'pointer',
          opacity: disabled ? 0.5 : 1,
          padding: '0.375rem',
          color: 'inherit',
        }}
      >
        <Plus size={18} aria-hidden className={iconClassName} />
      </button>

      {open && (
        <div
          role="menu"
          data-fi-composer-actions-menu=""
          className={menuClassName}
          style={
            menuClassName
              ? { position: 'absolute', bottom: '100%', left: 0, zIndex: 20 }
              : {
                  position: 'absolute',
                  bottom: '100%',
                  left: 0,
                  marginBottom: '0.5rem',
                  zIndex: 20,
                  minWidth: '13rem',
                  padding: '0.35rem',
                  borderRadius: 12,
                  border: '1px solid rgba(255,255,255,0.12)',
                  background: 'rgba(15,23,42,0.98)',
                  boxShadow: '0 12px 32px rgba(0,0,0,0.45)',
                }
          }
        >
          {actions.map((action) => (
            <button
              key={action.id}
              type="button"
              role="menuitem"
              disabled={action.disabled}
              onClick={() => {
                setOpen(false);
                action.onSelect();
              }}
              className={itemClassName}
              style={
                itemClassName
                  ? undefined
                  : {
                      display: 'flex',
                      alignItems: 'center',
                      gap: '0.6rem',
                      width: '100%',
                      padding: '0.5rem 0.65rem',
                      borderRadius: 8,
                      border: 'none',
                      background: 'transparent',
                      color: action.disabled ? '#64748b' : '#e2e8f0',
                      fontSize: '0.875rem',
                      textAlign: 'left',
                      cursor: action.disabled ? 'default' : 'pointer',
                    }
              }
            >
              {action.icon}
              <span>{action.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
