'use client';

/**
 * fi-glass · conversation-surface/ComposerRegion — the bottom section of the
 * surface: the new-chat CTA (B3-OG118-5 opt-out), the aboveComposer slot
 * (system banners, queues), and the ComposerFrame (header/body/footer anatomy,
 * COMPOSER-FRAME-1): drafts land in the header slot, the textarea is the body,
 * and the controls row (visualizer/mic/send) is the footer. The composer
 * column shares the transcript's fluid center cap and names the `fi-composer`
 * container for container-query-driven density (PR #312).
 */

import type { ReactNode, RefObject } from 'react';
import { Composer, ComposerFrame } from '../../../../composer';
import type { AgentConversationSurfaceProps } from '../../types';
import type { SurfaceDictation } from '../../hooks';
import { ComposerControls } from './ComposerControls';
import { NewChatButton } from './NewChatButton';

export interface ComposerRegionProps
  extends Pick<
    AgentConversationSurfaceProps,
    | 'aboveComposer'
    | 'composerHeader'
    | 'composerHeaderClassName'
    | 'composerBoxClassName'
    | 'composerAreaClassName'
    | 'composerTextareaClassName'
    | 'composerControlsClassName'
    | 'composerPlaceholder'
    | 'micSlotOverride'
    | 'micSlotClassName'
    | 'micButtonClassName'
    | 'voiceVisualizerClassName'
    | 'voiceVisualizerBarClassName'
    | 'sendButtonClassName'
    | 'sendButtonIconClassName'
  > {
  /** The fluid center cap (100% minus the responsive gutter). */
  contentInset: string;
  hasThread: boolean;
  isStreaming: boolean;
  newConversation: () => void;
  dictation: SurfaceDictation;
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  canSend: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  // Defaults resolved by the orchestrator → required here.
  showNewChatButton: boolean;
  newChatLabel: string;
  showSendButton: boolean;
  sendLabel: string;
}

export function ComposerRegion({
  contentInset,
  hasThread,
  isStreaming,
  newConversation,
  dictation,
  input,
  setInput,
  onSend,
  canSend,
  inputRef,
  showNewChatButton,
  newChatLabel,
  showSendButton,
  sendLabel,
  aboveComposer,
  composerHeader,
  composerHeaderClassName,
  composerBoxClassName,
  composerAreaClassName,
  composerTextareaClassName,
  composerControlsClassName,
  composerPlaceholder,
  micSlotOverride,
  micSlotClassName,
  micButtonClassName,
  voiceVisualizerClassName,
  voiceVisualizerBarClassName,
  sendButtonClassName,
  sendButtonIconClassName,
}: ComposerRegionProps) {
  const footer: ReactNode =
    showSendButton || micSlotOverride != null || dictation.micAvailable ? (
      <ComposerControls
        dictation={dictation}
        micSlotOverride={micSlotOverride}
        micSlotClassName={micSlotClassName}
        micButtonClassName={micButtonClassName}
        voiceVisualizerClassName={voiceVisualizerClassName}
        voiceVisualizerBarClassName={voiceVisualizerBarClassName}
        showSendButton={showSendButton}
        canSend={canSend}
        isStreaming={isStreaming}
        onSend={onSend}
        sendLabel={sendLabel}
        sendButtonClassName={sendButtonClassName}
        sendButtonIconClassName={sendButtonIconClassName}
      />
    ) : null;

  return (
    <div style={{ padding: '0.75rem 1rem 1.25rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
      {/* Composer column shares the transcript's fluid center cap (the
          section itself spans full width so its top border does too). */}
      <div style={{ maxWidth: contentInset, margin: '0 auto', width: '100%', containerType: 'inline-size', containerName: 'fi-composer' }}>
        {hasThread && showNewChatButton && (
          <NewChatButton onClick={newConversation} disabled={isStreaming} label={newChatLabel} />
        )}
        {aboveComposer && (
          <div className="fi-surface-above-composer" style={{ marginBottom: '0.5rem' }}>
            {aboveComposer}
          </div>
        )}
        {/* Floating composer box — ONE container wrapping the textarea row and
            the controls row, mirroring the shell's chat-input-floating-box
            (AURITY). The box structure is framework-owned so every consumer
            inherits the corrected anatomy; ComposerFrame formalizes it as
            header/body/footer slots. */}
        <ComposerFrame
          className={composerBoxClassName}
          header={composerHeader}
          headerClassName={composerHeaderClassName}
          footerClassName={composerControlsClassName}
          footer={footer}
        >
          <Composer
            message={input}
            loading={isStreaming}
            placeholder={composerPlaceholder}
            onMessageChange={setInput}
            onSend={onSend}
            areaClassName={composerAreaClassName}
            textareaClassName={composerTextareaClassName}
            // The input fills the composer area regardless of how the consumer
            // styles it (e.g. a flex area): growth is owned here, in the
            // framework, not patched in by a consumer reaching into `.relative`.
            wrapperStyle={{ flex: '1 1 0%', minWidth: 0 }}
            // Typed focus handle (B3-FIGLASS-10): the surface refocuses the
            // input after dictation/send/stream — no internal-DOM reach.
            textareaRef={inputRef}
          />
        </ComposerFrame>
      </div>
    </div>
  );
}
