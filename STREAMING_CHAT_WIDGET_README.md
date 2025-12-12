# Streaming Chat Widget - AURITY

## Overview

The AURITY chat widget now supports **real-time streaming responses** using OpenAI-compatible Server-Sent Events (SSE). This provides a more interactive user experience where text appears progressively as the AI generates it.

## Features

✅ **OpenAI-Compatible Streaming** - Uses standard SSE format
✅ **Progressive Text Display** - Text appears character-by-character
✅ **Real-time UI Updates** - No waiting for complete responses
✅ **Backward Compatible** - Falls back to regular responses when disabled
✅ **Error Handling** - Graceful handling of streaming failures

## Usage

### Basic Usage

```tsx
import { StreamingChatWidget } from '@/examples/StreamingChatWidget';

function MyComponent() {
  return (
    <StreamingChatWidget
      clinicId="clinic-123"
      clinicName="Downtown Medical Center"
      enableStreaming={true} // Enable streaming
    />
  );
}
```

### Using the Hook Directly

```tsx
import { useCheckinConversation } from '@/hooks/useCheckinConversation';

function MyChatComponent() {
  const {
    messages,
    streamingMessage, // New: current streaming content
    isTyping,
    sendMessage,
    // ... other properties
  } = useCheckinConversation({
    clinicId: 'clinic-123',
    enableStreaming: true, // Enable streaming
  });

  return (
    <div>
      {/* Display regular messages */}
      {messages.map(msg => (
        <div key={msg.metadata.id}>{msg.content}</div>
      ))}

      {/* Display streaming message */}
      {isTyping && streamingMessage && (
        <div className="streaming">
          {streamingMessage}
          <span className="cursor">|</span>
        </div>
      )}
    </div>
  );
}
```

## API Changes

### Hook Options

```tsx
interface UseCheckinConversationOptions {
  clinicId: string;
  clinicName?: string;
  enableStreaming?: boolean; // New: Enable streaming responses
  onComplete?: (result: { appointmentId: string; patientId: string }) => void;
  onError?: (error: string) => void;
}
```

### Hook Return

```tsx
interface UseCheckinConversationReturn {
  messages: FIMessage[];
  conversationState: ConversationState | null;
  loading: boolean;
  isTyping: boolean;
  sessionId: string | null;
  streamingMessage: string; // New: Current streaming message content
  startConversation: () => Promise<void>;
  sendMessage: (message: string) => Promise<void>;
  sendQuickReply: (reply: string) => Promise<void>;
  endConversation: () => Promise<void>;
}
```

## How It Works

### Streaming Flow

1. **User sends message** → `sendMessage()`
2. **Hook calls streaming API** → `/api/workflows/aurity/assistant/chat/stream`
3. **Server sends SSE chunks** → `data: {"choices": [{"delta": {"content": "Hel"}}]}`
4. **Hook updates UI progressively** → Text appears character-by-character
5. **Stream completes** → `[DONE]` marker received
6. **Final message added** → Streaming message becomes regular message

### Server-Sent Events Format

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1640995200,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"role":"assistant"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1640995200,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"Hello"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1640995200,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{"content":"! I"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1640995200,"model":"gpt-4o-mini","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

## Configuration

### Enable Streaming

```tsx
// Enable streaming
<StreamingChatWidget enableStreaming={true} />

// Disable streaming (default behavior)
<StreamingChatWidget enableStreaming={false} />
```

### Environment Variables

No additional environment variables are required. The streaming endpoint uses the same backend configuration as regular chat.

## Testing

### With Running Backend

```bash
# Test streaming endpoint directly
curl -X POST "http://localhost:7001/api/workflows/aurity/assistant/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello"}],
    "model": "gpt-4o-mini",
    "persona": "general_assistant",
    "session_id": "test-stream-123",
    "stream": true
  }'
```

### Unit Tests

```bash
# Run streaming tests
npm test -- --testPathPattern=streaming
```

## Performance Considerations

- **Chunk Size**: Currently set to 10 characters per chunk
- **Delay**: 50ms artificial delay between chunks (for demo)
- **Memory**: Streaming messages are cleared after completion
- **Error Recovery**: Automatic fallback to regular API on streaming failures

## Browser Support

- ✅ Chrome 70+
- ✅ Firefox 65+
- ✅ Safari 12+
- ✅ Edge 79+

All modern browsers support Server-Sent Events.

## Troubleshooting

### Streaming Not Working

1. **Check backend**: Ensure `/api/workflows/aurity/assistant/chat/stream` is accessible
2. **Check browser**: Verify SSE support in browser dev tools
3. **Check network**: Look for SSE connection in network tab
4. **Fallback**: Hook automatically falls back to regular API if streaming fails

### Performance Issues

1. **Reduce chunk size** in backend for more frequent updates
2. **Increase delay** between chunks to reduce server load
3. **Monitor memory** usage with large conversations

## Migration Guide

### From Non-Streaming to Streaming

```tsx
// Before
const { messages, sendMessage } = useCheckinConversation({
  clinicId: 'clinic-123'
});

// After
const { messages, streamingMessage, sendMessage } = useCheckinConversation({
  clinicId: 'clinic-123',
  enableStreaming: true // Add this
});

// Update UI to show streaming message
{messages.map(msg => <div>{msg.content}</div>)}
{isTyping && streamingMessage && <div>{streamingMessage}</div>}
```

## Future Enhancements

- **Configurable chunk size** via API parameters
- **Streaming speed control** (slow/fast/normal)
- **Pause/resume streaming** functionality
- **Streaming progress indicators** (percentage complete)
- **Voice synthesis integration** with streaming text
