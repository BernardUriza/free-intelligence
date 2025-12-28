'use client';

/**
 * EventDetailModal Component
 * 
 * Full-screen modal showing complete event details:
 * - Event type and timestamp
 * - Full content (no truncation)
 * - Metadata (session, persona, confidence, language)
 * - Copy to clipboard functionality
 */

import React, { useState } from 'react';
import { X, Clock, Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getEventColor, getEventTypeLabel, type UnifiedEvent } from '@/components/bryntum';

interface EventDetailModalProps {
  event: UnifiedEvent | null;
  onClose: () => void;
}

export function EventDetailModal({ event, onClose }: EventDetailModalProps) {
  const [copied, setCopied] = useState(false);

  if (!event) return null;

  const timestamp = new Date(event.timestamp * 1000);
  const eventTypeLabel = getEventTypeLabel(event.event_type);
  const eventColor = getEventColor(event.event_type);

  const handleCopyContent = async () => {
    try {
      await navigator.clipboard.writeText(event.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div
      className="fi-modal-backdrop"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 rounded-2xl shadow-2xl border border-slate-700 w-full max-w-lg mx-4 max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 fi-border-bottom">
          <div className="fi-flex-gap-md">
            <span className="w-3 h-3 rounded-full" style={{ backgroundColor: eventColor }} />
            <span className="font-medium text-white">{eventTypeLabel}</span>
            {event.source === 'audio' && event.duration && (
              <span className="fi-text-xs bg-slate-800 px-2 py-0.5 rounded">
                {event.duration.toFixed(1)}s
              </span>
            )}
          </div>
          <Button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-800 rounded-lg transition-colors"
            variant="ghost"
            size="sm"
            title="Cerrar"
            icon={X}
          />
        </div>

        {/* Timestamp */}
        <div className="px-4 py-3 bg-slate-800/50 fi-border-bottom">
          <div className="fi-flex-gap fi-subtitle">
            <Clock className="h-4 w-4" />
            <span>
              {timestamp.toLocaleString('es-MX', {
                weekday: 'long',
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
              })}
            </span>
          </div>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[50vh] overflow-y-auto">
          <div className="flex items-start justify-between gap-2 mb-2">
            <span className="fi-text-xs-muted uppercase tracking-wide">Contenido</span>
            <Button
              onClick={handleCopyContent}
              className="flex items-center gap-1.5 px-2 py-1 fi-text-xs hover:text-white hover:bg-slate-800 rounded transition-colors"
              variant="ghost"
              size="sm"
              title="Copiar contenido"
            >
              {copied ? (
                <>
                  <Check className="h-3 w-3 fi-text-success" />
                  <span className="fi-text-success">Copiado</span>
                </>
              ) : (
                <>
                  <Copy className="h-3 w-3" />
                  <span>Copiar</span>
                </>
              )}
            </Button>
          </div>
          <p className="text-sm fi-text whitespace-pre-wrap leading-relaxed">{event.content}</p>
        </div>

        {/* Metadata Footer */}
        {(event.session_id || event.persona || event.confidence || event.language) && (
          <div className="px-4 py-3 bg-slate-800/30 fi-border-top grid grid-cols-2 gap-2 text-xs">
            {event.session_id && (
              <div>
                <span className="text-slate-500">Sesión:</span>{' '}
                <span className="text-slate-400 font-mono">{event.session_id.slice(0, 12)}...</span>
              </div>
            )}
            {event.persona && (
              <div>
                <span className="text-slate-500">Persona:</span>{' '}
                <span className="text-slate-400">{event.persona}</span>
              </div>
            )}
            {event.confidence && (
              <div>
                <span className="text-slate-500">Confianza:</span>{' '}
                <span className="text-slate-400">{(event.confidence * 100).toFixed(0)}%</span>
              </div>
            )}
            {event.language && (
              <div>
                <span className="text-slate-500">Idioma:</span>{' '}
                <span className="text-slate-400">{event.language}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
