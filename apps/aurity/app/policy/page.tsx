"use client";

/**
 * Policy Snapshot Page
 * Card: FI-UI-FEAT-204
 *
 * Displays effective policy configuration from fi.policy.yaml
 * Read-only view with global banner integration
 */

import { useEffect, useState } from "react";
import { GenericPolicyViewer } from '@/components/policy/GenericPolicyViewer';
import { AppTemplate } from '@/components/layout/AppTemplate';
import { policyHeader } from '@/config/page-headers';

interface PolicyResponse {
  policy: any;
  metadata?: {
    source?: string;
    version?: string;
    timestamp?: string;
  };
}

export default function PolicyPage() {
  const [data, setData] = useState<PolicyResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Fetch policy via Next.js API route (avoids CORS issues)
    fetch('/api/policy')
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        return res.json();
      })
      .then((responseData: PolicyResponse) => {
        setData(responseData);
        setLoading(false);
      })
      .catch(err => {
        console.error('Failed to load policy:', err);
        setError(err.message || 'Unknown error');
        setLoading(false);
      });
  }, []);

  // Generate header config with metadata
  const headerConfig = policyHeader(
    data?.metadata
      ? {
          version: data.metadata.version,
          timestamp: data.metadata.timestamp,
          source: data.metadata.source,
        }
      : undefined
  );

  return (
    <AppTemplate headerConfig={headerConfig} maxWidth="full" padding="8" showWatermark={true} showGeometricBg={true}>
      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin h-8 w-8 border-4 border-purple-400 border-t-transparent rounded-full"></div>
          <span className="ml-3 text-slate-400">Loading policy...</span>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-6">
          <h2 className="text-xl font-bold fi-text-error mb-2">Failed to Load Policy</h2>
          <p className="fi-text">{error}</p>
          <p className="fi-subtitle mt-4">
            Make sure <code className="fi-text-error">config/fi.policy.yaml</code> exists and the backend is running.
          </p>
        </div>
      )}

      {/* Policy Viewer */}
      {!loading && !error && data && (
        <GenericPolicyViewer policy={data.policy} metadata={data.metadata} />
      )}
    </AppTemplate>
  );
}
