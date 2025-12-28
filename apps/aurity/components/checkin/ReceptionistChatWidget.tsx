/**
 * ReceptionistChatWidget - FI Receptionist Chat Interface
 *
 * Card: FI-CHECKIN-005
 * Conversational check-in widget using the state-machine backend
 *
 * Uses:
 * - useCheckinConversation hook for backend communication
 * - receptionistChatConfig for styling
 * - Quick replies from backend conversation state
 */

'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { ChatWidget } from '@/components/chat/ChatWidget';
import { useCheckinConversation } from '@aurity-standalone/hooks/useCheckinConversation';
import { receptionistChatConfig } from '@/config/chat.config';
import {
  receptionistEmptyStateConfig,
  receptionistQuickActions,
} from '@/config/chat-messages.config';
import type { ChatHook } from '@aurity-standalone/types/chat';

// =============================================================================
// TYPES
// =============================================================================

export interface ReceptionistChatWidgetProps {
  /** Clinic ID from QR code */
  clinicId: string;
  /** Optional clinic display name */
  clinicName?: string;
  /** Optional pre-filled patient name */
  patientName?: string;
  /** Called when check-in is successfully completed */
  onCheckinComplete?: (result: CheckinResult) => void;
}

export interface CheckinResult {
  patientId: string;
  appointmentId: string;
  queuePosition?: number;
  estimatedWaitMinutes?: number;
}

interface EmptyStateProps {
  onQuickAction: (message: string) => void;
  patientName?: string;
  loading: boolean;
}

interface QuickRepliesProps {
  quickReplies: string[];
  onQuickReply: (reply: string) => void;
  loading: boolean;
}

// =============================================================================
// COMPONENT
// =============================================================================

const ReceptionistEmptyState = ({ onQuickAction, patientName, loading }: EmptyStateProps) => (
  <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 text-center">
    <span className="text-5xl mb-4 block">
      {receptionistEmptyStateConfig.emoji}
    </span>
    <h2 className="fi-title-2xl mb-2">
      {receptionistEmptyStateConfig.welcomeTitle(patientName)}
    </h2>
    <p className="text-slate-400 max-w-md mx-auto">
      {receptionistEmptyStateConfig.welcomeSubtitle}
    </p>
    <div className="w-full max-w-sm space-y-2 my-8">
      {receptionistEmptyStateConfig.features.map((feature, idx) => (
        <div
          key={idx}
          className="flex items-center gap-3 px-4 py-2 bg-slate-800/50 rounded-lg"
        >
          <span className="text-indigo-400">{feature.icon}</span>
          <span className="text-sm fi-text">{feature.text}</span>
        </div>
      ))}
    </div>
    <div className="w-full max-w-sm">
      <p className="fi-text-xs-muted text-center mb-3">
        Selecciona una opción o escribe tu mensaje
      </p>
      <div className="grid grid-cols-2 gap-3">
        {receptionistQuickActions.map((action) => (
          <Button
            key={action.id}
            onClick={() => onQuickAction(action.message)}
            disabled={loading}
            className="flex flex-col items-center gap-2 px-4 py-4 bg-indigo-950/30 hover:bg-indigo-950/50 border border-indigo-600/30 hover:border-indigo-600/50 rounded-xl transition-all disabled:opacity-50"
            variant="ghost"
            size="lg"
            type="button"
            title={action.label}
          >
            <span className="text-2xl">{action.icon}</span>
            <span className="text-sm fi-text text-center">
              {action.label}
            </span>
          </Button>
        ))}
      </div>
    </div>
  </div>
);

const ReceptionistQuickReplies = ({ quickReplies, onQuickReply, loading }: QuickRepliesProps) => (
  <div className="px-4 pb-2 flex flex-wrap gap-2 justify-center">
    {quickReplies.map((reply, idx) => (
      <Button
        key={idx}
        onClick={() => onQuickReply(reply)}
        disabled={loading}
        className="px-4 py-2 bg-indigo-600/20 hover:bg-indigo-600/40 border border-indigo-500/40 text-indigo-300 text-sm rounded-full transition-all disabled:opacity-50"
        variant="ghost"
        size="sm"
        type="button"
        title={reply}
      >
        {reply}
      </Button>
    ))}
  </div>
);

export function ReceptionistChatWidget({
  clinicId,
  clinicName,
  patientName,
  onCheckinComplete,
}: ReceptionistChatWidgetProps) {
  const [hasStarted, setHasStarted] = useState(false);

  const checkinHook = useCheckinConversation({
    clinicId,
    clinicName: clinicName || 'la clínica',
    onComplete: (result) => {
      onCheckinComplete?.({
        patientId: result.patientId,
        appointmentId: result.appointmentId,
      });
    },
    onError: (error) => {
      console.error('[ReceptionistChatWidget] Error:', error);
    },
  });

  const handleQuickAction = async (actionMessage: string) => {
    if (checkinHook.loading) return;
    if (!hasStarted) {
      setHasStarted(true);
      await checkinHook.startConversation?.();
      setTimeout(() => {
        checkinHook.sendMessage(actionMessage);
      }, 500);
    }
  };

  const handleSendMessage = async (message: string) => {
    if (!hasStarted) {
      setHasStarted(true);
      await checkinHook.startConversation?.();
      await checkinHook.sendMessage(message);
    } else {
      await checkinHook.sendMessage(message);
    }
  };

  const showEmptyState = !hasStarted && checkinHook.messages.length === 0;

  const chatHook: ChatHook = {
    ...checkinHook,
    // Convert null to undefined and transform actions for ChatHook compatibility
    conversationState: checkinHook.conversationState
      ? {
          quickReplies: checkinHook.conversationState.quickReplies,
          actions: checkinHook.conversationState.actions?.map((action) => ({
            type: action.type,
            data: action.data ?? action,
          })),
          metadata: checkinHook.conversationState.metadata,
        }
      : undefined,
    sendMessage: handleSendMessage,
    loadingInitial: false,
    hasMoreMessages: false,
    loadingOlder: false,
    loadOlderMessages: async () => {},
    customEmptyState: showEmptyState ? (
      <ReceptionistEmptyState
        onQuickAction={handleQuickAction}
        patientName={patientName}
        loading={checkinHook.loading}
      />
    ) : null,
    customQuickReplies:
      checkinHook.conversationState?.quickReplies &&
      checkinHook.conversationState.quickReplies.length > 0 &&
      !checkinHook.loading ? (
        <ReceptionistQuickReplies
          quickReplies={checkinHook.conversationState.quickReplies}
          onQuickReply={checkinHook.sendQuickReply!}
          loading={checkinHook.loading}
        />
      ) : null,
  };

  return (
    <ChatWidget
      config={receptionistChatConfig}
      initialOpen={true}
      initialMode="fullscreen"
      embedded={true}
      chatHook={chatHook}
    />
  );
}
