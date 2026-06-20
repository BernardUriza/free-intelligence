import * as react from 'react';
import { ReactNode } from 'react';
import { ChatMessage, ChatHook } from '@free-intelligence/core';

/**
 * fi-glass · shell config — the ChatConfig contract the shell renders against.
 *
 * Copied (shape-for-shape) from aurity's `config/chat.config.ts` so the app can
 * pass its own ChatConfig into <ChatWidget config={…}> with zero friction
 * (TypeScript checks structurally). The shell only ever reads `title`,
 * `subtitle`, `theme.background.header` and `behavior.showThinking`; the rest of
 * the shape is kept identical so the default is complete and the app's superset
 * stays assignable. Persona styles are NOT here — they belong to the message
 * render layer (aurity domain), not the shell skeleton.
 */
interface ChatTheme {
    background: {
        header: string;
        body: string;
        input: string;
    };
    border: {
        main: string;
        input: string;
        bubble: string;
    };
    text: {
        primary: string;
        secondary: string;
        muted: string;
        accent: string;
    };
    accent: {
        from: string;
        to: string;
    };
    shadow: string;
    timestamp: {
        text: string;
        tooltip: string;
    };
}
interface ChatBehavior {
    autoScroll: boolean;
    showTyping: boolean;
    groupMessages: boolean;
    groupThresholdMinutes: number;
    showDayDividers: boolean;
    animateEntrance: boolean;
    maxMessages: number;
    inputPlaceholder: string;
    sendButtonLabel?: string;
    enableReactions: boolean;
    enableReadReceipts: boolean;
    enableThinking: boolean;
    showThinking: boolean;
}
interface TimestampConfig {
    show: boolean;
    format: 'relative' | 'absolute' | 'smart';
    showTooltip: boolean;
    relativeThreshold: number;
    showSeconds: boolean;
    position: 'top' | 'bottom' | 'inline';
    updateInterval?: number;
}
interface AnimationConfig {
    entrance: {
        enabled: boolean;
        duration: string;
        easing: string;
    };
    typing: {
        dotDuration: string;
        dotDelay: string;
    };
    scroll: {
        behavior: 'smooth' | 'auto';
        duration: number;
    };
}
interface ChatConfig {
    title: string;
    subtitle?: string;
    theme: ChatTheme;
    behavior: ChatBehavior;
    timestamp: TimestampConfig;
    animation: AnimationConfig;
    footer?: string;
    dimensions?: {
        width: string;
        height: string;
        minHeight?: string;
        maxHeight?: string;
    };
}
declare const defaultTheme: ChatTheme;
declare const defaultBehavior: ChatBehavior;
declare const defaultTimestampConfig: TimestampConfig;
declare const defaultAnimationConfig: AnimationConfig;
/** Neutral default — apps inject their own ChatConfig and only fall back here. */
declare const defaultChatConfig: ChatConfig;
/** Merge a partial app config over the fi-glass default (one level deep on the nested groups). */
declare function mergeChatConfig(custom?: Partial<ChatConfig>): ChatConfig;
interface ChatBreakpoints {
    mobile: string;
    tablet: string;
    desktop: string;
}
declare const CHAT_BREAKPOINTS: ChatBreakpoints;

/**
 * fi-glass · shell types — the dependency-inverted ChatWidget contract.
 *
 * The shell consumes core's `ChatHook` (the conversation spine) and receives
 * everything domain-shaped as props or slots: auth (`user`/`isAuthenticated`/
 * `onLogin`), navigation (`onNavigate`, a TYPED union — not next/link), the
 * persona selector / history / messages (React-node SLOTS the app fills), and
 * the voice + file-upload state (their hooks live in the app). fi-glass NEVER
 * imports useAuth / useFIConversation / usePersonas / next/* / @/components/ui/*.
 */

/** View modes handled by ChatWidgetContainer. */
type ChatViewMode = 'normal' | 'fullscreen' | 'dense' | 'minimized' | 'expanded';
/** Response verbosity preference (app-owned, surfaced in the toolbar). */
type ResponseMode = 'explanatory' | 'concise';
/** Persona id — opaque string, resolved by the app's persona registry. */
type PersonaType = string;
/** Typed navigation destinations — replaces the 3 hardcoded next/link hrefs. */
type ChatNavDest = 'chat' | 'downloads' | 'personas';
/** Upload lifecycle the file-preview renders against (state owned by the app). */
type UploadStatus = 'selecting' | 'uploading' | 'pending_instructions' | 'processing' | 'indexed' | 'error';
/** Voice recorder snapshot the toolbar's mic button renders against. */
interface VoiceRecordingState {
    isRecording: boolean;
    isTranscribing: boolean;
    audioLevel: number;
    isSilent: boolean;
    recordingTime: number;
}
/** Streaming snapshot passed through to the messages slot. */
interface ShellStreamingState {
    status: 'idle' | 'streaming' | 'complete' | 'error';
    content: string;
    thinking: string;
    isStreaming: boolean;
}
/**
 * ChatWidget props — generic over the message type (`TMessage`, the app's
 * FIMessage) and the custom-slot node type (`TNode`) the ChatHook is keyed on.
 */
interface ChatWidgetProps<TMessage = ChatMessage, TNode = unknown> {
    /** REQUIRED — the conversation hook. No internal default. */
    chatHook: ChatHook<TMessage, TNode>;
    /** App ChatConfig (merged over the fi-glass neutral default). */
    config?: Partial<ChatConfig>;
    user?: {
        sub?: string;
        name?: string;
    } | null;
    isAuthenticated?: boolean;
    onLogin?: () => void;
    onNavigate?: (dest: ChatNavDest) => void;
    isMobile?: boolean;
    initialOpen?: boolean;
    initialMode?: ChatViewMode;
    embedded?: boolean;
    message: string;
    onMessageChange: (value: string) => void;
    onSend: () => void;
    responseMode?: ResponseMode;
    selectedPersona?: PersonaType;
    personaName?: string;
    showThinking?: boolean;
    onResponseModeToggle?: () => void;
    onShowThinkingToggle?: () => void;
    onPersonaChange?: (persona: PersonaType) => void;
    onClearConversation?: () => void;
    voiceState?: VoiceRecordingState;
    onVoiceStart?: () => void;
    onVoiceStop?: () => void;
    uploadFile?: File | null;
    uploadStatus?: UploadStatus;
    isUploadActive?: boolean;
    onAttach?: () => void;
    onCancelUpload?: () => void;
    isStartingConversation?: boolean;
    onStartConversation?: () => void;
    /** PersonaSelectorPanel (uses @/components/ui/select) — lives in the app. */
    personaSelector?: ReactNode;
    /** HistorySearch (useAuth + backend fetch) — lives in the app. fi-glass owns the close. */
    renderHistory?: (ctx: {
        onClose: () => void;
    }) => ReactNode;
    /** ChatWidgetMessages + ./messages subtree (domain) — lives in the app. fi-glass owns the view mode. */
    renderMessages?: (ctx: {
        viewMode: ChatViewMode;
    }) => ReactNode;
    /** Copy-curl dev tool (uses app routes/env). */
    onCopyCurl?: () => void;
}
/** Props for the presentational shell skeleton (ChatContent). */
interface ChatContentProps {
    config: ChatConfig;
    embedded: boolean;
    isAuthenticated: boolean;
    userName?: string;
    viewMode: ChatViewMode;
    isHistoryOpen: boolean;
    isStartingConversation: boolean;
    messageCount: number;
    loading: boolean;
    isTyping: boolean;
    loadingInitial: boolean;
    customEmptyState?: ReactNode;
    customQuickReplies?: ReactNode;
    message: string;
    responseMode?: ResponseMode;
    selectedPersona?: PersonaType;
    personaName?: string;
    showThinking?: boolean;
    voiceState?: VoiceRecordingState;
    uploadFile?: File | null;
    uploadStatus?: UploadStatus;
    isUploadActive?: boolean;
    onNavigate?: (dest: ChatNavDest) => void;
    onModeChange: (mode: ChatViewMode) => void;
    onMinimize: () => void;
    onMaximize: () => void;
    onToggleDenseMode: () => void;
    onClose: () => void;
    onHistoryOpen: () => void;
    onHistoryClose: () => void;
    onStartConversation: () => void;
    onLogin: () => void;
    onMessageChange: (message: string) => void;
    onSend: () => void;
    onResponseModeToggle?: () => void;
    onShowThinkingToggle?: () => void;
    onPersonaChange?: (persona: PersonaType) => void;
    onClearConversation?: () => void;
    onVoiceStart?: () => void;
    onVoiceStop?: () => void;
    onAttach?: () => void;
    onCancelUpload?: () => void;
    onCopyCurl?: () => void;
    personaSelector?: ReactNode;
    renderHistory?: (ctx: {
        onClose: () => void;
    }) => ReactNode;
    renderMessages?: (ctx: {
        viewMode: ChatViewMode;
    }) => ReactNode;
}

declare function ChatWidget<TMessage = ChatMessage, TNode = unknown>({ chatHook, config: customConfig, user, isAuthenticated, onLogin, onNavigate, isMobile: isMobileProp, initialOpen, initialMode, embedded, message, onMessageChange, onSend, responseMode, selectedPersona, personaName, showThinking, onResponseModeToggle, onShowThinkingToggle, onPersonaChange, onClearConversation, voiceState, onVoiceStart, onVoiceStop, uploadFile, uploadStatus, isUploadActive, onAttach, onCancelUpload, isStartingConversation, onStartConversation, personaSelector, renderHistory, renderMessages, onCopyCurl, }: ChatWidgetProps<TMessage, TNode>): react.JSX.Element | null;

/**
 * Same surface as ChatWidget minus the launcher/view-mode knobs, which
 * ChatSurface fixes to the always-open full-page configuration.
 */
type ChatSurfaceProps<TMessage = ChatMessage, TNode = unknown> = Omit<ChatWidgetProps<TMessage, TNode>, 'initialOpen' | 'embedded' | 'initialMode'>;
declare function ChatSurface<TMessage = ChatMessage, TNode = unknown>(props: ChatSurfaceProps<TMessage, TNode>): react.JSX.Element;

declare function ChatContent({ config, embedded, isAuthenticated, userName, viewMode, isHistoryOpen, isStartingConversation, messageCount, loading, isTyping, loadingInitial, customEmptyState, customQuickReplies, message, responseMode, selectedPersona, personaName, showThinking, voiceState, uploadFile, uploadStatus, isUploadActive, onNavigate, onModeChange, onMinimize, onMaximize, onToggleDenseMode, onClose, onHistoryOpen, onHistoryClose, onStartConversation, onLogin, onMessageChange, onSend, onResponseModeToggle, onShowThinkingToggle, onPersonaChange: _onPersonaChange, onClearConversation, onVoiceStart, onVoiceStop, onAttach, onCancelUpload, onCopyCurl, personaSelector, renderHistory, renderMessages, }: ChatContentProps): react.JSX.Element;

interface ChatWidgetContainerProps {
    /** Current view mode */
    mode: ChatViewMode;
    /** Widget title (for minimized view) */
    title: string;
    /** Children (header, messages, input) */
    children: ReactNode;
    /** Whether the widget is embedded in a page (uses relative positioning) */
    embedded?: boolean;
    /** Callbacks */
    onModeChange: (mode: ChatViewMode) => void;
}
declare function ChatWidgetContainer(props: ChatWidgetContainerProps): react.JSX.Element;

interface ChatWidgetHeaderProps {
    title: string;
    subtitle?: string;
    backgroundClass?: string;
    mode: ChatViewMode;
    showControls?: boolean;
    showHistorySearch?: boolean;
    onNavigate?: (dest: ChatNavDest) => void;
    onMinimize?: () => void;
    onMaximize?: () => void;
    onToggleDenseMode?: () => void;
    onClose?: () => void;
    onHistorySearch?: () => void;
}
declare function ChatWidgetHeader({ title, subtitle, backgroundClass, mode, showControls, showHistorySearch, onNavigate, onMinimize, onMaximize, onToggleDenseMode, onClose, onHistorySearch, }: ChatWidgetHeaderProps): react.JSX.Element;

interface ChatToolbarProps {
    showAttach?: boolean;
    showLanguage?: boolean;
    showFormatting?: boolean;
    showResponseMode?: boolean;
    showVoice?: boolean;
    showPersonaSelector?: boolean;
    showThinkingToggle?: boolean;
    responseMode?: ResponseMode;
    selectedPersona?: PersonaType;
    showThinking?: boolean;
    voiceRecording?: VoiceRecordingState;
    /** Persona selector SLOT (app's PersonaSelectorPanel). */
    personaSelector?: ReactNode;
    onAttach?: () => void;
    onLanguage?: () => void;
    onFormatting?: () => void;
    onResponseModeToggle?: () => void;
    onVoiceStart?: () => void;
    onVoiceStop?: () => void;
    onShowThinkingToggle?: () => void;
    /** Show the clear-conversation control (off when no handler is wired). */
    showClear?: boolean;
    /** Clear conversation — the app wraps this with its confirm dialog. */
    onClearConversation?: () => void;
    /** Show copy-curl dev tool button. */
    showCopyCurl?: boolean;
    /** Copy-curl handler — the app builds the template + toasts. */
    onCopyCurl?: () => void;
    onSend?: () => void;
    canSend?: boolean;
    sendLoading?: boolean;
}
declare function ChatToolbar({ showAttach, showLanguage, showFormatting, showResponseMode, showVoice, showPersonaSelector, showThinkingToggle, responseMode, selectedPersona: _selectedPersona, showThinking, voiceRecording, personaSelector, onAttach, onLanguage, onFormatting, onResponseModeToggle, onVoiceStart, onVoiceStop, onShowThinkingToggle, showClear, onClearConversation, showCopyCurl, onCopyCurl, onSend, canSend, sendLoading, }: ChatToolbarProps): react.JSX.Element;

interface ChatFilePreviewProps {
    file: File;
    status: UploadStatus;
    progress?: number;
    error?: string;
    onCancel: () => void;
}
declare function ChatFilePreview({ file, status, progress, error, onCancel, }: ChatFilePreviewProps): react.JSX.Element;

interface ChatStartScreenProps {
    /** Whether the user is authenticated */
    isAuthenticated: boolean;
    /** User's display name */
    userName?: string;
    /** Callback when user clicks "Comenzar" */
    onStart: () => void;
    /** Callback when user clicks "Iniciar sesión" */
    onLogin: () => void;
    /** Typed navigation (downloads link) */
    onNavigate?: (dest: ChatNavDest) => void;
    /** Whether the start action is loading */
    isLoading?: boolean;
}
declare function ChatStartScreen({ isAuthenticated, userName, onStart, onLogin: _onLogin, onNavigate, isLoading, }: ChatStartScreenProps): react.JSX.Element;

/**
 * fi-glass · FloatingButton — the closed-state launcher (bottom-right).
 * Pure: lucide icon + app CSS classes (fi-fab-emerald, fi-dot-pulse-red,
 * fi-tooltip-right live in the app's stylesheet). Copied verbatim from aurity.
 */
interface FloatingButtonProps {
    onClick: () => void;
    isMobile: boolean;
}
declare function FloatingButton({ onClick, isMobile }: FloatingButtonProps): react.JSX.Element;

/**
 * fi-glass · useChatWidgetState — widget UI state (open/close, view mode,
 * history panel, conversation-started). Pure React, no domain. Copied verbatim
 * from aurity (it had zero coupling).
 */

interface UseChatWidgetStateOptions {
    initialOpen: boolean;
    initialMode: ChatViewMode;
}
interface UseChatWidgetStateReturn {
    isOpen: boolean;
    viewMode: ChatViewMode;
    isHistoryOpen: boolean;
    conversationStarted: boolean;
    isStartingConversation: boolean;
    open: () => void;
    close: () => void;
    setViewMode: (mode: ChatViewMode) => void;
    minimize: () => void;
    maximize: () => void;
    toggleDenseMode: () => void;
    openHistory: () => void;
    closeHistory: () => void;
    startConversation: () => void;
    onMessagesLoaded: (hasMessages: boolean) => void;
}
declare function useChatWidgetState({ initialOpen, initialMode, }: UseChatWidgetStateOptions): UseChatWidgetStateReturn;

/**
 * fi-glass · useMediaQuery — pure, tearing-free media-query subscription.
 *
 * Copied verbatim from aurity's `hooks/useMediaQuery.ts` (it had zero domain
 * coupling — only React). The shell's responsive container consumes it so
 * fi-glass never reaches back into the app for breakpoint state.
 *
 * - useSyncExternalStore for concurrent-safe reads
 * - SSR-safe (configurable server snapshot)
 * - global MediaQueryList cache shared across components
 * - RAF-debounced notifications
 * - legacy addListener/removeListener fallback
 */
interface UseMediaQueryOptions {
    ssrMatch?: boolean;
    useRaf?: boolean;
    cache?: boolean;
}
declare function useMediaQuery(query: string, options?: UseMediaQueryOptions): boolean;
interface Breakpoints {
    mobile: string;
    tablet: string;
    desktop: string;
}
interface BreakpointMatches {
    isMobile: boolean;
    isTablet: boolean;
    isDesktop: boolean;
}
declare function useBreakpoints(breakpoints: Breakpoints, options?: Pick<UseMediaQueryOptions, 'ssrMatch'>): BreakpointMatches;
declare function clearMediaQueryCache(): void;

declare const FI_TOUCH_TARGET_CLASS = "fi-touch-target";
/** Inject the idempotent touch-target stylesheet (no-op on the server / if already present). */
declare function ensureTouchTargetStyle(): void;
/** Ensure the touch-target stylesheet is present for the lifetime of a control. */
declare function useTouchTargetStyle(): void;
/** Compose {@link FI_TOUCH_TARGET_CLASS} with an optional consumer class (additive, order-stable). */
declare function withTouchTarget(className?: string): string;

export { type AnimationConfig, type BreakpointMatches, type Breakpoints, CHAT_BREAKPOINTS, type ChatBehavior, type ChatBreakpoints, type ChatConfig, ChatContent, type ChatContentProps, ChatFilePreview, type ChatFilePreviewProps, type ChatNavDest, ChatStartScreen, type ChatStartScreenProps, ChatSurface, type ChatSurfaceProps, type ChatTheme, ChatToolbar, type ChatToolbarProps, type ChatViewMode, ChatWidget, ChatWidgetContainer, type ChatWidgetContainerProps, ChatWidgetHeader, type ChatWidgetHeaderProps, type ChatWidgetProps, FI_TOUCH_TARGET_CLASS, FloatingButton, type FloatingButtonProps, type PersonaType, type ResponseMode, type ShellStreamingState, type TimestampConfig, type UploadStatus, type UseChatWidgetStateOptions, type UseChatWidgetStateReturn, type UseMediaQueryOptions, type VoiceRecordingState, clearMediaQueryCache, defaultAnimationConfig, defaultBehavior, defaultChatConfig, defaultTheme, defaultTimestampConfig, ensureTouchTargetStyle, mergeChatConfig, useBreakpoints, useChatWidgetState, useMediaQuery, useTouchTargetStyle, withTouchTarget };
