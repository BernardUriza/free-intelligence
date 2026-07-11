// fi-glass · message primitives (Plutonio, element 94).
// Generic, presentational, app-configurable via props/slots.
export { messageStyles, markdownStyles } from './styles';
export { MessageContent, type MessageContentProps } from './MessageContent';
// Exported so an app overriding `renderMarkdown` can reuse the same repair.
export { normalizeStreamedMarkdown } from './normalizeStreamedMarkdown';
export { CopyButton, type CopyButtonProps } from './CopyButton';
export { MessageBubble, type MessageBubbleProps } from './MessageBubble';
// OG118-IMAGE-UPLOAD-1: the images attached to a message, rendered in its bubble.
export { MessageImages, type MessageImagesProps } from './MessageImages';
// The default "who said this" row — rendered automatically off `message.author`.
export {
  MessageAuthorHeader,
  defaultMessageHeader,
  type MessageAuthorHeaderProps,
} from './MessageAuthorHeader';
// B3-FIGLASS-12: ChatGPT-style "show more" disclosure clamp for long content.
export { CollapsibleText, type CollapsibleTextProps } from './CollapsibleText';
export {
  MessageList,
  type MessageListProps,
  type MessageListGroup,
} from './MessageList';
