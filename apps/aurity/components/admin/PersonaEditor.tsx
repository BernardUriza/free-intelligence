/**
 * PersonaEditor Component
 *
 * Refactored slide-over panel with modular tab components:
 * - ConfigTab: Basic settings, model, voice, temperature
 * - PromptTab: System prompt editor
 * - ExamplesTab: Few-shot examples manager
 * - PersonaTestTab: Persona testing interface
 */

'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Brain,
  Save,
  Settings,
  FileText,
  List,
  Zap,
  Loader2,
} from 'lucide-react';
import type { Persona, PersonaUpdateRequest } from '@aurity-standalone/types/persona';
import { fetchPersona, updatePersona } from '@aurity-standalone/api-client/personas';
import { ConfigTab, PromptTab, ExamplesTab, PersonaTestTab } from './persona-editor';
import { toastError } from '@/lib/swal';
import { createLogger } from '@/lib/internal/logger';

const log = createLogger('PersonaEditor');

interface PersonaEditorProps {
  personaId: string;
  isOpen: boolean;
  onClose: () => void;
  onSave: (persona: Persona) => void;
}

type TabValue = 'config' | 'prompt' | 'examples' | 'test';

export function PersonaEditor({ personaId, isOpen, onClose, onSave }: PersonaEditorProps) {
  const [persona, setPersona] = useState<Persona | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabValue>('config');

  // Load persona data
  useEffect(() => {
    const loadPersona = async () => {
      try {
        setLoading(true);
        const data = await fetchPersona(personaId);
        setPersona(data);
      } catch (error) {
        log.error('Failed to load persona', { personaId, error: String(error) });
        toastError('Error al cargar la persona');
      } finally {
        setLoading(false);
      }
    };

    if (isOpen && personaId) {
      loadPersona();
    }
  }, [isOpen, personaId]);

  const handleSave = async () => {
    if (!persona) return;

    try {
      setSaving(true);

      const updates: PersonaUpdateRequest = {
        name: persona.name,
        description: persona.description,
        system_prompt: persona.system_prompt,
        model: persona.model,
        voice: persona.voice,
        temperature: persona.temperature,
        max_tokens: persona.max_tokens,
        examples: persona.examples,
      };

      const updated = await updatePersona(personaId, updates);
      onSave(updated);
      onClose();
    } catch (error) {
      log.error('Failed to save persona', { personaId, error: String(error) });
      toastError('Error al guardar la persona');
    } finally {
      setSaving(false);
    }
  };

  const handlePersonaChange = (updates: Partial<Persona>) => {
    if (!persona) return;
    setPersona({ ...persona, ...updates });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-over panel */}
      <div className="absolute inset-y-0 right-0 flex max-w-5xl">
        <div className="relative w-screen max-w-5xl">
          <div className="flex h-full flex-col bg-slate-900 shadow-2xl">
            {loading ? (
              <div className="flex items-center justify-center h-full">
                <Loader2 className="w-8 h-8 fi-text-purple animate-spin" />
              </div>
            ) : persona ? (
              <>
                {/* Header */}
                <div className="px-8 py-6 fi-border-bottom">
                  <div className="fi-flex-between">
                    <div>
                      <h2 className="fi-title-2xl flex items-center gap-3">
                        <Brain className="w-7 h-7 fi-text-purple" />
                        Editar Persona: {persona.name}
                      </h2>
                      <p className="fi-subtitle mt-1">
                        Versión {persona.version} · Última actualización:{' '}
                        {new Date(persona.last_updated).toLocaleDateString('es-MX')}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        onClick={onClose}
                        variant="secondary"
                      >
                        Cancelar
                      </Button>
                      <Button
                        onClick={handleSave}
                        disabled={saving}
                        variant="purple"
                        icon={Save}
                        loading={saving}
                      >
                        Guardar Cambios
                      </Button>
                    </div>
                  </div>

                  {/* Tabs */}
                  <div className="flex gap-2 mt-6">
                    {[
                      { value: 'config' as const, label: 'Configuración', icon: Settings },
                      { value: 'prompt' as const, label: 'System Prompt', icon: FileText },
                      { value: 'examples' as const, label: 'Examples', icon: List },
                      { value: 'test' as const, label: 'Probar', icon: Zap },
                    ].map((tab) => (
                      <Button
                        key={tab.value}
                        onClick={() => setActiveTab(tab.value)}
                        className={activeTab === tab.value ? 'fi-tab-pill-purple' : 'fi-tab-pill'}
                        variant={activeTab === tab.value ? 'purple' : 'ghost'}
                        size="sm"
                        type="button"
                      >
                        <tab.icon className="w-4 h-4" />
                        {tab.label}
                      </Button>
                    ))}
                  </div>
                </div>

                {/* Tab Content */}
                <div className="flex-1 overflow-y-auto px-8 py-6">
                  {activeTab === 'config' && (
                    <ConfigTab persona={persona} onChange={handlePersonaChange} />
                  )}
                  {activeTab === 'prompt' && (
                    <PromptTab persona={persona} onChange={handlePersonaChange} />
                  )}
                  {activeTab === 'examples' && (
                    <ExamplesTab persona={persona} onChange={handlePersonaChange} />
                  )}
                  {activeTab === 'test' && <PersonaTestTab personaId={personaId} />}
                </div>
              </>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
