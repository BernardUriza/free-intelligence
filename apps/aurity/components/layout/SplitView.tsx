/**
 * Split View Component
 * Card: FI-UI-FEAT-205
 *
 * Displays prompt and response side-by-side (or stacked on mobile)
 */

import ReactMarkdown from "react-markdown";
import { Button } from '@/components/ui/button';
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/cjs/styles/prism";
import type { Interaction } from "../types/interaction";

interface SplitViewProps {
  interaction: Interaction;
  noSpoilers: boolean;
  onCopyPrompt: () => void;
  onCopyResponse: () => void;
}

export function SplitView({
  interaction,
  noSpoilers,
  onCopyPrompt,
  onCopyResponse,
}: SplitViewProps) {
  const renderContent = (text: string, isSpoiler: boolean) => {
    if (noSpoilers && isSpoiler) {
      return <div className="layout-split-empty">Content hidden (No Spoilers mode active)</div>;
    }

    return (
      <div className="prose prose-invert max-w-none">
        <ReactMarkdown
          components={{
            code({ inline, className, children, ...props }: any) {
              const match = /language-(\w+)/.exec(className || "");
              return !inline && match ? (
                <SyntaxHighlighter style={vscDarkPlus} language={match[1]} PreTag="div" {...props}>
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              ) : (
                <code {...props}>{children}</code>
              );
            },
          }}
        >
          {text}
        </ReactMarkdown>
      </div>
    );
  };

  const countTokens = (text: string) => Math.ceil(text.length / 4);

  return (
    <div className="layout-split-grid">
      {/* Left Panel: Prompt */}
      <div className="layout-split-panel">
        <div className="layout-split-header">
          <div>
            <h2 className="layout-split-title">Prompt</h2>
            <p className="layout-split-meta">{noSpoilers ? "Hidden" : `~${countTokens(interaction.prompt)} tokens`}</p>
          </div>
          <Button onClick={onCopyPrompt} className="fi-btn-blue fi-btn-sm" variant="ghost" size="sm" title="Copy prompt">Copy</Button>
        </div>
        <div className="layout-split-content">{renderContent(interaction.prompt, false)}</div>
      </div>

      {/* Right Panel: SOAP Note */}
      <div className="layout-split-panel">
        <div className="layout-split-header">
          <div>
            <h2 className="layout-split-title">SOAP Note</h2>
            <p className="layout-split-meta">
              {noSpoilers ? "Hidden" : interaction.response ? `~${countTokens(interaction.response)} tokens` : "Not generated"}
            </p>
          </div>
          <Button onClick={onCopyResponse} className="fi-btn-purple fi-btn-sm" disabled={!interaction.response} variant="ghost" size="sm" title="Copy response">Copy</Button>
        </div>
        <div className="layout-split-content">
          {interaction.response ? renderContent(interaction.response, true) : (
            <div className="layout-split-empty">
              SOAP note not generated yet. Click &quot;Generate SOAP Note&quot; to create one.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
