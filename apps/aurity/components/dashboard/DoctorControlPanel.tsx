/**
 * DoctorControlPanel - TV Display Control Interface
 *
 * Card: FI-UI-FEAT-TVD-001
 * Comprehensive TV control with Messages, Media Upload, and AI Content
 *
 * Features:
 * - Tab 1: Text Messages (quick messages + custom)
 * - Tab 2: Multimedia Upload (images, videos)
 * - Tab 3: AI Content Generator (health tips, trivia) - NOW FUNCTIONAL
 * - Tab 4: FI Receptionist Chat
 */

'use client';

import { useState, useCallback } from 'react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { MediaUploader, type UploadedMedia } from './MediaUploader';
import { AIContentGenerator, type GeneratedContent } from './AIContentGenerator';
import { MessageSquare, Film, Sparkles, MessageCircle, Send, Video, Info, Lightbulb, HelpCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ReceptionistChatWidget } from '@/components/checkin/ReceptionistChatWidget';
import { QUICK_MESSAGES, MAX_MESSAGE_LENGTH } from '@/lib/dashboard/constants';
import { getDynamicIcon } from '@/lib/icons';

interface DoctorControlPanelProps {
  /** Callback when message is sent to TV */
  onMessageSend: (message: string) => void;

  /** Current message being displayed (if any) */
  currentMessage?: string | null;

  /** Clinic name for context */
  clinicName?: string;

  /** Doctor ID for media uploads */
  doctorId?: string;

  /** Clinic ID for media categorization */
  clinicId?: string;
}

export function DoctorControlPanel({
  onMessageSend,
  currentMessage = null,
  clinicName = 'la clínica',
  doctorId,
  clinicId,
}: DoctorControlPanelProps) {
  const [messageInput, setMessageInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [activeTab, setActiveTab] = useState('messages');

  // Use centralized quick messages from constants
  const quickMessages = QUICK_MESSAGES;

  const handleSendMessage = () => {
    if (!messageInput.trim()) return;

    setIsSending(true);

    // Simulate API call delay
    setTimeout(() => {
      onMessageSend(messageInput.trim());
      setMessageInput('');
      setIsSending(false);
    }, 500);
  };

  const handleQuickMessage = useCallback((message: string) => {
    setIsSending(true);

    setTimeout(() => {
      onMessageSend(message);
      setIsSending(false);
    }, 500);
  }, [onMessageSend]);

  const handleClearMessage = () => {
    setIsSending(true);

    setTimeout(() => {
      onMessageSend('');
      setIsSending(false);
    }, 500);
  };

  const handleMediaUpload = useCallback((media: UploadedMedia) => {
    console.log('Media uploaded:', media);
    // TODO: Add to carousel rotation
  }, []);

  const handleAIContentGenerated = useCallback((content: GeneratedContent) => {
    console.log('AI content generated:', content);
    // Send the content as a message to the TV display
    // Note: TV display uses text-only messages, icons rendered separately
    if (content.type === 'tip') {
      onMessageSend(`[TIP] ${content.content}`);
    } else if (content.type === 'trivia') {
      // Format trivia for display
      const triviaMsg = `[TRIVIA] ${content.content}`;
      onMessageSend(triviaMsg);
    }
  }, [onMessageSend]);

  return (
    <div className="dcp-shell">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="dcp-tabs-wrap">
        {/* Header */}
        <div className="dcp-header fi-border-bottom">
          <div className="dcp-header-row">
            <div>
              <h2 className="fi-title fi-flex-gap">
                <Video className="fi-icon-md fi-icon-purple" />
                Control de TV
              </h2>
              <p className="fi-subtitle">Contenido para sala de espera · {clinicName}</p>
            </div>

            {/* Live indicator */}
            <div className="fi-flex-gap">
              <div className="dcp-live-dot"></div>
              <span className="fi-text-xs-medium fi-text-purple dcp-live-label">TRANSMITIENDO</span>
            </div>
          </div>

          {/* Tabs Navigation */}
          <TabsList className="dcp-tabs-list">
            <TabsTrigger
              value="messages"
              className="dcp-tab-trigger"
            >
              <MessageSquare className="dcp-tab-icon" />
              Mensajes
            </TabsTrigger>
            <TabsTrigger
              value="media"
              className="dcp-tab-trigger"
            >
              <Film className="dcp-tab-icon" />
              Multimedia
            </TabsTrigger>
            <TabsTrigger
              value="ai-content"
              className="dcp-tab-trigger"
            >
              <Sparkles className="dcp-tab-icon" />
              Contenido IA
            </TabsTrigger>
            <TabsTrigger
              value="chat"
              className="dcp-tab-trigger-alt"
            >
              <MessageCircle className="dcp-tab-icon" />
              Chat IA
            </TabsTrigger>
          </TabsList>
        </div>

        {/* TAB 1: Messages */}
        <TabsContent value="messages" className="dcp-tab-content">
          {/* Current Message Display */}
          {currentMessage && (
            <div className="dcp-current-msg">
              <div className="dcp-current-msg-row">
                <div className="dcp-current-msg-body">
                  <p className="dcp-current-msg-label">MENSAJE ACTUAL EN TV</p>
                  <p className="dcp-current-msg-text">{currentMessage}</p>
                </div>
                <Button
                  onClick={handleClearMessage}
                  disabled={isSending}
                  variant="secondary"
                  size="sm"
                >
                  Quitar
                </Button>
              </div>
            </div>
          )}

          {/* Message Composer */}
          <div className="dcp-composer">
        {/* Custom Message Input */}
        <div>
          <label htmlFor="tv-message" className="fi-label">
            Mensaje Personalizado
          </label>
          <div className="dcp-input-row">
            <textarea
              id="tv-message"
              rows={3}
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              placeholder="Escribe un mensaje para los pacientes en sala de espera..."
              className="dcp-textarea"
              disabled={isSending}
            />
          </div>
          <div className="dcp-char-row">
            <span className={`dcp-char-count ${messageInput.length > MAX_MESSAGE_LENGTH ? 'fi-text-error' : 'dcp-char-count-ok'}`}>
              {messageInput.length}/{MAX_MESSAGE_LENGTH} caracteres
            </span>
            <Button
              onClick={handleSendMessage}
              disabled={!messageInput.trim() || isSending}
              variant="purple"
              size="sm"
              icon={Send}
              loading={isSending}
            >
              {isSending ? 'Enviando...' : 'Enviar a TV'}
            </Button>
          </div>
        </div>

        {/* Quick Messages */}
        <div>
          <label className="fi-label">
            Mensajes Rápidos
          </label>
          <div className="dcp-quick-grid">
            {quickMessages.map((msg) => {
              const MsgIcon = getDynamicIcon(msg.iconKey);
              return (
                <Button
                  key={msg.id}
                  type="button"
                  onClick={() => handleQuickMessage(msg.text)}
                  disabled={isSending}
                  className="dcp-quick-btn fi-text"
                  aria-label={`Enviar mensaje: ${msg.text}`}
                  variant="ghost"
                  size="sm"
                >
                  <span className="dcp-quick-icon" aria-hidden="true">
                    <MsgIcon className="dcp-quick-icon-inner" strokeWidth={1.5} />
                  </span>
                  <span className="dcp-quick-text">
                    {msg.text}
                  </span>
                </Button>
              );
            })}
          </div>
        </div>

            {/* Preview Mode Info */}
            <div className="dcp-info-box fi-border-top/50">
              <div className="dcp-info-inner">
                <Info className="fi-icon-md fi-text-primary dcp-info-icon" />
                <div className="dcp-info-body">
                  <p className="dcp-info-title">Vista Previa de TV</p>
                  <p className="dcp-info-desc fi-text-primary/80">
                    Los mensajes se intercalan con tips de salud y filosofía de Free Intelligence.
                    Tus mensajes aparecen cada ~1-2 minutos con duración de 20 segundos.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* TAB 2: Media Upload */}
        <TabsContent value="media" className="dcp-tab-content">
          <div className="dcp-tab-body">
            <MediaUploader
              onMediaUpload={handleMediaUpload}
              clinicId={clinicId}
              doctorId={doctorId}
            />
          </div>
        </TabsContent>

        {/* TAB 3: AI Content Generator - NOW FUNCTIONAL */}
        <TabsContent value="ai-content" className="dcp-tab-content">
          <div className="dcp-tab-body">
            <AIContentGenerator
              onContentGenerated={handleAIContentGenerated}
              clinicId={clinicId}
            />
          </div>
        </TabsContent>

        {/* TAB 4: FI Receptionist Chat */}
        <TabsContent value="chat" className="dcp-tab-content">
          <div className="dcp-chat-wrap">
            {/* Chat Header Info */}
            <div className="dcp-chat-header">
              <div className="fi-flex-between">
                <div className="fi-flex-gap">
                  <div className="dcp-chat-dot"></div>
                  <span className="fi-text-xs-medium dcp-chat-label">FI Receptionist Activo</span>
                </div>
                <span className="fi-text-xs-muted">
                  Prueba el chatbot de check-in
                </span>
              </div>
            </div>

            {/* Embedded Chat Widget */}
            <div className="dcp-chat-body">
              <ReceptionistChatWidget
                clinicId={clinicId || 'demo-clinic'}
                clinicName={clinicName}
                onCheckinComplete={(result) => {
                  console.log('[DoctorControlPanel] Check-in demo completed:', result);
                }}
              />
            </div>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
