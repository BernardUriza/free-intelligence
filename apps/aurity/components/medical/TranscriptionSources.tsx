/**
 * TranscriptionSources - 3 separate sources display
 *
 * Shows 3 independent transcription sources (NO mixing):
 * 1. WebSpeech (instant preview, browser native)
 * 2. Whisper Chunks (high quality, per-chunk)
 * 3. Full Transcription (concatenated final)
 *
 * All 3 sources stored separately in HDF5 for LLM analysis during diarization.
 */

'use client';

import { useState, useEffect } from 'react';
import { Clock, RefreshCw, AlertTriangle, Music, Volume2, Check, Zap, Square, Lightbulb } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { getBackendUrl } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';

interface ChunkMetrics {
  chunk_number: number;
  text: string;
  provider?: string; // deepgram (primary), azure_whisper (deprecated)
  polling_attempts?: number;
  resolution_time_seconds?: number;
  retry_attempts?: number;
  confidence?: number;
  duration?: number;
}

interface TranscriptionSourcesProps {
  webSpeechTranscripts: string[];
  whisperChunks: Array<ChunkMetrics>;
  fullTranscription: string;
  sessionId?: string;
  isFinalized?: boolean;
  className?: string;
}

type ActiveTab = 'webspeech' | 'chunks' | 'full';

export function TranscriptionSources({
  webSpeechTranscripts,
  whisperChunks,
  fullTranscription,
  sessionId,
  isFinalized = false,
  className = '',
}: TranscriptionSourcesProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>('webspeech');
  const [audioError, setAudioError] = useState<string | null>(null);
  const [audioLoaded, setAudioLoaded] = useState(false);

  // Build audio URL if session is finalized
  const audioUrl = sessionId && isFinalized
    ? `${getBackendUrl()}${ROUTES.medicalAi}/sessions/${sessionId}/audio`
    : null;

  // Debug: Log audio URL only when it changes
  useEffect(() => {
    if (audioUrl) {
      console.log('[TranscriptionSources] Audio URL:', audioUrl);
    }
  }, [audioUrl]);

  const handleAudioError = (e: React.SyntheticEvent<HTMLAudioElement, Event>) => {
    const audio = e.currentTarget;
    const error = audio.error;
    let errorMessage = 'Error desconocido al cargar audio';

    if (error) {
      switch (error.code) {
        case MediaError.MEDIA_ERR_ABORTED:
          errorMessage = 'Carga de audio abortada';
          break;
        case MediaError.MEDIA_ERR_NETWORK:
          errorMessage = 'Error de red al cargar audio';
          break;
        case MediaError.MEDIA_ERR_DECODE:
          errorMessage = 'Error al decodificar audio';
          break;
        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
          errorMessage = 'Formato de audio no soportado o archivo no encontrado';
          break;
      }
    }

    console.error('[TranscriptionSources] Audio error:', errorMessage, error);
    setAudioError(errorMessage);
  };

  const handleAudioCanPlay = () => {
    console.log('[TranscriptionSources] Audio loaded successfully');
    setAudioLoaded(true);
    setAudioError(null);
  };

  return (
    <div className={`fi-panel rounded-xl p-4 ${className}`}>
      <h3 className="fi-title mb-3">Fuentes de Transcripción</h3>

      {/* Audio Player (only when finalized) */}
      {audioUrl && (
        <div className="mb-4 fi-card-dark">
          <div className="flex items-center gap-2 mb-2">
            <Volume2 className="h-5 w-5 fi-text-purple" />
            <span className="text-sm font-medium fi-text-purple">Audio de la Consulta</span>
            {audioLoaded && (
              <span className="text-xs fi-text-green ml-auto flex items-center gap-1">
                <Check className="w-3 h-3" aria-hidden="true" /> Cargado
              </span>
            )}
          </div>

          <audio
            controls
            controlsList="nodownload"
            className="w-full"
            src={audioUrl}
            preload="auto"
            onError={handleAudioError}
            onCanPlay={handleAudioCanPlay}
            onLoadedMetadata={() => console.log('[TranscriptionSources] Audio metadata loaded')}
          >
            Tu navegador no soporta reproducción de audio.
          </audio>

          {audioError && (
            <div className="mt-2 fi-alert-compact-danger flex items-start gap-1">
              <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" aria-hidden="true" />
              <div>
                {audioError}
                <div className="mt-1 fi-text-error/60">
                  URL: {audioUrl}
                </div>
              </div>
            </div>
          )}

          {!audioError && (
            <p className="fi-text-xs-muted mt-2 flex items-center gap-1">
              <Lightbulb className="w-3.5 h-3.5" aria-hidden="true" />
              Escucha la grabación completa de la consulta médica
            </p>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <Button
          onClick={() => setActiveTab('webspeech')}
          className={activeTab === 'webspeech' ? 'fi-tab-pill-blue px-4' : 'fi-tab-pill px-4'}
          variant="ghost"
          size="sm"
          type="button"
          title={`WebSpeech (${webSpeechTranscripts.length})`}
        >
          WebSpeech ({webSpeechTranscripts.length})
        </Button>
        <Button
          onClick={() => setActiveTab('chunks')}
          className={activeTab === 'chunks' ? 'fi-tab-pill-green px-4' : 'fi-tab-pill px-4'}
          variant="ghost"
          size="sm"
          type="button"
          title={`Whisper Chunks (${whisperChunks.length})`}
        >
          Whisper Chunks ({whisperChunks.length})
        </Button>
        <Button
          onClick={() => setActiveTab('full')}
          className={activeTab === 'full' ? 'fi-tab-pill-purple px-4' : 'fi-tab-pill px-4'}
          variant="ghost"
          size="sm"
          type="button"
          title="Full Transcription"
        >
          Full Transcription
        </Button>
      </div>

      {/* Content with scroll */}
      <div className="fi-card-dark max-h-96 overflow-y-auto">
        {activeTab === 'webspeech' && (
          <div className="space-y-2">
            {webSpeechTranscripts.length === 0 ? (
              <p className="text-slate-400 text-sm italic">
                No hay transcripciones de WebSpeech aún...
              </p>
            ) : (
              webSpeechTranscripts.map((text, idx) => (
                <div
                  key={idx}
                  className="fi-transcript-item-blue"
                >
                  <span className="fi-text-primary font-mono text-xs mr-2">[{idx}]</span>
                  {text}
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'chunks' && (
          <div className="space-y-3">
            {whisperChunks.length === 0 ? (
              <p className="text-slate-400 text-sm italic">
                Esperando chunks de Whisper (~20s por chunk)...
              </p>
            ) : (
              whisperChunks.map((chunk, idx) => {
                const provider = chunk.provider || 'unknown';
                const pollingAttempts = chunk.polling_attempts || 0;
                const resolutionTime = chunk.resolution_time_seconds || 0;
                const retryAttempts = chunk.retry_attempts || 0;
                const confidence = chunk.confidence || 0;

                // Badge class for provider
                const providerBadge = provider === 'deepgram'
                  ? 'fi-badge-info'
                  : 'fi-badge-secondary'; // azure_whisper (deprecated) & others

                // Warning colors for high metrics
                const pollingColor = pollingAttempts > 5 ? 'text-yellow-400' : 'text-slate-400';
                const retryColor = retryAttempts > 0 ? 'text-orange-400' : 'text-slate-400';
                const timeColor = resolutionTime > 10 ? 'fi-text-error' : resolutionTime > 5 ? 'text-yellow-400' : 'fi-text-green';

                return (
                  <div
                    key={idx}
                    className="fi-transcript-item-green rounded-lg p-3"
                  >
                    {/* Header with chunk number and provider */}
                    <div className="flex items-center gap-2 mb-2 flex-wrap">
                      <span className="fi-label-mono-green">
                        [Chunk {chunk.chunk_number}]
                      </span>
                      <span className={`${providerBadge} flex items-center gap-1`}>
                        {provider === 'deepgram' && <Zap className="w-3 h-3" aria-hidden="true" />}
                        {provider === 'azure_whisper' && <Square className="w-3 h-3" aria-hidden="true" />}
                        {provider === 'deepgram' ? 'Deepgram' : provider === 'azure_whisper' ? 'Azure (deprecated)' : provider}
                      </span>
                      {confidence > 0 && (
                        <span className="fi-text-xs">
                          {(confidence * 100).toFixed(0)}% conf
                        </span>
                      )}
                    </div>

                    {/* Transcript text */}
                    <div className="text-green-200 mb-2">
                      {chunk.text}
                    </div>

                    {/* Metrics row */}
                    <div className="fi-metric-row border-t border-green-500/20 pt-2">
                      <span className={`fi-metric-item ${timeColor}`}>
                        <Clock className="fi-metric-icon" />
                        {resolutionTime.toFixed(1)}s
                      </span>

                      <span className={`fi-metric-item ${pollingColor}`} title="Polling attempts">
                        <RefreshCw className="fi-metric-icon" />
                        {pollingAttempts}p
                      </span>

                      {retryAttempts > 0 && (
                        <span className={`fi-metric-item ${retryColor}`} title="Retry attempts">
                          <AlertTriangle className="fi-metric-icon" />
                          {retryAttempts}r
                        </span>
                      )}

                      {chunk.duration && chunk.duration > 0 && (
                        <span className="fi-metric-item text-slate-400" title="Audio duration">
                          <Music className="fi-metric-icon" />
                          {chunk.duration.toFixed(1)}s
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}

        {activeTab === 'full' && (
          <div className="text-sm text-slate-200 leading-relaxed">
            {fullTranscription ? (
              <p className="whitespace-pre-wrap">{fullTranscription}</p>
            ) : (
              <p className="text-slate-400 italic">
                La transcripción completa se generará al finalizar la sesión...
              </p>
            )}
          </div>
        )}
      </div>

      {/* Info badge */}
      <div className="mt-3 fi-text-xs flex items-start gap-1">
        <Lightbulb className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" aria-hidden="true" />
        Las 3 fuentes se almacenan por separado en HDF5 para análisis del LLM durante
        diarización
      </div>
    </div>
  );
}
