"use client";

/**
 * Export Report Component - Phase 7 (FI-ONBOARD-008)
 *
 * Export onboarding evidence in multiple formats with preview
 */

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { FileText, Package, Wrench, Globe, Download, Lightbulb, CheckCircle, XCircle } from 'lucide-react';
import {
  OnboardingEvidence,
  generateMarkdownExport,
  generateJSONExport,
  generateHTMLExport,
  downloadFile,
} from "@/lib/export-evidence";

interface ExportReportProps {
  evidence: OnboardingEvidence;
  onComplete: () => void;
}

type ExportFormat = 'markdown' | 'json' | 'html';

export function ExportReport({ evidence, onComplete }: ExportReportProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('markdown');
  const [showPreview, setShowPreview] = useState(true);

  /**
   * Get preview content based on selected format
   */
  const getPreviewContent = (): string => {
    switch (selectedFormat) {
      case 'markdown':
        return generateMarkdownExport(evidence);
      case 'json':
        return generateJSONExport(evidence);
      case 'html':
        return generateHTMLExport(evidence);
    }
  };

  /**
   * Handle export download
   */
  const handleExport = () => {
    const timestamp = new Date().toISOString().split('T')[0];
    let content: string;
    let filename: string;
    let mimeType: string;

    switch (selectedFormat) {
      case 'markdown':
        content = generateMarkdownExport(evidence);
        filename = `aurity-onboarding-${timestamp}.md`;
        mimeType = 'text/markdown';
        break;
      case 'json':
        content = generateJSONExport(evidence);
        filename = `aurity-onboarding-${timestamp}.json`;
        mimeType = 'application/json';
        break;
      case 'html':
        content = generateHTMLExport(evidence);
        filename = `aurity-onboarding-${timestamp}.html`;
        mimeType = 'text/html';
        break;
    }

    downloadFile(content, filename, mimeType);
  };

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <h2 className="text-2xl font-bold text-slate-50 mb-2 flex items-center justify-center gap-2">
          <FileText className="w-7 h-7" strokeWidth={1.5} aria-hidden="true" />
          Export Onboarding Evidence
        </h2>
        <p className="text-slate-400">
          Phase 7 of 8 · Download completion report
        </p>
      </div>

      {/* FI Message */}
      <div className="p-6 bg-slate-900/60 backdrop-blur-xl rounded-xl border border-emerald-700/30">
        <div className="flex items-start gap-4">
          <Package className="w-8 h-8 text-emerald-400 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <div>
            <p className="text-sm font-semibold text-emerald-300 mb-2">
              Free-Intelligence · Tone: Empathetic (Final export)
            </p>
            <p className="text-sm fi-text leading-relaxed">
              Has completado el onboarding de AURITY. Este reporte contiene toda la evidencia de tu
              progreso: <strong>perfil de usuario</strong>, <strong>quiz de filosofía</strong>,
              <strong>paciente demo</strong>, y <strong>simulación de consulta</strong>.
            </p>
            <p className="text-sm fi-text mt-3">
              Puedes exportarlo en <span className="fi-text-info">3 formatos</span>:
              <strong className="fi-text-purple"> Markdown</strong> (developer-friendly),
              <strong className="fi-text-success"> JSON</strong> (machine-readable), o
              <strong className="text-yellow-400"> HTML</strong> (imprimible como PDF).
            </p>
          </div>
        </div>
      </div>

      {/* Format Selection */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Markdown */}
        <Button
          onClick={() => setSelectedFormat('markdown')}
          className={`p-6 rounded-xl border-2 transition-all text-left ${
            selectedFormat === 'markdown'
              ? 'border-purple-500/50 bg-purple-950/30 shadow-lg'
              : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600'
          }`}
          variant="ghost"
          size="lg"
          title="Markdown"
        >
          <div className="mb-3"><FileText className="w-8 h-8 text-purple-400" strokeWidth={1.5} aria-hidden="true" /></div>
          <h3 className="fi-section-title">Markdown</h3>
          <p className="fi-text-xs mb-3">
            Developer-friendly, readable text format
          </p>
          <div className="flex items-center justify-between text-xs">
            <span className="fi-text-purple">.md</span>
            <span className="text-slate-500">GitHub ready</span>
          </div>
        </Button>

        {/* JSON */}
        <Button
          onClick={() => setSelectedFormat('json')}
          className={`p-6 rounded-xl border-2 transition-all text-left ${
            selectedFormat === 'json'
              ? 'border-emerald-500/50 bg-emerald-950/30 shadow-lg'
              : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600'
          }`}
          variant="ghost"
          size="lg"
          title="JSON"
        >
          <div className="mb-3"><Wrench className="w-8 h-8 text-emerald-400" strokeWidth={1.5} aria-hidden="true" /></div>
          <h3 className="fi-section-title">JSON</h3>
          <p className="fi-text-xs mb-3">
            Machine-readable, structured data
          </p>
          <div className="flex items-center justify-between text-xs">
            <span className="fi-text-success">.json</span>
            <span className="text-slate-500">API compatible</span>
          </div>
        </Button>

        {/* HTML */}
        <Button
          onClick={() => setSelectedFormat('html')}
          className={`p-6 rounded-xl border-2 transition-all text-left ${
            selectedFormat === 'html'
              ? 'border-yellow-500/50 bg-yellow-950/30 shadow-lg'
              : 'border-slate-700/50 bg-slate-900/40 hover:border-slate-600'
          }`}
          variant="ghost"
          size="lg"
          title="HTML"
        >
          <div className="mb-3"><Globe className="w-8 h-8 text-yellow-400" strokeWidth={1.5} aria-hidden="true" /></div>
          <h3 className="fi-section-title">HTML</h3>
          <p className="fi-text-xs mb-3">
            Printable, browser-viewable format
          </p>
          <div className="flex items-center justify-between text-xs">
            <span className="text-yellow-400">.html</span>
            <span className="text-slate-500">PDF ready</span>
          </div>
        </Button>
      </div>

      {/* Preview Toggle */}
      <div className="fi-flex-between">
        <Button
          onClick={() => setShowPreview(!showPreview)}
          className="text-sm fi-text-info hover:text-cyan-300 underline transition-colors"
          variant="ghost"
          size="sm"
          title={showPreview ? 'Hide Preview' : 'Show Preview'}
        >
          {showPreview ? 'Hide Preview' : 'Show Preview'}
        </Button>
        <p className="fi-text-xs">
          Session ID: <code className="fi-text-success bg-slate-950/50 px-2 py-1 rounded">{evidence.sessionId}</code>
        </p>
      </div>

      {/* Preview */}
      {showPreview && (
        <div className="bg-slate-950/70 border border-slate-700/50 rounded-xl p-6 overflow-x-auto">
          <div className="flex items-center justify-between mb-4 fi-border-bottom/50 pb-3">
            <p className="text-sm font-semibold fi-text">Preview ({selectedFormat.toUpperCase()})</p>
            <span className="fi-text-xs-muted">Read-only</span>
          </div>
          <pre className="text-xs fi-text font-mono leading-relaxed whitespace-pre-wrap max-h-96 overflow-y-auto">
            {getPreviewContent()}
          </pre>
        </div>
      )}

      {/* Evidence Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 bg-blue-950/20 border border-blue-700/30 rounded-xl">
          <p className="text-xs fi-text-primary mb-1">User Profile</p>
          <p className="text-lg font-bold text-slate-200">
            {evidence.user.role ? <CheckCircle className="w-6 h-6 text-emerald-400" strokeWidth={1.5} aria-hidden="true" /> : <XCircle className="w-6 h-6 text-red-400" strokeWidth={1.5} aria-hidden="true" />}
          </p>
        </div>
        <div className="p-4 bg-purple-950/20 border border-purple-700/30 rounded-xl">
          <p className="text-xs fi-text-purple mb-1">Philosophy Quiz</p>
          <p className="text-lg font-bold text-slate-200">
            {(evidence.philosophy.glitchScore || 0) + (evidence.philosophy.betaScore || 0) + (evidence.philosophy.residenciaScore || 0) > 0 ? <CheckCircle className="w-6 h-6 text-emerald-400" strokeWidth={1.5} aria-hidden="true" /> : <XCircle className="w-6 h-6 text-red-400" strokeWidth={1.5} aria-hidden="true" />}
          </p>
        </div>
        <div className="p-4 bg-emerald-950/20 border border-emerald-700/30 rounded-xl">
          <p className="text-xs fi-text-success mb-1">Patient Demo</p>
          <p className="text-lg font-bold text-slate-200">
            {evidence.patient.nombre ? <CheckCircle className="w-6 h-6 text-emerald-400" strokeWidth={1.5} aria-hidden="true" /> : <XCircle className="w-6 h-6 text-red-400" strokeWidth={1.5} aria-hidden="true" />}
          </p>
        </div>
        <div className="p-4 bg-cyan-950/20 border border-cyan-700/30 rounded-xl">
          <p className="text-xs fi-text-info mb-1">Consultation</p>
          <p className="text-lg font-bold text-slate-200">
            {evidence.consultation.mode ? <CheckCircle className="w-6 h-6 text-emerald-400" strokeWidth={1.5} aria-hidden="true" /> : <XCircle className="w-6 h-6 text-red-400" strokeWidth={1.5} aria-hidden="true" />}
          </p>
        </div>
      </div>

      {/* Actions */}
      <div className="flex items-center justify-center gap-4">
        <Button onClick={handleExport} size="xl" className="flex items-center gap-2">
          <Download className="w-5 h-5" strokeWidth={1.5} aria-hidden="true" />
          Download {selectedFormat.toUpperCase()}
        </Button>
        <Button onClick={onComplete} variant="cyan" size="xl">
          Continue to Celebration →
        </Button>
      </div>

      {/* Note */}
      <div className="p-4 bg-yellow-950/20 border border-yellow-700/30 rounded-xl">
        <p className="text-xs text-yellow-300 flex items-start gap-2">
          <Lightbulb className="w-5 h-5 flex-shrink-0" strokeWidth={1.5} aria-hidden="true" />
          <span>
            <strong>Tip:</strong> Si seleccionas HTML, puedes abrirlo en tu navegador y usar
            &quot;Imprimir → Guardar como PDF&quot; para generar un PDF oficial del reporte.
          </span>
        </p>
      </div>
    </div>
  );
}
