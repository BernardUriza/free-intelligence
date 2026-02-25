/**
 * Timeline Event Configuration
 *
 * Longitudinal Memory configuration for medical events + audio chunks + chat messages
 * Supports: transcription, diarization, SOAP notes, audio playback, STT provider info
 *
 * Card: FI-PHIL-DOC-014 (Memoria Longitudinal Unificada)
 * Updated: 2025-11-22 - Added chat message support
 */

import React from 'react';
import { Clock, Play, Pause, Zap, Radio, FileAudio, ChevronDown, ChevronUp, MessageCircle, User, Bot, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { TimelineConfig, TimelineEvent } from '@/components/audit/EventTimeline';

// ============================================================================
// Persona Display Names (Human-readable Spanish)
// ============================================================================

/**
 * Mapping from technical persona IDs to human-readable display names.
 * Used in timeline/memory views for better UX.
 */
const PERSONA_DISPLAY_NAMES: Record<string, string> = {
  general_assistant: 'Asistente General',
  onboarding_guide: 'Guía de Bienvenida',
  clinical_advisor: 'Asesor Clínico',
  soap_editor: 'Editor SOAP',
  waiting_room_host: 'Anfitrión Sala de Espera',
  fi_receptionist: 'Recepcionista FI',
  system: 'Sistema',
};

/**
 * Get human-readable persona name from technical ID.
 * Falls back to formatted version of ID if not mapped.
 */
export function getPersonaDisplayName(personaId: string | undefined): string {
  if (!personaId) return 'Asistente';
  return PERSONA_DISPLAY_NAMES[personaId] || personaId.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

export const timelineEventConfig: TimelineConfig = {
  title: 'Session Events',
  emptyMessage: 'No hay eventos de transcripción disponibles',
  showSearch: true,
  showExport: true,
  maxHeight: 'max-h-[700px]',

  // Format timestamp (8:41:36 PM style)
  formatTimestamp: (timestamp: string | number): string => {
    const date = typeof timestamp === 'string' ? new Date(timestamp) : new Date(timestamp * 1000);
    return date.toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true,
    });
  },

  // Color scheme for event types
  getColors: (event: TimelineEvent) => {
    const type = event.type.toLowerCase();

    // Chat messages (user/assistant)
    if (type === 'chat_user') {
      return {
        bg: 'bg-sky-500/10',
        border: 'border-sky-500/30',
        text: 'text-sky-400',
        badge: 'bg-sky-500',
      };
    }

    if (type === 'chat_assistant') {
      return {
        bg: 'bg-violet-500/10',
        border: 'border-violet-500/30',
        text: 'text-violet-400',
        badge: 'bg-violet-500',
      };
    }

    // Audio/Medical events
    if (type === 'transcription') {
      return {
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/30',
        text: 'fi-text-success',
        badge: 'bg-emerald-500',
      };
    }

    if (type === 'diarization') {
      return {
        bg: 'bg-purple-500/10',
        border: 'border-purple-500/30',
        text: 'fi-text-purple',
        badge: 'bg-purple-500',
      };
    }

    if (type === 'soap') {
      return {
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/30',
        text: 'fi-text-primary',
        badge: 'bg-blue-500',
      };
    }

    // Audio errors (warning)
    if (type.includes('error') || type.includes('failed') || type.includes('timeout')) {
      return {
        bg: 'bg-red-500/10',
        border: 'border-red-500/30',
        text: 'fi-text-error',
        badge: 'bg-red-500',
      };
    }

    return {
      bg: 'bg-slate-500/10',
      border: 'border-slate-500/30',
      text: 'text-slate-400',
      badge: 'bg-slate-500',
    };
  },

  // Custom header with event number + audio controls + expand/collapse
  renderHeader: (event, isExpanded, toggleExpanded, actions) => {
    const colors = timelineEventConfig.getColors!(event);
    const eventNumber = event.metadata?.event_number || event.metadata?.chunk_number || '?';
    const sttProvider = event.metadata?.stt_provider || event.metadata?.provider;
    const duration = event.metadata?.duration;
    const confidence = event.metadata?.confidence;
    const isPlaying = actions?.playingId === event.id;

    // Status badge logic
    const hasTranscript = event.content.trim().length > 0;
    const hasDuration = duration && duration > 0;
    const isAudioError = event.type.toLowerCase().includes('error') ||
                        event.type.toLowerCase().includes('failed') ||
                        event.type.toLowerCase().includes('timeout');
    const errorCode = event.metadata?.error_code || event.metadata?.tipo_error;
    const errorSeverity = event.metadata?.severity || event.metadata?.severidad;
    let statusBadge = null;

    if (isAudioError) {
      // Audio error badge - shows error code and severity
      const errorLabel = errorCode
        ? errorCode.replace('AUDIO_', '').replace(/_/g, ' ')
        : event.type;
      const severityLabel = errorSeverity ? `[${errorSeverity.toUpperCase()}]` : '';
      statusBadge = (
        <span className="mem-status-error">
          {errorLabel} {severityLabel}
        </span>
      );
    } else if (hasTranscript && hasDuration) {
      statusBadge = (
        <span className="mem-status-valid">
          Valid
        </span>
      );
    } else if (hasDuration) {
      statusBadge = (
        <span className="mem-status-empty">
          Empty
        </span>
      );
    } else if (event.type.toLowerCase() === 'transcription') {
      statusBadge = (
        <span className="mem-status-error">
          Invalid
        </span>
      );
    }

    return (
      <div className="mem-header-row">
        <div className="mem-badges-wrap">
          {/* Event Number */}
          <div className="mem-event-number">#{eventNumber}</div>

          {/* Event Type Badge */}
          <div className={`mem-type-badge ${colors.bg} ${colors.border}`}>
            <span className={`mem-type-text ${colors.text}`}>
              {event.type}
            </span>
          </div>

          {/* Status Badge (for transcription events) */}
          {statusBadge}

          {/* Timestamp */}
          <div className="mem-pill-timestamp">
            <Clock className="h-3 w-3 text-slate-400" />
            <span className="mem-pill-text">
              {timelineEventConfig.formatTimestamp!(event.timestamp)}
            </span>
          </div>

          {/* STT Provider (if available) */}
          {sttProvider && (
            <div className="mem-pill-stt">
              <Radio className="h-3 w-3 fi-text-primary" />
              <span className="mem-pill-text-stt">
                {sttProvider === 'deepgram' ? 'Deepgram' :
                 sttProvider === 'azure_whisper' ? 'Azure (deprecated)' : sttProvider}
              </span>
            </div>
          )}

          {/* Duration (if available) */}
          {duration && (
            <div className="mem-pill-duration">
              <FileAudio className="h-3 w-3 text-slate-400" />
              <span className="mem-pill-text">
                {duration.toFixed(1)}s
              </span>
            </div>
          )}

          {/* Confidence (if available) */}
          {confidence !== undefined && (
            <div className={`mem-pill ${
              confidence > 0.8 ? 'mem-confidence-high' :
              confidence > 0.6 ? 'mem-confidence-mid' :
              'mem-confidence-low'
            }`}>
              <Zap className={`h-3 w-3 ${
                confidence > 0.8 ? 'fi-text-success' :
                confidence > 0.6 ? 'fi-text-warning' :
                'fi-text-error'
              }`} />
              <span className={
                confidence > 0.8 ? 'mem-confidence-text-high' :
                confidence > 0.6 ? 'mem-confidence-text-mid' :
                'mem-confidence-text-low'
              }>
                {(confidence * 100).toFixed(0)}%
              </span>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="mem-actions-wrap">
          {/* Play/Pause Button (if audio available) */}
          {event.metadata?.audio_hash && actions?.onPlay && (
            <Button onClick={() => actions.onPlay!(event)} className={isPlaying ? 'mem-btn-play-active' : 'mem-btn-play'} aria-label={isPlaying ? 'Pausar audio' : 'Reproducir audio'} variant={isPlaying ? 'primary' : 'ghost'} size="sm" type="button">
              {isPlaying ? (
                <Pause className="h-4 w-4" />
              ) : (
                <Play className="h-4 w-4" />
              )}
            </Button>
          )}

          {/* Expand/Collapse Button */}
          <Button onClick={toggleExpanded} className="mem-btn-expand" aria-label={isExpanded ? 'Contraer' : 'Expandir'} variant="ghost" size="sm" type="button">
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            )}
          </Button>
        </div>
      </div>
    );
  },

  // Custom content rendering with preview + technical details
  renderContent: (event: TimelineEvent, isExpanded: boolean) => {
    const preview = event.content.substring(0, 100);
    const hasMore = event.content.length > 100;

    // Technical details (for audio chunks)
    const hasAudioData = event.metadata?.audio_hash || event.metadata?.latency_ms;
    const audioHash = event.metadata?.audio_hash;
    const latencyMs = event.metadata?.latency_ms;
    const language = event.metadata?.language;
    const audioQuality = event.metadata?.audio_quality;

    return (
      <div className="space-y-2">
        {/* Main text (always visible) */}
        <p className="mem-content-text">
          {isExpanded ? event.content : preview}
          {!isExpanded && hasMore && '...'}
        </p>

        {/* Technical Details (when expanded and available) */}
        {isExpanded && hasAudioData && (
          <div className="mem-tech-section">
            <h4 className="mem-tech-heading">
              Technical Details
            </h4>
            <div className="mem-tech-grid">
              {language && (
                <div className="mem-tech-row">
                  <span className="text-slate-500">Language:</span>
                  <span className="fi-text font-mono">{language}</span>
                </div>
              )}
              {latencyMs !== undefined && (
                <div className="mem-tech-row">
                  <span className="text-slate-500">Latency:</span>
                  <span className="fi-text font-mono">{latencyMs}ms</span>
                </div>
              )}
              {audioQuality && (
                <div className="mem-tech-row">
                  <span className="text-slate-500">Quality:</span>
                  <span className="fi-text font-mono">{audioQuality}</span>
                </div>
              )}
              {audioHash && (
                <div className="mem-tech-row-wide">
                  <span className="text-slate-500">Hash:</span>
                  <span className="mem-tech-hash">
                    {audioHash.substring(0, 16)}...
                  </span>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    );
  },

  // Custom footer with tags
  renderFooter: (event: TimelineEvent) => {
    const who = event.metadata?.who || 'system';
    const tags = event.metadata?.tags || [];

    return (
      <div className="mem-footer">
        <span className="text-xs text-slate-500">by</span>
        <span className="mem-footer-who">
          {who}
        </span>
        {tags.map((tag: string) => (
          <span
            key={tag}
            className="mem-footer-tag"
          >
            {tag}
          </span>
        ))}
      </div>
    );
  },

  // Export to Markdown
  formatExport: (events: TimelineEvent[]): string => {
    const header = `# Session Timeline Export\n\nGenerated: ${new Date().toISOString()}\nTotal Events: ${events.length}\n\n---\n\n`;

    const body = events
      .map((event, idx) => {
        const timestamp = timelineEventConfig.formatTimestamp!(event.timestamp);
        return `## Event #${idx + 1} - ${event.type}\n**Time:** ${timestamp}\n**Content:** ${event.content}\n\n`;
      })
      .join('\n');

    return header + body;
  },

  // Search filter
  searchFilter: (event: TimelineEvent, query: string): boolean => {
    return (
      event.content.toLowerCase().includes(query) ||
      event.type.toLowerCase().includes(query) ||
      (event.metadata?.who && event.metadata.who.toLowerCase().includes(query)) ||
      (event.metadata?.tags &&
        event.metadata.tags.some((tag: string) => tag.toLowerCase().includes(query)))
    );
  },

  // Audio playback action
  actions: {
    onPlay: (event: TimelineEvent) => {
      // Get audio hash from metadata
      const audioHash = event.metadata?.audio_hash;
      const chunkNumber = event.metadata?.event_number || event.metadata?.chunk_number;

      if (!audioHash) {
        console.warn('[Timeline] No audio hash found for event', event.id);
        return;
      }

      console.log('[Timeline] Playing audio for event', event.id, {
        audioHash,
        chunkNumber,
      });
    },
  },
};

// ============================================================================
// Longitudinal Memory Config (Chat + Audio + Medical)
// "No existen sesiones. Solo una conversación infinita"
// ============================================================================

export const memoryConfig: TimelineConfig = {
  title: 'Memoria Longitudinal',
  emptyMessage: 'No hay eventos en tu memoria longitudinal',
  showSearch: true,
  showExport: true,
  maxHeight: 'max-h-[700px]',

  // Format with date + time: "13 ene · 08:32:03 p.m."
  formatTimestamp: (timestamp: string | number): string => {
    const date = typeof timestamp === 'number'
      ? new Date(timestamp * 1000)
      : new Date(timestamp);
    const dateStr = date.toLocaleDateString('es-MX', {
      day: 'numeric',
      month: 'short',
    });
    const timeStr = date.toLocaleTimeString('es-MX', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    return `${dateStr} · ${timeStr}`;
  },
  getColors: timelineEventConfig.getColors,

  // Custom header that differentiates chat vs audio events
  renderHeader: (event, isExpanded, toggleExpanded, actions) => {
    const colors = memoryConfig.getColors!(event);
    const type = event.type.toLowerCase();
    const isChat = type.startsWith('chat_');
    const isUser = type === 'chat_user';

    // For chat messages
    if (isChat) {
      const persona = event.metadata?.persona;

      return (
        <div className="mem-header-row">
          <div className="mem-badges-wrap">
            {/* Role Icon */}
            <div className={`mem-role-icon ${colors.bg} ${colors.border}`}>
              {isUser ? (
                <User className={`h-4 w-4 ${colors.text}`} />
              ) : (
                <Bot className={`h-4 w-4 ${colors.text}`} />
              )}
            </div>

            {/* Role Badge */}
            <div className={`mem-type-badge ${colors.bg} ${colors.border}`}>
              <span className={`mem-type-text ${colors.text}`}>
                {isUser ? 'Tú' : 'Asistente'}
              </span>
            </div>

            {/* Persona Badge (if assistant) */}
            {!isUser && persona && (
              <div className="mem-pill-persona">
                <Sparkles className="h-3 w-3 text-violet-400" />
                <span className="text-xs text-violet-300">
                  {getPersonaDisplayName(persona)}
                </span>
              </div>
            )}

            {/* Timestamp */}
            <div className="mem-pill-timestamp">
              <Clock className="h-3 w-3 text-slate-400" />
              <span className="mem-pill-text">
                {memoryConfig.formatTimestamp!(event.timestamp)}
              </span>
            </div>

            {/* Chat indicator */}
            <div className="mem-pill-chat">
              <MessageCircle className="h-3 w-3 text-slate-400" />
              <span className="fi-text-xs">chat</span>
            </div>
          </div>

          {/* Expand/Collapse */}
          <Button onClick={toggleExpanded} className="mem-btn-expand" aria-label={isExpanded ? 'Contraer' : 'Expandir'} variant="ghost" size="sm" type="button">
            {isExpanded ? (
              <ChevronUp className="h-4 w-4 text-slate-400" />
            ) : (
              <ChevronDown className="h-4 w-4 text-slate-400" />
            )}
          </Button>
        </div>
      );
    }

    // For audio/transcription events - use original header
    return timelineEventConfig.renderHeader!(event, isExpanded, toggleExpanded, actions);
  },

  // Content rendering for both chat and audio
  renderContent: (event: TimelineEvent, isExpanded: boolean) => {
    const type = event.type.toLowerCase();
    const isChat = type.startsWith('chat_');

    if (isChat) {
      const preview = event.content.substring(0, 200);
      const hasMore = event.content.length > 200;

      return (
        <div className="space-y-2">
          <p className="mem-chat-text">
            {isExpanded ? event.content : preview}
            {!isExpanded && hasMore && '...'}
          </p>

          {/* Session info when expanded */}
          {isExpanded && event.metadata?.session_id && (
            <div className="mem-session-divider">
              <div className="text-xs text-slate-500">
                <span className="font-mono">session: {event.metadata.session_id.substring(0, 16)}...</span>
              </div>
            </div>
          )}
        </div>
      );
    }

    // For audio events - use original content renderer
    return timelineEventConfig.renderContent!(event, isExpanded);
  },

  // Footer for chat messages
  renderFooter: (event: TimelineEvent) => {
    const type = event.type.toLowerCase();
    const isChat = type.startsWith('chat_');

    if (isChat) {
      // Minimal footer for chat
      return null;
    }

    // For audio events - use original footer
    return timelineEventConfig.renderFooter!(event);
  },

  // Export longitudinal memory
  formatExport: (events: TimelineEvent[]): string => {
    const chatCount = events.filter(e => e.type.toLowerCase().startsWith('chat_')).length;
    const audioCount = events.filter(e => e.type.toLowerCase() === 'transcription').length;

    const header = `# Memoria Longitudinal Unificada
Generated: ${new Date().toISOString()}
Total Events: ${events.length}
- Chat Messages: ${chatCount}
- Audio Transcriptions: ${audioCount}

---

`;

    const body = events
      .map((event) => {
        const timestamp = memoryConfig.formatTimestamp!(event.timestamp);
        const type = event.type.toLowerCase();
        const isChat = type.startsWith('chat_');
        const label = isChat
          ? (type === 'chat_user' ? 'Usuario' : 'Asistente')
          : event.type;

        return `## ${label} - ${timestamp}
${event.content}

`;
      })
      .join('\n');

    return header + body;
  },

  // Search filter for longitudinal memory
  searchFilter: (event: TimelineEvent, query: string): boolean => {
    const contentMatch = event.content.toLowerCase().includes(query);
    const typeMatch = event.type.toLowerCase().includes(query);
    const personaMatch = event.metadata?.persona?.toLowerCase().includes(query);

    return contentMatch || typeMatch || personaMatch;
  },

  actions: timelineEventConfig.actions,
};
