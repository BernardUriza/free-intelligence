'use client';

/**
 * PersonaSelectorPanel Component
 *
 * Compact persona selector using the modernized Select component.
 * Shows persona name, description, model, and configuration details.
 *
 * Features:
 * - Rich dropdown with icons, badges, and descriptions
 * - Model badge shows which LLM model each persona uses
 * - Metadata display (temperature, max tokens)
 * - Portal rendering for proper z-index
 *
 * Best Practices 2025-2026:
 * - Graceful degradation for missing model information
 * - Type-safe with explicit interfaces
 * - Accessible with ARIA labels
 * - Performance-optimized with memoization
 */

import Link from 'next/link';
import { Brain, Settings } from 'lucide-react';
import type { PersonaOption } from '@aurity-standalone/hooks/usePersonas';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  type RichItemData,
} from '@/components/ui/select';
import { getModelBadgeVariant } from '@/types/select-configs';
import { getPersonaIcon } from '@/components/ui/message/styles/persona-styles';
import { getVoiceDisplayName } from '@/lib/voiceAliases';

// ============================================================================
// Constants
// ============================================================================

/** Fallback text when model information is unavailable */
const MODEL_FALLBACK = 'Modelo desconocido';

/** Placeholder text when no persona is selected */
const PLACEHOLDER_TEXT = 'Seleccionar persona...';

/** Selector minimum and maximum widths */
const SELECTOR_WIDTH = { min: 160, max: 240 } as const;

// Dropdown width (previously unused) — removed to satisfy lint rules

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
// Helper Functions
// ============================================================================

/**
 * Builds metadata object for persona display
 * Includes temperature and max tokens when available
 */
function buildPersonaMetadata(persona: PersonaOption): Record<string, string | number> {
  const metadata: Record<string, string | number> = {};

  if (persona.temperature !== undefined) {
    metadata.temp = persona.temperature.toFixed(1);
  }

  if (persona.maxTokens !== undefined) {
    metadata.tokens = persona.maxTokens.toLocaleString();
  }

  return metadata;
}

/**
 * Builds rich item data for Select component
 * Handles missing model information gracefully
 */
function buildRichItemData(persona: PersonaOption): RichItemData {
  const voiceLabel = getVoiceDisplayName(persona.voice || null);
  const badgeText = persona.model ? `${persona.model}${voiceLabel ? ` · ${voiceLabel}` : ''}` : MODEL_FALLBACK;

  return {
    label: persona.name || persona.id,
    icon: getPersonaIcon(persona.id),
    description: persona.description,
    badge: {
      text: badgeText,
      variant: getModelBadgeVariant(persona.model),
    },
    metadata: buildPersonaMetadata(persona),
  };
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
  // Loading State
  if (loading) {
    return (
      <div
        className="chat-persona-loading"
        style={{ minWidth: SELECTOR_WIDTH.min }}
        role="status"
        aria-live="polite"
      >
        <Brain className="chat-persona-loading-icon" aria-hidden="true" />
        <span className="chat-persona-loading-text">Cargando...</span>
      </div>
    );
  }

  // Build initial rich items map for Select component
  // This allows the Select to show labels immediately without async loading
  const initialItems: Record<string, RichItemData> = {};
  personas.forEach((persona) => {
    initialItems[persona.id] = buildRichItemData(persona);
  });

  return (
    <Select value={selectedPersona} onValueChange={onSelect} items={initialItems}>
      {/* Trigger Button */}
      {/* Ultra-compact when container is small (icon-only), full when wider (@md = 384px) */}
      <SelectTrigger
        className="bg-slate-800/80 hover:bg-slate-700/80 border-slate-600/50 transition-colors min-w-0 @md:min-w-[160px] @md:max-w-[240px] px-2 @md:px-2.5 py-1.5"
      >
        <SelectValue
          showIcon
          showBadge
          showDescription={false}
          placeholder={PLACEHOLDER_TEXT}
          labelClassName="hidden @md:flex"
          badgeClassName="hidden @lg:inline-flex"
        />
      </SelectTrigger>

      {/* Dropdown Content */}
      <SelectContent
        portal
        className="max-h-[400px] overflow-y-auto w-[360px]"
      >
        {/* Header */}
        <div className="chat-persona-header">
          <div className="chat-persona-header-inner">
            <Brain className="chat-persona-header-icon" />
            <span className="chat-persona-header-title">AI Personas</span>
            <span className="chat-persona-header-count">{personas.length}</span>
          </div>
        </div>

        {/* Personas List */}
        {personas.map((persona) => {
          const Icon = getPersonaIcon(persona.id);
          const voiceLabel = getVoiceDisplayName(persona.voice || null);
          const badgeText = persona.model ? `${persona.model}${voiceLabel ? ` · ${voiceLabel}` : ''}` : MODEL_FALLBACK;

          return (
            <SelectItem
              key={persona.id}
              value={persona.id}
              icon={Icon}
              label={persona.name}
              description={persona.description}
              badge={{
                text: badgeText,
                variant: getModelBadgeVariant(persona.model),
              }}
              metadata={buildPersonaMetadata(persona)}
            />
          );
        })}

        {/* Footer with Edit Link */}
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
      </SelectContent>
    </Select>
  );
}
