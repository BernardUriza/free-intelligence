/**
 * DocumentEditModal Component
 *
 * Modal for editing document metadata (title, instructions, personas).
 * Card: FI-UI-FEAT-021
 */
'use client';

import { useState, useEffect } from 'react';
import {
  X,
  Save,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { DocumentMetadata, DocumentUpdateRequest } from '@aurity-standalone/types/knowledge';
import { AVAILABLE_PERSONAS } from '@aurity-standalone/types/knowledge';
import { updateDocument } from '@aurity-standalone/api-client/knowledge';

interface DocumentEditModalProps {
  isOpen: boolean;
  onClose: () => void;
  document: DocumentMetadata | null;
  onUpdate: (updatedDoc: DocumentMetadata) => void;
}

export function DocumentEditModal({
  isOpen,
  onClose,
  document,
  onUpdate,
}: DocumentEditModalProps) {
  const [title, setTitle] = useState('');
  const [usageInstructions, setUsageInstructions] = useState('');
  const [assignedPersonas, setAssignedPersonas] = useState<string[]>([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when document changes
  useEffect(() => {
    if (document) {
      setTitle(document.title || '');
      setUsageInstructions(document.usage_instructions || '');
      setAssignedPersonas(document.assigned_personas || []);
      setError(null);
    }
  }, [document]);

  if (!isOpen || !document) return null;

  const handlePersonaToggle = (personaId: string) => {
    setAssignedPersonas((prev) =>
      prev.includes(personaId)
        ? prev.filter((id) => id !== personaId)
        : [...prev, personaId]
    );
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const updates: DocumentUpdateRequest = {
        title: title || undefined,
        usage_instructions: usageInstructions || undefined,
        assigned_personas: assignedPersonas,
      };

      const updatedDoc = await updateDocument(document.doc_id, updates);
      onUpdate(updatedDoc);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const hasChanges =
    title !== (document.title || '') ||
    usageInstructions !== (document.usage_instructions || '') ||
    JSON.stringify(assignedPersonas.sort()) !==
      JSON.stringify((document.assigned_personas || []).sort());

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative bg-slate-900 border border-slate-700 rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-6 fi-border-bottom">
          <div className="fi-flex-gap-md">
            <div className="p-2 bg-blue-600/20 rounded-lg">
              <FileText className="w-5 h-5 fi-text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">
                Edit Document
              </h2>
              <p className="fi-subtitle">{document.filename}</p>
            </div>
          </div>
          <Button
            onClick={onClose}
            variant="ghost"
            size="sm"
            icon={X}
            aria-label="Close"
          />
        </div>

        {/* Content */}
        <div className="p-6 overflow-y-auto max-h-[60vh] space-y-6">
          {/* Error */}
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-900/30 border border-red-700 rounded-lg text-red-300">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span className="text-sm">{error}</span>
            </div>
          )}

          {/* Title */}
          <div className="fi-stack-sm">
            <label className="block text-sm font-medium fi-text">
              Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={document.filename}
              className="fi-input-panel"
            />
            <p className="fi-text-xs-muted">
              Display name for the document (defaults to filename)
            </p>
          </div>

          {/* Usage Instructions */}
          <div className="fi-stack-sm">
            <label className="block text-sm font-medium fi-text">
              Usage Instructions
            </label>
            <textarea
              value={usageInstructions}
              onChange={(e) => setUsageInstructions(e.target.value)}
              placeholder="Tell the AI how to use this document..."
              rows={4}
              className="fi-textarea-panel"
            />
            <p className="fi-text-xs-muted">
              These instructions help the AI understand when and how to reference
              this document
            </p>
          </div>

          {/* Assigned Personas */}
          <div className="fi-stack-md">
            <label className="block text-sm font-medium fi-text">
              Assigned Personas
            </label>
            <div className="grid grid-cols-2 gap-2">
              {AVAILABLE_PERSONAS.map((persona) => {
                const isSelected = assignedPersonas.includes(persona.id);
                return (
                    <Button
                      key={persona.id}
                      onClick={() => handlePersonaToggle(persona.id)}
                      className={`flex items-center gap-2 p-3 rounded-lg border transition-colors text-left ${
                        isSelected
                          ? 'bg-blue-600/20 border-blue-500 text-blue-300'
                          : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-600'
                      }`}
                      variant={isSelected ? 'primary' : 'ghost'}
                      size="sm"
                      type="button"
                      aria-pressed={isSelected}
                    >
                      <div
                        className={`w-4 h-4 rounded border-2 flex items-center justify-center ${
                          isSelected
                            ? 'bg-blue-500 border-blue-500'
                            : 'border-slate-600'
                        }`}
                      >
                        {isSelected && (
                          <svg
                            className="w-2.5 h-2.5 text-white"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                            strokeWidth={3}
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              d="M5 13l4 4L19 7"
                            />
                          </svg>
                        )}
                      </div>
                      <span className="text-sm">{persona.name}</span>
                    </Button>
                  );
              })}
            </div>
            <p className="fi-text-xs-muted">
              Select which AI personas can access this document
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 p-6 fi-border-top bg-slate-900/50">
          <Button
            onClick={onClose}
            variant="ghost"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={saving || !hasChanges}
            variant="primary"
            icon={saving ? undefined : Save}
            loading={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default DocumentEditModal;
