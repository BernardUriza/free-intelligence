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
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { messageStyles, markdownStyles } from './styles';
import { normalizeStreamedMarkdown } from './normalizeStreamedMarkdown';

export interface MessageContentProps {
  /** Is this a user message */
  isUser: boolean;
  /** Message content */
  content: string;
  /** Show streaming cursor */
  isStreaming?: boolean;
  /** Override how assistant content is rendered (default: markdown). */
  renderMarkdown?: (content: string) => ReactNode;
}

/** Default markdown component overrides (glass styling). */
const mdComponents = {
  p: ({ children }: { children?: ReactNode }) => (
    <p className={markdownStyles.p}>{children}</p>
  ),
  strong: ({ children }: { children?: ReactNode }) => (
    <strong className={markdownStyles.strong}>{children}</strong>
  ),
  em: ({ children }: { children?: ReactNode }) => (
    <em className={markdownStyles.em}>{children}</em>
  ),
  code: ({ children }: { children?: ReactNode }) => (
    <code className={markdownStyles.code}>{children}</code>
  ),
  pre: ({ children }: { children?: ReactNode }) => (
    <pre className={markdownStyles.pre}>{children}</pre>
  ),
  ul: ({ children }: { children?: ReactNode }) => (
    <ul className={markdownStyles.ul}>{children}</ul>
  ),
  ol: ({ children }: { children?: ReactNode }) => (
    <ol className={markdownStyles.ol}>{children}</ol>
  ),
  li: ({ children }: { children?: ReactNode }) => (
    <li className={markdownStyles.li}>
      <span className={markdownStyles.bullet}>•</span>
      <span className="flex-1">{children}</span>
    </li>
  ),
  h1: ({ children }: { children?: ReactNode }) => (
    <h1 className={markdownStyles.h1}>{children}</h1>
  ),
  h2: ({ children }: { children?: ReactNode }) => (
    <h2 className={markdownStyles.h2}>{children}</h2>
  ),
  h3: ({ children }: { children?: ReactNode }) => (
    <h3 className={markdownStyles.h3}>{children}</h3>
  ),
  blockquote: ({ children }: { children?: ReactNode }) => (
    <blockquote className={markdownStyles.blockquote}>{children}</blockquote>
  ),
  a: ({ href, children }: { href?: string; children?: ReactNode }) => (
    <a
      href={href}
      className={markdownStyles.link}
      target="_blank"
      rel="noopener noreferrer"
    >
      {children}
    </a>
  ),
};

function defaultRenderMarkdown(content: string): ReactNode {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
      {/* B3-FIGLASS-9: repair chunk-boundary glue (e.g. "fin.## Título") so a
          heading the stream stuck onto the previous sentence still renders as a
          heading. Pure + fence-safe; see normalizeStreamedMarkdown. */}
      {normalizeStreamedMarkdown(content)}
    </ReactMarkdown>
  );
}

export const MessageContent = memo(function MessageContent({
  isUser,
  content,
  isStreaming = false,
  renderMarkdown = defaultRenderMarkdown,
}: MessageContentProps) {
  const { content: styles } = messageStyles;

  return (
    <div
      className={`${styles.base} ${isUser ? styles.user : styles.assistant} ${styles.indent}`}
    >
      {isUser ? (
        // User: plain text, preserve whitespace
        <p className="whitespace-pre-wrap">{content}</p>
      ) : (
        // Assistant: markdown (overridable)
        renderMarkdown(content)
      )}

      {/* Streaming cursor */}
      {isStreaming && (
        <span className="inline-block w-1.5 h-4 bg-amber-400/80 ml-0.5 animate-pulse rounded-sm" />
      )}
    </div>
  );
});
