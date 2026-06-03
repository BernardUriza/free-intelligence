'use client';

/**
 * PersonaSelectorPanel Component
 *
 * Aurity's persona picker, now a thin domain wrapper over fi-glass's
 * <PersonaSelector> (Californio, element 98). fi-glass owns the dropdown
 * behavior (open/close, portal, keyboard, focus, ARIA); this file injects the
 * domain by slot: persona icons, the model/voice badge (BADGE_STYLES), metadata
 * chips, and the "edit personas" link (next/link — forbidden in fi-glass).
 *
 * The class strings below are the exact ones the previous Select-based markup
 * produced, so the render is identical by construction.
 */

import Link from 'next/link';
import { Brain, Settings } from 'lucide-react';
import type { PersonaOption } from '@aurity-standalone/hooks/usePersonas';
import { PersonaSelector } from 'fi-glass/persona-selector';
import { BADGE_STYLES, getModelBadgeVariant, type BadgeVariant } from '@/types/select-configs';
import { getPersonaIcon } from '@/components/ui/message/styles/persona-styles';
import { getVoiceDisplayName } from '@/lib/voiceAliases';

// ============================================================================
// Constants
// ============================================================================

/** Fallback text when model information is unavailable */
const MODEL_FALLBACK = 'Modelo desconocido';

/** Placeholder text when no persona is selected */
const PLACEHOLDER_TEXT = 'Seleccionar persona...';

/** Selector minimum width (loading state) */
const SELECTOR_MIN_WIDTH = 160;

/**
 * Trigger button class — composed verbatim from the old SelectTrigger
 * (its base classes) + aurity Button ghost/sm (`fi-btn-ghost fi-btn-sm`) +
 * the `chat-persona-trigger` override, so the trigger renders byte-identically.
 */
const TRIGGER_CLASS =
  'fi-btn-ghost fi-btn-sm flex w-full items-center justify-between rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-sm hover:bg-slate-700/50 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-slate-900 transition-colors chat-persona-trigger';

// ============================================================================
// Types
// ============================================================================

export interface PersonaSelectorPanelProps {
  /** List of available personas */
  personas: PersonaOption[];
  /** Currently selected persona ID */
  selectedPersona: string;
  /** Loading state */
  loading?: boolean;
  /** Callback when persona is selected */
  onSelect: (personaId: string) => void;
}

// ============================================================================
// Domain helpers
// ============================================================================

/** Build the model · voice badge text for a persona. */
function badgeText(persona: PersonaOption): string {
  const voiceLabel = getVoiceDisplayName(persona.voice || null);
  return persona.model
    ? `${persona.model}${voiceLabel ? ` · ${voiceLabel}` : ''}`
    : MODEL_FALLBACK;
}

/** Render a model badge span with the BADGE_STYLES palette (item variant). */
function ItemBadge({ persona }: { persona: PersonaOption }) {
  const variant: BadgeVariant = getModelBadgeVariant(persona.model);
  const styles = BADGE_STYLES[variant];
  if (!styles) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono rounded-md border ${styles.bg} ${styles.text} ${styles.border}`}
    >
      {badgeText(persona)}
    </span>
  );
}

/** Render the compact badge shown inside the trigger. */
function TriggerBadge({ persona }: { persona: PersonaOption }) {
  const variant: BadgeVariant = getModelBadgeVariant(persona.model);
  const styles = BADGE_STYLES[variant];
  if (!styles) return null;
  return (
    <span
      className={`px-1.5 py-0.5 text-[10px] font-mono rounded flex-shrink-0 border inline-flex ${styles.bg} ${styles.text} ${styles.border}`}
    >
      {badgeText(persona)}
    </span>
  );
}

/** Render the metadata chips (temp / tokens) for a persona. */
function PersonaMeta({ persona }: { persona: PersonaOption }) {
  const meta: Record<string, string | number> = {};
  if (persona.temperature !== undefined) meta.temp = persona.temperature.toFixed(1);
  if (persona.maxTokens !== undefined) meta.tokens = persona.maxTokens.toLocaleString();
  const entries = Object.entries(meta);
  if (!entries.length) return null;
  return (
    <>
      {entries.map(([key, val]) => (
        <span key={key} className="ui-select-meta-chip">
          {key}: {val}
        </span>
      ))}
    </>
  );
}

// ============================================================================
// Component
// ============================================================================

export function PersonaSelectorPanel({
  personas,
  selectedPersona,
  loading = false,
  onSelect,
}: PersonaSelectorPanelProps) {
  return (
    <PersonaSelector<PersonaOption>
      personas={personas}
      selected={selectedPersona}
      onSelect={onSelect}
      loading={loading}
      getPersonaId={(p) => p.id}
      getPersonaLabel={(p) => p.name || p.id}
      getPersonaDescription={(p) => p.description}
      triggerClassName={TRIGGER_CLASS}
      contentClassName="max-h-[400px] overflow-y-auto w-[360px]"
      ariaLabel="Seleccionar persona"
      renderLoading={() => (
        <div
          className="chat-persona-loading"
          style={{ minWidth: SELECTOR_MIN_WIDTH }}
          role="status"
          aria-live="polite"
        >
          <Brain className="chat-persona-loading-icon" aria-hidden="true" />
          <span className="chat-persona-loading-text">Cargando...</span>
        </div>
      )}
      renderTriggerValue={(persona) =>
        persona ? (
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {(() => {
              const Icon = getPersonaIcon(persona.id);
              return <Icon className="w-4 h-4 text-slate-400 flex-shrink-0" />;
            })()}
            <TriggerBadge persona={persona} />
          </div>
        ) : (
          <span className="text-slate-400">{PLACEHOLDER_TEXT}</span>
        )
      }
      renderHeader={({ count }) => (
        <div className="chat-persona-header">
          <div className="chat-persona-header-inner">
            <Brain className="chat-persona-header-icon" />
            <span className="chat-persona-header-title">AI Personas</span>
            <span className="chat-persona-header-count">{count}</span>
          </div>
        </div>
      )}
      renderPersonaIcon={(persona, { selected }) => {
        const Icon = getPersonaIcon(persona.id);
        return (
          <Icon className={`w-4 h-4 ${selected ? 'fi-text-purple' : 'text-slate-400'}`} />
        );
      }}
      renderPersonaBadge={(persona) => <ItemBadge persona={persona} />}
      renderPersonaMeta={(persona) => <PersonaMeta persona={persona} />}
      renderFooter={() => (
        <div className="chat-persona-footer">
          <div className="chat-persona-footer-inner">
            <p className="chat-persona-footer-text">
              Definen el comportamiento del AI
            </p>
            <Link href="/admin/personas/" className="chat-persona-edit-link" title="Editar personas">
              <Settings className="w-3 h-3" />
              <span>Editar</span>
            </Link>
          </div>
        </div>
      )}
    />
  );
}
