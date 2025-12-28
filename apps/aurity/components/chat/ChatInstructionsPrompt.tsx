/**
 * ChatInstructionsPrompt Component
 *
 * Quick replies for selecting how FI should use an uploaded document.
 * Card: FI-UI-FEAT-022
 */
'use client';

import { useState } from 'react';
import { Bot, CheckCircle, Edit3 } from 'lucide-react';
import { Button } from '@/components/ui/button';

export interface InstructionOption {
  id: string;
  label: string;
  description: string;
}

export const INSTRUCTION_OPTIONS: InstructionOption[] = [
  { id: 'reference_diagnosis', label: 'Referencia para diagnósticos', description: 'Usar como fuente autorizada para decisiones clínicas' },
  { id: 'quote_verbatim', label: 'Citar textualmente cuando aplique', description: 'Incluir citas directas del documento' },
  { id: 'general_context', label: 'Solo como contexto general', description: 'Usar como información de fondo sin citarlo' },
  { id: 'custom', label: 'Escribir instrucciones personalizadas', description: 'Definir instrucciones específicas' },
];

export const INSTRUCTION_TEXTS: Record<string, string> = {
  reference_diagnosis: 'Usar como referencia autorizada para diagnósticos y decisiones clínicas.',
  quote_verbatim: 'Citar textualmente cuando la información sea relevante a la consulta.',
  general_context: 'Usar solo como contexto general sin citar directamente.',
};

export interface ChatInstructionsPromptProps {
  filename: string;
  onSelect: (instruction: string) => void;
  onCancel?: () => void;
  disabled?: boolean;
}

export function ChatInstructionsPrompt({
  filename,
  onSelect,
  onCancel,
  disabled = false,
}: ChatInstructionsPromptProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [customText, setCustomText] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const handleOptionClick = (option: InstructionOption) => {
    if (disabled) return;
    if (option.id === 'custom') {
      setShowCustomInput(true);
      setSelectedId('custom');
    } else {
      setSelectedId(option.id);
      onSelect(INSTRUCTION_TEXTS[option.id]);
    }
  };

  const handleCustomSubmit = () => {
    if (customText.trim() && !disabled) onSelect(customText.trim());
  };

  const getOptionClass = (optionId: string) => {
    const isSelected = selectedId === optionId;
    const isDisabled = disabled || (selectedId !== null && selectedId !== optionId);
    if (isSelected) return `chat-instructions-option-selected ${isDisabled ? 'chat-instructions-option-disabled' : ''}`;
    return `chat-instructions-option ${isDisabled ? 'chat-instructions-option-disabled' : ''}`;
  };

  return (
    <div className="chat-instructions">
      <div className="chat-instructions-avatar">
        <Bot className="w-4 h-4 text-white" />
      </div>

      <div className="chat-instructions-body">
        <div className="chat-instructions-question">
          <p className="text-white text-sm">
            He recibido <span className="chat-instructions-filename">&apos;{filename}&apos;</span>.
            {' '}¿Cómo quieres que lo use?
          </p>
        </div>

        {!showCustomInput ? (
          <div className="chat-instructions-options">
            {INSTRUCTION_OPTIONS.map((option) => (
              <Button
                key={option.id}
                onClick={() => handleOptionClick(option)}
                disabled={disabled || (selectedId !== null && selectedId !== option.id)}
                className={getOptionClass(option.id)}
                variant="ghost"
                size="sm"
                title={option.label}
                type="button"
              >
                {selectedId === option.id && option.id !== 'custom' ? (
                  <CheckCircle className="w-4 h-4 fi-text-purple flex-shrink-0" />
                ) : option.id === 'custom' ? (
                  <Edit3 className="w-4 h-4 text-slate-400 flex-shrink-0" />
                ) : (
                  <div className="chat-instructions-option-radio" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="chat-instructions-option-label">{option.label}</p>
                  <p className="chat-instructions-option-desc">{option.description}</p>
                </div>
              </Button>
            ))}
          </div>
        ) : (
          <div className="chat-instructions-custom">
            <textarea
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              placeholder="Escribe tus instrucciones personalizadas..."
              className="chat-instructions-textarea"
              rows={3}
              disabled={disabled}
              autoFocus
            />
            <div className="chat-instructions-actions">
              <Button
                onClick={() => { setShowCustomInput(false); setSelectedId(null); setCustomText(''); onCancel?.(); }}
                disabled={disabled}
                className="chat-instructions-cancel"
                variant="ghost"
                size="sm"
                title="Cancelar"
                type="button"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleCustomSubmit}
                disabled={disabled || !customText.trim()}
                className="chat-instructions-confirm"
                variant="primary"
                size="sm"
                title="Confirmar"
                type="button"
              >
                Confirmar
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChatInstructionsPrompt;
