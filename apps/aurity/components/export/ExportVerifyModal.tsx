/**
 * ExportVerifyModal - Export session data and verify integrity
 *
 * Card: FI-UI-FEAT-203
 *
 * Features:
 * - Export session as MD/JSON
 * - Verify SHA-256 hash integrity
 * - Progress bar for long exports
 * - Accessible modal (Esc close, focus trap)
 */

'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import {
  X,
  Download,
  Shield,
  FileText,
  FileJson,
  CheckCircle,
  XCircle,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  createExport,
  verifyExport,
  pollExport,
  type ExportResponse,
  type VerifyResponse,
} from '@aurity-standalone/api-client/exports';

interface ExportVerifyModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  sessionTitle?: string;
}

type TabType = 'export' | 'verify';

interface ExportState {
  isLoading: boolean;
  progress: number;
  error: string | null;
  result: ExportResponse | null;
}

interface VerifyState {
  isLoading: boolean;
  error: string | null;
  result: VerifyResponse | null;
  expanded: boolean;
}

export function ExportVerifyModal({
  isOpen,
  onClose,
  sessionId,
  sessionTitle = 'Session',
}: ExportVerifyModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<TabType>('export');
  const [selectedFormats, setSelectedFormats] = useState<Set<'md' | 'json'>>(
    () => new Set<'md' | 'json'>(['md'])
  );

  const [exportState, setExportState] = useState<ExportState>({
    isLoading: false,
    progress: 0,
    error: null,
    result: null,
  });

  const [verifyState, setVerifyState] = useState<VerifyState>({
    isLoading: false,
    error: null,
    result: null,
    expanded: false,
  });

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  // Focus trap
  useEffect(() => {
    if (isOpen && modalRef.current) {
      const focusableElements = modalRef.current.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      );
      const firstElement = focusableElements[0] as HTMLElement;
      firstElement?.focus();
    }
  }, [isOpen]);

  // Toggle format selection
  const toggleFormat = (format: 'md' | 'json') => {
    const newFormats = new Set<'md' | 'json'>(selectedFormats);
    if (newFormats.has(format)) {
      newFormats.delete(format);
    } else {
      newFormats.add(format);
    }
    // Ensure at least one format is selected
    if (newFormats.size > 0) {
      setSelectedFormats(newFormats);
    }
  };

  // Handle export
  const handleExport = useCallback(async () => {
    if (selectedFormats.size === 0) return;

    setExportState({
      isLoading: true,
      progress: 10,
      error: null,
      result: null,
    });

    try {
      // Create export
      const exportResponse = await createExport({
        sessionId,
        formats: Array.from(selectedFormats),
        include: { transcript: true, events: true, attachments: false },
      });

      setExportState((prev) => ({ ...prev, progress: 50 }));

      // Poll until ready
      const finalExport = await pollExport(exportResponse.exportId);

      setExportState({
        isLoading: false,
        progress: 100,
        error: null,
        result: finalExport,
      });

      // Auto-download artifacts
      finalExport.artifacts.forEach((artifact) => {
        if (artifact.format !== 'manifest') {
          const link = document.createElement('a');
          link.href = artifact.url;
          link.download = `${sessionId}.${artifact.format}`;
          document.body.appendChild(link);
          link.click();
          document.body.removeChild(link);
        }
      });
    } catch (error) {
      setExportState({
        isLoading: false,
        progress: 0,
        error: error instanceof Error ? error.message : 'Export failed',
        result: null,
      });
    }
  }, [sessionId, selectedFormats]);

  // Handle verify
  const handleVerify = useCallback(async () => {
    if (!exportState.result) {
      setVerifyState({
        isLoading: false,
        error: 'No export to verify. Please export first.',
        result: null,
        expanded: false,
      });
      return;
    }

    setVerifyState({
      isLoading: true,
      error: null,
      result: null,
      expanded: false,
    });

    try {
      const result = await verifyExport(exportState.result.exportId);
      setVerifyState({
        isLoading: false,
        error: null,
        result,
        expanded: false,
      });
    } catch (error) {
      setVerifyState({
        isLoading: false,
        error: error instanceof Error ? error.message : 'Verification failed',
        result: null,
        expanded: false,
      });
    }
  }, [exportState.result]);

  if (!isOpen) return null;

  return (
    <div
      className="fi-modal-backdrop"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={modalRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="export-dialog"
      >
        {/* Header */}
        <div className="export-header fi-border-bottom">
          <h2 id="modal-title" className="fi-title">
            Export & Verify Session
          </h2>
          <Button
            onClick={onClose}
            variant="ghost"
            size="sm"
            icon={X}
            aria-label="Close modal"
          />
        </div>

        {/* Tabs */}
        <div className="flex fi-border-bottom">
          <Button
            onClick={() => setActiveTab('export')}
            className={`fi-tab fi-tab-full fi-tab-centered ${
              activeTab === 'export' ? 'fi-tab-active-emerald border-b-2' : 'fi-tab-inactive'
            }`}
            variant="ghost"
            size="sm"
            type="button"
            title="Export tab"
          >
            <Download className="fi-icon-sm" />
            Export
          </Button>
          <Button
            onClick={() => setActiveTab('verify')}
            className={`fi-tab fi-tab-full fi-tab-centered ${
              activeTab === 'verify' ? 'fi-tab-active-emerald border-b-2' : 'fi-tab-inactive'
            }`}
            variant="ghost"
            size="sm"
            type="button"
            title="Verify tab"
          >
            <Shield className="fi-icon-sm" />
            Verify
          </Button>
        </div>

        {/* Content */}
        <div className="p-6">
          {activeTab === 'export' && (
            <div className="fi-stack-lg">
              <div>
                <p className="fi-subtitle mb-3">
                  Export &quot;{sessionTitle}&quot; as:
                </p>

                {/* Format selection */}
                <div className="flex gap-3">
                  <Button
                    onClick={() => toggleFormat('md')}
                    className={selectedFormats.has('md')
                      ? 'export-format-btn-selected'
                      : 'export-format-btn-default'}
                    variant="ghost"
                    size="sm"
                    type="button"
                    title="Markdown"
                  >
                    <FileText className="h-5 w-5" />
                    <span>Markdown</span>
                  </Button>
                  <Button
                    onClick={() => toggleFormat('json')}
                    className={selectedFormats.has('json')
                      ? 'export-format-btn-selected'
                      : 'export-format-btn-default'}
                    variant="ghost"
                    size="sm"
                    type="button"
                    title="JSON"
                  >
                    <FileJson className="h-5 w-5" />
                    <span>JSON</span>
                  </Button>
                </div>
              </div>

              {/* Progress bar */}
              {exportState.isLoading && (
                <div className="fi-stack-sm">
                  <div className="export-progress-track">
                    <div
                      className="export-progress-fill"
                      style={{ width: `${exportState.progress}%` }}
                    />
                  </div>
                  <p className="fi-text-xs text-center">
                    Preparing export...
                  </p>
                </div>
              )}

              {/* Error */}
              {exportState.error && (
                <div className="export-alert-error">
                  <XCircle className="export-alert-icon fi-text-error" />
                  <p className="text-sm text-red-300">{exportState.error}</p>
                </div>
              )}

              {/* Success */}
              {exportState.result && !exportState.isLoading && (
                <div className="export-alert-success">
                  <CheckCircle className="export-alert-icon fi-text-success" />
                  <p className="text-sm text-emerald-300">
                    Export complete! {exportState.result.artifacts.length} files
                    downloaded.
                  </p>
                </div>
              )}

              {/* Export button */}
              <Button
                onClick={handleExport}
                disabled={exportState.isLoading || selectedFormats.size === 0}
                variant="primary"
                fullWidth
                icon={Download}
                loading={exportState.isLoading}
              >
                {exportState.isLoading ? 'Exporting...' : 'Export Session'}
              </Button>
            </div>
          )}

          {activeTab === 'verify' && (
            <div className="space-y-4">
              <p className="fi-subtitle">
                Verify the integrity of exported session data by checking
                SHA-256 hashes.
              </p>

              {/* Verify result */}
              {verifyState.result && (
                <div
                  className={verifyState.result.ok
                    ? 'export-verify-result-ok'
                    : 'export-verify-result-fail'}
                >
                  <div className="fi-flex-between">
                    <div className="fi-flex-gap">
                      {verifyState.result.ok ? (
                        <>
                          <CheckCircle className="export-result-icon fi-text-success" />
                          <span className="text-emerald-300 font-medium">
                            Verification Passed
                          </span>
                        </>
                      ) : (
                        <>
                          <XCircle className="export-result-icon fi-text-error" />
                          <span className="text-red-300 font-medium">
                            Verification Failed
                          </span>
                        </>
                      )}
                    </div>
                    <Button
                      onClick={() =>
                        setVerifyState((prev) => ({
                          ...prev,
                          expanded: !prev.expanded,
                        }))
                      }
                      variant="ghost"
                      size="sm"
                      icon={verifyState.expanded ? ChevronUp : ChevronDown}
                      aria-label={verifyState.expanded ? 'Collapse details' : 'Expand details'}
                    />
                  </div>

                  {/* Details */}
                  {verifyState.expanded && (
                    <div className="export-verify-details fi-border-top">
                      {verifyState.result.results.map((r, i) => (
                        <div
                          key={i}
                          className="export-verify-row"
                        >
                          <span className="text-slate-400">{r.target}</span>
                          <span
                            className={r.ok ? 'fi-text-success' : 'fi-text-error'}
                          >
                            {r.ok ? 'OK' : r.message || 'Failed'}
                          </span>
                        </div>
                      ))}
                      <div className="pt-2 fi-text-xs-muted">
                        Verified at {new Date().toLocaleString()}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Error */}
              {verifyState.error && (
                <div className="export-alert-error">
                  <XCircle className="export-alert-icon fi-text-error" />
                  <p className="text-sm text-red-300">{verifyState.error}</p>
                </div>
              )}

              {/* Verify button */}
              <Button
                onClick={handleVerify}
                disabled={verifyState.isLoading}
                variant="secondary"
                fullWidth
                icon={Shield}
                loading={verifyState.isLoading}
              >
                {verifyState.isLoading ? 'Verifying...' : 'Verify Integrity'}
              </Button>

              {!exportState.result && (
                <p className="fi-text-xs-muted text-center">
                  Export a session first to verify its integrity.
                </p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="export-footer fi-border-top">
          <p className="fi-text-xs-muted text-center">
            Session ID: {sessionId}
          </p>
        </div>
      </div>
    </div>
  );
}

export default ExportVerifyModal;
