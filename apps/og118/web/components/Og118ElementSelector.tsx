'use client';

/**
 * Og118ElementSelector — the "elemento" switch (OG118-ELEMENTS-COMPOSER-SWITCH-1).
 *
 * og118's ChatGPT-style persona switch: choosing an element swaps the answering
 * persona (Vultur for Oxígeno) for the whole conversation. After COMPOSER-SWITCH-1
 * the PRIMARY trigger lives in the composer (near the input — it affects the next
 * turn, like switching custom GPTs in ChatGPT), and the sidebar keeps only a
 * read-only indicator of the active element (Og118ElementIndicator).
 *
 * Dropdown behavior, a11y and positioning are the framework's (fi-glass
 * PersonaSelector, Californio). This consumer owns ONLY the meaning, now fed RICH:
 * the atomic-number·symbol badge, the Spanish persona description, the engine chip
 * (Vultur / ALICE / Insult), the header + count, and the og emerald accent — the
 * same render slots aurity's PersonaSelectorPanel uses, so og118's switch reads as
 * ordered as aurity's instead of a bare list.
 */

import { PersonaSelector } from 'fi-glass/persona-selector';
import { AgentSidebarSection } from 'fi-glass/agent';
import type { Og118Element } from '../lib/og118Element';

export interface Og118ElementSelectorProps {
  elements: Og118Element[];
  selected: string;
  onSelect: (slug: string) => void;
  loading?: boolean;
}

const TRIGGER_CLASS =
  'flex w-full items-center justify-between gap-2 rounded-lg border border-emerald-500/30 bg-white/5 px-3 py-2 text-sm text-slate-100 transition-colors hover:border-emerald-400/50 focus:outline-none focus:ring-2 focus:ring-emerald-500/40';

/** The "8 · O" atomic badge (just the symbol for the base og slot). */
function atomicBadge(el: Og118Element, selected: boolean) {
  const label = el.atomicNumber > 0 ? `${el.atomicNumber} · ${el.symbol}` : el.symbol;
  return (
    <span
      className={`inline-flex min-w-[2.2rem] justify-center rounded px-1.5 py-0.5 text-xs font-semibold font-mono ${
        selected ? 'bg-emerald-500/30 text-emerald-100' : 'bg-white/10 text-slate-200'
      }`}
    >
      {label}
    </span>
  );
}

/** The engine/persona chip (Vultur / ALICE / Insult) — real registry data. */
function engineChip(engine: string) {
  return (
    <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[11px] font-mono border border-emerald-500/30 bg-emerald-500/10 text-emerald-200">
      {engine}
    </span>
  );
}

/**
 * The rich element switch. Primary placement is the composer (aboveComposer slot).
 */
export function Og118ElementSelector({
  elements,
  selected,
  onSelect,
  loading = false,
}: Og118ElementSelectorProps) {
  return (
    <PersonaSelector<Og118Element>
      personas={elements}
      selected={selected}
      onSelect={onSelect}
      getPersonaId={(el) => el.slug}
      getPersonaLabel={(el) => el.displayName}
      getPersonaDescription={(el) => el.description || undefined}
      loading={loading}
      ariaLabel="Seleccionar elemento"
      triggerClassName={TRIGGER_CLASS}
      contentClassName="max-h-[400px] overflow-y-auto w-[360px]"
      renderTriggerValue={(sel) => (
        <span className="flex items-center gap-2 truncate">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-300/80">
            Elemento
          </span>
          {sel ? atomicBadge(sel, false) : null}
          <span className="truncate">{sel ? sel.displayName : 'og118 (base)'}</span>
        </span>
      )}
      renderHeader={({ count }) => (
        <div className="flex items-center gap-2 border-b border-slate-700 px-3 py-2 mb-1">
          <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
            Elementos
          </span>
          <span className="ml-auto rounded-full bg-emerald-500/20 px-2 py-0.5 text-[11px] text-emerald-200">
            {count}
          </span>
        </div>
      )}
      renderPersonaIcon={(el, ctx) => atomicBadge(el, ctx.selected)}
      renderPersonaMeta={(el) => (el.engine ? engineChip(el.engine) : null)}
    />
  );
}

/**
 * Og118ElementIndicator — the sidebar's read-only summary of the active element
 * (COMPOSER-SWITCH-1: the sidebar shows state, the composer owns the control).
 */
export function Og118ElementIndicator({ element }: { element?: Og118Element }) {
  return (
    <AgentSidebarSection title="Elemento activo" count={1} ariaLabel="Elemento activo">
      <div className="flex items-center gap-2 px-3 py-2 text-sm text-slate-200">
        {element ? atomicBadge(element, true) : null}
        <span className="truncate">{element ? element.displayName : 'og118 (base)'}</span>
        {element?.engine ? <span className="ml-auto">{engineChip(element.engine)}</span> : null}
      </div>
    </AgentSidebarSection>
  );
}
