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

const STATUS_CONFIG: Record<DocumentStatus, { icon: typeof Clock; color: string; bg: string; label: string }> = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Pendiente' },
  processing: { icon: Loader2, color: 'fi-text-primary', bg: 'bg-blue-500/10', label: 'Procesando' },
  indexed: { icon: CheckCircle, color: 'fi-text-success', bg: 'bg-emerald-500/10', label: 'Indexado' },
  error: { icon: AlertCircle, color: 'fi-text-error', bg: 'bg-red-500/10', label: 'Error' },
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
        console.error('Error loading questions:', err);
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
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop with blur */}
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div
        className={`
          absolute bg-slate-900 border border-slate-700 shadow-2xl overflow-hidden
          flex flex-col
          transition-all duration-300 ease-out
          ${isFullscreen
            ? 'inset-2 rounded-xl'
            : 'inset-4 sm:inset-8 lg:inset-12 xl:inset-16 rounded-2xl'
          }
        `}
      >
        {/* Header */}
        <header className="flex items-center justify-between px-4 sm:px-6 py-4 fi-border-bottom bg-slate-800/50">
          <div className="flex items-center gap-3 min-w-0">
            {/* Document Type Icon */}
            <div className="p-2.5 rounded-xl bg-gradient-to-br from-slate-700 to-slate-800 border border-slate-600">
              <TypeIcon className="w-5 h-5 fi-text" />
            </div>

            {/* Title & Type */}
            <div className="min-w-0">
              <h2 className="fi-title truncate">
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
              className="hidden lg:flex"
              title={showMetadata ? 'Ocultar metadatos' : 'Mostrar metadatos'}
            >
              <Layers className="w-4 h-4" />
            </Button>

            {/* Fullscreen Toggle */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setIsFullscreen(!isFullscreen)}
              title={isFullscreen ? 'Salir de pantalla completa' : 'Pantalla completa'}
            >
              {isFullscreen ? (
                <Minimize2 className="w-4 h-4" />
              ) : (
                <Maximize2 className="w-4 h-4" />
              )}
            </Button>

            {/* Close Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="text-slate-400 hover:text-white"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
        </header>

        {/* Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Main Content Panel */}
          <main className="flex-1 flex flex-col overflow-hidden">
            {/* Toolbar */}
            <div className="flex items-center justify-between px-4 sm:px-6 py-3 fi-border-bottom/50 bg-slate-800/30">
              <div className="fi-flex-gap">
                {/* Status Badge */}
                <span
                  className={`
                    inline-flex items-center gap-1.5 px-3 py-1 rounded-full fi-text-xs-medium
                    ${statusConfig.bg} ${statusConfig.color} border border-current/20
                  `}
                >
                  <StatusIcon className={`w-3.5 h-3.5 ${docMeta.status === 'processing' ? 'animate-spin' : ''}`} />
                  {statusConfig.label}
                </span>

                {/* Chunks Count */}
                {docMeta.chunks_count > 0 && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-slate-700/50 fi-text-xs">
                    <Hash className="w-3 h-3" />
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
                  className="text-slate-400 hover:text-white"
                >
                  {copied ? (
                    <Check className="w-4 h-4 fi-text-success" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                  <span className="ml-1.5 hidden sm:inline">Copiar</span>
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDownload}
                  disabled={!fullDoc?.text || loading}
                  className="text-slate-400 hover:text-white"
                >
                  <Download className="w-4 h-4" />
                  <span className="ml-1.5 hidden sm:inline">Descargar</span>
                </Button>
              </div>
            </div>

            {/* Content Viewer */}
            <div className="flex-1 overflow-auto p-4 sm:p-6">
              {loading ? (
                <div className="fi-empty-state h-full text-slate-400">
                  <Loader2 className="w-10 h-10 animate-spin mb-4" />
                  <p>Cargando contenido...</p>
                </div>
              ) : error ? (
                <div className="fi-empty-state h-full fi-text-error">
                  <AlertCircle className="w-10 h-10 mb-4" />
                  <p className="font-medium">Error al cargar</p>
                  <p className="text-sm text-slate-500 mt-1">{error}</p>
                </div>
              ) : fullDoc?.text ? (
                <ContentRenderer
                  text={fullDoc.text}
                  docType={docMeta.doc_type}
                />
              ) : (
                <div className="fi-empty-state h-full text-slate-400">
                  <FileQuestion className="w-10 h-10 mb-4 opacity-50" />
                  <p>No hay contenido disponible</p>
                  <p className="text-sm text-slate-500 mt-1">
                    El documento no tiene texto extraído
                  </p>
                </div>
              )}
            </div>
          </main>

          {/* Metadata Sidebar */}
          {showMetadata && (
            <aside className="hidden lg:flex w-80 flex-col border-l border-slate-700 bg-slate-800/30 overflow-y-auto">
              <div className="p-6 space-y-6">
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
                      <span className="truncate" title={docMeta.filename}>
                        {docMeta.filename}
                      </span>
                    </MetadataItem>
                  )}
                </MetadataSection>

                {/* Usage Instructions */}
                {docMeta.usage_instructions && (
                  <MetadataSection title="Instrucciones de Uso" icon={FileCode}>
                    <p className="text-sm fi-text italic leading-relaxed">
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
                          color: 'text-slate-400',
                          label: personaId,
                        };
                        const PersonaIcon = config.icon;
                        return (
                          <div
                            key={personaId}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-700/30 border border-slate-600/50"
                          >
                            <PersonaIcon className={`w-4 h-4 ${config.color}`} />
                            <span className="text-sm fi-text">{config.label}</span>
                          </div>
                        );
                      })}
                    </div>
                  </MetadataSection>
                )}

                {/* Questions Section */}
                <MetadataSection title={`Preguntas (${questions.length})`} icon={HelpCircle}>
                  {loadingQuestions ? (
                    <div className="flex items-center gap-2 text-slate-400 text-sm">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Cargando...</span>
                    </div>
                  ) : questions.length === 0 ? (
                    <p className="text-slate-500 text-sm italic">Sin preguntas aún</p>
                  ) : (
                    <div className="space-y-3">
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
                    <div className="p-3 rounded-lg bg-red-900/20 border border-red-700/50">
                      <p className="text-sm fi-text-error">{docMeta.error_message}</p>
                    </div>
                  </MetadataSection>
                )}

                {/* Hash for verification */}
                <MetadataSection title="Verificación" icon={Hash} defaultCollapsed>
                  <div className="font-mono fi-text-xs-muted break-all p-2 bg-slate-900/50 rounded">
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
      className={`
        ${isCode ? 'font-mono text-sm' : 'text-base'}
        fi-text whitespace-pre-wrap leading-relaxed
        selection:bg-emerald-500/30
      `}
    >
      {/* Line numbers for code-like content */}
      {isCode ? (
        <div className="relative">
          {text.split('\n').map((line, i) => (
            <div key={i} className="flex group hover:bg-slate-800/30 -mx-2 px-2 rounded">
              <span className="w-10 flex-shrink-0 text-slate-600 text-right pr-4 select-none text-xs leading-6">
                {i + 1}
              </span>
              <span className="flex-1 leading-6">{line || ' '}</span>
            </div>
          ))}
        </div>
      ) : (
        <div className="prose prose-invert prose-slate max-w-none">
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
        className="flex items-center gap-2 w-full text-left mb-3 group"
        variant="ghost"
        size="sm"
        type="button"
      >
        {collapsed ? (
          <ChevronRight className="w-4 h-4 text-slate-500 group-hover:text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-500 group-hover:text-slate-400" />
        )}
        <Icon className="w-4 h-4 text-slate-400" />
        <span className="text-sm font-medium fi-text group-hover:text-white">
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
    <div className="flex items-start gap-2 text-sm">
      <Icon className="w-3.5 h-3.5 text-slate-500 mt-0.5 flex-shrink-0" />
      <span className="text-slate-500 flex-shrink-0">{label}:</span>
      <span className="fi-text min-w-0">{children}</span>
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
    <div className={`rounded-lg p-3 ${config.bgClass}`}>
      <div className={`flex items-center gap-2 mb-2 ${config.textClass}`}>
        <Icon className="w-4 h-4" />
        <span className="text-sm font-medium">
          {config.label} ({questions.length})
        </span>
      </div>
      <ul className="space-y-1.5">
        {questions.map((q) => (
          <li key={q.question_id} className="text-sm text-slate-300">
            <span className="text-slate-500 mr-1">•</span>
            {q.question}
            {source === 'user_query' && q.timestamp && (
              <span className="text-slate-500 text-xs ml-2">
                {formatRelativeTime(q.timestamp)}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
