/**
 * useOfflineSync Hook - Access offline sync status and queue in React components
 */

import { useEffect, useState } from 'react'
import { syncManager, SyncEvent } from '../services/syncManager'

export interface OfflineSyncStatus {
  isOnline: boolean
  isSyncing: boolean
  queuedCount: number
  readyToRetry: number
  lastSyncTime?: number
  lastError?: string
}

export function useOfflineSync() {
  const [status, setStatus] = useState<OfflineSyncStatus>({
    isOnline: navigator.onLine,
    isSyncing: false,
    queuedCount: 0,
    readyToRetry: 0
  })

  useEffect(() => {
    let isMounted = true

    // Initialize sync manager and set up listeners
    const initializeSync = async () => {
      try {
        await syncManager.init()

        // Subscribe to sync events
        const unsubscribe = syncManager.onSync((event: SyncEvent) => {
          if (!isMounted) return

          setStatus((prev) => {
            const updated = { ...prev }

            switch (event.type) {
              case 'sync_started':
                updated.isSyncing = true
                break

              case 'sync_completed':
              case 'sync_failed':
                updated.isSyncing = false
                updated.lastSyncTime = event.timestamp
                if (event.type === 'sync_failed' && event.error) {
                  updated.lastError = event.error
                }
                // Refresh queue stats
                updateQueueStats()
                break

              default:
                break
            }

            return updated
          })
        })

        // Update online status
        const handleOnline = () => {
          if (isMounted) {
            setStatus((prev) => ({ ...prev, isOnline: true }))
          }
        }

        const handleOffline = () => {
          if (isMounted) {
            setStatus((prev) => ({ ...prev, isOnline: false }))
          }
        }

        window.addEventListener('online', handleOnline)
        window.addEventListener('offline', handleOffline)

        // Initial queue stats
        await updateQueueStats()

        // Cleanup
        return () => {
          unsubscribe()
          window.removeEventListener('online', handleOnline)
          window.removeEventListener('offline', handleOffline)
        }
      } catch (error) {
        console.error('Failed to initialize sync manager:', error)
      }
    }

    const updateQueueStats = async () => {
      try {
        const stats = await syncManager.getQueueStats()
        if (isMounted) {
          setStatus((prev) => ({
            ...prev,
            queuedCount: stats.totalQueued,
            readyToRetry: stats.readyToRetry
          }))
        }
      } catch (error) {
        console.error('Failed to get queue stats:', error)
      }
    }

    const cleanup = initializeSync()

    return () => {
      isMounted = false
      cleanup.then((fn) => fn && fn())
    }
  }, [])

  return status
}
