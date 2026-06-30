'use client';

/**
 * Og118ElementSelector — the "elemento" picker in the sidebar (OG118-ELEMENTS-ADR-1).
 *
 * This is og118's ChatGPT-style persona switch: choosing an element swaps the
 * answering persona (Vultur for Oxígeno) for the whole conversation. The dropdown
 * behavior, a11y and positioning are the framework's (fi-glass PersonaSelector,
 * Californio) — this consumer owns ONLY the meaning: which elements, the Spanish
 * copy, the og118 emerald trigger, the atomic-number/symbol presentation. The
 * section header reuses AgentSidebarSection, the same skeleton as Projects and
 * Conversations, so all three sidebar groups share one anatomy.
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
  'flex w-full items-center justify-between gap-2 rounded-lg border border-emerald-500/30 bg-white/5 px-3 py-2 text-sm text-slate-100 transition-colors hover:border-emerald-400/50';

function symbolBadge(el: Og118Element, selected: boolean) {
  return (
    <span
      className={`inline-flex min-w-[1.6rem] justify-center rounded px-1.5 py-0.5 text-xs font-semibold ${
        selected ? 'bg-emerald-500/30 text-emerald-100' : 'bg-white/10 text-slate-200'
      }`}
    >
      {el.symbol}
    </span>
  );
}

export function Og118ElementSelector({
  elements,
  selected,
  onSelect,
  loading = false,
}: Og118ElementSelectorProps) {
  return (
    <AgentSidebarSection title="Elemento" count={elements.length} ariaLabel="Elemento activo">
      <PersonaSelector<Og118Element>
        personas={elements}
        selected={selected}
        onSelect={onSelect}
        getPersonaId={(el) => el.slug}
        getPersonaLabel={(el) => el.displayName}
        loading={loading}
        ariaLabel="Seleccionar elemento"
        triggerClassName={TRIGGER_CLASS}
        renderTriggerValue={(sel) => (
          <span className="flex items-center gap-2 truncate">
            {sel ? symbolBadge(sel, false) : null}
            <span className="truncate">{sel ? sel.displayName : 'og118 (base)'}</span>
          </span>
        )}
        renderPersonaIcon={(el, ctx) => symbolBadge(el, ctx.selected)}
      />
    </AgentSidebarSection>
  );
}
