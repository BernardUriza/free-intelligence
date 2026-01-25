'use client';

/**
 * HistorySearch Component
 *
 * Semantic search over user's conversation history.
 * Leverages backend embeddings (conversation_memory.h5) for
 * "la conversación que nunca termina" (FI-PHIL-DOC-014)
 */

import { useState } from 'react';
import { Search, Clock, TrendingUp, X, Lightbulb } from 'lucide-react';
import { useAuth } from '@aurity-standalone/hooks/useAuth';

export interface InteractionResult {
  session_id: string;
  timestamp: number;
  role: 'user' | 'assistant';
  content: string;
  persona?: string;
  similarity: number;
}

export interface HistorySearchResponse {
  results: InteractionResult[];
  total_interactions: number;
  query: string;
}

export interface HistorySearchProps {
  onSelectResult?: (result: InteractionResult) => void;
  mode?: 'panel' | 'modal';
  onClose?: () => void;
}

function getSimilarityClass(similarity: number): string {
  if (similarity >= 0.8) return 'chat-history-similarity-high';
  if (similarity >= 0.6) return 'chat-history-similarity-medium';
  if (similarity >= 0.4) return 'chat-history-similarity-low';
  return 'chat-history-similarity-minimal';
}

export function HistorySearch({ onSelectResult, mode = 'panel', onClose }: HistorySearchProps) {
  const { user } = useAuth();
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<InteractionResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalInteractions, setTotalInteractions] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async () => {
    if (!query.trim() || !user?.sub) return;

    setLoading(true);
    setError(null);

    try {
      const { assistantApi } = await import('@/lib/api/assistant');
      const data = await assistantApi.searchHistory({
        query: query.trim(),
        doctor_id: user.sub,
        limit: 20,
      });

      const transformedResults: InteractionResult[] = data.results.flatMap((item) => {
        const timestamp = Math.floor(new Date(item.timestamp).getTime() / 1000);
        const similarity = item.relevance_score ?? 0;
        const results: InteractionResult[] = [];

        if (item.query) {
          results.push({ session_id: item.session_id, timestamp, role: 'user', content: item.query, similarity });
        }
        if (item.response) {
          results.push({ session_id: item.session_id, timestamp, role: 'assistant', content: item.response, similarity });
        }
        return results;
      });

      setResults(transformedResults);
      setTotalInteractions(data.total_interactions ?? data.total);
    } catch (err) {
      console.error('History search error:', err);
      setError(err instanceof Error ? err.message : 'Error al buscar historial');
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: number) => {
    const date = new Date(timestamp * 1000);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'Hoy';
    if (diffDays === 1) return 'Ayer';
    if (diffDays < 7) return `Hace ${diffDays} días`;
    if (diffDays < 30) return `Hace ${Math.floor(diffDays / 7)} semanas`;
    if (diffDays < 365) return `Hace ${Math.floor(diffDays / 30)} meses`;
    return date.toLocaleDateString('es-MX');
  };

  const containerClass = mode === 'modal' ? 'chat-history-modal' : 'w-full h-full';
  const panelClass = mode === 'modal' ? 'chat-history-modal-content' : 'chat-history-panel';

  return (
    <div className={containerClass}>
      <div className={panelClass}>
        {/* Header */}
        <div className="chat-history-header">
          <div className="fi-flex-gap-md">
            <Search className="h-5 w-5 fi-text-purple" />
            <div>
              <h3 className="chat-history-title">Buscar en Historial</h3>
              {totalInteractions > 0 && (
                <p className="chat-history-subtitle">
                  {totalInteractions.toLocaleString()} interacciones almacenadas
                </p>
              )}
            </div>
          </div>

          {mode === 'modal' && onClose && (
            <button onClick={onClose} className="chat-history-close" aria-label="Cerrar">
              <X className="h-5 w-5" />
            </button>
          )}
        </div>

        {/* Search Input */}
        <div className="chat-history-search-bar">
          <div className="flex gap-3">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Busca temas, síntomas, diagnósticos..."
              className="chat-history-input"
            />
            <button
              onClick={handleSearch}
              disabled={loading || !query.trim()}
              className="chat-history-search-btn"
            >
              <Search className="h-4 w-4" />
              {loading ? 'Buscando...' : 'Buscar'}
            </button>
          </div>
          <p className="chat-history-hint flex items-center gap-1">
            <Lightbulb className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
            Búsqueda semántica: encuentra conversaciones por tema, no solo palabras exactas
          </p>
        </div>

        {/* Results */}
        <div className="chat-history-results">
          {error && <div className="chat-history-error">{error}</div>}

          {results.length === 0 && !error && !loading && query && (
            <div className="chat-history-empty">
              <Search className="chat-history-empty-icon" />
              <p>No se encontraron resultados para &quot;{query}&quot;</p>
              <p className="text-xs mt-2">Prueba con otros términos o conceptos</p>
            </div>
          )}

          {results.length === 0 && !query && (
            <div className="chat-history-empty">
              <Clock className="chat-history-empty-icon" />
              <p>Busca en tu historial completo</p>
              <p className="text-xs mt-2">Todas tus conversaciones están indexadas y listas para buscar</p>
            </div>
          )}

          {results.map((result, idx) => (
            <div
              key={`${result.session_id}-${idx}`}
              onClick={() => onSelectResult?.(result)}
              className="chat-history-result"
            >
              <div className="chat-history-result-header">
                <div className="fi-flex-gap">
                  <span className={getSimilarityClass(result.similarity)}>
                    <TrendingUp className="inline h-3 w-3 mr-1" />
                    {Math.round(result.similarity * 100)}% relevante
                  </span>
                  {result.persona && <span className="fi-text-xs-muted">{result.persona}</span>}
                </div>
                <span className="chat-history-timestamp">
                  <Clock className="h-3 w-3" />
                  {formatTimestamp(result.timestamp)}
                </span>
              </div>

              <div className="space-y-1">
                <div className="chat-history-role">
                  {result.role === 'user' ? 'Tú' : 'Free Intelligence'}
                </div>
                <p className="chat-history-content">{result.content}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Footer Stats */}
        {results.length > 0 && (
          <div className="chat-history-footer">
            <p className="chat-history-stats">
              Mostrando {results.length} de {totalInteractions.toLocaleString()} interacciones
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
