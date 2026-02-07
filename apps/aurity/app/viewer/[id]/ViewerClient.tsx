'use client';

import { useEffect, useState, useCallback } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import {
  ArrowLeft,
  Download,
  CheckCircle,
  Loader2,
  AlertCircle,
  Eye,
  EyeOff,
} from 'lucide-react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { SplitView } from '@/components/layout/SplitView';
import { MetadataPanel } from '@/components/dashboard/MetadataPanel';
import type { Interaction } from '@/components/types/interaction';
import { api } from '@/lib/api/client';

export default function ViewerClient() {
  const params = useParams();
  const searchParams = useSearchParams();

  const id = params.id as string;
  const index = searchParams.get('index') ? parseInt(searchParams.get('index')!) : 0;

  const [interaction, setInteraction] = useState<Interaction | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [noSpoilers, setNoSpoilers] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);

  // Fetch interaction data
  useEffect(() => {
    interface SessionResponse {
      interactions?: Array<{
        id?: string;
        prompt?: string;
        user_message?: string;
        response?: string;
        assistant_message?: string;
        provider?: string;
        model?: string;
        latency_ms?: number;
        tokens_in?: number;
        prompt_tokens?: number;
        tokens_out?: number;
        completion_tokens?: number;
        content_hash?: string;
        manifest_hash?: string;
        created_at?: string;
        updated_at?: string;
        metadata?: Record<string, unknown>;
      }>;
      provider?: string;
      model?: string;
      created_at?: string;
    }

    interface MemoryResponse {
      events?: Array<{
        id?: string;
        content?: string;
        provider?: string;
        model?: string;
        duration?: number;
        content_hash?: string;
        timestamp?: number;
        metadata?: Record<string, unknown>;
      }>;
    }

    const fetchInteraction = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Try to fetch from sessions API
        const data = await api.get<SessionResponse>(
          `/api/aurity/medical-ai/sessions/${id}`
        );

        // Get interaction by index
        const interactions = data.interactions || [];
        const targetInteraction = interactions[index];

        if (!targetInteraction) {
          throw new Error(`Interaction ${index} not found in session`);
        }

        // Map to Interaction type
        setInteraction({
          id: targetInteraction.id || `${id}-${index}`,
          session_id: id,
          prompt: targetInteraction.prompt || targetInteraction.user_message || '',
          response: targetInteraction.response || targetInteraction.assistant_message || '',
          provider: targetInteraction.provider || data.provider || 'unknown',
          model: targetInteraction.model || data.model || 'unknown',
          latency_ms: targetInteraction.latency_ms,
          tokens_in: targetInteraction.tokens_in || targetInteraction.prompt_tokens,
          tokens_out: targetInteraction.tokens_out || targetInteraction.completion_tokens,
          content_hash: targetInteraction.content_hash || '',
          manifest_hash: targetInteraction.manifest_hash,
          created_at: targetInteraction.created_at || data.created_at || new Date().toISOString(),
          updated_at: targetInteraction.updated_at,
          metadata: targetInteraction.metadata || {},
        });
      } catch (err) {
        // Fallback: try to load from timeline/memory endpoint
        try {
          const memData = await api.get<MemoryResponse>(
            `/api/aurity/timeline/memory?session_id=${id}&limit=100`
          );

          const events = memData.events || [];
          const event = events[index];

          if (event) {
            setInteraction({
              id: event.id || `${id}-${index}`,
              session_id: id,
              prompt: event.content || '',
              response: '',
              provider: event.provider || 'unknown',
              model: event.model || 'unknown',
              latency_ms: event.duration,
              tokens_in: 0,
              tokens_out: 0,
              content_hash: event.content_hash || '',
              created_at: new Date((event.timestamp || 0) * 1000).toISOString(),
              metadata: event.metadata || {},
            });
            setError(null);
            return;
          }
        } catch {
          // Ignore fallback errors
        }

        setError(err instanceof Error ? err.message : 'Failed to load interaction');
      } finally {
        setIsLoading(false);
      }
    };

    if (id) {
      fetchInteraction();
    }
  }, [id, index]);

  // Copy handlers
  const handleCopyPrompt = useCallback(async () => {
    if (!interaction?.prompt) return;
    try {
      await navigator.clipboard.writeText(interaction.prompt);
      setCopiedPrompt(true);
      setTimeout(() => setCopiedPrompt(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [interaction?.prompt]);

  const handleCopyResponse = useCallback(async () => {
    if (!interaction?.response) return;
    try {
      await navigator.clipboard.writeText(interaction.response);
      setCopiedResponse(true);
      setTimeout(() => setCopiedResponse(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [interaction?.response]);

  // Export handler
  const handleExport = useCallback(async () => {
    if (!interaction) return;

    const exportData = {
      interaction: {
        id: interaction.id,
        session_id: interaction.session_id,
        prompt: noSpoilers ? '[HIDDEN]' : interaction.prompt,
        response: noSpoilers ? '[HIDDEN]' : interaction.response,
        provider: interaction.provider,
        model: interaction.model,
        latency_ms: interaction.latency_ms,
        tokens_in: interaction.tokens_in,
        tokens_out: interaction.tokens_out,
        content_hash: interaction.content_hash,
        manifest_hash: interaction.manifest_hash,
        created_at: interaction.created_at,
        updated_at: interaction.updated_at,
      },
      exported_at: new Date().toISOString(),
      no_spoilers: noSpoilers,
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `interaction-${interaction.id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }, [interaction, noSpoilers]);

  // Loading state
  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-10 w-10 animate-spin text-emerald-500 mx-auto mb-4" />
          <p className="text-slate-400">Loading interaction...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !interaction) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="text-center max-w-md p-6">
          <AlertCircle className="h-12 w-12 fi-text-error mx-auto mb-4" />
          <h1 className="text-xl font-semibold text-white mb-2">
            Failed to Load Interaction
          </h1>
          <p className="text-slate-400 mb-6">{error || 'Unknown error'}</p>
          <Button
            onClick={() => window.location.href = '/timeline'}
            variant="secondary"
            icon={ArrowLeft}
          >
            Back to Timeline
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 fi-border-bottom sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/timeline"
                className="p-2 rounded-lg fi-hover-interactive"
                aria-label="Back to timeline"
              >
                <ArrowLeft className="fi-icon-md" />
              </Link>
              <div>
                <h1 className="fi-title">
                  Interaction Viewer
                </h1>
                <p className="fi-subtitle">
                  Session: {id.substring(0, 12)}... • Index: {index}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {/* No Spoilers Toggle */}
              <button
                onClick={() => setNoSpoilers(!noSpoilers)}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                  noSpoilers
                    ? 'bg-amber-600 text-white'
                    : 'bg-slate-700 fi-text hover:bg-slate-600'
                }`}
                title={noSpoilers ? 'Show content' : 'Hide content (No Spoilers)'}
              >
                {noSpoilers ? (
                  <EyeOff className="fi-icon-sm" />
                ) : (
                  <Eye className="fi-icon-sm" />
                )}
                <span className="hidden sm:inline text-sm">
                  {noSpoilers ? 'Hidden' : 'Visible'}
                </span>
              </button>

              {/* Export Button */}
              <button
                onClick={handleExport}
                className="flex items-center gap-2 px-3 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
              >
                <Download className="h-4 w-4" />
                <span className="hidden sm:inline text-sm">Export</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Split View */}
        <SplitView
          interaction={interaction}
          noSpoilers={noSpoilers}
          onCopyPrompt={handleCopyPrompt}
          onCopyResponse={handleCopyResponse}
        />

        {/* Copy success indicators */}
        {(copiedPrompt || copiedResponse) && (
          <div className="fixed bottom-4 right-4 flex items-center gap-2 px-4 py-2 bg-emerald-600 text-white rounded-lg shadow-lg">
            <CheckCircle className="h-4 w-4" />
            Copied to clipboard!
          </div>
        )}

        {/* Metadata Panel */}
        <MetadataPanel interaction={interaction} />
      </main>
    </div>
  );
}
