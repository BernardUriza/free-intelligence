'use client';

/**
 * MessageContent - Markdown rendered content
 *
 * Clean markdown with subtle styling
 * User messages: plain text
 * Assistant messages: full markdown
 */

import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { BaseMessageProps } from '../core/types';
import { messageStyles, markdownStyles } from '../config/styles';

export interface MessageContentProps extends BaseMessageProps {
  /** Message content */
  content: string;
  /** Show streaming cursor */
  isStreaming?: boolean;
}

/** Markdown component overrides */
const mdComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className={markdownStyles.p}>{children}</p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className={markdownStyles.strong}>{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className={markdownStyles.em}>{children}</em>
  ),
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className={markdownStyles.code}>{children}</code>
  ),
  pre: ({ children }: { children?: React.ReactNode }) => (
    <pre className={markdownStyles.pre}>{children}</pre>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className={markdownStyles.ul}>{children}</ul>
  ),
  ol: ({ children }: { children?: React.ReactNode }) => (
    <ol className={markdownStyles.ol}>{children}</ol>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className={markdownStyles.li}>
      <span className={markdownStyles.bullet}>•</span>
      <span className="flex-1">{children}</span>
    </li>
  ),
  h1: ({ children }: { children?: React.ReactNode }) => (
    <h1 className={markdownStyles.h1}>{children}</h1>
  ),
  h2: ({ children }: { children?: React.ReactNode }) => (
    <h2 className={markdownStyles.h2}>{children}</h2>
  ),
  h3: ({ children }: { children?: React.ReactNode }) => (
    <h3 className={markdownStyles.h3}>{children}</h3>
  ),
  blockquote: ({ children }: { children?: React.ReactNode }) => (
    <blockquote className={markdownStyles.blockquote}>{children}</blockquote>
  ),
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
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

export const MessageContent = memo(function MessageContent({
  isUser,
  content,
  isStreaming = false,
}: MessageContentProps) {
  const { content: styles } = messageStyles;

  return (
    <div className={`${styles.base} ${isUser ? styles.user : styles.assistant} ${styles.indent}`}>
      {isUser ? (
        // User: plain text, preserve whitespace
        <p className="whitespace-pre-wrap">{content}</p>
      ) : (
        // Assistant: markdown
        <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>
          {content}
        </ReactMarkdown>
      )}

      {/* Streaming cursor */}
      {isStreaming && (
        <span className="inline-block w-1.5 h-4 bg-amber-400/80 ml-0.5 animate-pulse rounded-sm" />
      )}
    </div>
  );
});
