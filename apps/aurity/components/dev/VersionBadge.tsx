'use client';

/**
 * VersionBadge - Floating version indicator for E2E testing
 *
 * Displays current version in corner. Version number comes from /releases.json
 * (source of truth for UI), while environment/build info comes from backend /api/version.
 * Used by CI/CD to verify frontend-backend connectivity.
 *
 * @example
 * // Test with curl:
 * curl -s http://localhost:9000 | grep "data-version"
 */

import { useState, useEffect } from 'react';
import { getBackendUrl } from '@/lib/api/client';
import { ROUTES } from '@/lib/api/routes';
import { getTarget, isDesktop, getBackendPort } from '@/lib/config/deployment';
import { Button } from '@/components/ui/button';

interface VersionData {
  service: string;
  version: string;
  environment: string;
  build_timestamp: string;
  backend_port?: number;
}

export function VersionBadge() {
  const [version, setVersion] = useState<VersionData | null>(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const fetchVersion = async () => {
      try {
        // Fetch release version from releases.json (source of truth for UI version)
        let releaseVersion: string | null = null;
        try {
          const releasesRes = await fetch('/releases.json');
          if (releasesRes.ok) {
            const releasesData = await releasesRes.json();
            releaseVersion = releasesData.releases?.[0]?.version || null;
          }
        } catch {
          console.debug('VersionBadge: Could not fetch releases.json');
        }

        // Fetch backend info (environment, build_timestamp, etc.)
        const backendUrl = getBackendUrl();
        const res = await fetch(`${backendUrl}${ROUTES.version}`, {
          headers: { 'Accept': 'application/json' },
        });
        if (res.ok) {
          const data = await res.json();
          // Get port from deployment config (handles dynamic Tauri port)
          const backendPort = getBackendPort() ?? undefined;
          setVersion({
            ...data,
            // releases.json version takes priority over backend version
            version: releaseVersion || data.version,
            backend_port: backendPort,
          });
        }
      } catch (err) {
        // Silently fail - version badge is non-critical
        console.debug('VersionBadge: Could not fetch version', err);
      }
    };

    fetchVersion();
  }, []);

  // Don't render in production unless explicitly enabled
  const showBadge = process.env.NODE_ENV !== 'production' ||
    process.env.NEXT_PUBLIC_SHOW_VERSION_BADGE === 'true';

  if (!showBadge && !version) return null;

  return (
    <div
      className="fixed bottom-4 left-4 z-50"
      data-testid="version-badge"
      data-version={version?.version || 'loading'}
      data-environment={version?.environment || 'unknown'}
    >
      <Button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 px-3 py-1.5 text-xs font-mono bg-slate-800/90 text-slate-300 rounded-full border border-slate-700 hover:bg-slate-700 transition-colors shadow-lg backdrop-blur-sm"
        title="Click for version details"
        variant="ghost"
        size="sm"
        type="button"
      >
        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span>
          {version ? `v${version.version}` : 'Loading...'}
        </span>
        {isDesktop() && (
          <span className="text-purple-400">DESKTOP</span>
        )}
        {version?.environment === 'development' && !isDesktop() && (
          <span className="text-amber-400">DEV</span>
        )}
      </Button>

      {expanded && version && (
        <div className="absolute bottom-full left-0 mb-2 p-3 bg-slate-800/95 border border-slate-700 rounded-lg shadow-xl backdrop-blur-sm min-w-[280px]">
          <div className="text-xs font-mono text-slate-300 space-y-1">
            <div className="flex justify-between">
              <span className="text-slate-500">Service:</span>
              <span className="text-emerald-400">{version.service}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Version:</span>
              <span className="text-white">{version.version}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Environment:</span>
              <span className={version.environment === 'production' ? 'text-emerald-400' : 'text-amber-400'}>
                {version.environment}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Target:</span>
              <span className={isDesktop() ? 'text-purple-400' : 'text-cyan-400'}>
                {getTarget().toUpperCase()}
              </span>
            </div>
            {version.backend_port && (
              <div className="flex justify-between">
                <span className="text-slate-500">Backend Port:</span>
                <span className="text-orange-400">{version.backend_port}</span>
              </div>
            )}
            <div className="flex justify-between">
              <span className="text-slate-500">Build:</span>
              <span className="text-slate-400 text-[10px]">
                {new Date(version.build_timestamp).toLocaleString()}
              </span>
            </div>
            <div className="pt-2 border-t border-slate-700 mt-2">
              <span className="text-slate-500 text-[10px]">
                E2E: curl /version | jq -r .python_e2e_code | python3
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
