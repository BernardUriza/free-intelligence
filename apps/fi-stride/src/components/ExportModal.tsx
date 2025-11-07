/**
 * Free Intelligence - Export & Verify Modal
 *
 * Modal for exporting sessions with manifest and verification.
 *
 * File: apps/aurity/ui/components/ExportModal.tsx
 * Card: FI-UI-FEAT-203
 * Created: 2025-10-30
 *
 * Features:
 * - Format selection (MD, JSON, or both)
 * - Include options (transcript, events, attachments)
 * - Estimated size hint
 * - Processing state with spinner
 * - Downloadable links when ready
 * - Hash verification with badges
 * - Copy manifest to clipboard
 * - Accessibility: focus trap, Esc to close, aria-live
 */

'use client';

import { useEffect, useRef, useState } from 'react';
import {
  createExport,
  verifyExport,
  pollExport,
  type ExportRequest,
  type ExportResponse,
  type VerifyResponse,
  type ExportArtifact,
} from '@/lib/api/exports';

// ============================================================================
// TYPES
// ============================================================================

type ExportState = 'idle' | 'processing' | 'ready' | 'error';
type VerifyState = 'idle' | 'verifying' | 'verified' | 'failed';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  sessionId: string;
  sessionPreview?: string;
}

// ============================================================================
// COMPONENT
// ============================================================================

export default function ExportModal({
  isOpen,
  onClose,
  sessionId,
  sessionPreview = 'Session',
}: ExportModalProps) {
  // Form state
  const [formats, setFormats] = useState<('md' | 'json')[]>(['md', 'json']);
  const [includeTranscript, setIncludeTranscript] = useState(true);
  const [includeEvents, setIncludeEvents] = useState(true);
  const [includeAttachments, setIncludeAttachments] = useState(false);

  // Export state
  const [exportState, setExportState] = useState<ExportState>('idle');
  const [exportData, setExportData] = useState<ExportResponse | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);

  // Verify state
  const [verifyState, setVerifyState] = useState<VerifyState>('idle');
  const [verifyData, setVerifyData] = useState<VerifyResponse | null>(null);

  // Refs
  const modalRef = useRef<HTMLDivElement>(null);
  const firstFocusableRef = useRef<HTMLButtonElement>(null);

  // ============================================================================
  // EFFECTS
  // ============================================================================

  // Focus trap
  useEffect(() => {
    if (isOpen && firstFocusableRef.current) {
      firstFocusableRef.current.focus();
    }
  }, [isOpen]);

  // Esc key to close
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [isOpen, onClose]);

  // Reset state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setExportState('idle');
      setExportData(null);
      setExportError(null);
      setVerifyState('idle');
      setVerifyData(null);
    }
  }, [isOpen]);

  // ============================================================================
  // HANDLERS
  // ============================================================================

  const handleExport = async () => {
    if (formats.length === 0) {
      setExportError('Please select at least one format');
      return;
    }

    setExportState('processing');
    setExportError(null);

    try {
      const request: ExportRequest = {
        sessionId,
        formats,
        include: {
          transcript: includeTranscript,
          events: includeEvents,
          attachments: includeAttachments,
        },
      };

      // Create export
      const result = await createExport(request);

      // If processing, poll until ready
      if (result.status === 'processing') {
        const finalResult = await pollExport(result.exportId);
        setExportData(finalResult);
      } else {
        setExportData(result);
      }

      setExportState('ready');
    } catch (error) {
      console.error('Export error:', error);
      setExportError(error instanceof Error ? error.message : 'Export failed');
      setExportState('error');
    }
  };

  const handleVerify = async () => {
    if (!exportData) return;

    setVerifyState('verifying');

    try {
      const result = await verifyExport(exportData.exportId);
      setVerifyData(result);
      setVerifyState(result.ok ? 'verified' : 'failed');
    } catch (error) {
      console.error('Verify error:', error);
      setVerifyState('failed');
    }
  };

  const handleCopyManifest = async () => {
    if (!exportData) return;

    try {
      const response = await fetch(exportData.manifestUrl);
      const manifest = await response.text();
      await navigator.clipboard.writeText(manifest);
      alert('Manifest copied to clipboard!');
    } catch (error) {
      console.error('Copy error:', error);
      alert('Failed to copy manifest');
    }
  };

  const handleDownload = (url: string, filename: string) => {
    // Open in new tab for download
    window.open(url, '_blank');
  };

  const formatBytes = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const estimatedSize =
    (includeTranscript ? 2000 : 0) +
    (includeEvents ? 1000 : 0) +
    (includeAttachments ? 5000 : 0);

  // ============================================================================
  // RENDER
  // ============================================================================

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-modal-title"
    >
      <div
        ref={modalRef}
        className="bg-slate-900 border border-slate-700 rounded-lg shadow-2xl w-full max-w-2xl mx-4 overflow-hidden"
      >
        {/* Header */}
        <div className="bg-slate-800 px-6 py-4 border-b border-slate-700 flex items-center justify-between">
          <h2 id="export-modal-title" className="text-xl font-semibold text-slate-100">
            Export Session
          </h2>
          <button
            ref={firstFocusableRef}
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 transition-colors"
            aria-label="Close modal"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-6 space-y-6">
          {/* Session Info */}
          <div className="bg-slate-800/50 border border-slate-700 rounded px-4 py-3">
            <p className="text-sm text-slate-400">Session</p>
            <p className="text-slate-100 font-mono text-sm mt-1">{sessionPreview}</p>
          </div>

          {/* State: Idle/Form */}
          {exportState === 'idle' && (
            <>
              {/* Format Selection */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Export Formats
                </label>
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formats.includes('md')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormats([...formats, 'md']);
                        } else {
                          setFormats(formats.filter((f) => f !== 'md'));
                        }
                      }}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500"
                    />
                    <span className="text-slate-300">Markdown (.md)</span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formats.includes('json')}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormats([...formats, 'json']);
                        } else {
                          setFormats(formats.filter((f) => f !== 'json'));
                        }
                      }}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500"
                    />
                    <span className="text-slate-300">JSON (.json)</span>
                  </label>
                </div>
              </div>

              {/* Include Options */}
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Include
                </label>
                <div className="space-y-2">
                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeTranscript}
                      onChange={(e) => setIncludeTranscript(e.target.checked)}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500"
                    />
                    <span className="text-slate-300">Transcript</span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeEvents}
                      onChange={(e) => setIncludeEvents(e.target.checked)}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500"
                    />
                    <span className="text-slate-300">Events</span>
                  </label>

                  <label className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={includeAttachments}
                      onChange={(e) => setIncludeAttachments(e.target.checked)}
                      className="w-4 h-4 rounded border-slate-600 bg-slate-800 text-blue-500"
                    />
                    <span className="text-slate-300">Attachments</span>
                  </label>
                </div>
              </div>

              {/* Size Estimate */}
              <div className="bg-blue-900/20 border border-blue-700/50 rounded px-4 py-3">
                <p className="text-sm text-blue-300">
                  Estimated size: ~{formatBytes(estimatedSize)}
                </p>
              </div>
            </>
          )}

          {/* State: Processing */}
          {exportState === 'processing' && (
            <div
              className="flex flex-col items-center justify-center py-12"
              role="status"
              aria-live="polite"
            >
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-slate-600 border-t-blue-500 mb-4"></div>
              <p className="text-slate-300">Preparing artefacts...</p>
            </div>
          )}

          {/* State: Ready */}
          {exportState === 'ready' && exportData && (
            <div className="space-y-4" role="region" aria-live="polite">
              <div className="bg-green-900/20 border border-green-700/50 rounded px-4 py-3">
                <p className="text-green-300 font-medium">✓ Export ready!</p>
              </div>

              {/* Download Links */}
              <div className="space-y-2">
                <p className="text-sm font-medium text-slate-300">Downloads</p>
                {exportData.artifacts
                  .filter((a) => a.format !== 'manifest')
                  .map((artifact) => (
                    <div
                      key={artifact.format}
                      className="flex items-center justify-between bg-slate-800 border border-slate-700 rounded px-4 py-3"
                    >
                      <div>
                        <p className="text-slate-100 font-medium">
                          session.{artifact.format}
                        </p>
                        <p className="text-xs text-slate-400">
                          {formatBytes(artifact.bytes)} · {artifact.sha256.slice(0, 12)}...
                        </p>
                      </div>
                      <button
                        onClick={() =>
                          handleDownload(artifact.url, `session.${artifact.format}`)
                        }
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                      >
                        Download
                      </button>
                    </div>
                  ))}

                {/* Manifest */}
                <div className="flex items-center justify-between bg-slate-800 border border-slate-700 rounded px-4 py-3">
                  <div>
                    <p className="text-slate-100 font-medium">manifest.json</p>
                    <p className="text-xs text-slate-400">Integrity manifest</p>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={handleCopyManifest}
                      className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
                    >
                      Copy
                    </button>
                    <button
                      onClick={() =>
                        handleDownload(exportData.manifestUrl, 'manifest.json')
                      }
                      className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
                    >
                      Download
                    </button>
                  </div>
                </div>
              </div>

              {/* Verify Section */}
              <div className="border-t border-slate-700 pt-4">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-sm font-medium text-slate-300">Verification</p>
                  {verifyState === 'idle' && (
                    <button
                      onClick={handleVerify}
                      className="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded transition-colors"
                    >
                      Verify Integrity
                    </button>
                  )}
                </div>

                {verifyState === 'verifying' && (
                  <div className="flex items-center space-x-2 text-slate-400">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-slate-600 border-t-green-500"></div>
                    <span className="text-sm">Verifying...</span>
                  </div>
                )}

                {(verifyState === 'verified' || verifyState === 'failed') && verifyData && (
                  <div className="space-y-2">
                    {verifyData.results.map((result) => (
                      <div
                        key={result.target}
                        className={`flex items-center space-x-2 px-3 py-2 rounded ${
                          result.ok
                            ? 'bg-green-900/20 border border-green-700/50'
                            : 'bg-red-900/20 border border-red-700/50'
                        }`}
                      >
                        <span
                          className={`font-bold ${
                            result.ok ? 'text-green-400' : 'text-red-400'
                          }`}
                        >
                          {result.ok ? '✓' : '✗'}
                        </span>
                        <span
                          className={result.ok ? 'text-green-300' : 'text-red-300'}
                        >
                          {result.target}
                        </span>
                        {result.message && (
                          <span className="text-xs text-slate-400">
                            ({result.message})
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* State: Error */}
          {exportState === 'error' && (
            <div className="space-y-4">
              <div
                className="bg-red-900/20 border border-red-700/50 rounded px-4 py-3"
                role="alert"
              >
                <p className="text-red-300 font-medium">Export failed</p>
                <p className="text-sm text-red-400 mt-1">{exportError}</p>
              </div>
              <button
                onClick={() => {
                  setExportState('idle');
                  setExportError(null);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors"
              >
                Try Again
              </button>
            </div>
          )}
        </div>

        {/* Footer */}
        {exportState === 'idle' && (
          <div className="bg-slate-800 px-6 py-4 border-t border-slate-700 flex justify-end space-x-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleExport}
              disabled={formats.length === 0}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Export
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
