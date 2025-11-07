/**
 * Offline Queue Manager - Queue and retry requests when offline
 * Stores failed requests in IndexedDB and retries them when connection is restored
 */

export interface QueuedRequest {
  id: string
  endpoint: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  headers?: Record<string, string>
  body?: unknown
  timestamp: number
  retries: number
  maxRetries: number
  nextRetryTime: number
}

const DB_NAME = 'FIStride'
const DB_VERSION = 1
const QUEUE_STORE = 'offlineQueue'

export class OfflineQueueManager {
  private db: IDBDatabase | null = null
  private syncInProgress = false
  private retryIntervals = [1000, 2000, 5000, 10000, 30000] // milliseconds

  async init(): Promise<void> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DB_NAME, DB_VERSION)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => {
        this.db = request.result
        resolve()
      }

      request.onupgradeneeded = (event) => {
        const db = (event.target as IDBOpenDBRequest).result

        if (!db.objectStoreNames.contains(QUEUE_STORE)) {
          const store = db.createObjectStore(QUEUE_STORE, { keyPath: 'id' })
          store.createIndex('nextRetryTime', 'nextRetryTime', { unique: false })
          store.createIndex('timestamp', 'timestamp', { unique: false })
        }
      }
    })
  }

  /**
   * Generate unique request ID
   */
  private generateId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Add request to offline queue
   */
  async addToQueue(
    endpoint: string,
    method: 'GET' | 'POST' | 'PUT' | 'DELETE',
    body?: unknown,
    headers?: Record<string, string>,
    maxRetries: number = 5
  ): Promise<string> {
    if (!this.db) throw new Error('Database not initialized')

    const id = this.generateId()
    const queuedRequest: QueuedRequest = {
      id,
      endpoint,
      method,
      headers,
      body,
      timestamp: Date.now(),
      retries: 0,
      maxRetries,
      nextRetryTime: Date.now() // Retry immediately first
    }

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([QUEUE_STORE], 'readwrite')
      const store = transaction.objectStore(QUEUE_STORE)
      const request = store.add(queuedRequest)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve(id)
    })
  }

  /**
   * Remove request from queue after successful retry
   */
  async removeFromQueue(id: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([QUEUE_STORE], 'readwrite')
      const store = transaction.objectStore(QUEUE_STORE)
      const request = store.delete(id)

      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve()
    })
  }

  /**
   * Get all queued requests
   */
  async getQueuedRequests(): Promise<QueuedRequest[]> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve) => {
      try {
        const transaction = this.db!.transaction([QUEUE_STORE], 'readonly')
        const store = transaction.objectStore(QUEUE_STORE)
        const request = store.getAll()

        request.onerror = () => resolve([])
        request.onsuccess = () => resolve(request.result || [])
      } catch {
        // Store doesn't exist yet, return empty array
        resolve([])
      }
    })
  }

  /**
   * Get requests ready to retry (nextRetryTime <= now)
   */
  async getReadyToRetry(): Promise<QueuedRequest[]> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve) => {
      try {
        const transaction = this.db!.transaction([QUEUE_STORE], 'readonly')
        const store = transaction.objectStore(QUEUE_STORE)
        const index = store.index('nextRetryTime')
        const range = IDBKeyRange.upperBound(Date.now())
        const request = index.getAll(range)

        request.onerror = () => resolve([])
        request.onsuccess = () => resolve(request.result || [])
      } catch {
        // Index or store doesn't exist yet, return empty array
        resolve([])
      }
    })
  }

  /**
   * Update retry count and schedule next retry
   */
  async updateRetryCount(id: string): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([QUEUE_STORE], 'readwrite')
      const store = transaction.objectStore(QUEUE_STORE)
      const getRequest = store.get(id)

      getRequest.onerror = () => reject(getRequest.error)
      getRequest.onsuccess = () => {
        const queuedRequest = getRequest.result as QueuedRequest

        if (queuedRequest) {
          queuedRequest.retries += 1

          // Calculate next retry time with exponential backoff
          const backoffIndex = Math.min(
            queuedRequest.retries - 1,
            this.retryIntervals.length - 1
          )
          const backoffDelay = this.retryIntervals[backoffIndex]
          queuedRequest.nextRetryTime = Date.now() + backoffDelay

          const updateRequest = store.put(queuedRequest)
          updateRequest.onerror = () => reject(updateRequest.error)
          updateRequest.onsuccess = () => resolve()
        } else {
          reject(new Error('Request not found'))
        }
      }
    })
  }

  /**
   * Clear entire queue (usually after successful sync or manual reset)
   */
  async clearQueue(): Promise<void> {
    if (!this.db) throw new Error('Database not initialized')

    return new Promise((resolve, reject) => {
      const transaction = this.db!.transaction([QUEUE_STORE], 'readwrite')
      const store = transaction.objectStore(QUEUE_STORE)
      const request = store.clear()

      request.onerror = () => reject(request.error)
      request.onsuccess = () => resolve()
    })
  }

  /**
   * Get queue statistics
   */
  async getQueueStats(): Promise<{
    totalQueued: number
    readyToRetry: number
    oldestRequest: number // timestamp in ms
  }> {
    const all = await this.getQueuedRequests()
    const ready = await this.getReadyToRetry()

    return {
      totalQueued: all.length,
      readyToRetry: ready.length,
      oldestRequest: all.length > 0 ? Math.min(...all.map((r) => r.timestamp)) : 0
    }
  }

  /**
   * Check if sync is currently in progress
   */
  isSyncInProgress(): boolean {
    return this.syncInProgress
  }

  /**
   * Set sync in progress flag
   */
  setSyncInProgress(inProgress: boolean): void {
    this.syncInProgress = inProgress
  }
}

export const offlineQueue = new OfflineQueueManager()
