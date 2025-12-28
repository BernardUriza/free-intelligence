/**
 * CodeBlock Component - Stub
 *
 * Minimal implementation to unblock build.
 */

import React from 'react';

export interface CodeBlockProps {
  code: string;
  language?: string;
  filename?: string;
  className?: string;
  showLineNumbers?: boolean;
}

export function CodeBlock({
  code,
  language = 'bash',
  filename,
  className = '',
}: CodeBlockProps) {
  return (
    <div className={`rounded-lg overflow-hidden ${className}`}>
      {filename && (
        <div className="bg-slate-800 px-4 py-2 fi-text-xs fi-border-bottom">
          {filename}
        </div>
      )}
      <div className="bg-slate-900 p-4">
        <pre className="text-sm fi-text overflow-x-auto">
          <code className={`language-${language}`}>{code}</code>
        </pre>
      </div>
    </div>
  );
}
