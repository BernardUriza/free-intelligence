/**
 * DocumentPreviewModal - Creative Document Preview Component
 *
 * Features:
 * - Split-view layout with metadata sidebar
 * - Syntax highlighting for code/markdown
 * - Copy to clipboard functionality
 * - Download original file
 * - Chunk visualization for indexed documents
 * - Dark theme optimized
 *
 * Inspired by: Notion, GitHub, VS Code preview panels
 * Card: FI-UI-FEAT-021
 */

'use client';

import { useState, useEffect } from 'react';
import { createLogger } from '@/lib/internal/logger';
import {
  X,
  FileText,
  FileCode,
  Image as ImageIcon,
  File,
  FileQuestion,
  Copy,
  Check,
  Download,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2,
  Bot,
  Stethoscope,
  Hand,
  Hash,
  Calendar,
  User,
  HardDrive,
  Layers,
  ChevronDown,
  ChevronRight,
  Maximize2,
  Minimize2,
  HelpCircle,
  Sparkles,
  MessageCircle,
} from 'lucide-react';

const log = createLogger('DocumentPreview');
import { Button } from '@/components/ui/button';
import { fetchDocument, formatFileSize, formatDate, getDocumentQuestions } from '@aurity-standalone/api-client/knowledge';
import type { DocumentMetadata, Document, DocumentType, DocumentStatus, DocumentQuestion, QuestionSource } from '@aurity-standalone/types/knowledge';
import { toastSuccess, toastError } from '@/lib/swal';
import { QUESTION_SOURCE_CONFIG, formatRelativeTime } from './knowledge';

// =============================================================================
// TYPES & CONSTANTS
// =============================================================================

interface DocumentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: DocumentMetadata | null;
}

const TYPE_ICONS: Record<DocumentType, typeof FileText> = {
  pdf: FileText,
  docx: FileText,
  markdown: FileCode,
  text: File,
  image: ImageIcon,
  unknown: FileQuestion,
};

const TYPE_LABELS: Record<DocumentType, string> = {
  pdf: 'PDF Document',
  docx: 'Word Document',
  markdown: 'Markdown',
  text: 'Plain Text',
  image: 'Image',
  unknown: 'Unknown',
};

const STATUS_CONFIG: Record<DocumentStatus, { icon: typeof Clock; statusClass: string; label: string }> = {
  pending: { icon: Clock, statusClass: 'kno-status-pending', label: 'Pendiente' },
  processing: { icon: Loader2, statusClass: 'kno-status-processing', label: 'Procesando' },
  indexed: { icon: CheckCircle, statusClass: 'kno-status-indexed', label: 'Indexado' },
  error: { icon: AlertCircle, statusClass: 'kno-status-error', label: 'Error' },
};

const PERSONA_CONFIG: Record<string, { icon: typeof Bot; color: string; label: string }> = {
  general_assistant: { icon: Bot, color: 'fi-text-purple', label: 'General Assistant' },
  clinical_advisor: { icon: Stethoscope, color: 'fi-text-success', label: 'Clinical Advisor' },
  soap_editor: { icon: FileText, color: 'fi-text-primary', label: 'SOAP Editor' },
  onboarding_guide: { icon: Hand, color: 'fi-text-warning', label: 'Onboarding Guide' },
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function DocumentPreviewModal({ isOpen, onClose, document: docMeta }: DocumentPreviewModalProps) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fullDoc, setFullDoc] = useState<Document | null>(null);
  const [copied, setCopied] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showMetadata, setShowMetadata] = useState(true);
  const [questions, setQuestions] = useState<DocumentQuestion[]>([]);
  const [loadingQuestions, setLoadingQuestions] = useState(false);

  // Load full document with content when modal opens
  useEffect(() => {
    if (!isOpen || !docMeta) {
      setFullDoc(null);
      setError(null);
      return;
    }

    const loadDocument = async () => {
      setLoading(true);
      setError(null);
      try {
        const doc = await fetchDocument(docMeta.doc_id, true);
        setFullDoc(doc);
      } catch {
        setError('Error al cargar documento');
      } finally {
        setLoading(false);
      }
    };

    loadDocument();
  }, [isOpen, docMeta]);

  // Load questions when modal opens
  useEffect(() => {
    if (!isOpen || !docMeta?.doc_id) {
      setQuestions([]);
      return;
    }

    const loadQuestions = async () => {
      setLoadingQuestions(true);
      try {
        const qs = await getDocumentQuestions(docMeta.doc_id);
        setQuestions(qs);
      } catch (err) {
        log.error('Failed to load questions', { error: String(err) });
        setQuestions([]);
      } finally {
        setLoadingQuestions(false);
      }
    };

    loadQuestions();
  }, [isOpen, docMeta?.doc_id]);

  // Handle copy to clipboard
  const handleCopy = async () => {
    if (!fullDoc?.text) return;
    try {
      await navigator.clipboard.writeText(fullDoc.text);
      setCopied(true);
      toastSuccess('Contenido copiado');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toastError('Error al copiar');
    }
  };

  // Handle download
  const handleDownload = () => {
    if (!fullDoc?.text || !docMeta) return;
    const blob = new Blob([fullDoc.text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = docMeta.filename || `${docMeta.title}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toastSuccess('Descarga iniciada');
  };

  if (!isOpen || !docMeta) return null;

  const TypeIcon = TYPE_ICONS[docMeta.doc_type] || FileQuestion;
  const statusConfig = STATUS_CONFIG[docMeta.status];
  const StatusIcon = statusConfig.icon;

  return (
    <div className="kno-modal-overlay">
      {/* Backdrop with blur */}
      <div
        className="kno-modal-backdrop"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div
        className={`kno-modal-container ${isFullscreen ? 'kno-modal-fullscreen' : 'kno-modal-normal'}`}
      >
        {/* Header */}
        <header className="kno-header">
          <div className="kno-header-left">
            {/* Document Type Icon */}
            <div className="kno-type-icon-box">
              <TypeIcon className="kno-type-icon" />
            </div>

            {/* Title & Type */}
            <div className="kno-header-title-wrap">
              <h2 className="kno-title">
                {docMeta.title || docMeta.filename || 'Documento'}
              </h2>
              <p className="fi-text-xs">
                {TYPE_LABELS[docMeta.doc_type]} • {formatFileSize(docMeta.size_bytes)}
              </p>
            </div>
          </div>

          {/* Header Actions */}
          <div className="fi-flex-gap">
            {/* Toggle Metadata Sidebar */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowMetadata(!showMetadata)}
              className="kno-desktop-only"
              title={showMetadata ? 'Ocultar metadatos' : 'Mostrar metadatos'}
            >
              <Layers className="kno-btn-icon" />
            </Button>

            {/* Fullscreen Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsFullscreen(!isFullscreen)}
              title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
            >
              {isFullscreen ? (
                <Minimize2 className="kno-btn-icon" />
              ) : (
                <Maximize2 className="kno-btn-icon" />
              )}
            </Button>

            {/* Close Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="kno-ghost-action"
            >
              <X className="kno-close-icon" />
            </Button>
          </div>
        </header>

        {/* Content Area */}
        <div className="kno-content-wrap">
          {/* Main Content Panel */}
          <main className="kno-main-panel">
            {/* Toolbar */}
            <div className="kno-toolbar">
              <div className="fi-flex-gap">
                {/* Status Badge */}
                <span
                  className={`kno-status-badge ${statusConfig.statusClass}`}
                >
                  <StatusIcon className={`kno-status-icon ${docMeta.status === 'processing' ? 'animate-spin' : ''}`} />
                  {statusConfig.label}
                </span>

                {/* Chunks Count */}
                {docMeta.chunks_count > 0 && (
                  <span className="kno-chunks-badge">
                    <Hash className="kno-chunks-icon" />
                    {docMeta.chunks_count} chunks
                  </span>
                )}
              </div>

              {/* Content Actions */}
              <div className="fi-flex-gap">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleCopy}
                  disabled={!fullDoc?.text || loading}
                  className="kno-ghost-action"
                >
                  {copied ? (
                    <Check className="kno-btn-icon fi-text-success" />
                  ) : (
                    <Copy className="kno-btn-icon" />
                  )}
                  <span className="kno-action-label">Copiar</span>
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDownload}
                  disabled={!fullDoc?.text || loading}
                  className="kno-ghost-action"
                >
                  <Download className="kno-btn-icon" />
                  <span className="kno-action-label">Descargar</span>
                </Button>
              </div>
            </div>

            {/* Content Viewer */}
            <div className="kno-content-area">
              {loading ? (
                <div className="kno-state-muted">
                  <Loader2 className="kno-loading-spinner" />
                  <p>Cargando contenido...</p>
                </div>
              ) : error ? (
                <div className="kno-state-error-full">
                  <AlertCircle className="kno-state-icon" />
                  <p className="kno-error-title">Error al cargar</p>
                  <p className="kno-state-detail">{error}</p>
                </div>
              ) : fullDoc?.text ? (
                <ContentRenderer
                  text={fullDoc.text}
                  docType={docMeta.doc_type}
                />
              ) : (
                <div className="kno-state-muted">
                  <FileQuestion className="kno-empty-icon" />
                  <p>No hay contenido disponible</p>
                  <p className="kno-state-detail">
                    El documento no tiene texto extraído
                  </p>
                </div>
              )}
            </div>
          </main>

          {/* Metadata Sidebar */}
          {showMetadata && (
            <aside className="kno-sidebar">
              <div className="kno-sidebar-body">
                {/* Document Info Section */}
                <MetadataSection title="Información" icon={FileText}>
                  <MetadataItem icon={Calendar} label="Subido">
                    {formatDate(docMeta.uploaded_at)}
                  </MetadataItem>
                  <MetadataItem icon={User} label="Por">
                    {docMeta.uploaded_by || 'Sistema'}
                  </MetadataItem>
                  <MetadataItem icon={HardDrive} label="Tamaño">
                    {formatFileSize(docMeta.size_bytes)}
                  </MetadataItem>
                  {docMeta.filename && (
                    <MetadataItem icon={File} label="Archivo">
                      <span className="kno-filename" title={docMeta.filename}>
                        {docMeta.filename}
                      </span>
                    </MetadataItem>
                  )}
                </MetadataSection>

                {/* Usage Instructions */}
                {docMeta.usage_instructions && (
                  <MetadataSection title="Instrucciones de Uso" icon={FileCode}>
                    <p className="kno-usage-text">
                      &ldquo;{docMeta.usage_instructions}&rdquo;
                    </p>
                  </MetadataSection>
                )}

                {/* Assigned Personas */}
                {docMeta.assigned_personas && docMeta.assigned_personas.length > 0 && (
                  <MetadataSection title="Personas Asignadas" icon={Bot}>
                    <div className="fi-stack-sm">
                      {docMeta.assigned_personas.map((personaId) => {
                        const config = PERSONA_CONFIG[personaId] || {
                          icon: Bot,
                          color: 'kno-persona-icon-default',
                          label: personaId,
                        };
                        const PersonaIcon = config.icon;
                        return (
                          <div
                            key={personaId}
                            className="kno-persona-card"
                          >
                            <PersonaIcon className={`kno-persona-icon ${config.color}`} />
                            <span className="kno-persona-label">{config.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </MetadataSection>
                )}

                {/* Questions Section */}
                <MetadataSection title={`Preguntas (${questions.length})`} icon={HelpCircle}>
                  {loadingQuestions ? (
                    <div className="kno-questions-loading">
                      <Loader2 className="kno-qloading-icon" />
                      <span>Cargando...</span>
                    </div>
                  ) : questions.length === 0 ? (
                    <p className="kno-questions-empty">Sin preguntas aún</p>
                  ) : (
                    <div className="fi-stack-md">
                      <QuestionGroup
                        source="llm_initial"
                        questions={questions.filter(q => q.source === 'llm_initial')}
                      />
                      <QuestionGroup
                        source="user_query"
                        questions={questions.filter(q => q.source === 'user_query')}
                      />
                    </div>
                  )}
                </MetadataSection>

                {/* Error Message */}
                {docMeta.error_message && (
                  <MetadataSection title="Error" icon={AlertCircle}>
                    <div className="kno-error-card">
                      <p className="kno-error-text">{docMeta.error_message}</p>
                    </div>
                  </MetadataSection>
                )}

                {/* Hash for verification */}
                <MetadataSection title="Verificación" icon={Hash} defaultCollapsed>
                  <div className="kno-hash-display">
                    SHA256: {docMeta.sha256}
                  </div>
                </MetadataSection>
              </div>
            </aside>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// CONTENT RENDERER
// =============================================================================

function ContentRenderer({ text, docType }: { text: string; docType: DocumentType }) {
  // For markdown, we could add syntax highlighting in the future
  const isCode = docType === 'markdown' || docType === 'text';

  return (
    <div
      className={isCode ? 'kno-content-code' : 'kno-content-prose'}
    >
      {/* Line numbers for code-like content */}
      {isCode ? (
        <div className="relative">
          {text.split('\n').map((line, i) => (
            <div key={i} className="group kno-line-row">
              <span className="kno-line-number">
                {i + 1}
              </span>
              <span className="kno-line-content">{line || ' '}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="kno-content-rich">
          {text}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// METADATA COMPONENTS
// =============================================================================

interface MetadataSectionProps {
  title: string;
  icon: typeof FileText;
  children: React.ReactNode;
  defaultCollapsed?: boolean;
}

function MetadataSection({ title, icon: Icon, children, defaultCollapsed = false }: MetadataSectionProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <div>
      <Button
        onClick={() => setCollapsed(!collapsed)}
        className="group kno-meta-toggle"
        variant="ghost"
        size="sm"
        type="button"
      >
        {collapsed ? (
          <ChevronRight className="kno-meta-chevron" />
        ) : (
          <ChevronDown className="kno-meta-chevron" />
        )}
        <Icon className="kno-meta-section-icon" />
        <span className="kno-meta-title">
          {title}
        </span>
      </Button>
      {!collapsed && <div className="pl-6 fi-stack-sm">{children}</div>}
    </div>
  );
}

interface MetadataItemProps {
  icon: typeof FileText;
  label: string;
  children: React.ReactNode;
}

function MetadataItem({ icon: Icon, label, children }: MetadataItemProps) {
  return (
    <div className="kno-meta-item">
      <Icon className="kno-meta-item-icon" />
      <span className="kno-meta-item-label">{label}:</span>
      <span className="kno-meta-value">{children}</span>
    </div>
  );
}

// =============================================================================
// QUESTION GROUP COMPONENT
// =============================================================================

interface QuestionGroupProps {
  source: QuestionSource;
  questions: DocumentQuestion[];
}

function QuestionGroup({ source, questions }: QuestionGroupProps) {
  if (questions.length === 0) return null;

  const config = QUESTION_SOURCE_CONFIG[source];
  const Icon = config.icon;

  return (
    <div className={`kno-question-group ${config.bgClass}`}>
      <div className={`kno-question-header ${config.textClass}`}>
        <Icon className="kno-btn-icon" />
        <span className="kno-question-title">
          {config.label} ({questions.length})
        </span>
      </div>
      <ul className="kno-question-list">
        {questions.map((q) => (
          <li key={q.question_id} className="kno-question-item">
            <span className="kno-question-bullet">•</span>
            {q.question}
            {source === 'user_query' && q.timestamp && (
              <span className="kno-question-time">
                {formatRelativeTime(q.timestamp)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
