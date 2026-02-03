'use client';

import { useState, useCallback, type ChangeEvent, type KeyboardEvent } from 'react';
import { X, Zap, Brain, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { SOAPData, ChatMessage } from '../types';

interface AIChatbotProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  soapData: SOAPData;
  onSOAPUpdate: (updatedData: SOAPData) => void;
}

export function AIChatbot({
  isOpen,
  onClose,
  sessionId,
  soapData,
  onSOAPUpdate,
}: AIChatbotProps) {
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const handleChatSend = useCallback(async () => {
    const message = chatInput.trim();
    if (!message || chatLoading) return;

    setChatInput('');
    setChatLoading(true);
    setChatMessages((prev) => [...prev, { role: 'user', content: message }]);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/api/aurity/medical-ai/sessions/${sessionId}/assistant`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ command: message, current_soap: soapData }),
        }
      );

      if (!response.ok) {
        const errorData = await response
          .json()
          .catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const result = await response.json();

      // Apply updates to SOAP data
      const updatedSOAP = { ...soapData };
      for (const [field, operation] of Object.entries(result.updates)) {
        const opString = operation as string;
        const colonIndex = opString.indexOf(':');
        const op = opString.substring(0, colonIndex);
        const content = opString.substring(colonIndex + 1);

        const fieldKey = field as keyof SOAPData;
        if (op === 'append') {
          (updatedSOAP[fieldKey] as string) =
            ((updatedSOAP[fieldKey] as string) || '') + content;
        } else if (op === 'replace') {
          (updatedSOAP[fieldKey] as string) = content;
        } else if (op === 'add_item' && Array.isArray(updatedSOAP[fieldKey])) {
          let itemToAdd: unknown = content;
          if (content.trim().startsWith('{')) {
            try {
              itemToAdd = JSON.parse(content);
            } catch {
              /* keep as string */
            }
          }
          (updatedSOAP[fieldKey] as unknown[]).push(itemToAdd);
        } else if (op === 'add_items' && Array.isArray(updatedSOAP[fieldKey])) {
          try {
            const items = JSON.parse(content);
            if (Array.isArray(items)) {
              (updatedSOAP[fieldKey] as unknown[]).push(...items);
            }
          } catch {
            /* ignore parse errors */
          }
        }
      }

      onSOAPUpdate(updatedSOAP);
      setChatMessages((prev) => [
        ...prev,
        { role: 'assistant', content: result.explanation },
      ]);
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `Lo siento, ocurrió un error: ${err instanceof Error ? err.message : 'Error desconocido'}`,
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }, [chatInput, chatLoading, sessionId, soapData, onSOAPUpdate]);

  const handleKeyPress = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter') handleChatSend();
    },
    [handleChatSend]
  );

  if (!isOpen) return null;

  return (
    <div
      className="fixed bottom-6 right-6 w-96 bg-slate-900 rounded-xl border border-emerald-500 shadow-2xl z-40 flex flex-col max-h-[600px]"
      role="dialog"
      aria-label="Asistente IA"
    >
      <div className="bg-gradient-to-r from-emerald-600 to-cyan-600 p-4 rounded-t-xl flex justify-between items-center">
        <div className="fi-flex-gap">
          <Zap className="h-5 w-5 text-white" aria-hidden="true" />
          <h3 className="text-white font-bold">Asistente IA</h3>
        </div>
        <Button
          onClick={onClose}
          variant="ghost"
          size="sm"
          icon={X}
          className="text-white hover:bg-white/20"
          aria-label="Cerrar asistente"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-800">
        {chatMessages.length === 0 && (
          <div className="text-center text-slate-400 py-8">
            <Brain
              className="h-12 w-12 mx-auto mb-3 fi-text-success"
              aria-hidden="true"
            />
            <p className="text-sm">Escribe comandos como:</p>
            <p className="text-xs mt-2 fi-text-success">
              &quot;nota 1: la paciente vive con VIH&quot;
            </p>
            <p className="text-xs fi-text-success">
              &quot;agregar alergia a penicilina&quot;
            </p>
          </div>
        )}

        {chatMessages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] px-4 py-2 rounded-lg ${
                msg.role === 'user'
                  ? 'bg-emerald-600 text-white'
                  : 'bg-slate-700 text-slate-200'
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {chatLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-700 px-4 py-2 rounded-lg">
              <div className="fi-flex-gap">
                <Loader2
                  className="h-4 w-4 animate-spin fi-text-success"
                  aria-hidden="true"
                />
                <p className="fi-subtitle">Procesando...</p>
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="p-4 fi-border-top">
        <div className="flex gap-2">
          <Input
            type="text"
            value={chatInput}
            onChange={(e: ChangeEvent<HTMLInputElement>) =>
              setChatInput(e.target.value)
            }
            onKeyPress={handleKeyPress}
            placeholder="Escribe un comando..."
            className="flex-1 text-sm"
            disabled={chatLoading}
          />
          <Button
            onClick={handleChatSend}
            disabled={!chatInput.trim() || chatLoading}
            variant="success"
            icon={Zap}
          />
        </div>
      </div>
    </div>
  );
}
