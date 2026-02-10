"use client";

/**
 * Policy Viewer Component
 * Card: FI-UI-FEAT-204
 *
 * Displays effective policy configuration in read-only format
 * Uses accordion sections for organization
 */

import { useState } from "react";
import {
  ShieldCheck,
  Lock,
  CloudUpload,
  FileText,
  Clock,
  EyeOff,
} from "lucide-react";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";

interface PolicyData {
  sovereignty?: {
    egress?: {
      default?: string;
      allowlist?: string[];
    };
  };
  privacy?: {
    phi?: {
      enabled?: boolean;
    };
    redaction?: {
      spoilers?: boolean;
      style_file?: string;
    };
  };
  timeline?: {
    auto?: {
      enabled?: boolean;
    };
    auto_archive_days?: number;
  };
  mutation?: {
    append_only?: boolean;
    event_required?: boolean;
  };
  export?: {
    enabled?: boolean;
    formats?: string[];
    manifest_required?: boolean;
  };
  retention?: {
    audit_logs_days?: number;
    session_min_days?: number;
  };
  security?: {
    lan_only?: boolean;
    auth_required?: boolean;
  };
  llm?: {
    enabled?: boolean;
    providers?: string[];
    audit?: {
      required?: boolean;
    };
  };
  observability?: {
    chaos_drills_enabled?: boolean;
  };
}

interface PolicyViewerProps {
  policy: PolicyData;
  metadata?: {
    source?: string;
    version?: string;
    timestamp?: string;
  };
}

export function PolicyViewer({ policy, metadata }: PolicyViewerProps) {
  // Loading state reserved for async policy refresh feature
  const [, setLoading] = useState(false);
  void setLoading; // Reserved for future use

  return (
    <div className="fi-stack-xl">
      {/* Header */}
      <div className="fi-flex-between">
        <div>
          <h1 className="pol-page-title">
            <ShieldCheck className="pol-header-icon fi-text-primary" />
            <span>Policy Snapshot</span>
          </h1>
          <p className="pol-page-subtitle">
            Effective configuration from <code className="fi-text-primary">{metadata?.source || 'fi.policy.yaml'}</code>
          </p>
        </div>

        {metadata && (
          <div className="fi-subtitle pol-metadata">
            <div>Version: <span className="fi-text">{metadata.version}</span></div>
            <div>Updated: <span className="fi-text">{new Date(metadata.timestamp || '').toLocaleString()}</span></div>
          </div>
        )}
      </div>

      {/* Policy Sections - Accordion */}
      <Accordion type="multiple" className="pol-accordion-list">
        {/* Egress Policy */}
        <AccordionItem value="egress" className="fi-panel">
          <AccordionTrigger className="pol-accordion-trigger">
            <div className="pol-trigger-inner">
              <CloudUpload className="pol-section-icon fi-text-primary" />
              <span className="pol-section-title">Egress Policy</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="pol-accordion-body">
            <div className="fi-grid-2">
              <div>
                <label className="pol-label">Default</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.sovereignty?.egress?.default || 'N/A'}</code>
                </div>
              </div>
              <div>
                <label className="pol-label">Allow</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.sovereignty?.egress?.default === 'allow' ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>

            <div>
              <label className="pol-label">Destinations Allowlist</label>
              <div className="pol-list">
                {policy.sovereignty?.egress?.allowlist?.map((dest, i) => (
                  <div key={i} className="pol-code-item">
                    {dest}
                  </div>
                )) || <div className="pol-empty">No destinations configured</div>}
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* PHI Redaction */}
        <AccordionItem value="phi" className="fi-panel">
          <AccordionTrigger className="pol-accordion-trigger">
            <div className="pol-trigger-inner">
              <EyeOff className="pol-section-icon fi-text-purple" />
              <span className="pol-section-title">PHI Redaction</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="pol-accordion-body">
            <div className="fi-grid-2">
              <div>
                <label className="pol-label">PHI Enabled</label>
                <div className="fi-input-display">
                  <code className={`${policy.privacy?.phi?.enabled ? 'pol-code-warning' : 'fi-text-green'}`}>
                    {policy.privacy?.phi?.enabled ? 'true' : 'false'}
                  </code>
                </div>
              </div>
              <div>
                <label className="pol-label">Spoilers Redaction</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.privacy?.redaction?.spoilers ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>

            {policy.privacy?.redaction?.style_file && (
              <div>
                <label className="pol-label">Style File</label>
                <div className="fi-input-display pol-input-mono">
                  {policy.privacy.redaction.style_file}
                </div>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        {/* Timeline Auto-export */}
        <AccordionItem value="timeline" className="fi-panel">
          <AccordionTrigger className="pol-accordion-trigger">
            <div className="pol-trigger-inner">
              <FileText className="pol-section-icon fi-text-green" />
              <span className="pol-section-title">Timeline Auto-export</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="pol-accordion-body">
            <div className="fi-grid-2">
              <div>
                <label className="pol-label">Auto Enabled</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.timeline?.auto?.enabled ? 'true' : 'false'}</code>
                </div>
              </div>
              <div>
                <label className="pol-label">Auto Archive Days</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.timeline?.auto_archive_days || 'N/A'}</code>
                </div>
              </div>
            </div>

            <div>
              <label className="pol-label">Export Formats</label>
              <div className="pol-list">
                {policy.export?.formats?.map((format, i) => (
                  <div key={i} className="pol-code-item-inline">
                    {format}
                  </div>
                )) || <div className="pol-empty">No formats configured</div>}
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Mutation Rules */}
        <AccordionItem value="mutation" className="fi-panel">
          <AccordionTrigger className="pol-accordion-trigger">
            <div className="pol-trigger-inner">
              <Lock className="pol-section-icon pol-icon-orange" />
              <span className="pol-section-title">Mutation Rules</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="pol-accordion-body">
            <div className="fi-grid-2">
              <div>
                <label className="pol-label">Append Only</label>
                <div className="fi-input-display">
                  <code className={`${policy.mutation?.append_only ? 'fi-text-green' : 'pol-code-warning'}`}>
                    {policy.mutation?.append_only ? 'true' : 'false'}
                  </code>
                </div>
              </div>
              <div>
                <label className="pol-label">Event Required</label>
                <div className="fi-input-display">
                  <code className={`${policy.mutation?.event_required ? 'fi-text-green' : 'pol-code-warning'}`}>
                    {policy.mutation?.event_required ? 'true' : 'false'}
                  </code>
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Security & LLM */}
        <AccordionItem value="security" className="fi-panel">
          <AccordionTrigger className="pol-accordion-trigger">
            <div className="pol-trigger-inner">
              <ShieldCheck className="pol-section-icon fi-text-error" />
              <span className="pol-section-title">Security & LLM</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="pol-accordion-body">
            <div className="fi-grid-3">
              <div>
                <label className="pol-label">LAN Only</label>
                <div className="fi-input-display">
                  <code className={`${policy.security?.lan_only ? 'fi-text-green' : 'pol-code-warning'}`}>
                    {policy.security?.lan_only ? 'true' : 'false'}
                  </code>
                </div>
              </div>
              <div>
                <label className="pol-label">Auth Required</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.security?.auth_required ? 'true' : 'false'}</code>
                </div>
              </div>
              <div>
                <label className="pol-label">LLM Audit</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.llm?.audit?.required ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>

            <div>
              <label className="pol-label">LLM Providers</label>
              <div className="pol-list">
                {policy.llm?.providers && Object.keys(policy.llm.providers).length > 0 ? (
                  Object.keys(policy.llm.providers).map((providerName) => (
                    <div key={providerName} className="pol-code-item-inline">
                      {providerName}
                    </div>
                  ))
                ) : (
                  <div className="pol-empty">No providers configured</div>
                )}
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Retention & Observability */}
        <AccordionItem value="retention" className="fi-panel">
          <AccordionTrigger className="pol-accordion-trigger">
            <div className="pol-trigger-inner">
              <Clock className="pol-section-icon fi-text-info" />
              <span className="pol-section-title">Retention & Observability</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="pol-accordion-body">
            <div className="fi-grid-3">
              <div>
                <label className="pol-label">Audit Logs (days)</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.retention?.audit_logs_days || 'N/A'}</code>
                </div>
              </div>
              <div>
                <label className="pol-label">Session Min (days)</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.retention?.session_min_days || 'N/A'}</code>
                </div>
              </div>
              <div>
                <label className="pol-label">Chaos Drills</label>
                <div className="fi-input-display">
                  <code className="pol-code-value">{policy.observability?.chaos_drills_enabled ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Footer Notice */}
      <div className="fi-panel pol-footer">
        <p className="fi-subtitle">
          <strong className="pol-note-strong">Note:</strong> This view is read-only. To modify policy settings, edit{' '}
          <code className="fi-text-primary">config/fi.policy.yaml</code> and restart the backend service.
        </p>
      </div>
    </div>
  );
}
