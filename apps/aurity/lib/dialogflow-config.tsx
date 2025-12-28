/**
 * DialogFlow Configuration
 *
 * Configuration for displaying speaker diarization segments
 * Matches the design from components/medical/DialogueFlow.tsx
 */

import React from 'react';
import { Clock, Zap, Edit2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { TimelineConfig, TimelineEvent } from '@/components/audit/EventTimeline';

export const dialogFlowConfig: TimelineConfig = {
  title: 'Revisión del Diálogo',
  emptyMessage: 'No hay segmentos de diarización disponibles',
  showSearch: true,
  showExport: true,
  maxHeight: 'max-h-[600px]',

  // Format timestamp (00:45 style for audio)
  formatTimestamp: (timestamp: string | number): string => {
    const seconds = typeof timestamp === 'number' ? timestamp : parseFloat(timestamp);
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  },

  // Color scheme for speakers
  getColors: (event: TimelineEvent) => {
    const speaker = event.metadata?.speaker?.toLowerCase() || event.type.toLowerCase();

    if (speaker === 'medico' || speaker === 'doctor') {
      return {
        bg: 'bg-blue-500/10',
        border: 'border-blue-500/30',
        text: 'fi-text-primary',
        badge: 'bg-blue-500',
      };
    }

    if (speaker === 'paciente' || speaker === 'patient') {
      return {
        bg: 'bg-emerald-500/10',
        border: 'border-emerald-500/30',
        text: 'fi-text-success',
        badge: 'bg-emerald-500',
      };
    }

    return {
      bg: 'bg-slate-500/10',
      border: 'border-slate-500/30',
      text: 'text-slate-400',
      badge: 'bg-slate-500',
    };
  },

  // Custom header with speaker and timestamp range
  renderHeader: (event: TimelineEvent) => {
    const colors = dialogFlowConfig.getColors!(event);
    const speaker = event.metadata?.speaker || event.type;
    const startTime = event.metadata?.start_time || 0;
    const endTime = event.metadata?.end_time || 0;
    const duration = endTime - startTime;
    const confidence = event.metadata?.confidence;

    return (
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3 flex-wrap">
          {/* Speaker Badge */}
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-md ${colors.bg} border ${colors.border}`}>
            <div className={`w-2 h-2 ${colors.badge} rounded-full`}></div>
            <span className={`text-sm font-semibold ${colors.text}`}>
              {speaker.toUpperCase()}
            </span>
          </div>

          {/* Timestamp Range */}
          <Button
            onClick={() => {
              if (dialogFlowConfig.actions?.onPlay) {
                dialogFlowConfig.actions.onPlay(event);
              }
            }}
            className="flex items-center gap-1.5 px-2 py-1 bg-slate-900/50 hover:bg-slate-900 border border-slate-700 rounded-md transition-colors group"
            title="Ir a este momento"
            variant="ghost"
            size="sm"
            type="button"
          >
            <Clock className="h-3.5 w-3.5 text-slate-400 group-hover:text-white" />
            <span className="text-xs font-mono text-slate-400 group-hover:text-white">
              {dialogFlowConfig.formatTimestamp!(startTime)} → {dialogFlowConfig.formatTimestamp!(endTime)}
            </span>
            <span className="text-xs text-slate-500 ml-1">
              ({duration.toFixed(1)}s)
            </span>
          </Button>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Confidence */}
          {confidence !== undefined && (
            <div className="flex items-center gap-1 px-2 py-1 bg-slate-900/30 rounded-md">
              <Zap className="h-3 w-3 text-yellow-400" />
              <span className="fi-text-xs">
                {Math.round(confidence * 100)}%
              </span>
            </div>
          )}

          {/* Edit Button */}
          {dialogFlowConfig.actions?.onEdit && (
            <Button onClick={() => dialogFlowConfig.actions!.onEdit!(event)} className="p-1 hover:bg-slate-700/50 rounded transition-colors" aria-label="Editar segmento" variant="ghost" size="sm" type="button">
              <Edit2 className="h-4 w-4 text-slate-400" />
            </Button>
          )}
        </div>
      </div>
    );
  },

  // Custom content rendering with improved text
  renderContent: (event: TimelineEvent, isExpanded: boolean) => {
    const improvedText = event.metadata?.improved_text;
    const hasImprovedText = improvedText && improvedText !== event.content;

    if (!hasImprovedText) {
      return (
        <div className="space-y-2">
          <p className="fi-text leading-relaxed">{event.content}</p>
        </div>
      );
    }

    return (
      <div className="space-y-2">
        {/* Improved Text (GPT-4 enhanced) */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Zap className="h-3.5 w-3.5 fi-text-purple" />
            <span className="fi-text-xs-medium fi-text-purple">
              Texto mejorado (GPT-4)
            </span>
          </div>
          <p className="text-slate-200 leading-relaxed font-medium">
            {improvedText}
          </p>
        </div>

        {/* Original text (collapsible) */}
        {isExpanded && (
          <div className="pt-2 fi-border-top/50">
            <span className="text-xs text-slate-500 mb-1 block">
              Texto original:
            </span>
            <p className="text-slate-400 text-sm leading-relaxed italic">
              {event.content}
            </p>
          </div>
        )}
      </div>
    );
  },

  // Export to Markdown
  formatExport: (events: TimelineEvent[]): string => {
    const header = `# Dialogue Transcript Export\n\nGenerated: ${new Date().toISOString()}\nTotal Segments: ${events.length}\n\n---\n\n`;

    const body = events
      .map((event) => {
        const speaker = event.metadata?.speaker || event.type;
        const startTime = dialogFlowConfig.formatTimestamp!(event.metadata?.start_time || 0);
        const endTime = dialogFlowConfig.formatTimestamp!(event.metadata?.end_time || 0);
        const improvedText = event.metadata?.improved_text;
        const text = improvedText || event.content;

        return `## ${speaker.toUpperCase()} (${startTime} → ${endTime})\n\n${text}\n`;
      })
      .join('\n');

    return header + body;
  },

  // Search filter
  searchFilter: (event: TimelineEvent, query: string): boolean => {
    return (
      event.content.toLowerCase().includes(query) ||
      (event.metadata?.improved_text &&
        event.metadata.improved_text.toLowerCase().includes(query)) ||
      (event.metadata?.speaker && event.metadata.speaker.toLowerCase().includes(query))
    );
  },
};
