/**
 * ConversationCapture - Re-export from modular structure
 *
 * This file maintains backward compatibility.
 * The component has been refactored into:
 *   components/medical/conversation-capture/
 *
 * @see ./conversation-capture/ConversationCapture.tsx
 */

export { ConversationCapture } from './conversation-capture';
export type { ConversationCaptureProps, WorkflowStatus, ChunkMetric, ChunkStatus } from './conversation-capture';
