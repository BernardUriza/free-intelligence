"use client";

/**
 * SessionAuditPanel - Doctor review and feedback UI
 *
 * Allows doctor to:
 * - Review SOAP notes with inline corrections
 * - See orchestration steps (complexity, personas, confidence)
 * - View safety flags (low confidence, medication interactions)
 * - Submit rating and feedback (approve/reject/needs_review)
 *
 * Based on: docs/designs/patient-manager-feedback-design.md
 */

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  X,
  AlertTriangle,
  FileText,
  Stethoscope,
  Brain,
  MessageSquare,
  Star,
  CheckCircle2,
  XOctagon,
  Clock,
} from 'lucide-react';
import { showWarning, toastError } from '@/lib/swal';
import { api } from '@/lib/api/client';

// Types
interface AuditData {
  session_id: string;
  patient: {
    id?: string;
    name?: string;
    age?: number;
    comorbidities?: string[];
  };
  session_metadata: {
    date: string;
    duration_seconds: number;
    doctor: string;
    status: 'pending_review' | 'approved' | 'rejected';
  };
  orchestration: {
    strategy: string;
    personas_invoked: string[];
    confidence_score: number;
    complexity_score: number;
    steps: OrchestrationStep[];
  };
  soap_note: {
    subjective?: string;
    objective?: string;
    assessment?: any;
    plan?: any;
  };
  diarization: {
    segments: any[];
  };
  flags: Flag[];
  doctor_feedback: any | null;
}

interface Flag {
  type: string;
  severity: 'critical' | 'warning';
  message: string;
  location: string;
}

interface OrchestrationStep {
  step: number;
  persona: string;
  timestamp: string;
  output: any;
  duration_ms?: number;
}

interface Correction {
  section: string;
  original: string;
  corrected: string;
  timestamp: string;
}

interface DoctorFeedback {
  rating: number | null;
  comments: string;
  corrections: Correction[];
}

interface SessionAuditPanelProps {
  sessionId: string;
  isOpen: boolean;
  onClose: () => void;
  onApprove?: () => void;
  onReject?: () => void;
}

export function SessionAuditPanel({
  sessionId,
  isOpen,
  onClose,
  onApprove,
  onReject,
}: SessionAuditPanelProps) {
  const [auditData, setAuditData] = useState<AuditData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'overview' | 'soap' | 'orchestration' | 'transcript'>('overview');
  const [feedback, setFeedback] = useState<DoctorFeedback>({
    rating: null,
    comments: '',
    corrections: [],
  });
  const [submitting, setSubmitting] = useState(false);

  // Fetch audit data
  useEffect(() => {
    if (!isOpen || !sessionId) return;

    async function fetchAuditData() {
      try {
        setLoading(true);
        setError(null);

        const data = await api.get<AuditData>(`/api/sessions/${sessionId}/audit`);
        setAuditData(data);
      } catch (err) {
        console.error('Failed to load audit data:', err);
        setError(err instanceof Error ? err.message : 'Error al cargar auditoría');
      } finally {
        setLoading(false);
      }
    }

    fetchAuditData();
  }, [isOpen, sessionId]);

  // Submit feedback
  async function handleSubmit(decision: 'approved' | 'rejected' | 'needs_review') {
    if (!feedback.rating) {
      await showWarning('Calificación requerida', 'Por favor califica la sesión (1-5 estrellas)');
      return;
    }

    try {
      setSubmitting(true);

      await api.post(`/api/sessions/${sessionId}/feedback`, {
        rating: feedback.rating,
        comments: feedback.comments,
        corrections: feedback.corrections,
        decision,
      });

      // Success!
      if (decision === 'approved' && onApprove) onApprove();
      if (decision === 'rejected' && onReject) onReject();

      onClose();
    } catch (err) {
      console.error('Failed to submit feedback:', err);
      toastError(err instanceof Error ? err.message : 'Error al enviar feedback');
    } finally {
      setSubmitting(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" onClick={onClose} />

      {/* Panel - Slide-over from right */}
      <div className="fi-panel-slide">
        {/* Header */}
        <div className="fi-panel-slide-header">
          <div className="fi-flex-between">
            <div>
              <h2 className="text-xl sm:fi-title-2xl">
                Auditoría de Sesión
              </h2>
              {auditData && (
                <p className="fi-subtitle mt-1">
                  {auditData.patient.name || 'Paciente'} · {new Date(auditData.session_metadata.date).toLocaleDateString('es-MX')}
                </p>
              )}
            </div>

            {/* Quick Actions */}
            <div className="fi-flex-gap">
              <Button
                onClick={() => handleSubmit('approved')}
                disabled={!feedback.rating || submitting}
                variant="success"
                icon={CheckCircle2}
              >
                Aprobar
              </Button>
              <Button
                onClick={() => handleSubmit('rejected')}
                disabled={!feedback.rating || submitting}
                variant="danger"
                icon={XOctagon}
              >
                Rechazar
              </Button>
              <Button
                onClick={onClose}
                className="fi-btn-icon-sm"
                variant="ghost"
                size="sm"
                type="button"
                aria-label="Close"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>
          </div>

          {/* Flags Banner */}
          {auditData && auditData.flags.length > 0 && (
            <div className="mt-4 space-y-2">
              {auditData.flags.map((flag, idx) => (
                <div
                  key={idx}
                  className={`p-3 rounded-lg border flex items-start gap-3 ${
                    flag.severity === 'critical'
                      ? 'bg-red-900/20 border-red-700'
                      : 'bg-yellow-900/20 border-yellow-700'
                  }`}
                >
                  <AlertTriangle className={`w-5 h-5 flex-shrink-0 ${
                    flag.severity === 'critical' ? 'fi-text-error' : 'text-yellow-400'
                  }`} />
                  <div className="flex-1 min-w-0">
                    <div className="fi-title-sm">
                      {flag.type.replace(/_/g, ' ').toUpperCase()}
                    </div>
                    <div className="text-sm fi-text mt-1">{flag.message}</div>
                    <div className="fi-text-xs-muted mt-1">Ubicación: {flag.location}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Content */}
        <div className="p-4 sm:p-6">
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500" />
            </div>
          )}

          {error && (
            <div className="p-4 bg-red-900/20 border border-red-700 rounded-lg fi-text-error">
              {error}
            </div>
          )}

          {auditData && (
            <>
              {/* Tabs */}
              <div className="flex gap-2 mb-6 fi-border-bottom overflow-x-auto">
                {[
                  { id: 'overview', label: 'Overview', icon: FileText },
                  { id: 'soap', label: 'SOAP', icon: Stethoscope },
                  { id: 'orchestration', label: 'Razonamiento IA', icon: Brain },
                  { id: 'transcript', label: 'Transcripción', icon: MessageSquare },
                ].map(tab => (
                  <Button
                    key={tab.id}
                    type="button"
                    onClick={() => setActiveTab(tab.id as any)}
                    className={`fi-tab-underline fi-tab-with-icon ${
                      activeTab === tab.id ? 'fi-tab-active-blue' : 'fi-tab-inactive'
                    }`}
                    variant={activeTab === tab.id ? 'primary' : 'ghost'}
                    size="sm"
                    aria-pressed={activeTab === tab.id}
                  >
                    <tab.icon className="fi-icon-sm" />
                    {tab.label}
                  </Button>
                ))}
              </div>

              {/* Tab Content */}
              {activeTab === 'overview' && (
                <OverviewTab data={auditData} />
              )}

              {activeTab === 'soap' && (
                <SOAPTab
                  soapNote={auditData.soap_note}
                  onCorrection={(correction) => {
                    setFeedback({
                      ...feedback,
                      corrections: [...feedback.corrections, correction],
                    });
                  }}
                />
              )}

              {activeTab === 'orchestration' && (
                <OrchestrationTab
                  orchestration={auditData.orchestration}
                />
              )}

              {activeTab === 'transcript' && (
                <TranscriptTab segments={auditData.diarization.segments} />
              )}

              {/* Feedback Form */}
              <div className="mt-8 pt-6 fi-border-top">
                <h3 className="fi-title mb-4">
                  Feedback del Doctor
                </h3>

                {/* Rating */}
                <div className="mb-4">
                  <label className="fi-label">
                    Calidad General del Procesamiento
                  </label>
                  <div className="flex gap-2">
                    {[1, 2, 3, 4, 5].map((rating) => (
                          <Button
                            key={rating}
                            onClick={() => setFeedback({ ...feedback, rating })}
                            className={`p-3 rounded-lg transition-all ${
                              feedback.rating === rating
                                ? 'bg-yellow-500 text-white scale-110'
                                : 'bg-slate-700 text-slate-400 hover:bg-slate-600'
                            }`}
                            variant={feedback.rating === rating ? 'primary' : 'ghost'}
                            size="sm"
                            type="button"
                            aria-pressed={feedback.rating === rating}
                          >
                            <Star className={`w-5 h-5 ${feedback.rating !== null && rating <= feedback.rating ? 'fill-current' : ''}`} />
                          </Button>
                        ))}
                  </div>
                </div>

                {/* Comments */}
                <div className="mb-4">
                  <label className="fi-label">
                    Comentarios Adicionales
                  </label>
                  <textarea
                    className="fi-textarea-panel"
                    rows={4}
                    placeholder="Ej: El diagnóstico es correcto pero faltó mencionar el seguimiento a 3 meses..."
                    value={feedback.comments}
                    onChange={(e) => setFeedback({ ...feedback, comments: e.target.value })}
                  />
                </div>

                {/* Corrections Summary */}
                {feedback.corrections.length > 0 && (
                  <div className="mb-4 p-3 bg-blue-950/20 border border-blue-900 rounded-lg">
                    <div className="text-sm font-semibold fi-text-primary mb-2">
                      Correcciones Aplicadas ({feedback.corrections.length})
                    </div>
                    <ul className="text-xs fi-text space-y-1">
                      {feedback.corrections.map((corr, idx) => (
                        <li key={idx} className="break-words">
                          • {corr.section}: &quot;{corr.original.substring(0, 30)}...&quot; → &quot;{corr.corrected.substring(0, 30)}...&quot;
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Helper components (simplified versions - full implementations would be longer)

function OverviewTab({ data }: { data: AuditData }) {
  return (
    <div className="space-y-6">
      <div className="fi-grid-4">
        <MetricCard label="Estrategia" value={data.orchestration.strategy} color="blue" />
        <MetricCard label="Pasos" value={data.orchestration.personas_invoked.length} color="purple" />
        <MetricCard label="Confianza" value={`${(data.orchestration.confidence_score * 100).toFixed(0)}%`} color="emerald" />
        <MetricCard label="Complejidad" value={data.orchestration.complexity_score.toFixed(1)} color="amber" />
      </div>
    </div>
  );
}

function MetricCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="fi-card-solid">
      <div className="fi-text-xs-muted mb-1">{label}</div>
      <div className={`text-2xl font-bold text-${color}-400`}>{value}</div>
    </div>
  );
}

function SOAPTab({ soapNote, onCorrection: _onCorrection }: { soapNote: any; onCorrection: (c: Correction) => void }) {
  return (
    <div className="space-y-4 fi-text">
      <p className="text-sm">SOAP editing implementation would go here (see design doc for details)</p>
      <pre className="p-4 bg-slate-800 rounded-lg text-xs overflow-x-auto">
        {JSON.stringify(soapNote, null, 2)}
      </pre>
    </div>
  );
}

function OrchestrationTab({ orchestration }: { orchestration: AuditData['orchestration'] }) {
  return (
    <div className="fi-stack-lg">
      <div className="text-sm fi-text">
        <strong>Estrategia:</strong> {orchestration.strategy}
      </div>
      <div className="text-sm fi-text">
        <strong>Personas Invoked:</strong> {orchestration.personas_invoked.join(' → ')}
      </div>
      {orchestration.steps.length > 0 && (
        <div className="space-y-3">
          {orchestration.steps.map((step, idx) => (
            <div key={idx} className="fi-card-solid">
              <div className="fi-title-sm">
                Step {step.step}: {step.persona}
              </div>
              <div className="fi-text-xs mt-1">
                {new Date(step.timestamp).toLocaleTimeString('es-MX')}
              </div>
              {step.duration_ms && (
                <div className="fi-text-xs-muted mt-1">
                  <Clock className="w-3 h-3 inline mr-1" />
                  {step.duration_ms}ms
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TranscriptTab({ segments }: { segments: any[] }) {
  return (
    <div className="fi-stack-sm">
      {segments.length === 0 && (
        <p className="text-slate-400 text-sm">No hay segmentos de diarización disponibles.</p>
      )}
      {segments.map((seg, idx) => (
        <div key={idx} className="p-3 bg-slate-800 rounded-lg">
          <div className="fi-text-xs-muted">{seg.speaker || 'Unknown'}</div>
          <div className="text-sm fi-text mt-1">{seg.text || seg.transcript}</div>
        </div>
      ))}
    </div>
  );
}
