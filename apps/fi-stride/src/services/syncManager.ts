/**
 * Sync Manager - Handle syncing queued requests when online
 * Processes offline queue and retries failed requests
 */

import { offlineQueue, QueuedRequest } from './offlineQueue'
import { apiClient } from './apiClient'

export interface SyncEvent {
  type: 'sync_started' | 'sync_completed' | 'sync_failed' | 'request_success' | 'request_failed'
  requestId?: string
  endpoint?: string
  error?: string
  timestamp: number
}

type SyncEventListener = (event: SyncEvent) => void

export class SyncManager {
  private listeners: Set<SyncEventListener> = new Set()
  private isOnline = navigator.onLine
  private syncCheckInterval: NodeJS.Timeout | null = null

  async init(): Promise<void> {
    // Initialize offline queue
    await offlineQueue.init()

    // Listen to online/offline events
    window.addEventListener('online', () => this.handleOnline())
    window.addEventListener('offline', () => this.handleOffline())

    // Periodically check for requests to retry
    this.startSyncCheck()

    // Initial sync if online
    if (this.isOnline) {
      await this.sync()
    }
  }

  /**
   * Handle coming online
   */
  private async handleOnline(): Promise<void> {
    this.isOnline = true
    this.emit({
      type: 'sync_started',
      timestamp: Date.now()
    })

    // Attempt to sync queued requests
    await this.sync()
  }

  /**
   * Handle going offline
   */
  private handleOffline(): void {
    this.isOnline = false
  }

  /**
   * Start periodic sync check
   */
  private startSyncCheck(): void {
    // Check every 5 seconds for requests ready to retry
    this.syncCheckInterval = setInterval(async () => {
      if (this.isOnline && !offlineQueue.isSyncInProgress()) {
        const stats = await offlineQueue.getQueueStats()

        // If there are requests ready to retry, attempt sync
        if (stats.readyToRetry > 0) {
          await this.sync()
        }
      }
    }, 5000)
  }

  /**
   * Stop sync check
   */
  stopSyncCheck(): void {
    if (this.syncCheckInterval) {
      clearInterval(this.syncCheckInterval)
      this.syncCheckInterval = null
    }
  }

  /**
   * Main sync function - process all queued requests
   */
  async sync(): Promise<{ success: number; failed: number }> {
    if (!this.isOnline || offlineQueue.isSyncInProgress()) {
      return { success: 0, failed: 0 }
    }

    offlineQueue.setSyncInProgress(true)

    try {
      const readyToRetry = await offlineQueue.getReadyToRetry()

      let successCount = 0
      let failureCount = 0

      for (const request of readyToRetry) {
        const success = await this.retryRequest(request)

        if (success) {
          successCount++
          await offlineQueue.removeFromQueue(request.id)

          this.emit({
            type: 'request_success',
            requestId: request.id,
            endpoint: request.endpoint,
            timestamp: Date.now()
          })
        } else {
          failureCount++

          // Check if we've exceeded max retries
          if (request.retries >= request.maxRetries) {
            await offlineQueue.removeFromQueue(request.id)

            this.emit({
              type: 'request_failed',
              requestId: request.id,
              endpoint: request.endpoint,
              error: 'Max retries exceeded',
              timestamp: Date.now()
            })
          } else {
            // Update retry count and schedule next retry
            await offlineQueue.updateRetryCount(request.id)

            this.emit({
              type: 'request_failed',
              requestId: request.id,
              endpoint: request.endpoint,
              error: `Retry ${request.retries + 1}/${request.maxRetries}`,
              timestamp: Date.now()
            })
          }
        }

        // Small delay between retries to avoid overwhelming the server
        await new Promise((resolve) => setTimeout(resolve, 100))
      }

      this.emit({
        type: 'sync_completed',
        timestamp: Date.now()
      })

      return { success: successCount, failed: failureCount }
    } catch (error) {
      this.emit({
        type: 'sync_failed',
        error: error instanceof Error ? error.message : 'Unknown error',
        timestamp: Date.now()
      })

      return { success: 0, failed: 0 }
    } finally {
      offlineQueue.setSyncInProgress(false)
    }
  }

  /**
   * Retry a single request
   */
  private async retryRequest(request: QueuedRequest): Promise<boolean> {
    try {
      const options: any = {
        timeout: 10000
      }

      if (request.headers) {
        options.headers = request.headers
      }

      if (request.body) {
        options.body = request.body
      }

      switch (request.method) {
        case 'GET':
          await apiClient.get(request.endpoint, options)
          return true
        case 'POST':
          await apiClient.post(request.endpoint, request.body, options)
          return true
        case 'PUT':
          await apiClient.put(request.endpoint, request.body, options)
          return true
        case 'DELETE':
          await apiClient.delete(request.endpoint, options)
          return true
        default:
          return false
      }
    } catch (error) {
      console.warn(`Failed to retry request ${request.id}:`, error)
      return false
    }
  }

  /**
   * Subscribe to sync events
   */
  onSync(listener: SyncEventListener): () => void {
    this.listeners.add(listener)

    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener)
    }
  }

  /**
   * Emit sync event to all listeners
   */
  private emit(event: SyncEvent): void {
    this.listeners.forEach((listener) => {
      try {
        listener(event)
      } catch (error) {
        console.error('Error in sync listener:', error)
      }
    })
  }

  /**
   * Get current online status
   */
  isOnlineStatus(): boolean {
    return this.isOnline
  }

  /**
   * Get queue statistics
   */
  async getQueueStats() {
    return offlineQueue.getQueueStats()
  }

  /**
   * Clear queue (for manual reset)
   */
  async clearQueue(): Promise<void> {
    await offlineQueue.clearQueue()
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.stopSyncCheck()
    this.listeners.clear()
    window.removeEventListener('online', () => this.handleOnline())
    window.removeEventListener('offline', () => this.handleOffline())
  }
}

export const syncManager = new SyncManager()
