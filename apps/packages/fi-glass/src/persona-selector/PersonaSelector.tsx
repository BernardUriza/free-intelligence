'use client';

/**
 * fi-glass · PersonaSelector — Californio (element 98), configurable optional.
 *
 * A generic, accessible single-select dropdown for choosing a "persona" (or any
 * keyed entity). fi-glass OWNS the dropdown behavior — open/close, click-outside,
 * portal positioning with flip-up, keyboard navigation (Arrow/Enter/Space),
 * focus-on-open, and full ARIA (listbox/option/aria-selected/aria-expanded). That
 * behavior is generic, not domain — it belongs to the framework, the same way the
 * clipboard logic belongs to <CopyButton>.
 *
 * The mechanics here are LIFTED from aurity's proven `components/ui/select.tsx`
 * (the same code, battle-tested in production), decoupled from its two domain
 * deps: the `Button` component (→ plain <button>) and `select-configs` badge
 * palette (→ injected via the renderPersonaBadge slot). No new accessibility
 * dependency is added — the monorepo ships none, and a downloadable framework
 * should not force Radix/React-Aria onto every consumer (og118 charter).
 *
 * DOMAIN stays in the app, injected by slot:
 *  - icons, badges, model metadata → render* slots (each gets `{ selected }`)
 *  - the persona's label/description → getPersonaLabel / getPersonaDescription
 *  - the header copy + the "edit personas" link → renderHeader / renderFooter
 *
 * CONFIGURABILITY (fire test): an app restyles via *ClassName props, relabels via
 * the render slots, or drops a section (omit the slot) — all without touching
 * fi-glass. `<T>` is opaque; the only thing fi-glass reads is the id via
 * getPersonaId.
 */

import {
  useCallback,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from 'react';
import { createPortal } from 'react-dom';
import { ChevronDown, Check } from 'lucide-react';

export interface PersonaSlotContext {
  /** Whether the persona this slot renders is the selected one. */
  selected: boolean;
}

export interface PersonaSelectorProps<T> {
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

  // ── Item slots (domain) ──────────────────────────────────────────────────
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

  // ── Container slots (domain) ─────────────────────────────────────────────
  /** The trigger's inner content (before the chevron). Defaults to placeholder. */
  renderTriggerValue?: (selected: T | undefined, isOpen: boolean) => ReactNode;
  /** Dropdown header (e.g. title + count). */
  renderHeader?: (ctx: { count: number }) => ReactNode;
  /** Dropdown footer (e.g. an "edit personas" link). `close()` shuts the menu. */
  renderFooter?: (ctx: { close: () => void }) => ReactNode;
  /** Loading-state renderer (default: minimal text). */
  renderLoading?: () => ReactNode;

  /** Trigger content when nothing is selected and no renderTriggerValue given. */
  placeholder?: ReactNode;

  // ── Styling hooks (app keeps its CSS) ────────────────────────────────────
  /** Root wrapper class. */
  className?: string;
  /** Trigger button class — pass the exact legacy string for byte-identical look. */
  triggerClassName?: string;
  /** Extra class appended to the portalled content panel. */
  contentClassName?: string;
  /** Accessible label for the trigger. */
  ariaLabel?: string;
}

const TRIGGER_DEFAULT =
  'flex w-full items-center justify-between rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm transition-colors';
const CONTENT_BASE =
  'rounded-md border border-slate-700 bg-slate-800 p-1 shadow-lg';
const ITEM_BASE = 'cursor-pointer rounded-lg px-3 py-2 text-left transition-all';

export function PersonaSelector<T>({
  personas,
  selected,
  onSelect,
  getPersonaId,
  loading = false,
  getPersonaLabel,
  getPersonaDescription,
  renderPersonaIcon,
  renderPersonaBadge,
  renderPersonaMeta,
  renderTriggerValue,
  renderHeader,
  renderFooter,
  renderLoading,
  placeholder = 'Seleccionar...',
  className = 'relative',
  triggerClassName,
  contentClassName = '',
  ariaLabel,
}: PersonaSelectorProps<T>) {
  const [isOpen, setIsOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0, width: 0 });
  const triggerRef = useRef<HTMLButtonElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const reactId = useId();
  const triggerId = `persona-trigger-${reactId}`;
  const contentId = `persona-content-${reactId}`;

  const close = useCallback(() => setIsOpen(false), []);

  // Close on outside click (mousedown, matches aurity's Select).
  useEffect(() => {
    if (!isOpen) return;
    const handle = (event: MouseEvent) => {
      const target = event.target as Node;
      if (
        triggerRef.current?.contains(target) ||
        contentRef.current?.contains(target)
      ) {
        return;
      }
      setIsOpen(false);
    };
    document.addEventListener('mousedown', handle);
    return () => document.removeEventListener('mousedown', handle);
  }, [isOpen]);

  // Portal positioning with flip-up when there's no room below.
  useEffect(() => {
    if (!isOpen) return;
    const trigger = triggerRef.current;
    if (!trigger) return;

    const rect = trigger.getBoundingClientRect();
    const baseTop = rect.bottom + window.scrollY + 4;
    const left = rect.left + window.scrollX;
    const width = rect.width;
    setPosition({ top: baseTop, left, width });

    const raf = requestAnimationFrame(() => {
      const el = contentRef.current;
      if (!el) return;
      const height = el.offsetHeight;
      const spaceBelow = window.innerHeight - rect.bottom;
      if (spaceBelow < height && rect.top > height) {
        setPosition({ top: rect.top + window.scrollY - height - 4, left, width });
      }
    });
    return () => cancelAnimationFrame(raf);
  }, [isOpen]);

  // Focus the selected (or first) option when the menu opens.
  useEffect(() => {
    if (!isOpen) return;
    const raf = requestAnimationFrame(() => {
      const content = contentRef.current;
      if (!content) return;
      const sel = content.querySelector(
        '[role="option"][aria-selected="true"]',
      ) as HTMLElement | null;
      const first = content.querySelector('[role="option"]') as HTMLElement | null;
      (sel || first)?.focus();
    });
    return () => cancelAnimationFrame(raf);
  }, [isOpen]);

  const handleOptionKeyDown = (event: React.KeyboardEvent) => {
    const key = event.key;
    if (key === 'Enter' || key === ' ') {
      event.preventDefault();
      (event.currentTarget as HTMLElement).click();
      return;
    }
    if (key === 'Escape') {
      event.preventDefault();
      setIsOpen(false);
      triggerRef.current?.focus();
      return;
    }
    if (key === 'ArrowDown' || key === 'ArrowUp') {
      event.preventDefault();
      const root = (event.currentTarget as HTMLElement).closest(
        '[data-persona-content]',
      ) as HTMLElement | null;
      const options = root
        ? (Array.from(root.querySelectorAll('[role="option"]')) as HTMLElement[])
        : [];
      if (!options.length) return;
      const idx = options.indexOf(event.currentTarget as HTMLElement);
      const nextIdx =
        key === 'ArrowDown'
          ? (idx + 1) % options.length
          : (idx - 1 + options.length) % options.length;
      options[nextIdx]?.focus();
    }
  };

  if (loading) {
    return renderLoading ? (
      <>{renderLoading()}</>
    ) : (
      <div role="status" aria-live="polite">
        Cargando...
      </div>
    );
  }

  const selectedPersona = personas.find((p) => getPersonaId(p) === selected);

  const triggerInner = renderTriggerValue
    ? renderTriggerValue(selectedPersona, isOpen)
    : selectedPersona && getPersonaLabel
      ? getPersonaLabel(selectedPersona)
      : placeholder;

  const content = isOpen ? (
    <div
      ref={contentRef}
      id={contentId}
      role="listbox"
      aria-labelledby={triggerId}
      tabIndex={-1}
      data-persona-content
      style={{
        position: 'fixed',
        top: `${position.top}px`,
        left: `${position.left}px`,
        minWidth: `${position.width}px`,
        zIndex: 9999,
      }}
      className={`${CONTENT_BASE} ${contentClassName}`.trim()}
    >
      {renderHeader?.({ count: personas.length })}

      {personas.map((persona) => {
        const id = getPersonaId(persona);
        const isSelected = id === selected;
        const ctx: PersonaSlotContext = { selected: isSelected };
        const badge = renderPersonaBadge?.(persona, ctx);
        const meta = renderPersonaMeta?.(persona);
        const description = getPersonaDescription?.(persona);

        return (
          <div
            key={id}
            role="option"
            aria-selected={isSelected}
            tabIndex={0}
            onClick={() => {
              onSelect(id);
              setIsOpen(false);
            }}
            onKeyDown={handleOptionKeyDown}
            className={`${ITEM_BASE} hover:bg-slate-700/60 ${
              isSelected
                ? 'bg-purple-500/20 border-purple-500/50 border'
                : 'bg-slate-700/30 border border-transparent'
            }`}
          >
            <div className="flex items-center gap-2 mb-1">
              {renderPersonaIcon?.(persona, ctx)}
              <span
                className={`font-medium text-sm ${
                  isSelected ? 'text-purple-200' : 'text-slate-200'
                }`}
              >
                {getPersonaLabel?.(persona) ?? id}
              </span>
              {isSelected && <Check className="w-4 h-4 fi-text-purple ml-auto" />}
            </div>

            {description && (
              <p className="fi-text-xs mb-2 line-clamp-2">{description}</p>
            )}

            {(badge || meta) && (
              <div className="flex items-center gap-2 flex-wrap">
                {badge}
                {meta}
              </div>
            )}
          </div>
        );
      })}

      {renderFooter?.({ close })}
    </div>
  ) : null;

  return (
    <div className={className} data-persona-root>
      <button
        ref={triggerRef}
        id={triggerId}
        type="button"
        onClick={() => setIsOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={isOpen}
        aria-controls={isOpen ? contentId : undefined}
        aria-label={ariaLabel}
        className={triggerClassName ?? TRIGGER_DEFAULT}
      >
        {triggerInner}
        <ChevronDown
          className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`}
        />
      </button>
      {content && createPortal(content, document.body)}
    </div>
  );
}
