/**
 * PromptTab - System Prompt Editor
 *
 * Full-screen textarea for editing persona system prompts
 */

import type { Persona } from '@aurity-standalone/types/persona';

interface PromptTabProps {
  persona: Persona;
  onChange: (updates: Partial<Persona>) => void;
}

export function PromptTab({ persona, onChange }: PromptTabProps) {
  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between mb-2">
        <label className="text-sm font-medium fi-text">System Prompt</label>
        <div className="fi-text-xs-muted">
          {persona.system_prompt.length} caracteres
        </div>
      </div>
      <textarea
        className="w-full p-4 fi-panel text-white font-mono text-sm focus:border-purple-500 focus:outline-none"
        rows={25}
        value={persona.system_prompt}
        onChange={(e) => onChange({ system_prompt: e.target.value })}
        placeholder="Eres un..."
      />
    </div>
  );
}
