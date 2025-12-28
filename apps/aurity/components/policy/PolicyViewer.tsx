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
          <h1 className="text-3xl font-bold text-slate-50 flex items-center space-x-3">
            <ShieldCheck className="h-8 w-8 fi-text-primary" />
            <span>Policy Snapshot</span>
          </h1>
          <p className="text-slate-400 mt-2">
            Effective configuration from <code className="fi-text-primary">{metadata?.source || 'fi.policy.yaml'}</code>
          </p>
        </div>

        {metadata && (
          <div className="fi-subtitle space-y-1">
            <div>Version: <span className="fi-text">{metadata.version}</span></div>
            <div>Updated: <span className="fi-text">{new Date(metadata.timestamp || '').toLocaleString()}</span></div>
          </div>
        )}
      </div>

      {/* Policy Sections - Accordion */}
      <Accordion type="multiple" className="space-y-4">
        {/* Egress Policy */}
        <AccordionItem value="egress" className="fi-panel">
          <AccordionTrigger className="px-6 py-4 hover:bg-slate-700/50">
            <div className="flex items-center space-x-3">
              <CloudUpload className="h-5 w-5 fi-text-primary" />
              <span className="text-lg font-semibold text-slate-50">Egress Policy</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4 space-y-3">
            <div className="fi-grid-2">
              <div>
                <label className="text-sm font-medium text-slate-400">Default</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.sovereignty?.egress?.default || 'N/A'}</code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">Allow</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.sovereignty?.egress?.default === 'allow' ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-400">Destinations Allowlist</label>
              <div className="mt-1 space-y-2">
                {policy.sovereignty?.egress?.allowlist?.map((dest, i) => (
                  <div key={i} className="px-3 py-2 bg-slate-900 rounded border border-slate-700 font-mono text-sm text-slate-200">
                    {dest}
                  </div>
                )) || <div className="text-slate-500 italic">No destinations configured</div>}
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* PHI Redaction */}
        <AccordionItem value="phi" className="fi-panel">
          <AccordionTrigger className="px-6 py-4 hover:bg-slate-700/50">
            <div className="flex items-center space-x-3">
              <EyeOff className="h-5 w-5 fi-text-purple" />
              <span className="text-lg font-semibold text-slate-50">PHI Redaction</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4 space-y-3">
            <div className="fi-grid-2">
              <div>
                <label className="text-sm font-medium text-slate-400">PHI Enabled</label>
                <div className="fi-input-display">
                  <code className={`${policy.privacy?.phi?.enabled ? 'text-yellow-400' : 'fi-text-green'}`}>
                    {policy.privacy?.phi?.enabled ? 'true' : 'false'}
                  </code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">Spoilers Redaction</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.privacy?.redaction?.spoilers ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>

            {policy.privacy?.redaction?.style_file && (
              <div>
                <label className="text-sm font-medium text-slate-400">Style File</label>
                <div className="fi-input-display font-mono text-sm text-slate-200">
                  {policy.privacy.redaction.style_file}
                </div>
              </div>
            )}
          </AccordionContent>
        </AccordionItem>

        {/* Timeline Auto-export */}
        <AccordionItem value="timeline" className="fi-panel">
          <AccordionTrigger className="px-6 py-4 hover:bg-slate-700/50">
            <div className="flex items-center space-x-3">
              <FileText className="h-5 w-5 fi-text-green" />
              <span className="text-lg font-semibold text-slate-50">Timeline Auto-export</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4 space-y-3">
            <div className="fi-grid-2">
              <div>
                <label className="text-sm font-medium text-slate-400">Auto Enabled</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.timeline?.auto?.enabled ? 'true' : 'false'}</code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">Auto Archive Days</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.timeline?.auto_archive_days || 'N/A'}</code>
                </div>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-400">Export Formats</label>
              <div className="mt-1 space-y-2">
                {policy.export?.formats?.map((format, i) => (
                  <div key={i} className="px-3 py-2 bg-slate-900 rounded border border-slate-700 font-mono text-sm text-slate-200 inline-block mr-2">
                    {format}
                  </div>
                )) || <div className="text-slate-500 italic">No formats configured</div>}
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Mutation Rules */}
        <AccordionItem value="mutation" className="fi-panel">
          <AccordionTrigger className="px-6 py-4 hover:bg-slate-700/50">
            <div className="flex items-center space-x-3">
              <Lock className="h-5 w-5 text-orange-400" />
              <span className="text-lg font-semibold text-slate-50">Mutation Rules</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4 space-y-3">
            <div className="fi-grid-2">
              <div>
                <label className="text-sm font-medium text-slate-400">Append Only</label>
                <div className="fi-input-display">
                  <code className={`${policy.mutation?.append_only ? 'fi-text-green' : 'text-yellow-400'}`}>
                    {policy.mutation?.append_only ? 'true' : 'false'}
                  </code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">Event Required</label>
                <div className="fi-input-display">
                  <code className={`${policy.mutation?.event_required ? 'fi-text-green' : 'text-yellow-400'}`}>
                    {policy.mutation?.event_required ? 'true' : 'false'}
                  </code>
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Security & LLM */}
        <AccordionItem value="security" className="fi-panel">
          <AccordionTrigger className="px-6 py-4 hover:bg-slate-700/50">
            <div className="flex items-center space-x-3">
              <ShieldCheck className="h-5 w-5 fi-text-error" />
              <span className="text-lg font-semibold text-slate-50">Security & LLM</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4 space-y-3">
            <div className="fi-grid-3">
              <div>
                <label className="text-sm font-medium text-slate-400">LAN Only</label>
                <div className="fi-input-display">
                  <code className={`${policy.security?.lan_only ? 'fi-text-green' : 'text-yellow-400'}`}>
                    {policy.security?.lan_only ? 'true' : 'false'}
                  </code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">Auth Required</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.security?.auth_required ? 'true' : 'false'}</code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">LLM Audit</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.llm?.audit?.required ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>

            <div>
              <label className="text-sm font-medium text-slate-400">LLM Providers</label>
              <div className="mt-1 space-y-2">
                {policy.llm?.providers && Object.keys(policy.llm.providers).length > 0 ? (
                  Object.keys(policy.llm.providers).map((providerName) => (
                    <div key={providerName} className="px-3 py-2 bg-slate-900 rounded border border-slate-700 font-mono text-sm text-slate-200 inline-block mr-2">
                      {providerName}
                    </div>
                  ))
                ) : (
                  <div className="text-slate-500 italic">No providers configured</div>
                )}
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>

        {/* Retention & Observability */}
        <AccordionItem value="retention" className="fi-panel">
          <AccordionTrigger className="px-6 py-4 hover:bg-slate-700/50">
            <div className="flex items-center space-x-3">
              <Clock className="h-5 w-5 fi-text-info" />
              <span className="text-lg font-semibold text-slate-50">Retention & Observability</span>
            </div>
          </AccordionTrigger>
          <AccordionContent className="px-6 pb-4 space-y-3">
            <div className="fi-grid-3">
              <div>
                <label className="text-sm font-medium text-slate-400">Audit Logs (days)</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.retention?.audit_logs_days || 'N/A'}</code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">Session Min (days)</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.retention?.session_min_days || 'N/A'}</code>
                </div>
              </div>
              <div>
                <label className="text-sm font-medium text-slate-400">Chaos Drills</label>
                <div className="fi-input-display">
                  <code className="text-slate-200">{policy.observability?.chaos_drills_enabled ? 'true' : 'false'}</code>
                </div>
              </div>
            </div>
          </AccordionContent>
        </AccordionItem>
      </Accordion>

      {/* Footer Notice */}
      <div className="fi-panel p-4">
        <p className="fi-subtitle">
          <strong className="text-slate-50">Note:</strong> This view is read-only. To modify policy settings, edit{' '}
          <code className="fi-text-primary">config/fi.policy.yaml</code> and restart the backend service.
        </p>
      </div>
    </div>
  );
}
