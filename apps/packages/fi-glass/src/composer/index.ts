// fi-glass · composer (Americio, element 95 — slice 1/2).
export { Composer, type ComposerProps } from './Composer';
export {
  AutoResizeTextarea,
  type AutoResizeTextareaProps,
} from './AutoResizeTextarea';
export {
  ComposerFrame,
  ensureComposerFrameStyle,
  useComposerFrameStyle,
  type ComposerFrameProps,
} from './ComposerFrame';
// OG118-IMAGE-UPLOAD-1: image attachments (state hook + chips + attach trigger).
export {
  useComposerImages,
  COMPOSER_IMAGE_ACCEPT,
  COMPOSER_IMAGE_MEDIA_TYPES,
  DEFAULT_MAX_IMAGES,
  type ComposerImageDraft,
  type ComposerImages,
  type UseComposerImagesOptions,
} from './useComposerImages';
export {
  useImagePicker,
  ComposerImageChips,
  type ImagePicker,
  type ComposerImageChipsProps,
} from './ComposerImageAttachments';
// The shared "+" — one trigger for every add-to-this-turn capability.
export {
  ComposerActions,
  type ComposerAction,
  type ComposerActionsProps,
} from './ComposerActions';
