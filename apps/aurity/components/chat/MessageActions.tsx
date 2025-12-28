'use client';

/**
 * MessageActions Component
 *
 * Practical message actions (copy, delete, etc.)
 * Simple, clean, functional.
 */

import { useState } from 'react';
import { Copy, Check, MoreVertical, Trash2, Pin, Reply, Volume2 } from 'lucide-react';
import { confirmDelete } from '@/lib/swal';
import { Button } from '@/components/ui/button';

export interface MessageActionsProps {
  /** Message content to copy */
  content: string;

  /** Message ID */
  messageId?: string;

  /** Show delete button */
  canDelete?: boolean;

  /** Show pin button */
  canPin?: boolean;

  /** Callbacks */
  onDelete?: (messageId: string) => void;
  onPin?: (messageId: string) => void;
  onReply?: (messageId: string) => void;

  /** Position: 'top-right' | 'bottom-right' */
  position?: 'top-right' | 'bottom-right';
}

/**
 * Copy button with visual feedback
 */
export function CopyButton({ content, size = 'sm' }: { content: string; size?: 'xs' | 'sm' | 'md' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
  };

  const buttonSizeClasses = {
    xs: 'p-1',
    sm: 'p-1.5',
    md: 'p-2',
  };

  return (
    <Button
      onClick={handleCopy}
      className={`${buttonSizeClasses[size]} ${copied ? 'chat-action-btn-success' : 'chat-action-btn'} group-copy`}
      title={copied ? 'Copiado!' : 'Copiar mensaje'}
      aria-label={copied ? 'Copied' : 'Copy message'}
      variant="ghost"
      size={size === 'xs' ? 'xs' : size === 'sm' ? 'sm' : 'md'}
      type="button"
    >
      {copied ? <Check className={sizeClasses[size]} /> : <Copy className={sizeClasses[size]} />}
      <span className="chat-action-tooltip group-copy-hover:opacity-100">
        {copied ? '✓ ¡Copiado!' : 'Copiar mensaje'}
      </span>
    </Button>
  );
}

/**
 * Speak button with Azure TTS
 *
 * ChatGPT-inspired: Opens a floating AudioPlayer component
 * Loading: Pulsing dot (not spinner)
 */
export function SpeakButton({
  content,
  size = 'sm',
  voice = 'nova',
  isUserMessage = false,
  onOpenPlayer,
}: {
  content: string;
  size?: 'xs' | 'sm' | 'md';
  voice?: string;
  /** Whether this is a user message (allows voice selection in player) */
  isUserMessage?: boolean;
  /** Callback to open the global audio player (required - provided by AudioPlayerContext) */
  onOpenPlayer: (text: string, voice: string, isUserMessage?: boolean) => void;
}) {
  const sizeClasses = {
    xs: 'w-3 h-3',
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4',
  };

  const buttonSizeClasses = {
    xs: 'p-1',
    sm: 'p-1.5',
    md: 'p-2',
  };

  // Format voice name for display
  const formatVoiceName = (voiceId: string): string => {
    const match = voiceId.match(/([A-Z][a-z]+)Neural$/);
    if (match) return match[1];
    return voiceId.charAt(0).toUpperCase() + voiceId.slice(1);
  };

  const voiceDisplay = formatVoiceName(voice);

  const handleClick = () => {
    // Use global audio player (always available now via AudioPlayerContext)
    onOpenPlayer(content, voice, isUserMessage);
  };

  return (
    <Button
      onClick={handleClick}
      className={`${buttonSizeClasses[size]} chat-action-btn`}
      title={`Escuchar (${voiceDisplay})`}
      aria-label={`Escuchar mensaje con voz ${voiceDisplay}`}
      variant="ghost"
      size={size === 'xs' ? 'xs' : size === 'sm' ? 'sm' : 'md'}
      type="button"
    >
      <Volume2 className={sizeClasses[size]} />
    </Button>
  );
}

/**
 * Message actions dropdown menu
 */
export function MessageActions({
  content,
  messageId,
  canDelete = false,
  canPin = false,
  onDelete,
  onPin,
  onReply,
  position = 'top-right',
}: MessageActionsProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
      setIsOpen(false);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const positionClasses = {
    'top-right': '-top-1 -right-1',
    'bottom-right': '-bottom-1 -right-1',
  };

  return (
    <div className={`absolute ${positionClasses[position]} z-20 opacity-100 group-hover:opacity-100 transition-opacity duration-200`}>
      <div className="chat-action-bar">
        <CopyButton content={content} size="sm" />

        {(canDelete || canPin || onReply) && (
          <div className="relative">
            <Button onClick={() => setIsOpen(!isOpen)} className="chat-action-btn" aria-label="More actions" variant="ghost" size="sm" type="button">
              <MoreVertical className="w-3.5 h-3.5" />
            </Button>

            {isOpen && (
              <>
                <div className="fixed inset-0 z-20" onClick={() => setIsOpen(false)} />
                <div className={`chat-action-menu ${position === 'bottom-right' ? 'bottom-full mb-1' : 'top-full mt-1'}`}>
                  <Button onClick={handleCopy} className="chat-action-menu-item" variant="ghost" size="sm" type="button">
                    {copied ? (
                      <><Check className="w-4 h-4 fi-text-green" /><span className="fi-text-green">¡Copiado!</span></>
                    ) : (
                      <><Copy className="w-4 h-4" /><span>Copiar</span></>
                    )}
                  </Button>

                  {onReply && messageId && (
                    <Button onClick={() => { onReply(messageId); setIsOpen(false); }} className="chat-action-menu-item" variant="ghost" size="sm" type="button">
                      <Reply className="w-4 h-4" /><span>Responder</span>
                    </Button>
                  )}

                  {canPin && onPin && messageId && (
                    <Button onClick={() => { onPin(messageId); setIsOpen(false); }} className="chat-action-menu-item" variant="ghost" size="sm" type="button">
                      <Pin className="w-4 h-4" /><span>Fijar</span>
                    </Button>
                  )}

                  {canDelete && onDelete && messageId && (
                    <>
                      <div className="chat-dropdown-divider" />
                      <Button
                        onClick={async () => {
                          const confirmed = await confirmDelete('este mensaje');
                          if (confirmed) { onDelete(messageId); setIsOpen(false); }
                        }}
                        className="chat-action-menu-item-danger"
                        variant="danger"
                        size="sm"
                        type="button"
                      >
                        <Trash2 className="w-4 h-4" /><span>Eliminar</span>
                      </Button>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Code block with copy button
 */
export function CodeBlockWithCopy({ code, language }: { code: string; language?: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy code:', err);
    }
  };

  return (
    <div className="chat-code-block">
      <div className="chat-code-header">
        {language && <span className="chat-code-lang">{language}</span>}
        <Button onClick={handleCopy} className="chat-code-copy" variant="ghost" size="sm" type="button">
          {copied ? (
            <><Check className="w-3.5 h-3.5 fi-text-green" /><span className="text-xs fi-text-green">Copiado</span></>
          ) : (
            <><Copy className="w-3.5 h-3.5" /><span className="text-xs">Copiar</span></>
          )}
        </Button>
      </div>
      <pre className="chat-code-pre">
        <code className="chat-code-content">{code}</code>
      </pre>
    </div>
  );
}
