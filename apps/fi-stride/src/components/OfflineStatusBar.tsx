/**
 * Offline Status Bar - Shows offline status and sync progress
 * Displays network connectivity, queued requests, and sync status
 */

import { useOfflineSync } from '../hooks/useOfflineSync'

export function OfflineStatusBar() {
  const status = useOfflineSync()

  // Don't show anything if online and no queued requests
  if (status.isOnline && status.queuedCount === 0) {
    return null
  }

  return (
    <div
      className={`fixed bottom-0 left-0 right-0 p-3 text-sm font-medium transition-all duration-300 ${
        status.isOnline
          ? 'bg-green-900 text-green-100 border-t border-green-700'
          : 'bg-red-900 text-red-100 border-t border-red-700'
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Status indicator */}
          <span className="text-lg">
            {status.isOnline ? '🌐' : '📡'}
          </span>

          {/* Status text */}
          <div className="flex flex-col gap-1">
            <div className="font-semibold">
              {status.isOnline ? 'Online' : 'Offline'}
            </div>

            {/* Queue and sync status */}
            {(status.queuedCount > 0 || status.isSyncing) && (
              <div className="text-xs opacity-90">
                {status.isSyncing && (
                  <>
                    ⏳ Syncing...
                    {status.readyToRetry > 0 && ` (${status.readyToRetry} ready)`}
                  </>
                )}

                {!status.isSyncing && status.queuedCount > 0 && (
                  <>
                    📦 {status.queuedCount} pending
                    {status.readyToRetry > 0 && ` • ${status.readyToRetry} ready to retry`}
                  </>
                )}

                {status.lastError && (
                  <div className="text-xs mt-1 opacity-75">
                    ⚠️ Last sync error: {status.lastError}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Status badge */}
        <div className="flex items-center gap-2">
          {status.isSyncing && (
            <span className="inline-block w-2 h-2 bg-current rounded-full animate-pulse" />
          )}

          {!status.isOnline && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-red-800 text-red-100">
              No Connection
            </span>
          )}

          {status.isOnline && status.queuedCount > 0 && !status.isSyncing && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-semibold bg-green-800 text-green-100">
              {status.queuedCount} Queued
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
