import * as react from 'react';

/**
 * fi-glass · shell types — the SHARED vocabulary live surfaces speak.
 *
 * What is left here is only what MORE THAN ONE surface uses: og118 types its
 * project uploads against `UploadStatus`, aurity's relocated glass-shell speaks
 * `ChatViewMode`/`ChatNavDest`/`ResponseMode`/`PersonaType`, and the toolbar's
 * mic renders against `VoiceRecordingState`. The widget-shaped props contracts
 * (`ChatWidgetProps`, `ChatContentProps`, `ShellStreamingState`) moved to
 * `apps/aurity/components/chat/glass-shell/types.ts` with the components they
 * describe (B3-FIGLASS-SHELL-CONSOLIDATION-1).
 *
 * fi-glass NEVER imports useAuth / useFIConversation / usePersonas / next/* /
 * @/components/ui/*.
 */
/** View modes a chat container can render in (aurity's glass-shell reads this). */
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

interface ChatFilePreviewProps {
    file: File;
    status: UploadStatus;
    progress?: number;
    error?: string;
    onCancel: () => void;
}
declare function ChatFilePreview({ file, status, progress, error, onCancel, }: ChatFilePreviewProps): react.JSX.Element;

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

export { type BreakpointMatches, type Breakpoints, ChatFilePreview, type ChatFilePreviewProps, type ChatNavDest, type ChatViewMode, FI_TOUCH_TARGET_CLASS, type PersonaType, type ResponseMode, type UploadStatus, type UseMediaQueryOptions, type VoiceRecordingState, clearMediaQueryCache, ensureTouchTargetStyle, useBreakpoints, useMediaQuery, useTouchTargetStyle, withTouchTarget };
