/**
 * Metadata Panel Component
 * Card: FI-UI-FEAT-205
 *
 * Displays interaction metadata at the bottom
 */

import type { Interaction } from "../types/interaction";

interface MetadataPanelProps {
  interaction: Interaction;
}

export function MetadataPanel({ interaction }: MetadataPanelProps) {
  const formatDate = (isoString: string) => {
    return new Date(isoString).toLocaleString();
  };

  const formatHash = (hash: string) => {
    // Show first 16 and last 8 characters
    if (hash.length > 24) {
      return `${hash.substring(0, 16)}...${hash.substring(hash.length - 8)}`;
    }
    return hash;
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6">
      <h2 className="text-xl font-semibold text-slate-100 mb-4">Metadata</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Provider & Model */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-2">Provider & Model</h3>
          <div className="space-y-1">
            <div className="fi-flex-gap">
              <span className="fi-text font-medium">{interaction.provider}</span>
              <span className="text-slate-500">/</span>
              <span className="fi-text">{interaction.model}</span>
            </div>
          </div>
        </div>

        {/* Performance */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-2">Performance</h3>
          <div className="space-y-1">
            <div className="fi-text">
              <span className="text-slate-500">Latency:</span>{" "}
              <span className="font-mono">{interaction.latency_ms || "N/A"}</span>
              {interaction.latency_ms && <span className="text-slate-500">ms</span>}
            </div>
            <div className="fi-text">
              <span className="text-slate-500">Tokens:</span>{" "}
              <span className="font-mono">
                {interaction.tokens_in || "?"} in / {interaction.tokens_out || "?"} out
              </span>
            </div>
          </div>
        </div>

        {/* Timestamps */}
        <div>
          <h3 className="text-sm font-medium text-slate-400 mb-2">Timestamps</h3>
          <div className="space-y-1">
            <div className="fi-text text-sm">
              <span className="text-slate-500">Created:</span>{" "}
              <span className="font-mono text-xs">{formatDate(interaction.created_at)}</span>
            </div>
            {interaction.updated_at && (
              <div className="fi-text text-sm">
                <span className="text-slate-500">Updated:</span>{" "}
                <span className="font-mono text-xs">{formatDate(interaction.updated_at)}</span>
              </div>
            )}
          </div>
        </div>

        {/* Hashes */}
        <div className="md:col-span-2">
          <h3 className="text-sm font-medium text-slate-400 mb-2">Integrity Hashes</h3>
          <div className="space-y-2">
            <div>
              <div className="fi-text-xs-muted mb-1">Content Hash</div>
              <div className="font-mono text-xs fi-text bg-slate-900 px-2 py-1 rounded break-all">
                {formatHash(interaction.content_hash)}
              </div>
            </div>
            {interaction.manifest_hash && (
              <div>
                <div className="fi-text-xs-muted mb-1">Manifest Hash</div>
                <div className="font-mono text-xs fi-text bg-slate-900 px-2 py-1 rounded break-all">
                  {formatHash(interaction.manifest_hash)}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Additional Metadata */}
        {interaction.metadata && Object.keys(interaction.metadata).length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-slate-400 mb-2">Additional Info</h3>
            <div className="space-y-1">
              {Object.entries(interaction.metadata).map(([key, value]) => (
                <div key={key} className="fi-text text-sm">
                  <span className="text-slate-500">{key}:</span>{" "}
                  <span className="font-mono text-xs">
                    {typeof value === "object" ? JSON.stringify(value) : String(value)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
