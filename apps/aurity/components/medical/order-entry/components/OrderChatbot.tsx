'use client';

/**
 * OrderChatbot Component
 *
 * AI-powered chatbot panel for creating orders via natural language.
 */

import { Zap, X, Send, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { ChatMessage } from '../types';

interface OrderChatbotProps {
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  onInputChange: (value: string) => void;
  onSend: () => void;
  onClose: () => void;
}

export function OrderChatbot({
  messages,
  input,
  loading,
  onInputChange,
  onSend,
  onClose,
}: OrderChatbotProps) {
  return (
    <div className="med-chatbot-shell-orders">
      {/* Header */}
      <div className="med-chatbot-header">
        <div className="fi-flex-gap">
          <Zap className="h-5 w-5 text-white" />
          <h3 className="text-white font-bold">Asistente IA - Órdenes</h3>
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-800">
        {messages.length === 0 && (
          <div className="text-center text-slate-400 py-8">
            <Zap className="h-12 w-12 mx-auto mb-3 fi-text-success" />
            <p className="text-sm">Escribe comandos como:</p>
            <p className="text-xs mt-2 fi-text-success">&quot;solicita biometría hemática completa&quot;</p>
            <p className="text-xs fi-text-success">&quot;receta losartán 50mg c/12h&quot;</p>
            <p className="text-xs fi-text-success">&quot;agrega radiografía de tórax PA&quot;</p>
          </div>
        )}

        {messages.map((msg, idx) => (
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

        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-700 px-4 py-2 rounded-lg">
              <Loader2 className="h-4 w-4 fi-text-success animate-spin" />
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-4 fi-border-top bg-slate-900">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => onInputChange(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && onSend()}
            placeholder="Escribe un comando..."
            className="med-chatbot-input"
            disabled={loading}
          />
          <Button
            onClick={onSend}
            disabled={!input.trim() || loading}
            variant="success"
            icon={Send}
          />
        </div>
      </div>
    </div>
  );
}
