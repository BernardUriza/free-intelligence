/**
 * H5 Debug Modal
 *
 * Development-only modal for inspecting HDF5 session data.
 *
 * Features:
 * - Summary cards (duration, words, WPM, chunks)
 * - Full transcription display
 * - Chunk detail breakdown with status indicators
 * - Metadata panel (latency, audio availability)
 *
 * Trigger: Ctrl+Shift+H (development mode only)
 *
 * Author: Bernard Uriza Orozco
 * Created: 2025-11-15 (Extracted from ConversationCapture Phase 7)
 */

import { formatTime } from '@/lib/audio/formatting';
import { X, MessageSquare, Layers, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface H5Data {
  session_id: string;
  chunks?: Array<{
    index: number;
    transcript?: string;
    latency_ms?: number;
    status: string;
  }>;
  transcription_full: string;
  word_count: number;
  duration_seconds: number;
  avg_latency_ms?: number;
  wpm: number;
  full_audio_available: boolean;
}

interface H5DebugModalProps {
  h5Data: H5Data | null;
  isOpen: boolean;
  onClose: () => void;
}

export function H5DebugModal({ h5Data, isOpen, onClose }: H5DebugModalProps) {
  if (!isOpen || !h5Data) return null;

  return (
    <div className="fi-modal-backdrop bg-black/80 animate-in fade-in">
      <div className="bg-slate-900 rounded-2xl border border-yellow-500/50 max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col animate-in zoom-in duration-300">
        {/* Modal Header - DEV MODE WARNING */}
        <div className="px-6 py-4 border-b border-yellow-500/50 flex items-center justify-between bg-gradient-to-r from-yellow-900/20 to-slate-900">
          <div className="fi-flex-gap-md">
            <div className="px-2 py-1 bg-yellow-500/20 text-yellow-400 text-xs font-bold rounded border border-yellow-500/50">
              DEV TOOLS
            </div>
            <div>
              <h2 className="fi-title-xl">HDF5 Session Inspector</h2>
              <p className="fi-subtitle">Session ID: {h5Data.session_id}</p>
            </div>
          </div>
          <Button
            onClick={onClose}
            variant="ghost"
            size="sm"
            icon={X}
            aria-label="Cerrar"
          />
        </div>

        {/* Modal Body - Scrollable */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Summary Cards */}
          <div className="fi-grid-4">
            <div className="fi-card">
              <div className="fi-text-xs mb-1">Duración Total</div>
              <div className="text-2xl font-bold fi-text-info">{formatTime(h5Data.duration_seconds || 0)}</div>
            </div>
            <div className="fi-card">
              <div className="fi-text-xs mb-1">Palabras</div>
              <div className="text-2xl font-bold fi-text-success">{h5Data.word_count || 0}</div>
            </div>
            <div className="fi-card">
              <div className="fi-text-xs mb-1">WPM</div>
              <div className="text-2xl font-bold fi-text-purple">{h5Data.wpm || 0}</div>
            </div>
            <div className="fi-card">
              <div className="fi-text-xs mb-1">Chunks</div>
              <div className="text-2xl font-bold text-yellow-400">{h5Data.chunks?.length || 0}</div>
            </div>
          </div>

          {/* Full Transcription */}
          <div className="fi-card">
            <h3 className="fi-title-sm mb-3 flex items-center gap-2">
              <MessageSquare className="fi-icon-sm" />
              Transcripción Completa
            </h3>
            <div className="bg-slate-900/50 rounded p-3 max-h-48 overflow-y-auto">
              <p className="fi-text text-sm leading-relaxed whitespace-pre-wrap">
                {h5Data.transcription_full || 'No hay transcripción disponible'}
              </p>
            </div>
          </div>

          {/* Chunks Detail */}
          {h5Data.chunks && h5Data.chunks.length > 0 && (
            <div className="fi-card">
              <h3 className="fi-title-sm mb-3 flex items-center gap-2">
                <Layers className="fi-icon-sm" />
                Desglose por Chunks ({h5Data.chunks.length})
              </h3>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {h5Data.chunks.map((chunk, idx) => (
                  <div key={idx} className="bg-slate-900/50 rounded p-3 border border-slate-700/50">
                    <div className="flex items-start justify-between mb-2">
                      <div className="fi-flex-gap">
                        <span className="px-2 py-0.5 bg-cyan-500/20 fi-text-info rounded text-xs font-mono">
                          Chunk {chunk.index}
                        </span>
                        {chunk.latency_ms && (
                          <span className="fi-text-xs-muted">
                            {(chunk.latency_ms / 1000).toFixed(1)}s
                          </span>
                        )}
                      </div>
                      <span className={`px-2 py-0.5 rounded fi-text-xs-medium ${
                        chunk.status === 'completed' ? 'bg-emerald-500/20 fi-text-success' :
                        chunk.status === 'failed' ? 'bg-red-500/20 fi-text-error' :
                        'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {chunk.status}
                      </span>
                    </div>
                    <p className="fi-text text-sm">
                      {chunk.transcript || <span className="text-slate-600 italic">Sin transcripción</span>}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Metadata */}
          <div className="fi-card">
            <h3 className="fi-title-sm mb-3 flex items-center gap-2">
              <Info className="fi-icon-sm" />
              Metadatos
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-slate-900/50 rounded p-3">
                <div className="fi-text-xs mb-1">Latencia Promedio</div>
                <div className="text-lg font-mono fi-text-info">
                  {h5Data.avg_latency_ms ? `${(h5Data.avg_latency_ms / 1000).toFixed(2)}s` : 'N/A'}
                </div>
              </div>
              <div className="bg-slate-900/50 rounded p-3">
                <div className="fi-text-xs mb-1">Audio Completo</div>
                <div className="text-lg font-semibold">
                  {h5Data.full_audio_available ? (
                    <span className="fi-text-success">Disponible</span>
                  ) : (
                    <span className="text-slate-500">No disponible</span>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Modal Footer - DEV MODE INFO */}
        <div className="px-6 py-4 border-t border-yellow-500/50 flex items-center justify-between bg-slate-800/50">
          <p className="fi-text-xs">
            Hotkey: <kbd className="px-2 py-1 bg-slate-700 rounded text-yellow-400 font-mono">Ctrl+Shift+H</kbd>
          </p>
          <Button
            onClick={onClose}
            variant="ghost"
          >
            Cerrar
          </Button>
        </div>
      </div>
    </div>
  );
}
