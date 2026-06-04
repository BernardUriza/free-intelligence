'use client';

/**
 * fi-glass · ChatStartScreen — pre-conversation gate.
 *
 * Unauthenticated → promotes the desktop app (a "go to downloads" action);
 * authenticated → an explicit "start" button (prevents accidental LLM calls).
 *
 * The original `<Link href="/downloads">` is inverted to `onNavigate('downloads')`
 * — a typed callback, so fi-glass never imports next/link and the same render
 * works under static export / Capacitor.
 */

import { Download, MessageSquareText, Monitor, Shield, Sparkles } from 'lucide-react';
import type { ChatNavDest } from './types';

export interface ChatStartScreenProps {
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** User's display name */
  userName?: string;
  /** Callback when user clicks "Comenzar" */
  onStart: () => void;
  /** Callback when user clicks "Iniciar sesión" */
  onLogin: () => void;
  /** Typed navigation (downloads link) */
  onNavigate?: (dest: ChatNavDest) => void;
  /** Whether the start action is loading */
  isLoading?: boolean;
}

export function ChatStartScreen({
  isAuthenticated,
  userName,
  onStart,
  onLogin: _onLogin,
  onNavigate,
  isLoading = false,
}: ChatStartScreenProps) {
  // NOT AUTHENTICATED - Promote desktop app
  if (!isAuthenticated) {
    return (
      <div className="chat-start-screen">
        <div className="chat-start-container">
          <div className="flex justify-center">
            <div className="chat-start-icon">
              <Monitor className="fi-icon-xl text-purple-400" />
            </div>
          </div>

          <div className="fi-stack-sm">
            <h3 className="chat-start-title">¡Pruébalo en tu escritorio!</h3>
            <p className="chat-start-subtitle">
              IA offline para tu desarrollo profesional. Licencias piloto gratuitas
              disponibles. ¡Descarga la tuya!
            </p>
          </div>

          <button
            type="button"
            onClick={() => onNavigate?.('downloads')}
            className="chat-start-btn-login"
          >
            <Download className="fi-icon-md" />
            Ir a Descargas
          </button>

          <p className="chat-start-hint">
            100% privado, funciona sin internet
          </p>
        </div>
      </div>
    );
  }

  // AUTHENTICATED - Show start button
  return (
    <div className="chat-start-screen">
      <div className="chat-start-container">
        <div className="pt-4 flex justify-center">
          <div className="chat-start-icon-large">
            <Sparkles className="w-10 h-10 fi-text-purple" />
          </div>
        </div>

        <div className="fi-stack-sm">
          <h3 className="chat-start-title-large">
            Hola, {userName?.split(' ')[0] || 'Doctor'}
          </h3>
          <p className="chat-start-subtitle">
            Soy tu asistente de Free Intelligence. Estoy listo para ayudarte con
            consultas médicas, notas SOAP y análisis clínicos.
          </p>
        </div>

        <div className="chat-start-features">
          <div className="chat-start-feature">
            <MessageSquareText className="w-4 h-4 fi-text-purple flex-shrink-0" />
            <span>Conversación privada y segura</span>
          </div>
          <div className="chat-start-feature">
            <Shield className="w-4 h-4 fi-text-green flex-shrink-0" />
            <span>Datos encriptados localmente</span>
          </div>
        </div>

        <button onClick={onStart} disabled={isLoading} className="chat-start-btn-begin">
          {isLoading ? (
            <>
              <div className="chat-start-spinner" />
              Iniciando...
            </>
          ) : (
            <>
              <MessageSquareText className="w-5 h-5" />
              Comenzar conversación
            </>
          )}
        </button>

        <p className="chat-start-hint">
          Presiona para iniciar una nueva conversación
        </p>
      </div>
    </div>
  );
}
