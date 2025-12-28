/**
 * ExamplesTab - Few-Shot Examples Manager
 *
 * Add, edit, and remove few-shot examples for persona training
 */

import type { Persona } from '@aurity-standalone/types/persona';
import { Plus, Trash2, List } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ExamplesTabProps {
  persona: Persona;
  onChange: (updates: Partial<Persona>) => void;
}

export function ExamplesTab({ persona, onChange }: ExamplesTabProps) {
  const addExample = () => {
    onChange({
      examples: [...persona.examples, { input: '', output: '' }],
    });
  };

  const removeExample = (index: number) => {
    onChange({
      examples: persona.examples.filter((_, i) => i !== index),
    });
  };

  const updateExample = (
    index: number,
    field: 'input' | 'output',
    value: string
  ) => {
    const newExamples = [...persona.examples];
    newExamples[index] = {
      ...newExamples[index],
      [field]: value,
    };
    onChange({ examples: newExamples });
  };

  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between mb-4">
        <h3 className="fi-title">
          Few-Shot Examples ({persona.examples.length})
        </h3>
        <Button
          onClick={addExample}
          variant="purple"
          icon={Plus}
        >
          Agregar Example
        </Button>
      </div>

      {persona.examples.length === 0 ? (
        <div className="fi-empty-state-muted">
          <List className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No hay examples configurados</p>
          <p className="text-sm mt-1">
            Agrega examples para mejorar la precisión de la persona
          </p>
        </div>
      ) : (
        <div className="fi-stack-xl">
          {persona.examples.map((example, index) => (
            <div
              key={index}
              className="fi-card-solid"
            >
              <div className="flex items-center justify-between mb-3">
                <span className="fi-title-sm">
                  Example {index + 1}
                </span>
                <Button
                  onClick={() => removeExample(index)}
                  variant="ghost"
                  size="sm"
                  icon={Trash2}
                  className="fi-text-error hover:bg-slate-700"
                  aria-label="Eliminar example"
                />
              </div>

              <div className="space-y-3">
                <div>
                  <label className="block fi-text-xs mb-1">Input</label>
                  <textarea
                    className="w-full p-2 bg-slate-900 border border-slate-600 rounded text-white text-sm font-mono focus:border-purple-500 focus:outline-none"
                    rows={3}
                    value={example.input}
                    onChange={(e) => updateExample(index, 'input', e.target.value)}
                    placeholder="Entrada de ejemplo..."
                  />
                </div>
                <div>
                  <label className="block fi-text-xs mb-1">Output</label>
                  <textarea
                    className="w-full p-2 bg-slate-900 border border-slate-600 rounded text-white text-sm font-mono focus:border-purple-500 focus:outline-none"
                    rows={3}
                    value={
                      typeof example.output === 'string'
                        ? example.output
                        : JSON.stringify(example.output, null, 2)
                    }
                    onChange={(e) => updateExample(index, 'output', e.target.value)}
                    placeholder="Salida esperada..."
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
