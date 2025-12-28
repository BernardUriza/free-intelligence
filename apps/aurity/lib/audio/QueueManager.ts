/**
 * QueueManager - Deduplication and cache for audio requests
 *
 * Features:
 * - Hash-based deduplication: SHA-256 of `text::voice::provider`
 * - Temporal cache: 5-minute TTL for identical requests
 * - LRU eviction: Maximum 50 cached entries
 * - Single-stream concurrency: New requests cancel current playback (limite_concurrencia = 1)
 * - In-memory storage: Map<hash, CachedAudio> (not localStorage for privacy)
 *
 * Append-only principle: Cache keys are immutable SHA-256 hashes.
 * Zero-trust principle: No assumptions about cache persistence.
 *
 * @module QueueManager
 * @see /apps/aurity/docs/audio/IDEMPOTENCY.md
 */

export interface AudioRequest {
  id: string; // UUID
  text: string;
  voice: string;
  provider: 'openai' | 'openai-steerable';
  timestamp: number;
  priority: number; // Higher = more urgent (user messages = 2, assistant = 1)
}

export interface CachedAudio {
  hash: string;
  audioUrl: string; // Blob URL (blob:https://...)
  expiresAt: number;
  voice: string;
  createdAt: number;
}

/**
 * QueueManager class
 *
 * Manages audio request queue, cache, and deduplication.
 */
export class QueueManager {
  private queue: AudioRequest[] = [];
  private cache: Map<string, CachedAudio> = new Map();
  private currentRequest: AudioRequest | null = null;
  private readonly CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
  private readonly MAX_CACHE_SIZE = 50; // LRU eviction at 50 entries

  /**
   * Generate SHA-256 hash for deduplication
   *
   * Hash = SHA256(text::voice::provider)
   *
   * Example:
   * ```typescript
   * text = "Buenos días"
   * voice = "nova"
   * provider = "openai"
   * hash = SHA256("Buenos días::nova::openai")
   * ```
   *
   * @param text - Text to synthesize
   * @param voice - Voice ID
   * @param provider - Provider ID
   * @returns SHA-256 hash (hex string)
   */
  private async hashRequest(
    text: string,
    voice: string,
    provider: string
  ): Promise<string> {
    const data = `${text}::${voice}::${provider}`;
    const encoder = new TextEncoder();
    const buffer = await crypto.subtle.digest('SHA-256', encoder.encode(data));
    const hashArray = Array.from(new Uint8Array(buffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Check cache for existing audio
   *
   * Returns cached audio URL if:
   * - Hash exists in cache
   * - Cache entry has not expired (TTL check)
   *
   * @param text - Text to synthesize
   * @param voice - Voice ID
   * @param provider - Provider ID
   * @returns Cached audio URL or null if not found/expired
   */
  async getCached(
    text: string,
    voice: string,
    provider: string
  ): Promise<string | null> {
    const hash = await this.hashRequest(text, voice, provider);
    const cached = this.cache.get(hash);

    if (!cached) return null;

    // Check expiration
    if (Date.now() > cached.expiresAt) {
      this.cache.delete(hash);
      URL.revokeObjectURL(cached.audioUrl); // Cleanup blob URL
      return null;
    }

    return cached.audioUrl;
  }

  /**
   * Add to cache
   *
   * Performs LRU eviction if cache is full (> MAX_CACHE_SIZE).
   *
   * @param text - Text to synthesize
   * @param voice - Voice ID
   * @param provider - Provider ID
   * @param audioUrl - Blob URL to cache
   */
  async addToCache(
    text: string,
    voice: string,
    provider: string,
    audioUrl: string
  ): Promise<void> {
    const hash = await this.hashRequest(text, voice, provider);

    // LRU eviction if cache full
    if (this.cache.size >= this.MAX_CACHE_SIZE) {
      const oldestKey = Array.from(this.cache.entries())
        .sort((a, b) => a[1].createdAt - b[1].createdAt)[0][0];
      const oldest = this.cache.get(oldestKey);
      if (oldest) URL.revokeObjectURL(oldest.audioUrl); // Cleanup
      this.cache.delete(oldestKey);
    }

    this.cache.set(hash, {
      hash,
      audioUrl,
      expiresAt: Date.now() + this.CACHE_TTL_MS,
      voice,
      createdAt: Date.now(),
    });
  }

  /**
   * Enqueue audio request (with deduplication)
   *
   * Checks cache first. If cache hit, returns audio URL immediately.
   * If cache miss, adds request to queue.
   *
   * Single-stream concurrency: Cancels current request when new request is enqueued.
   *
   * @param request - Audio request (without ID)
   * @returns Request ID (UUID)
   */
  async enqueue(request: Omit<AudioRequest, 'id'>): Promise<string> {
    // Check cache first
    const cachedUrl = await this.getCached(
      request.text,
      request.voice,
      request.provider
    );
    if (cachedUrl) {
      // Cache hit - return immediately (no queue)
      return cachedUrl;
    }

    const id = crypto.randomUUID();
    const fullRequest: AudioRequest = { ...request, id };

    // Single-stream: cancel current if new request
    if (this.currentRequest) {
      this.currentRequest = null; // Signal cancellation
    }

    this.queue.push(fullRequest);
    return id;
  }

  /**
   * Dequeue next request
   *
   * Returns highest priority request from queue.
   * Sorts queue by priority (descending) before dequeuing.
   *
   * @returns Next AudioRequest or null if queue is empty
   */
  dequeue(): AudioRequest | null {
    if (this.queue.length === 0) return null;

    // Sort by priority (descending)
    this.queue.sort((a, b) => b.priority - a.priority);

    const next = this.queue.shift()!;
    this.currentRequest = next;
    return next;
  }

  /**
   * Clear cache (for testing or privacy)
   *
   * Revokes all blob URLs and clears cache.
   */
  clearCache(): void {
    this.cache.forEach(cached => URL.revokeObjectURL(cached.audioUrl));
    this.cache.clear();
  }

  /**
   * Get cache statistics
   *
   * @returns Cache size, max size, and entries with expiration times
   */
  getCacheStats() {
    return {
      size: this.cache.size,
      maxSize: this.MAX_CACHE_SIZE,
      entries: Array.from(this.cache.values()).map(c => ({
        voice: c.voice,
        expiresIn: Math.max(0, c.expiresAt - Date.now()),
      })),
    };
  }
}
