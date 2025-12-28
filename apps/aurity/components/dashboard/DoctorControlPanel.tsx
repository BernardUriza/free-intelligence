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
import { MessageSquare, Film, Sparkles, MessageCircle, Send, Video, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ReceptionistChatWidget } from '@/components/checkin/ReceptionistChatWidget';
import { QUICK_MESSAGES, MAX_MESSAGE_LENGTH } from '@/lib/dashboard/constants';

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
    if (content.type === 'tip') {
      onMessageSend(`💡 ${content.content}`);
    } else if (content.type === 'trivia') {
      // Format trivia for display
      const triviaMsg = `❓ ${content.content}`;
      onMessageSend(triviaMsg);
    }
  }, [onMessageSend]);

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-lg overflow-hidden">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        {/* Header */}
        <div className="px-6 py-4 bg-slate-900/50 fi-border-bottom">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="fi-title flex items-center gap-2">
                <Video className="fi-icon-md fi-icon-purple" />
                Control de TV
              </h2>
              <p className="fi-subtitle">Contenido para sala de espera · {clinicName}</p>
            </div>

            {/* Live indicator */}
            <div className="fi-flex-gap">
              <div className="w-2 h-2 bg-purple-500 rounded-full animate-pulse shadow-lg shadow-purple-500/50"></div>
              <span className="fi-text-xs-medium fi-text-purple tracking-wide">TRANSMITIENDO</span>
            </div>
          </div>

          {/* Tabs Navigation */}
          <TabsList className="bg-slate-900/80 p-1 w-full grid grid-cols-4 gap-1">
            <TabsTrigger
              value="messages"
              className="data-[state=active]:bg-purple-600 data-[state=active]:text-white data-[state=inactive]:text-slate-400 data-[state=inactive]:hover:text-white rounded-md transition-all"
            >
              <MessageSquare className="w-4 h-4 mr-2" />
              Mensajes
            </TabsTrigger>
            <TabsTrigger
              value="media"
              className="data-[state=active]:bg-purple-600 data-[state=active]:text-white data-[state=inactive]:text-slate-400 data-[state=inactive]:hover:text-white rounded-md transition-all"
            >
              <Film className="w-4 h-4 mr-2" />
              Multimedia
            </TabsTrigger>
            <TabsTrigger
              value="ai-content"
              className="data-[state=active]:bg-purple-600 data-[state=active]:text-white data-[state=inactive]:text-slate-400 data-[state=inactive]:hover:text-white rounded-md transition-all"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              Contenido IA
            </TabsTrigger>
            <TabsTrigger
              value="chat"
              className="data-[state=active]:bg-indigo-600 data-[state=active]:text-white data-[state=inactive]:text-slate-400 data-[state=inactive]:hover:text-white rounded-md transition-all"
            >
              <MessageCircle className="w-4 h-4 mr-2" />
              Chat IA
            </TabsTrigger>
          </TabsList>
        </div>

        {/* TAB 1: Messages */}
        <TabsContent value="messages" className="mt-0">
          {/* Current Message Display */}
          {currentMessage && (
            <div className="px-6 py-4 bg-purple-950/20 border-b border-purple-700/30">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <p className="text-xs text-purple-300 font-medium mb-1">MENSAJE ACTUAL EN TV</p>
                  <p className="text-sm text-white">{currentMessage}</p>
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
          <div className="p-6 space-y-4">
        {/* Custom Message Input */}
        <div>
          <label htmlFor="tv-message" className="fi-label">
            Mensaje Personalizado
          </label>
          <div className="flex gap-2">
            <textarea
              id="tv-message"
              rows={3}
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              placeholder="Escribe un mensaje para los pacientes en sala de espera..."
              className="flex-1 px-4 py-2 bg-slate-900/50 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-purple-500 text-sm resize-none"
              disabled={isSending}
            />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className={`text-xs ${messageInput.length > MAX_MESSAGE_LENGTH ? 'fi-text-error' : 'text-slate-500'}`}>
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
          <div className="grid grid-cols-1 gap-2">
            {quickMessages.map((msg) => (
              <Button
                key={msg.id}
                type="button"
                onClick={() => handleQuickMessage(`${msg.emoji} ${msg.text}`)}
                disabled={isSending}
                className="px-4 py-2 bg-slate-900/50 hover:bg-slate-800 border border-slate-600 hover:border-purple-500/50 disabled:bg-slate-900 disabled:cursor-not-allowed text-left text-sm fi-text hover:text-white rounded-lg transition-all group"
                aria-label={`Enviar mensaje: ${msg.text}`}
                variant="ghost"
                size="sm"
              >
                <span className="group-hover:text-purple-300">
                  {msg.emoji} {msg.text}
                </span>
              </Button>
            ))}
          </div>
        </div>

            {/* Preview Mode Info */}
            <div className="pt-4 fi-border-top/50">
              <div className="flex items-start gap-3 p-3 bg-blue-950/20 border border-blue-700/30 rounded-lg">
                <Info className="fi-icon-md fi-text-primary flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-blue-300 mb-1">Vista Previa de TV</p>
                  <p className="text-xs fi-text-primary/80 leading-relaxed">
                    Los mensajes se intercalan con tips de salud y filosofía de Free Intelligence.
                    Tus mensajes aparecen cada ~1-2 minutos con duración de 20 segundos.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        {/* TAB 2: Media Upload */}
        <TabsContent value="media" className="mt-0">
          <div className="p-6">
            <MediaUploader
              onMediaUpload={handleMediaUpload}
              clinicId={clinicId}
              doctorId={doctorId}
            />
          </div>
        </TabsContent>

        {/* TAB 3: AI Content Generator - NOW FUNCTIONAL */}
        <TabsContent value="ai-content" className="mt-0">
          <div className="p-6">
            <AIContentGenerator
              onContentGenerated={handleAIContentGenerated}
              clinicId={clinicId}
            />
          </div>
        </TabsContent>

        {/* TAB 4: FI Receptionist Chat */}
        <TabsContent value="chat" className="mt-0">
          <div className="h-[500px] flex flex-col">
            {/* Chat Header Info */}
            <div className="px-4 py-3 bg-indigo-950/30 border-b border-indigo-700/30">
              <div className="fi-flex-between">
                <div className="fi-flex-gap">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="fi-text-xs-medium text-indigo-300">FI Receptionist Activo</span>
                </div>
                <span className="fi-text-xs-muted">
                  Prueba el chatbot de check-in
                </span>
              </div>
            </div>

            {/* Embedded Chat Widget */}
            <div className="flex-1 overflow-hidden">
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
