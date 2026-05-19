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
import { Building2, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ChatWidget } from '@/components/chat/ChatWidget';
import { useCheckinConversation } from '@aurity-standalone/hooks/useCheckinConversation';
import { createLogger } from '@/lib/internal/logger';
import { receptionistChatConfig } from '@/config/chat.config';

const log = createLogger('ReceptionistChat');
import {
  receptionistEmptyStateConfig,
  receptionistQuickActions,
} from '@/config/chat-messages.config';
import { getDynamicIcon } from '@/lib/icons';
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
    <span className="mb-4 block" aria-hidden="true">
      <Building2 className="w-12 h-12 text-indigo-400" strokeWidth={1.5} />
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
          className="checkin-feature-item"
        >
          <span className="text-indigo-400" aria-hidden="true">
            <Check className="w-4 h-4" strokeWidth={2} />
          </span>
          <span className="text-sm fi-text">{feature.text}</span>
        </div>
      ))}
    </div>
    <div className="w-full max-w-sm">
      <p className="fi-text-xs-muted text-center mb-3">
        Selecciona una opción o escribe tu mensaje
      </p>
      <div className="grid grid-cols-2 gap-3">
        {receptionistQuickActions.map((action) => {
          const ActionIcon = getDynamicIcon(action.iconKey);
          return (
            <Button
              key={action.id}
              onClick={() => onQuickAction(action.message)}
              disabled={loading}
              className="checkin-quick-action"
              variant="ghost"
              size="lg"
              type="button"
              title={action.label}
            >
              <span aria-hidden="true">
                <ActionIcon className="w-6 h-6" strokeWidth={1.5} />
              </span>
              <span className="text-sm fi-text text-center">
                {action.label}
              </span>
            </Button>
          );
        })}
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
        className="checkin-quick-reply"
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
      log.error('Conversation error', { error: String(error) });
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
