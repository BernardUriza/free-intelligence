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
    <div className="pex-root">
      <div className="pex-header">
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
          <List className="pex-empty-icon" />
          <p>No hay examples configurados</p>
          <p className="pex-empty-hint">
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
              <div className="pex-card-header">
                <span className="fi-title-sm">
                  Example {index + 1}
                </span>
                <Button
                  onClick={() => removeExample(index)}
                  variant="ghost"
                  size="sm"
                  icon={Trash2}
                  className="pex-delete-btn"
                  aria-label="Eliminar example"
                />
              </div>

              <div className="pex-fields">
                <div>
                  <label className="pex-field-label">Input</label>
                  <textarea
                    className="pex-textarea"
                    rows={3}
                    value={example.input}
                    onChange={(e) => updateExample(index, 'input', e.target.value)}
                    placeholder="Entrada de ejemplo..."
                  />
                </div>
                <div>
                  <label className="pex-field-label">Output</label>
                  <textarea
                    className="pex-textarea"
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
