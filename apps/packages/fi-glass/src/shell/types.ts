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
export type ChatViewMode =
  | 'normal'
  | 'fullscreen'
  | 'dense'
  | 'minimized'
  | 'expanded';

/** Response verbosity preference (app-owned, surfaced in the toolbar). */
export type ResponseMode = 'explanatory' | 'concise';

/** Persona id — opaque string, resolved by the app's persona registry. */
export type PersonaType = string;

/** Typed navigation destinations — replaces the 3 hardcoded next/link hrefs. */
export type ChatNavDest = 'chat' | 'downloads' | 'personas';

/** Upload lifecycle the file-preview renders against (state owned by the app). */
export type UploadStatus =
  | 'selecting'
  | 'uploading'
  | 'pending_instructions'
  | 'processing'
  | 'indexed'
  | 'error';

/** Voice recorder snapshot the toolbar's mic button renders against. */
export interface VoiceRecordingState {
  isRecording: boolean;
  isTranscribing: boolean;
  audioLevel: number;
  isSilent: boolean;
  recordingTime: number;
}
