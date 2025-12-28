'use client';

/**
 * SummaryExport Component - AURITY Medical Workflow
 *
 * Final summary and export options for consultation data.
 * Integrates with FI backend export services.
 *
 * Features:
 * - Display consultation summary
 * - Export to PDF/Markdown
 * - Send to HDF5 corpus
 *
 * File: apps/aurity/components/medical/SummaryExport.tsx
 */

import React, { useState } from 'react';
import { Download, FileText, Database, Check, Archive, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface SummaryExportProps {
  onPrevious?: () => void;
  onComplete?: () => void;
  className?: string;
}

interface ConsultationSummary {
  patient: string;
  date: string;
  duration: string;
  transcriptionLength: number;
  soapComplete: boolean;
  ordersCount: number;
}

export function SummaryExport({
  onPrevious,
  onComplete,
  className = ''
}: SummaryExportProps) {
  // State
  const [isExporting, setIsExporting] = useState(false);
  const [exportComplete, setExportComplete] = useState(false);
  const [exportFormat, setExportFormat] = useState<'pdf' | 'markdown' | 'corpus'>('corpus');

  // Summary data (would come from workflow context)
  const summary: ConsultationSummary = {
    patient: 'Juan Pérez',
    date: new Date().toLocaleString('es-MX'),
    duration: '00:08:23',
    transcriptionLength: 1247,
    soapComplete: true,
    ordersCount: 3
  };

  // Handle export
  const handleExport = async () => {
    setIsExporting(true);

    try {
      // Simulate export delay
      await new Promise(resolve => setTimeout(resolve, 2000));

      // TODO: Call FI backend export service
      console.log('Exporting consultation data to:', exportFormat);

      setExportComplete(true);

      // Auto-complete after 1 second
      setTimeout(() => {
        if (onComplete) {
          onComplete();
        }
      }, 1000);

    } catch (error) {
      console.error('Export failed:', error);
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className={`space-y-6 ${className}`}>
      {/* Header */}
      <div className="text-center">
        <h2 className="fi-title-2xl mb-2">Resumen y Exportación</h2>
        <p className="text-slate-400">Revisa el resumen y guarda la consulta</p>
      </div>

      {/* Summary Cards */}
      <div className="fi-grid-2">
        <div className="fi-card-xl">
          <div className="fi-subtitle mb-1">Paciente</div>
          <div className="fi-title-xl">{summary.patient}</div>
        </div>

        <div className="fi-card-xl">
          <div className="fi-subtitle mb-1">Duración</div>
          <div className="text-xl font-semibold fi-text-success">{summary.duration}</div>
        </div>

        <div className="fi-card-xl">
          <div className="fi-subtitle mb-1">Transcripción</div>
          <div className="text-xl font-semibold fi-text-info">
            {summary.transcriptionLength} caracteres
          </div>
        </div>

        <div className="fi-card-xl">
          <div className="fi-subtitle mb-1">Órdenes</div>
          <div className="text-xl font-semibold fi-text-purple">{summary.ordersCount}</div>
        </div>
      </div>

      {/* Completeness Check */}
      <div className={summary.soapComplete ? 'fi-alert-success' : 'fi-alert-warning'}>
        {summary.soapComplete ? (
          <>
            <Check className="h-5 w-5 fi-text-green" />
            <span className="fi-text-green font-medium">Consulta completa y lista para exportar</span>
          </>
        ) : (
          <>
            <AlertCircle className="h-5 w-5 fi-text-warning" />
            <span className="fi-text-warning font-medium">Faltan datos por completar</span>
          </>
        )}
      </div>

      {/* Export Options */}
      <div className="fi-card-xl">
        <h3 className="fi-title mb-4">Formato de Exportación</h3>

        <div className="fi-stack-md">
          {/* Corpus (HDF5) */}
          <Button
            onClick={() => setExportFormat('corpus')}
            className={exportFormat === 'corpus' ? 'fi-option-card-selected' : 'fi-option-card'}
            variant={exportFormat === 'corpus' ? 'primary' : 'ghost'}
            size="sm"
            type="button"
          >
            <Database className={`h-6 w-6 ${
              exportFormat === 'corpus' ? 'fi-text-success' : 'text-slate-400'
            }`} />
            <div className="flex-1">
              <div className="font-medium text-white">Corpus HDF5</div>
              <div className="fi-subtitle">
                Almacenamiento inmutable con provenance completo
              </div>
            </div>
            {exportFormat === 'corpus' && (
              <Check className="h-5 w-5 fi-text-success" />
            )}
          </Button>

          {/* PDF */}
          <Button
            onClick={() => setExportFormat('pdf')}
            className={exportFormat === 'pdf' ? 'fi-option-card-selected' : 'fi-option-card'}
            variant={exportFormat === 'pdf' ? 'primary' : 'ghost'}
            size="sm"
            type="button"
          >
            <FileText className={`h-6 w-6 ${
              exportFormat === 'pdf' ? 'fi-text-success' : 'text-slate-400'
            }`} />
            <div className="flex-1">
              <div className="font-medium text-white">PDF</div>
              <div className="fi-subtitle">
                Documento imprimible para archivo físico
              </div>
            </div>
            {exportFormat === 'pdf' && (
              <Check className="h-5 w-5 fi-text-success" />
            )}
          </Button>

          {/* Markdown */}
          <Button
            onClick={() => setExportFormat('markdown')}
            className={exportFormat === 'markdown' ? 'fi-option-card-selected' : 'fi-option-card'}
            variant={exportFormat === 'markdown' ? 'primary' : 'ghost'}
            size="sm"
            type="button"
          >
            <Archive className={`h-6 w-6 ${
              exportFormat === 'markdown' ? 'fi-text-success' : 'text-slate-400'
            }`} />
            <div className="flex-1">
              <div className="font-medium text-white">Markdown</div>
              <div className="fi-subtitle">
                Formato de texto plano legible
              </div>
            </div>
            {exportFormat === 'markdown' && (
              <Check className="h-5 w-5 fi-text-success" />
            )}
          </Button>
        </div>
      </div>

      {/* Export Success */}
      {exportComplete && (
        <div className="p-4 rounded-lg border bg-green-500/10 border-green-500/30 flex items-center gap-3">
          <Check className="h-5 w-5 fi-text-green" />
          <span className="fi-text-green font-medium">
            Consulta exportada exitosamente al corpus FI
          </span>
        </div>
      )}

      {/* Export Button */}
      <Button
        onClick={handleExport}
        disabled={isExporting || exportComplete || !summary.soapComplete}
        variant={exportComplete ? 'success' : 'primary'}
        size="xl"
        icon={isExporting ? undefined : exportComplete ? Check : Download}
        loading={isExporting}
        fullWidth
        className="shadow-lg"
      >
        {isExporting ? 'Exportando...' : exportComplete ? 'Exportado' : 'Exportar Consulta'}
      </Button>

      {/* Navigation */}
      <div className="flex gap-4">
        {onPrevious && !exportComplete && (
          <Button
            onClick={onPrevious}
            disabled={isExporting}
            variant="secondary"
            size="lg"
            className="flex-1"
          >
            Anterior
          </Button>
        )}
      </div>
    </div>
  );
}
