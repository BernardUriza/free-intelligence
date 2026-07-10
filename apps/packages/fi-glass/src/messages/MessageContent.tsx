'use client';

/**
 * fi-glass · MessageContent — rendered message body primitive.
 *
 * User messages: plain text (whitespace preserved).
 * Assistant messages: markdown (react-markdown + remark-gfm by default).
 *
 * CONFIGURABILITY (fire test): an app swaps the markdown engine via the
 * `renderMarkdown` slot without touching fi-glass. Default reproduces aurity's
 * exact markdown component overrides.
 */

import { memo, type ReactNode } from 'react';
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { messageStyles, markdownStyles } from './styles';
import { normalizeStreamedMarkdown } from './normalizeStreamedMarkdown';
import { CollapsibleText } from './CollapsibleText';

export interface MessageContentProps {
  /** Is this a user message */
  isUser: boolean;
  /** Message content */
  content: string;
  /** Show streaming cursor */
  isStreaming?: boolean;
  /** Override how assistant content is rendered (default: markdown). */
  renderMarkdown?: (content: string) => ReactNode;
  /**
   * B3-FIGLASS-12 — clamp long content behind a "show more" disclosure
   * (ChatGPT parity for long pasted user messages). Never combine with
   * `isStreaming`: a live answer must stay fully visible while it grows.
   */
  collapsible?: boolean;
  /** Collapsed max height in px when `collapsible`. Default 264. */
  collapsedMaxHeight?: number;
  /** Disclosure copy (app-owned). Defaults: "Mostrar más" / "Mostrar menos". */
  showMoreLabel?: string;
  showLessLabel?: string;
  /** Class for the disclosure toggle button. */
  collapseToggleClassName?: string;
}

/** Default markdown component overrides (glass styling).
 * Props are inferred from the Partial<Components> context so each slot
 * accepts ExtraProps (node?) without an explicit annotation. */
const mdComponents: Partial<Components> = {
  p: ({ children }) => <p className={markdownStyles.p}>{children}</p>,
  strong: ({ children }) => <strong className={markdownStyles.strong}>{children}</strong>,
  em: ({ children }) => <em className={markdownStyles.em}>{children}</em>,
  code: ({ children }) => <code className={markdownStyles.code}>{children}</code>,
  pre: ({ children }) => <pre className={markdownStyles.pre}>{children}</pre>,
  ul: ({ children }) => <ul className={markdownStyles.ul}>{children}</ul>,
  ol: ({ children }) => <ol className={markdownStyles.ol}>{children}</ol>,
  li: ({ children }) => (
    <li className={markdownStyles.li}>
      <span className={markdownStyles.bullet}>•</span>
      <span className="flex-1">{children}</span>
    </li>
  ),
  h1: ({ children }) => <h1 className={markdownStyles.h1}>{children}</h1>,
  h2: ({ children }) => <h2 className={markdownStyles.h2}>{children}</h2>,
  h3: ({ children }) => <h3 className={markdownStyles.h3}>{children}</h3>,
  blockquote: ({ children }) => <blockquote className={markdownStyles.blockquote}>{children}</blockquote>,
  a: ({ href, children }) => (
    <a href={href} className={markdownStyles.link} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  ),
};

function defaultRenderMarkdown(content: string): ReactNode {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]} components={mdComponents}>
      {/* remarkBreaks (B3-FIGLASS-VISUAL-1): LLMs separate paragraphs with a
          SINGLE newline far more than a double one — a real reply carried 155
          single vs 20 double. CommonMark folds a single \n into a space, so the
          whole answer collapsed into one <p> and rendered as a wall of glued
          sentences ("…inaceptable.Quiero…"). remark-breaks honors the model's
          single \n as a visible line break, the way ChatGPT/Claude.ai do.
          normalizeStreamedMarkdown still repairs the heading-glue case. */}
      {normalizeStreamedMarkdown(content)}
    </ReactMarkdown>
  );
}

export const MessageContent = memo(function MessageContent({
  isUser,
  content,
  isStreaming = false,
  renderMarkdown = defaultRenderMarkdown,
  collapsible = false,
  collapsedMaxHeight,
  showMoreLabel,
  showLessLabel,
  collapseToggleClassName,
}: MessageContentProps) {
  const { content: styles } = messageStyles;

  const body = isUser ? (
    // User: plain text, preserve whitespace
    <p className="whitespace-pre-wrap">{content}</p>
  ) : (
    // Assistant: markdown (overridable)
    renderMarkdown(content)
  );

  return (
    <div
      className={`${styles.base} ${isUser ? styles.user : styles.assistant} ${styles.indent}`}
    >
      {collapsible && !isStreaming ? (
        <CollapsibleText
          maxHeight={collapsedMaxHeight}
          showMoreLabel={showMoreLabel}
          showLessLabel={showLessLabel}
          toggleClassName={collapseToggleClassName}
        >
          {body}
        </CollapsibleText>
      ) : (
        body
      )}

      {/* Streaming cursor */}
      {isStreaming && (
        <span className="inline-block w-1.5 h-4 bg-amber-400/80 ml-0.5 animate-pulse rounded-sm" />
      )}
    </div>
  );
});
