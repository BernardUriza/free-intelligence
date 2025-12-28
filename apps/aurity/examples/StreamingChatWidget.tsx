import React, { useState } from 'react';
import { useCheckinConversation } from '@aurity-standalone/hooks/useCheckinConversation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';

/**
 * Example component showing how to use streaming in the chat widget
 */
export function StreamingChatWidget({
  clinicId,
  clinicName,
  enableStreaming = true, // Enable streaming by default
}: {
  clinicId: string;
  clinicName?: string;
  enableStreaming?: boolean;
}) {
  const {
    messages,
    conversationState,
    loading,
    isTyping,
    sessionId,
    streamingMessage, // New: current streaming content
    startConversation,
    sendMessage,
    sendQuickReply,
    endConversation,
  } = useCheckinConversation({
    clinicId,
    clinicName,
    enableStreaming, // Pass streaming option
  });

  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = async () => {
    if (!inputValue.trim()) return;
    await sendMessage(inputValue);
    setInputValue('');
  };

  const handleQuickReply = async (reply: string) => {
    await sendQuickReply(reply);
  };

  // Show streaming message if available
  const _currentAssistantMessage = streamingMessage || messages[messages.length - 1]?.content || '';

  return (
    <Card className="w-full max-w-2xl mx-auto p-6">
      <div className="space-y-4">
        {/* Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Check-in Assistant</h2>
          {enableStreaming && (
            <span className="text-sm text-green-600 bg-green-50 px-2 py-1 rounded">
              Streaming Enabled
            </span>
          )}
        </div>

        {/* Messages */}
        <div className="space-y-3 min-h-[300px] max-h-[400px] overflow-y-auto">
          {messages.map((message) => (
            <div
              key={message.metadata.id}
              className={`p-3 rounded-lg ${
                message.role === 'user'
                  ? 'bg-blue-50 ml-12'
                  : 'bg-gray-50 mr-12'
              }`}
            >
              <p className="text-sm">{message.content}</p>
              <span className="text-xs text-gray-500 mt-1 block">
                {new Date(message.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}

          {/* Streaming message */}
          {isTyping && streamingMessage && (
            <div className="bg-gray-50 mr-12 p-3 rounded-lg">
              <p className="text-sm">{streamingMessage}</p>
              <span className="text-xs text-blue-500 mt-1 block animate-pulse">
                Typing...
              </span>
            </div>
          )}

          {/* Typing indicator when not streaming */}
          {isTyping && !streamingMessage && (
            <div className="bg-gray-50 mr-12 p-3 rounded-lg">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          )}
        </div>

        {/* Quick Replies */}
        {conversationState?.quickReplies && conversationState.quickReplies.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {conversationState.quickReplies.map((reply, index) => (
              <Button
                key={index}
                variant="outline"
                size="sm"
                onClick={() => handleQuickReply(reply)}
                disabled={loading}
              >
                {reply}
              </Button>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="flex gap-2">
          <Input
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Type your message..."
            onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
            disabled={loading}
          />
          <Button
            onClick={handleSendMessage}
            disabled={loading || !inputValue.trim()}
          >
            Send
          </Button>
        </div>

        {/* Controls */}
        <div className="flex gap-2">
          {!sessionId ? (
            <Button onClick={startConversation} disabled={loading}>
              Start Conversation
            </Button>
          ) : (
            <Button variant="outline" onClick={endConversation}>
              End Conversation
            </Button>
          )}
        </div>

        {/* Status */}
        {sessionId && (
          <div className="text-xs text-gray-500">
            Session: {sessionId.slice(0, 8)}... |
            State: {conversationState?.state || 'unknown'} |
            Streaming: {enableStreaming ? 'ON' : 'OFF'}
          </div>
        )}
      </div>
    </Card>
  );
}