'use client';

/**
 * ChatStartScreen Component
 *
 * Pre-conversation screen that requires user to explicitly start the chat.
 * Prevents accidental LLM calls and shows login prompt for unauthenticated users.
 */

import { LogIn, MessageSquareText, Shield, Sparkles } from 'lucide-react';

export interface ChatStartScreenProps {
  /** Whether the user is authenticated */
  isAuthenticated: boolean;
  /** User's display name */
  userName?: string;
  /** Callback when user clicks "Comenzar" */
  onStart: () => void;
  /** Callback when user clicks "Iniciar sesión" */
  onLogin: () => void;
  /** Whether the start action is loading */
  isLoading?: boolean;
}

export function ChatStartScreen({
  isAuthenticated,
  userName,
  onStart,
  onLogin,
  isLoading = false,
}: ChatStartScreenProps) {
  // NOT AUTHENTICATED - Show login prompt
  if (!isAuthenticated) {
    return (
      <div className="chat-start-screen">
        <div className="chat-start-container">
          <div className="flex justify-center">
            <div className="chat-start-icon">
              <Shield className="fi-icon-xl text-slate-400" />
            </div>
          </div>

          <div className="fi-stack-sm">
            <h3 className="chat-start-title">Inicia sesión para continuar</h3>
            <p className="chat-start-subtitle">
              Para proteger tu privacidad y guardar tu historial de conversaciones,
              necesitas iniciar sesión.
            </p>
          </div>

          <button onClick={onLogin} className="chat-start-btn-login">
            <LogIn className="fi-icon-md" />
            Iniciar sesión
          </button>

          <p className="chat-start-hint">
            Tus datos están protegidos con encriptación AES-256
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
            Hola, {userName?.split(' ')[0] || 'Doctor'} 👋
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
