/**
 * DocumentUploadModal Component
 *
 * Modal for uploading new documents with drag & drop support.
 * Card: FI-UI-FEAT-021
 */

'use client';

import { useState, useRef, useCallback } from 'react';
import { Button } from '@/components/ui/button';
import { createLogger } from '@/lib/internal/logger';
import {
  X,
  Upload,
  CheckCircle,
  AlertCircle,
  Bot,
} from 'lucide-react';

const log = createLogger('DocumentUpload');
import type { DocumentMetadata } from '@aurity-standalone/types/knowledge';
import { uploadDocument, formatFileSize } from '@aurity-standalone/api-client/knowledge';
import { AVAILABLE_PERSONAS } from '@aurity-standalone/types/knowledge';
import {
  PERSONA_ICONS,
  ACCEPTED_EXTENSIONS,
  validateFile,
} from './knowledge/constants';

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (doc: DocumentMetadata) => void;
}

export function DocumentUploadModal({ isOpen, onClose, onSuccess }: DocumentUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [usageInstructions, setUsageInstructions] = useState('');
  const [selectedPersonas, setSelectedPersonas] = useState<string[]>(['general_assistant']);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  // Declared before handleDrop which uses it
  const validateAndSetFile = useCallback((fileToValidate: File) => {
    setError(null);

    const validation = validateFile(fileToValidate);
    if (!validation.valid) {
      setError(validation.error || 'Invalid file');
      return;
    }

    setFile(fileToValidate);
    // Auto-fill title from filename (without extension)
    if (!title) {
      const nameWithoutExt = fileToValidate.name.replace(/\.[^/.]+$/, '');
      setTitle(nameWithoutExt.replace(/[_-]/g, ' '));
    }
  }, [title]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      validateAndSetFile(droppedFile);
    }
  }, [validateAndSetFile]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      validateAndSetFile(selectedFile);
    }
  };

  const togglePersona = (personaId: string) => {
    setSelectedPersonas((prev) =>
      prev.includes(personaId)
        ? prev.filter((p) => p !== personaId)
        : [...prev, personaId]
    );
  };

  const handleUpload = async () => {
    if (!file) return;

    try {
      setUploading(true);
      setError(null);

      const doc = await uploadDocument(file, {
        title: title || undefined,
        usage_instructions: usageInstructions || undefined,
        assigned_personas: selectedPersonas.length > 0 ? selectedPersonas : undefined,
      });

      onSuccess(doc);
      handleClose();
    } catch (err) {
      log.error('Upload failed', { error: String(err) });
      setError(err instanceof Error ? err.message : 'Error al subir el documento');
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    if (uploading) return;
    setFile(null);
    setTitle('');
    setUsageInstructions('');
    setSelectedPersonas(['general_assistant']);
    setError(null);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Modal */}
      <div className="admin-modal-upload">
          {/* Header */}
          <div className="flex items-center justify-between p-6 fi-border-bottom">
            <div className="fi-flex-gap-md">
              <div className="p-2 rounded-lg bg-emerald-900 border border-emerald-700">
                <Upload className="w-5 h-5 fi-text-success" />
              </div>
              <h2 className="fi-title-xl">Subir Documento</h2>
            </div>
            <button
              onClick={handleClose}
              disabled={uploading}
              className="fi-icon-btn-ghost"
            >
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 space-y-5">
            {/* Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                isDragging
                  ? 'border-emerald-500 bg-emerald-900/20'
                  : file
                  ? 'border-emerald-600 bg-emerald-900/10'
                  : 'border-slate-600 hover:border-slate-500 hover:bg-slate-800/50'
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept={ACCEPTED_EXTENSIONS}
                onChange={handleFileSelect}
                className="hidden"
              />

              {file ? (
                <div className="flex items-center justify-center gap-3">
                  <CheckCircle className="w-8 h-8 fi-text-success" />
                  <div className="text-left">
                    <p className="text-white font-medium">{file.name}</p>
                    <p className="fi-subtitle">{formatFileSize(file.size)}</p>
                  </div>
                </div>
              ) : (
                <>
                  <Upload className={`w-12 h-12 mx-auto mb-3 ${isDragging ? 'fi-text-success' : 'text-slate-500'}`} />
                  <p className="text-white font-medium mb-1">
                    {isDragging ? 'Suelta el archivo aquí' : 'Arrastra un archivo o haz clic'}
                  </p>
                  <p className="fi-subtitle">
                    PDF, DOCX, Markdown, TXT, PNG, JPG (máx. 50MB)
                  </p>
                </>
              )}
            </div>

            {/* Title */}
            <div>
              <label className="fi-label">
                Título del Documento
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Ej: Protocolo de Diabetes Tipo 2"
                className="fi-input"
              />
            </div>

            {/* Usage Instructions */}
            <div>
              <label className="fi-label">
                Instrucciones de Uso
              </label>
              <textarea
                value={usageInstructions}
                onChange={(e) => setUsageInstructions(e.target.value)}
                placeholder="Ej: Usar como referencia para diagnósticos de DM2 y tratamientos..."
                rows={3}
                className="fi-input resize-none"
              />
            </div>

            {/* Persona Assignment */}
            <div>
              <label className="fi-label">
                Asignar a Personas
              </label>
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_PERSONAS.map((persona) => {
                  const PersonaIcon = PERSONA_ICONS[persona.id] || Bot;
                  const isSelected = selectedPersonas.includes(persona.id);
                  return (
                    <button
                      key={persona.id}
                      onClick={() => togglePersona(persona.id)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg border transition-all ${
                        isSelected
                          ? 'bg-emerald-900/50 border-emerald-600 text-emerald-300'
                          : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                      }`}
                    >
                      <PersonaIcon className="w-4 h-4" />
                      <span className="text-sm">{persona.name}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Error */}
            {error && (
              <div className="flex items-center gap-2 p-3 bg-red-900/20 border border-red-800 rounded-lg">
                <AlertCircle className="w-5 h-5 fi-text-error flex-shrink-0" />
                <p className="text-sm text-red-300">{error}</p>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 p-6 fi-border-top">
            <Button
              onClick={handleClose}
              disabled={uploading}
              variant="secondary"
            >
              Cancelar
            </Button>
            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
              variant="success"
              icon={uploading ? undefined : Upload}
              loading={uploading}
            >
              {uploading ? 'Subiendo...' : 'Subir Documento'}
            </Button>
          </div>
        </div>
    </div>
  );
}
