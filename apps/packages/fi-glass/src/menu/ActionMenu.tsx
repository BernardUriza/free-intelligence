'use client';

/**
 * fi-glass · ActionMenu — the framework's ONE menu, extracted from aurity.
 *
 * aurity is the SSOT of this framework: its chat toolbar has always opened its
 * actions ("Adjuntar archivo", "Cambiar idioma", …) from a trigger that portals
 * a dropdown to `document.body`, positions it off the trigger's rect and opens it
 * UPWARD — because the composer lives at the bottom of the viewport and an
 * in-flow menu would be clipped by the composer's `overflow: hidden`.
 *
 * That anatomy was hand-written inside ChatToolbar, so when og118's composer grew
 * its own actions it could not reuse it and grew a second, incompatible menu. The
 * duplication is the bug. This is aurity's menu, lifted verbatim into the
 * framework so BOTH surfaces render the same thing:
 *
 *   - aurity's shell toolbar → trigger `⋮`, dressed with its own `chat-dropdown`
 *     CSS (the classNames it already used — nothing about it changes).
 *   - og118's composer      → trigger `+`, using the built-in styling.
 *
 * The anatomy (portal, positioning, upward opening, backdrop, dismissal) belongs
 * to the framework; the trigger icon and the dress belong to the consumer.
 */

import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

export interface MenuAction {
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

export interface ActionMenuProps {
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

export function ActionMenu({
  actions,
  trigger,
  triggerLabel,
  triggerClassName,
  triggerStyle,
  disabled = false,
  menuClassName,
  itemClassName,
  dividerClassName,
  triggerAttribute,
}: ActionMenuProps) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  // aurity's positioning, unchanged: anchor to the trigger's rect, 8px above it,
  // and let the menu grow upward (transform below).
  useEffect(() => {
    if (open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPosition({ top: rect.top - 8, left: rect.left });
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [open]);

  if (actions.length === 0) return null;

  const triggerProps = triggerAttribute ? { [triggerAttribute]: '' } : {};

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={triggerClassName}
        style={triggerStyle as never}
        title={triggerLabel}
        aria-label={triggerLabel}
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={disabled}
        {...triggerProps}
      >
        {trigger}
      </button>

      {open &&
        typeof document !== 'undefined' &&
        createPortal(
          <>
            {/* Backdrop: an outside click dismisses (aurity's pattern). */}
            <div
              className="fixed inset-0 z-[9998]"
              onClick={() => setOpen(false)}
              aria-hidden="true"
            />
            <div
              role="menu"
              data-fi-action-menu=""
              className={menuClassName}
              style={{
                position: 'fixed',
                top: position.top,
                left: position.left,
                // Grow UPWARD from the anchor — the composer is at the bottom.
                transform: 'translateY(-100%)',
                zIndex: 9999,
                ...(menuClassName
                  ? {}
                  : {
                      minWidth: '13rem',
                      padding: '0.35rem',
                      borderRadius: 12,
                      border: '1px solid rgba(255,255,255,0.12)',
                      background: 'rgba(15,23,42,0.98)',
                      boxShadow: '0 12px 32px rgba(0,0,0,0.45)',
                    }),
              }}
            >
              {actions.map((action) => {
                const item = (
                  <button
                    key={action.id}
                    type="button"
                    role="menuitem"
                    disabled={action.disabled}
                    onClick={() => {
                      setOpen(false);
                      action.onSelect();
                    }}
                    className={action.className ?? itemClassName}
                    style={
                      action.className ?? itemClassName
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
                );
                const divider = action.dividerBefore ? (
                  <div
                    className={dividerClassName}
                    style={
                      dividerClassName
                        ? undefined
                        : { height: 1, margin: '0.25rem 0', background: 'rgba(255,255,255,0.08)' }
                    }
                  />
                ) : null;
                // A gated entry (aurity's `@md:hidden`) carries its divider inside
                // the wrapper, so hiding the item hides its rule too.
                return action.wrapperClassName ? (
                  <div key={action.id} className={action.wrapperClassName}>
                    {divider}
                    {item}
                  </div>
                ) : (
                  <Fragment key={action.id}>
                    {divider}
                    {item}
                  </Fragment>
                );
              })}
            </div>
          </>,
          document.body,
        )}
    </>
  );
}
