/**
 * @aurity-standalone/hooks
 *
 * Custom React hooks for Aurity healthcare platform.
 * Provides hooks for authentication, chat, AI assistants, medical workflows, and more.
 *
 * @packageDocumentation
 */

// Authentication & Authorization
export * from './useAuth';
export * from './useRBAC';

// Chat & Conversation
export * from './useChat';
export * from './useFIConversation';
export * from './useCheckinConversation';
export * from './useChatUpload';
export * from './useMessageGroups';
export * from './useOptimisticMessages';
export * from './useEmotionalContext';

// AI & Personas
export * from './usePersonas';

// Medical & Recording
export * from './useRecorder';
export * from './useTranscription';
