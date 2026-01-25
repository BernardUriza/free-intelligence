/**
 * ConfigTab - Persona Configuration Tab
 *
 * Handles basic persona settings:
 * - Name, Description
 * - Model, Voice, Temperature, Max Tokens
 */

import { useState, useEffect } from 'react';
import type { Persona } from '@aurity-standalone/types/persona';
import { LLM_MODELS } from '@aurity-standalone/types/persona';
import type { LLMModel } from '@aurity-standalone/types/llm';
import { fetchLLMModels } from '@aurity-standalone/api-client/llm-models';
import { VOICE_GROUPS, getVoiceInfo } from '@aurity-standalone/types/voices';
import { Mic, Loader2, Cpu, Target, Globe, Mic2, Star } from 'lucide-react';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
  SelectGroup
} from '@/components/ui/select';
import { getProviderFromModel, getProviderBadgeVariant } from '@/types/select-configs';

interface ConfigTabProps {
  persona: Persona;
  // eslint-disable-next-line no-unused-vars
  onChange: (updates: Partial<Persona>) => void;
}

export function ConfigTab({ persona, onChange }: ConfigTabProps) {
  const currentVoice = persona.voice ? getVoiceInfo(persona.voice) : null;
  const [llmModels, setLlmModels] = useState<LLMModel[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);

  // Load LLM models from API
  useEffect(() => {
    const loadModels = async () => {
      try {
        const models = await fetchLLMModels({ includeInactive: false });
        setLlmModels(models);
      } catch (error) {
        console.error('Failed to load LLM models, using fallback:', error);
        // Fallback to hardcoded models if API fails
        setLlmModels([]);
      } finally {
        setLoadingModels(false);
      }
    };
    loadModels();
  }, []);

  // Use API models if available, otherwise fall back to hardcoded
  const availableModels = llmModels.length > 0
    ? llmModels.map(m => ({ value: m.id, label: m.label }))
    : LLM_MODELS;

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Basic Info */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="fi-label">
            Nombre de Persona
          </label>
          <Input
            type="text"
            className="p-3"
            value={persona.name}
            onChange={(e) => onChange({ name: e.target.value })}
          />
        </div>
        <div>
          <label className="fi-label">
            ID Interno
          </label>
          <input
            type="text"
            className="w-full p-3 fi-panel text-slate-500 font-mono"
            value={persona.id}
            disabled
          />
        </div>
      </div>

      {/* Description */}
      <div>
        <label className="fi-label">
          Descripción
        </label>
        <textarea
          className="w-full p-3 fi-panel text-white focus:border-purple-500 focus:outline-none"
          rows={3}
          value={persona.description}
          onChange={(e) => onChange({ description: e.target.value })}
          placeholder="Describe el propósito y especialización de esta persona..."
        />
      </div>

      {/* Model Selection */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <label className="flex items-center gap-2 fi-label">
            <Cpu className="w-4 h-4" />
            Modelo LLM
          </label>
          {loadingModels ? (
            <div className="w-full p-3 fi-panel flex items-center gap-2 text-slate-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              Cargando modelos...
            </div>
          ) : (
            <Select value={persona.model} onValueChange={(v) => onChange({ model: v })}>
              <SelectTrigger>
                <SelectValue placeholder="Seleccionar modelo..." />
              </SelectTrigger>
              <SelectContent portal>
                {availableModels.map((model) => {
                  const provider = getProviderFromModel(model.value);
                  const badgeVariant = getProviderBadgeVariant(provider);
                  
                  return (
                    <SelectItem
                      key={model.value}
                      value={model.value}
                      label={model.label}
                      badge={{
                        text: provider,
                        variant: badgeVariant,
                      }}
                    />
                  );
                })}
              </SelectContent>
            </Select>
          )}
        </div>
        <div>
          <label className="fi-label">
            Max Tokens
          </label>
          <input
            type="number"
            className="w-full p-3 fi-panel text-white font-mono focus:border-purple-500 focus:outline-none"
            value={persona.max_tokens}
            onChange={(e) =>
              onChange({ max_tokens: parseInt(e.target.value) || 0 })
            }
          />
        </div>
      </div>

      {/* Voice Selection */}
      <div>
        <label className="flex items-center gap-2 fi-label">
          <Mic className="w-4 h-4" />
          Voz TTS (Text-to-Speech)
        </label>
        {currentVoice && (
          <div className="mb-3 fi-note">
            <div className="fi-flex-between">
              <div>
                <div className="fi-title-sm-medium">
                  {currentVoice.label}
                </div>
                <div className="fi-text-xs flex items-center gap-1">
                  {currentVoice.provider === 'openai-steerable'
                    ? <><Target className="w-3 h-3 inline" aria-hidden="true" /> OpenAI Steerable (Acento Mexicano)</>
                    : currentVoice.provider === 'azure-openai'
                    ? <><Globe className="w-3 h-3 inline" aria-hidden="true" /> Azure OpenAI (Nativa Mexicana)</>
                    : <><Mic2 className="w-3 h-3 inline" aria-hidden="true" /> OpenAI Standard</>}
                  {currentVoice.description && ` · ${currentVoice.description}`}
                </div>
              </div>
              {currentVoice.recommended && (
                <span className="px-2 py-1 bg-purple-600 text-white text-xs rounded-md flex items-center gap-1">
                  <Star className="w-3 h-3" strokeWidth={1.5} aria-hidden="true" /> Recomendada
                </span>
              )}
            </div>
          </div>
        )}
        <Select
          value={persona.voice || ''}
          onValueChange={(val) => onChange({ voice: val || null })}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Sin voz (Solo texto)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">Sin voz (Solo texto)</SelectItem>
            {VOICE_GROUPS.map((group) => (
              <SelectGroup key={group.label} label={group.label}>
                {group.voices.map((voice) => (
                  <SelectItem key={`${voice.provider}-${voice.value}`} value={voice.value}>
                    {voice.label}
                    {voice.recommended && <Star className="w-3 h-3 inline ml-1 text-yellow-400" strokeWidth={1.5} aria-hidden="true" />}
                    {voice.description ? ` · ${voice.description}` : ''}
                  </SelectItem>
                ))}
              </SelectGroup>
            ))}
          </SelectContent>
        </Select>
        <p className="fi-text-xs-muted mt-2 flex items-center gap-1 flex-wrap">
          <Target className="w-3 h-3 inline" aria-hidden="true" /> Steerable: Acento mexicano natural |
          <Globe className="w-3 h-3 inline ml-1" aria-hidden="true" /> Azure: Voces nativas |
          <Mic2 className="w-3 h-3 inline ml-1" aria-hidden="true" /> Standard: Inglés/General
        </p>
      </div>

      {/* Temperature Slider */}
      <div>
        <label className="fi-label">
          Temperature: {persona.temperature.toFixed(2)}
          <span className="fi-text-xs-muted ml-2">
            (
            {persona.temperature < 0.3
              ? 'Determinístico'
              : persona.temperature < 0.7
              ? 'Balanceado'
              : 'Creativo'}
            )
          </span>
        </label>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          className="w-full h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-purple-600"
          value={persona.temperature}
          onChange={(e) => onChange({ temperature: parseFloat(e.target.value) })}
        />
        <div className="flex justify-between fi-text-xs-muted mt-1">
          <span>0.0 (Preciso)</span>
          <span>0.5 (Balance)</span>
          <span>1.0 (Creativo)</span>
        </div>
      </div>
    </div>
  );
}
