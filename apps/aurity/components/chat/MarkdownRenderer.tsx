'use client';

/**
 * MarkdownRenderer Component
 *
 * Renders markdown content with GFM, code highlighting, emoji support, and custom styling.
 * Uses semantic CSS classes from chat.css (chat-md-*)
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Components } from 'react-markdown';

export interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const markdownComponents: Components = {
  h1: ({ children }) => <h1 className="chat-md-h1">{children}</h1>,
  h2: ({ children }) => <h2 className="chat-md-h2">{children}</h2>,
  h3: ({ children }) => <h3 className="chat-md-h3">{children}</h3>,
  h4: ({ children }) => <h4 className="chat-md-h4">{children}</h4>,
  p: ({ children }) => <p className="chat-md-p">{children}</p>,
  ul: ({ children }) => <ul className="chat-md-ul">{children}</ul>,
  ol: ({ children }) => <ol className="chat-md-ol">{children}</ol>,
  li: ({ children }) => <li className="chat-md-li">{children}</li>,

  code: ({ className, children, ...props }: React.HTMLAttributes<HTMLElement>) => {
    const match = /language-(\w+)/.exec(className || '');
    const isInline = !match;
    return isInline ? (
      <code className="chat-md-code-inline" {...props}>{children}</code>
    ) : (
      <code className={`chat-md-code-block ${className || ''}`} {...props}>{children}</code>
    );
  },

  blockquote: ({ children }) => <blockquote className="chat-md-blockquote">{children}</blockquote>,

  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="chat-md-link">
      {children}
    </a>
  ),

  hr: () => <hr className="chat-md-hr" />,
  strong: ({ children }) => <strong className="chat-md-strong">{children}</strong>,
  em: ({ children }) => <em className="chat-md-em">{children}</em>,

  table: ({ children }) => (
    <div className="chat-md-table-wrapper">
      <table className="chat-md-table">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="chat-md-thead">{children}</thead>,
  tbody: ({ children }) => <tbody className="chat-md-tbody">{children}</tbody>,
  tr: ({ children }) => <tr className="chat-md-tr">{children}</tr>,
  th: ({ children }) => <th className="chat-md-th">{children}</th>,
  td: ({ children }) => <td className="chat-md-td">{children}</td>,
};

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  return (
    <div className={`markdown-content ${className}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
}
