"use client";

/**
 * Generic Policy Viewer
 *
 * Displays any policy structure dynamically without hardcoded interfaces.
 * Shows the actual YAML content as-is with collapsible sections.
 */

import { useState } from "react";
import { ChevronDown, ChevronRight, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";

interface GenericPolicyViewerProps {
  policy: Record<string, any>;
  metadata?: {
    source?: string;
    version?: string;
    timestamp?: string;
  };
}

export function GenericPolicyViewer({ policy, metadata }: GenericPolicyViewerProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  const toggleSection = (key: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const copySection = (key: string, value: any) => {
    const yaml = JSON.stringify(value, null, 2);
    navigator.clipboard.writeText(yaml);
    setCopiedSection(key);
    setTimeout(() => setCopiedSection(null), 2000);
  };

  const renderValue = (value: any, depth: number = 0): React.ReactNode => {
    if (value === null || value === undefined) {
      return <span className="pol-value-null">null</span>;
    }

    if (typeof value === 'boolean') {
      return <span className={value ? 'fi-text-green' : 'fi-text-error'}>{value.toString()}</span>;
    }

    if (typeof value === 'number') {
      return <span className="fi-text-primary">{value}</span>;
    }

    if (typeof value === 'string') {
      return <span className="pol-value-string">&quot;{value}&quot;</span>;
    }

    if (Array.isArray(value)) {
      if (value.length === 0) {
        return <span className="pol-value-empty-arr">[]</span>;
      }
      return (
        <div className="pol-value-arr-wrap">
          {value.map((item, idx) => (
            <div key={idx} className="pol-value-arr-item">
              <span className="pol-value-arr-dash">-</span>
              {renderValue(item, depth + 1)}
            </div>
          ))}
        </div>
      );
    }

    if (typeof value === 'object') {
      return (
        <div className="pol-value-obj-wrap">
          {Object.entries(value).map(([k, v]) => (
            <div key={k} className="pol-value-obj-entry">
              <span className="fi-text-purple pol-value-obj-key">{k}:</span>
              {renderValue(v, depth + 1)}
            </div>
          ))}
        </div>
      );
    }

    return <span className="pol-value-fallback">{String(value)}</span>;
  };

  const sections = Object.entries(policy).filter(([key]) => key !== 'metadata');

  return (
    <div className="pol-viewer-root">
      {/* Metadata Header */}
      {metadata && (
        <div className="fi-card-compact">
          <div className="fi-grid-3 pol-viewer-meta-grid">
            <div>
              <span className="pol-viewer-meta-label">Version:</span>
              <span className="pol-viewer-meta-value fi-text">{metadata.version}</span>
            </div>
            <div>
              <span className="pol-viewer-meta-label">Updated:</span>
              <span className="pol-viewer-meta-date fi-text">{metadata.timestamp}</span>
            </div>
            <div>
              <span className="pol-viewer-meta-label">Source:</span>
              <span className="pol-viewer-meta-source">{metadata.source?.split('/').pop()}</span>
            </div>
          </div>
        </div>
      )}

      {/* Policy Sections */}
      <div className="fi-stack-md">
        {sections.map(([key, value]) => {
          const isExpanded = expandedSections.has(key);
          const isCopied = copiedSection === key;

          return (
            <div
              key={key}
              className="pol-viewer-panel"
            >
              {/* Section Header */}
              <div
                className="pol-viewer-section-header"
                onClick={() => toggleSection(key)}
              >
                <div className="fi-flex-gap-md">
                  {isExpanded ? (
                    <ChevronDown className="pol-viewer-chevron" />
                  ) : (
                    <ChevronRight className="pol-viewer-chevron" />
                  )}
                  <h3 className="pol-viewer-section-title">
                    {key.replace(/_/g, ' ')}
                  </h3>
                  {typeof value === 'object' && !Array.isArray(value) && (
                    <span className="pol-viewer-field-badge">
                      {Object.keys(value).length} fields
                    </span>
                  )}
                </div>

                <Button
                  onClick={(e) => {
                    e.stopPropagation();
                    copySection(key, value);
                  }}
                  className="pol-viewer-copy-btn"
                  title="Copy section"
                  variant="ghost"
                  size="sm"
                  type="button"
                >
                  {isCopied ? (
                    <Check className="pol-viewer-icon-sm fi-text-green" />
                  ) : (
                    <Copy className="pol-viewer-icon-copy" />
                  )}
                </Button>
              </div>

              {/* Section Content */}
              {isExpanded && (
                <div className="pol-viewer-section-content fi-border-top">
                  <div className="pol-viewer-content-inner">
                    {renderValue(value)}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Policy Metadata Section (if exists) */}
      {policy.metadata && (
        <div className="pol-viewer-meta-section">
          <h4 className="pol-viewer-meta-title">Policy Metadata</h4>
          <div className="pol-viewer-meta-body">
            {renderValue(policy.metadata)}
          </div>
        </div>
      )}
    </div>
  );
}
