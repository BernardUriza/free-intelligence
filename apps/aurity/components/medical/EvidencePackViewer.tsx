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
import { ROUTES } from '@/lib/api/routes';
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
    transcripcion_audio: <Activity className="evpack-docicon-cyan" />,
    lab_result: <FileText className="evpack-docicon-blue" />,
    clinical_note: <FileText className="evpack-docicon-green" />,
    prescription: <FileText className="evpack-docicon-purple" />,
    imaging: <FileText className="evpack-docicon-amber" />,
  };
  return icons[type] || <FileText className="evpack-docicon-default" />;
};

const SeverityBadge: React.FC<{ severity?: string }> = ({ severity }) => {
  if (!severity) return null;

  const colors = {
    leve: 'evpack-severity-leve',
    moderada: 'evpack-severity-moderada',
    grave: 'evpack-severity-grave',
  };

  return (
    <span className={`evpack-severity-wrap fi-text-xs-medium ${colors[severity as keyof typeof colors] || 'evpack-severity-default'}`}>
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
          `${ROUTES.medicalAi}/sessions/${sessionId}/evidence`
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
      <div className="evpack-container">
        <Card className="evpack-card">
          <CardContent className="py-12">
            <div className="fi-empty-state gap-4">
              <Loader2 className="evpack-loading-icon" />
              <p className="evpack-loading-text">Cargando Evidence Pack...</p>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (error || !pack) {
    return (
      <div className="evpack-container">
        <Card className="evpack-card">
          <CardContent className="py-8">
            <div className="evpack-warning-banner">
              <AlertCircle className="evpack-warning-icon fi-text-warning" />
              <p className="evpack-warning-text">
                {error || 'No se encontró Evidence Pack para esta sesión'}
              </p>
            </div>

            {/* Navigation */}
            <div className="evpack-error-nav">
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
    <div className="evpack-container-spaced">
      {/* Header Card */}
      <Card className="evpack-card-header">
        <CardHeader>
          <div className="evpack-header-row">
            <div className="fi-flex-gap-md">
              <div className="evpack-header-icon-box">
                <Shield className="evpack-header-shield fi-text-info" />
              </div>
              <div>
                <CardTitle className="evpack-card-title">Evidence Pack</CardTitle>
                <p className="evpack-subtitle">
                  ID: {pack.pack_id}
                </p>
              </div>
            </div>
            <div className="evpack-header-meta">
              <Badge className="evpack-badge-sources">
                <CheckCircle className="evpack-badge-icon" />
                {pack.sources.length} fuente{pack.sources.length !== 1 ? 's' : ''}
              </Badge>
              <div className="evpack-date-row">
                <Calendar className="evpack-date-icon" />
                {new Date(pack.created_at).toLocaleDateString('es-MX')}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Clinical Question */}
      {pack.consulta && (
        <Card className="evpack-card">
          <CardHeader>
            <CardTitle className="evpack-card-title-section">
              <Quote className="evpack-section-icon fi-text-purple" />
              Consulta Clínica
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="fi-text evpack-consulta-text">
              {pack.consulta}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Evidence-Based Response */}
      {pack.response && (
        <Card className="evpack-card">
          <CardHeader>
            <CardTitle className="evpack-card-title-section">
              <FileText className="evpack-section-icon fi-text-info" />
              Respuesta Basada en Evidencia
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="evpack-response-prose">
              <pre className="evpack-response-pre fi-text">
                {pack.response}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Sources */}
      <Card className="evpack-card">
        <CardHeader>
          <CardTitle className="evpack-card-title-section">
            <FileText className="evpack-section-icon fi-text-success" />
            Fuentes Clínicas ({pack.sources.length})
          </CardTitle>
        </CardHeader>
        <CardContent className="evpack-sources-list">
          {pack.sources.map((source, idx) => (
            <div
              key={source.source_id}
              className="evpack-source-card"
            >
              <div className="evpack-source-header">
                <div className="fi-flex-gap-md">
                  <DocumentTypeIcon type={source.tipo_doc} />
                  <div>
                    <h3 className="evpack-source-title">
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
                <div className="evpack-source-finding">
                  <p className="evpack-source-finding-text fi-text">
                    {source.hallazgo}
                  </p>
                </div>
              )}

              <div className="fi-flex-gap evpack-source-hash-row">
                <Hash className="evpack-source-hash-icon" />
                <code className="evpack-source-hash-code">
                  {pack.source_hashes[idx]?.slice(0, 16)}...
                </code>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Medical Disclaimer */}
      <div className="evpack-warning-banner">
        <AlertCircle className="evpack-warning-icon fi-text-warning" />
        <p className="evpack-warning-text">
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
          className="evpack-next-btn"
        >
          Siguiente
        </Button>
      </div>
    </div>
  );
}
