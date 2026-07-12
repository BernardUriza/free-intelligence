'use client';

/**
 * fi-glass · conversation-surface/ComposerRegion — the bottom section of the
 * surface: the new-chat CTA (B3-OG118-5 opt-out), the aboveComposer slot
 * (system banners, queues), and the ComposerFrame (header/body/footer anatomy,
 * COMPOSER-FRAME-1): drafts land in the header slot, the textarea is the body,
 * and the controls row (visualizer/mic/send) is the footer. The composer
 * column shares the transcript's fluid center cap and names the `fi-composer`
 * container for container-query-driven density (PR #312).
 *
 * Contract shape (REGION-PROPS-1, kills the 29-prop thread-through): the
 * region takes the surface's whole public props object as `surface` — it reads
 * its slice and resolves ITS copy defaults — plus one `state` object with the
 * orchestrator-owned composing state and the shared layout inset.
 */

import type { ReactNode, RefObject } from 'react';
import { Composer, ComposerFrame } from '../../../../composer';
import { ImagePlus } from 'lucide-react';
import {
  useImagePicker,
  ComposerImageChips,
} from '../../../../composer/ComposerImageAttachments';
import { ComposerActions, type ComposerAction } from '../../../../composer/ComposerActions';
import type { ComposerImages } from '../../../../composer/useComposerImages';
import type { AgentConversationSurfaceProps } from '../../types';
import type { SurfaceDictation } from '../../hooks';
import { ComposerControls } from './ComposerControls';
import { NewChatButton } from './NewChatButton';

/** The orchestrator-owned state the composer region renders. */
export interface SurfaceComposerState {
  input: string;
  setInput: (value: string) => void;
  onSend: () => void;
  canSend: boolean;
  inputRef: RefObject<HTMLTextAreaElement | null>;
  dictation: SurfaceDictation;
  isStreaming: boolean;
  /** Cancel the streaming turn — undefined when the transport cannot abort. */
  onStop?: () => void;
  hasThread: boolean;
  newConversation: () => void;
  /** Image-attachment state (OG118-IMAGE-UPLOAD-1) — null when the surface's
   * `imageAttachments` switch is off, and the composer renders as before. */
  images: ComposerImages | null;
}

export interface ComposerRegionProps {
  /** The surface's public props — the region reads its slice + copy defaults. */
  surface: AgentConversationSurfaceProps;
  state: SurfaceComposerState;
  /** The fluid center cap (100% minus the responsive gutter). */
  contentInset: string;
}

export function ComposerRegion({ surface, state, contentInset }: ComposerRegionProps) {
  const {
    input,
    setInput,
    onSend,
    canSend,
    inputRef,
    dictation,
    isStreaming,
    onStop,
    hasThread,
    newConversation,
    images,
  } = state;
  const {
    aboveComposer,
    composerHeader,
    composerHeaderClassName,
    composerFooterStart,
    composerFooterStartClassName,
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
    stopButtonClassName,
    showNewChatButton = true,
    newChatLabel = 'New chat',
    showSendButton = true,
    sendLabel = 'Enviar mensaje',
    stopLabel = 'Detener respuesta',
    attachImageLabel = 'Adjuntar imagen',
    composerActions,
    composerActionsLabel,
    composerActionsMenuClassName,
    composerActionsItemClassName,
    attachImageButtonClassName,
    imageChipsClassName,
  } = surface;

  // OG118-IMAGE-UPLOAD-1: the chips are a preview OF the message being composed,
  // so they live in the ComposerFrame HEADER (like the audio draft); the attach
  // trigger is something the user sets before composing, so it leads the
  // FOOTER-START rail (COMPOSER-FOOTER-ZONES-1), before the app's own chips.
  const imageChips =
    images && images.drafts.length > 0 ? (
      <ComposerImageChips
        drafts={images.drafts}
        onRemove={images.remove}
        disabled={isStreaming}
        className={imageChipsClassName}
      />
    ) : null;
  // Every "add something to this turn" capability hangs off ONE "+": attaching an
  // image is an action, not a button of its own (a button per capability is the
  // crowding ComposerActions exists to prevent). The app can inject more actions
  // — upload a document to the active project, and whatever comes next — and they
  // land in the same menu instead of growing the rail.
  const imagePicker = useImagePicker((files) => void (images && images.addFiles(files)));
  const actions: ComposerAction[] = [
    ...(images
      ? [
          {
            id: 'attach-image',
            label: attachImageLabel ?? 'Adjuntar imagen',
            icon: <ImagePlus size={16} aria-hidden />,
            onSelect: imagePicker.open,
          },
        ]
      : []),
    ...(composerActions ?? []),
  ];
  const attachButton =
    actions.length > 0 ? (
      <>
        {images ? imagePicker.input : null}
        <ComposerActions
          actions={actions}
          disabled={isStreaming}
          label={composerActionsLabel}
          className={attachImageButtonClassName}
          menuClassName={composerActionsMenuClassName}
          itemClassName={composerActionsItemClassName}
        />
      </>
    ) : null;
  const header =
    imageChips || composerHeader ? (
      <>
        {imageChips}
        {composerHeader}
      </>
    ) : undefined;
  const footerStart =
    attachButton || composerFooterStart ? (
      <>
        {attachButton}
        {composerFooterStart}
      </>
    ) : undefined;

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
        onStop={onStop}
        sendLabel={sendLabel}
        stopLabel={stopLabel}
        sendButtonClassName={sendButtonClassName}
        sendButtonIconClassName={sendButtonIconClassName}
        stopButtonClassName={stopButtonClassName}
      />
    ) : null;

  return (
    <div
      style={{
        // The composer is the surface's bottom edge, so it is what a notched
        // phone's home indicator overlaps once the app runs full-bleed
        // (`viewport-fit=cover` / an installed standalone PWA). env() resolves
        // to 0px everywhere else, so the desktop padding is unchanged.
        padding: '0.75rem 1rem calc(1.25rem + env(safe-area-inset-bottom, 0px))',
        paddingLeft: 'calc(1rem + env(safe-area-inset-left, 0px))',
        paddingRight: 'calc(1rem + env(safe-area-inset-right, 0px))',
        borderTop: '1px solid rgba(255,255,255,0.06)',
      }}
    >
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
          header={header}
          headerClassName={composerHeaderClassName}
          footerClassName={composerControlsClassName}
          footerStart={footerStart}
          footerStartClassName={composerFooterStartClassName}
          footer={footer}
        >
          <Composer
            message={input}
            loading={isStreaming}
            placeholder={composerPlaceholder}
            onMessageChange={setInput}
            onSend={onSend}
            // Paste-an-image (ChatGPT parity): image files in the clipboard
            // become attachment chips; plain-text paste falls through untouched.
            onPaste={
              images
                ? (e) => {
                    if (images.handlePaste(e)) e.preventDefault();
                  }
                : undefined
            }
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
