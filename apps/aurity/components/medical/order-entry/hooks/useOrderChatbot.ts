/**
 * useOrderChatbot Hook
 *
 * Manages AI chatbot state and LLM-based order creation.
 */

import { useState, useCallback } from 'react';
import { medicalWorkflowApi, type MedicalOrder } from '@aurity-standalone/api-client/medical-workflow';
import type { ChatMessage, OrderType } from '../types';

interface UseOrderChatbotProps {
  sessionId: string;
  onOrderCreated: (order: MedicalOrder) => void;
}

export function useOrderChatbot({ sessionId, onOrderCreated }: UseOrderChatbotProps) {
  const [showChatbot, setShowChatbot] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const toggleChatbot = useCallback(() => {
    setShowChatbot(prev => !prev);
  }, []);

  const closeChatbot = useCallback(() => {
    setShowChatbot(false);
  }, []);

  const handleChatSend = useCallback(async () => {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput('');
    setChatLoading(true);

    setChatMessages(prev => [...prev, { role: 'user', content: userMessage }]);

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_BASE}/api/aurity/medical-ai/sessions/${sessionId}/assistant`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            command: userMessage,
            current_soap: {
              diagnosticTests: [],
              medications: [],
              pastMedicalHistory: [],
              allergies: [],
              hpi: '',
              physicalExam: '',
              primaryDiagnosis: null,
              differentialDiagnoses: [],
              followUp: ''
            }
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      // Process diagnostic tests
      if (result.updates.diagnosticTests) {
        const tests = parseOperationContent(result.updates.diagnosticTests);

        for (const test of tests) {
          const orderType: OrderType = isImagingTest(test) ? 'imaging' : 'lab';

          const orderId = await medicalWorkflowApi.createOrder(sessionId, {
            type: orderType,
            description: test,
          });

          onOrderCreated({
            id: orderId,
            type: orderType,
            description: test,
            source: 'manual',
            created_at: new Date().toISOString()
          });
        }
      }

      // Process medications
      if (result.updates.medications) {
        const meds = parseOperationContent(result.updates.medications, true);

        for (const med of meds) {
          const description = typeof med === 'string'
            ? med
            : `${med.name} ${med.dosage} ${med.frequency}`;

          const orderId = await medicalWorkflowApi.createOrder(sessionId, {
            type: 'medication',
            description,
          });

          onOrderCreated({
            id: orderId,
            type: 'medication',
            description,
            source: 'manual',
            created_at: new Date().toISOString()
          });
        }
      }

      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: result.explanation
      }]);
    } catch (error) {
      console.error('[Chatbot] Error:', error);
      setChatMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : 'Desconocido'}`
      }]);
    } finally {
      setChatLoading(false);
    }
  }, [chatInput, chatLoading, sessionId, onOrderCreated]);

  return {
    showChatbot,
    chatMessages,
    chatInput,
    chatLoading,
    toggleChatbot,
    closeChatbot,
    setChatInput,
    handleChatSend,
  };
}

// Helper functions
function parseOperationContent(operation: string, parseJson = false): any[] {
  const colonIndex = operation.indexOf(':');
  const op = operation.substring(0, colonIndex);
  const content = operation.substring(colonIndex + 1);

  if (op === 'add_items') {
    return JSON.parse(content);
  } else if (op === 'add_item') {
    return parseJson ? [JSON.parse(content)] : [content];
  }
  return [];
}

function isImagingTest(test: string): boolean {
  const lowerTest = test.toLowerCase();
  return lowerTest.includes('radiografía') ||
         lowerTest.includes('tomografía') ||
         lowerTest.includes('resonancia');
}
