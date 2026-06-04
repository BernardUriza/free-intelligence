'use client';

/**
 * MessageActions Component
 *
 * Practical message actions (copy, delete, etc.)
 * Simple, clean, functional.
 */

import { useState } from 'react';
import { Copy, Check, MoreVertical, Trash2, Pin, Reply } from 'lucide-react';
import { confirmDelete } from '@/lib/swal';
import { Button } from '@/components/ui/button';
import { createLogger } from '@/lib/internal/logger';
import { SpeakButton as GlassSpeakButton } from 'fi-glass/voice';

const log = createLogger('MessageActions');

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
      log.error('Failed to copy', { error: String(err) });
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
        {copied ? '¡Copiado!' : 'Copiar mensaje'}
      </span>
    </Button>
  );
}

/**
 * Speak button with Azure TTS
 *
 * Thin domain wrapper over fi-glass's <SpeakButton> (Californio, element 98).
 * fi-glass owns the presentation; aurity injects the exact class string the old
 * Button (ghost) produced — `fi-btn-ghost fi-btn-<size> <pad> chat-action-btn` —
 * so the button renders byte-identically. Playback is the app's job, opened via
 * onOpenPlayer (provided by AudioPlayerContext).
 */
const SPEAK_FI_BTN_SIZE = { xs: 'fi-btn-xs', sm: 'fi-btn-sm', md: '' } as const;
const SPEAK_PAD = { xs: 'p-1', sm: 'p-1.5', md: 'p-2' } as const;

export function SpeakButton(props: {
  content: string;
  size?: 'xs' | 'sm' | 'md';
  voice?: string;
  /** Whether this is a user message (allows voice selection in player) */
  isUserMessage?: boolean;
  /** Callback to open the global audio player (required - provided by AudioPlayerContext) */
  onOpenPlayer: (text: string, voice: string, isUserMessage?: boolean) => void;
}) {
  const size = props.size ?? 'sm';
  const className = ['fi-btn-ghost', SPEAK_FI_BTN_SIZE[size], `${SPEAK_PAD[size]} chat-action-btn`]
    .filter(Boolean)
    .join(' ');
  return <GlassSpeakButton {...props} size={size} className={className} />;
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
      log.error('Failed to copy', { error: String(err) });
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
      log.error('Failed to copy code', { error: String(err) });
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
