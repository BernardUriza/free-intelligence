/**
 * Demo Dataset Banner
 *
 * Displays demo mode status with manifest info and config button.
 *
 * File: components/demo-banner.tsx
 * Card: FI-UI-FEAT-207
 * Created: 2025-10-30
 *
 * Philosophy AURITY:
 * - Control visible: seed, perfil, error% mostrados
 * - Trazabilidad: manifest copiable
 */

'use client';

import { useState } from 'react';
import {
  BeakerIcon,
  ClipboardDocumentIcon,
  Cog6ToothIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { Button } from '@/components/ui/button';
import { DemoConfig, DemoManifest } from '@/lib/demo/types';
import { DemoConfigModal } from './demo-config-modal';

interface DemoBannerProps {
  config: DemoConfig;
  manifest: DemoManifest | null;
  onConfigUpdate: (config: DemoConfig) => void;
}

export function DemoBanner({
  config,
  manifest,
  onConfigUpdate,
}: DemoBannerProps) {
  const [showModal, setShowModal] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [copied, setCopied] = useState(false);

  if (dismissed) return null;

  const handleCopyManifest = () => {
    if (!manifest) return;

    const manifestText = JSON.stringify(manifest, null, 2);
    navigator.clipboard.writeText(manifestText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <>
      <div className="bg-amber-900/20 border-b border-amber-800/50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-2">
          <div className="fi-flex-between">
            <div className="flex items-center space-x-3">
              <BeakerIcon className="h-5 w-5 fi-text-warning" />
              <span className="text-sm font-medium text-amber-200">
                Demo Mode
              </span>
              <div className="flex items-center space-x-2 text-xs text-amber-300/70">
                <span className="px-2 py-0.5 bg-amber-800/30 rounded">
                  Seed: {config.seed}
                </span>
                <span className="px-2 py-0.5 bg-amber-800/30 rounded">
                  {config.sessions} sessions
                </span>
                <span className="px-2 py-0.5 bg-amber-800/30 rounded">
                  Profile: {config.eventsProfile}
                </span>
                {config.errorRatePct > 0 && (
                  <span className="px-2 py-0.5 bg-red-800/30 rounded text-red-300">
                    Error: {config.errorRatePct}%
                  </span>
                )}
                {manifest && (
                  <span className="px-2 py-0.5 bg-amber-800/30 rounded font-mono">
                    #{manifest.ids_digest}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-2">
              {manifest && (
                <Button
                  onClick={handleCopyManifest}
                  variant="ghost"
                  size="sm"
                  className={`p-1 hover:bg-amber-800/30 ${copied ? 'fi-text-green' : 'text-amber-300'}`}
                  aria-label="Copy manifest"
                >
                  <ClipboardDocumentIcon className="h-5 w-5" />
                </Button>
              )}
              <Button
                onClick={() => setShowModal(true)}
                variant="ghost"
                size="sm"
                className="p-1 hover:bg-amber-800/30 text-amber-300"
                aria-label="Configure demo"
              >
                <Cog6ToothIcon className="h-5 w-5" />
              </Button>
              <Button
                onClick={() => setDismissed(true)}
                variant="ghost"
                size="sm"
                className="p-1 hover:bg-amber-800/30 text-amber-300"
                aria-label="Dismiss"
              >
                <XMarkIcon className="h-5 w-5" />
              </Button>
            </div>
          </div>

          {copied && (
            <div className="text-xs fi-text-green mt-1">
              Manifest copied to clipboard
            </div>
          )}
        </div>
      </div>

      <DemoConfigModal
        isOpen={showModal}
        onClose={() => setShowModal(false)}
        currentConfig={config}
        onApply={onConfigUpdate}
      />
    </>
  );
}
