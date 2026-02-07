'use client';

/**
 * Evidence Pack Viewer Component
 * Integrated into Medical AI Workflow
 * FI-DATA-RES-021: Evidence Packs Implementation
 */

import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { api } from '@/lib/api/client';
import {
  FileText,
  Hash,
  Calendar,
  Shield,
  AlertCircle,
  CheckCircle,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Quote,
  Activity
} from 'lucide-react';
import { Button } from '@/components/ui/button';

interface Citation {
  citation_id: number;
  source_id: string;
  text: string;
  page_number?: number;
  confidence: number;
}

interface ClinicalSource {
  source_id: string;
  tipo_doc: string;
  fecha: string;
  paciente_id: string;
  hallazgo?: string;
  severidad?: string;
  raw_text?: string;
  citations?: Citation[];
}

interface EvidencePack {
  pack_id: string;
  created_at: string;
  session_id?: string;
  sources: ClinicalSource[];
  source_hashes: string[];
  policy_snapshot_id: string;
  citations?: Citation[];
  consulta?: string;
  response?: string;
}

interface EvidencePackViewerProps {
  sessionId?: string;
  onNext?: () => void;
  onPrevious?: () => void;
}

const DocumentTypeIcon: React.FC<{ type: string }> = ({ type }) => {
  const icons: { [key: string]: JSX.Element } = {
    transcripcion_audio: <Activity className="w-4 h-4 text-cyan-500" />,
    lab_result: <FileText className="w-4 h-4 text-blue-500" />,
    clinical_note: <FileText className="w-4 h-4 text-green-500" />,
    prescription: <FileText className="w-4 h-4 text-purple-500" />,
    imaging: <FileText className="w-4 h-4 text-amber-500" />,
  };
  return icons[type] || <FileText className="w-4 h-4 text-slate-400" />;
};

const SeverityBadge: React.FC<{ severity?: string }> = ({ severity }) => {
  if (!severity) return null;

  const colors = {
    leve: 'bg-green-500/10 fi-text-green border-green-500/30',
    moderada: 'bg-amber-500/10 fi-text-warning border-amber-500/30',
    grave: 'bg-red-500/10 fi-text-error border-red-500/30',
  };

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-md fi-text-xs-medium border ${colors[severity as keyof typeof colors] || 'bg-slate-500/10 text-slate-400 border-slate-500/30'}`}>
      {severity}
    </span>
  );
};

export function EvidencePackViewer({ sessionId, onNext, onPrevious }: EvidencePackViewerProps) {
  const [pack, setPack] = useState<EvidencePack | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchEvidencePack = async () => {
      if (!sessionId) {
        setError('No session ID provided');
        setLoading(false);
        return;
      }

      try {
        // Fetch evidence pack from workflow API (auto-generates if not exists)
        const data = await api.get<{ session_id: string; evidence_pack: EvidencePack }>(
          `/api/aurity/medical-ai/sessions/${sessionId}/evidence`
        );
        setPack(data.evidence_pack);  // Backend wraps in { session_id, evidence_pack }

        console.log('[EvidencePackViewer] Loaded evidence pack:', data.evidence_pack.pack_id);
      } catch (err) {
        console.error('[EvidencePackViewer] Error loading evidence pack:', err);

        const errorMsg = err instanceof Error ? err.message : String(err);
        // Check if it's a "not found" error (expected when SOAP doesn't exist yet)
        const isNoDataError = errorMsg.includes('not found') ||
                             errorMsg.includes('404') ||
                             errorMsg.includes('does not exist');

        if (isNoDataError) {
          console.log('[EvidencePackViewer] Evidence pack not ready yet');
          setError('El Evidence Pack se generará cuando las notas SOAP estén disponibles');
        } else {
          setError(err instanceof Error ? err.message : 'Failed to load evidence pack');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchEvidencePack();
  }, [sessionId]);

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto">
        <Card className="bg-slate-900/50 border-slate-800/50">
          <CardContent className="py-12">
            <div className="fi-empty-state gap-4">
              <Loader2 className="h-8 w-8 text-cyan-500 animate-spin" />
              <p className="text-slate-400">Cargando Evidence Pack...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !pack) {
    return (
      <div className="max-w-5xl mx-auto">
        <Card className="bg-slate-900/50 border-slate-800/50">
          <CardContent className="py-8">
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex items-start gap-3">
              <AlertCircle className="h-4 w-4 fi-text-warning mt-0.5 flex-shrink-0" />
              <p className="text-amber-300 text-sm">
                {error || 'No se encontró Evidence Pack para esta sesión'}
              </p>
            </div>

            {/* Navigation */}
            <div className="flex items-center justify-between mt-6">
              <Button
                onClick={onPrevious}
                variant="secondary"
                icon={ChevronLeft}
              >
                Anterior
              </Button>
              <Button
                onClick={onNext}
                variant="cyan"
                icon={ChevronRight}
              >
                Siguiente
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header Card */}
      <Card className="bg-gradient-to-br from-cyan-500/10 to-purple-500/10 border-cyan-500/30">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="fi-flex-gap-md">
              <div className="w-12 h-12 bg-cyan-500/20 rounded-xl flex items-center justify-center">
                <Shield className="h-6 w-6 fi-text-info" />
              </div>
              <div>
                <CardTitle className="text-white">Evidence Pack</CardTitle>
                <p className="fi-subtitle mt-1">
                  ID: {pack.pack_id}
                </p>
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              <Badge className="bg-emerald-500/10 fi-text-success border border-emerald-500/30">
                <CheckCircle className="h-3 w-3 mr-1" />
                {pack.sources.length} fuente{pack.sources.length !== 1 ? 's' : ''}
              </Badge>
              <div className="fi-flex-gap fi-text-xs">
                <Calendar className="h-3 w-3" />
                {new Date(pack.created_at).toLocaleDateString('es-MX')}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Clinical Question */}
      {pack.consulta && (
        <Card className="bg-slate-900/50 border-slate-800/50">
          <CardHeader>
            <CardTitle className="text-lg text-white fi-flex-gap">
              <Quote className="h-5 w-5 fi-text-purple" />
              Consulta Clínica
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="fi-text text-base leading-relaxed">
              {pack.consulta}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Evidence-Based Response */}
      {pack.response && (
        <Card className="bg-slate-900/50 border-slate-800/50">
          <CardHeader>
            <CardTitle className="text-lg text-white fi-flex-gap">
              <FileText className="h-5 w-5 fi-text-info" />
              Respuesta Basada en Evidencia
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose prose-invert prose-sm max-w-none">
              <pre className="whitespace-pre-wrap fi-text text-sm leading-relaxed font-sans bg-slate-800/50 p-4 rounded-lg">
                {pack.response}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sources */}
      <Card className="bg-slate-900/50 border-slate-800/50">
        <CardHeader>
          <CardTitle className="text-lg text-white fi-flex-gap">
            <FileText className="h-5 w-5 fi-text-success" />
            Fuentes Clínicas ({pack.sources.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {pack.sources.map((source, idx) => (
            <div
              key={source.source_id}
              className="p-4 bg-slate-800/50 border border-slate-700/50 rounded-xl"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="fi-flex-gap-md">
                  <DocumentTypeIcon type={source.tipo_doc} />
                  <div>
                    <h3 className="text-white font-semibold">
                      {source.tipo_doc.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </h3>
                    <p className="fi-text-xs">
                      {new Date(source.fecha).toLocaleDateString('es-MX')}
                    </p>
                  </div>
                </div>
                <SeverityBadge severity={source.severidad} />
              </div>

              {source.hallazgo && (
                <div className="mb-3">
                  <p className="text-sm fi-text">
                    {source.hallazgo}
                  </p>
                </div>
              )}

              <div className="fi-flex-gap text-xs">
                <Hash className="h-3 w-3 text-slate-500" />
                <code className="text-slate-400 font-mono text-xs">
                  {pack.source_hashes[idx]?.slice(0, 16)}...
                </code>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Medical Disclaimer */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="h-4 w-4 fi-text-warning mt-0.5 flex-shrink-0" />
        <p className="text-amber-300 text-sm">
          <strong>Nota importante:</strong> Esta respuesta contiene únicamente evidencia extraída de los documentos fuente.
          No constituye un diagnóstico médico. Toda decisión clínica debe ser validada por un profesional de la salud.
        </p>
      </div>

      {/* Navigation */}
      <div className="fi-flex-between">
        <Button
          onClick={onPrevious}
          variant="secondary"
          size="lg"
          icon={ChevronLeft}
        >
          Anterior
        </Button>
        <Button
          onClick={onNext}
          variant="cyan"
          size="lg"
          icon={ChevronRight}
          className="shadow-lg shadow-cyan-500/20"
        >
          Siguiente
        </Button>
      </div>
    </div>
  );
}
