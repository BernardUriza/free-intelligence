/**
 * ErrorSampler - Probabilistic Sampling for Noise Reduction
 *
 * After deduplication, remaining errors are sampled to further reduce noise.
 * In development: 10% sampling (log 1 per 10 residual errors)
 * In production: 100% sampling (log all errors)
 *
 * Combined with 5s dedupe window, this achieves ~98% noise reduction
 * for repeated errors while maintaining visibility of varied issues.
 *
 * @module lib/audio/ErrorSampler
 */

/**
 * Development environment sampling rate (10%)
 * @default 0.1
 */
const DEV_SAMPLE_RATE = 0.1;

/**
 * Production environment sampling rate (100%)
 * @default 1.0
 */
const PROD_SAMPLE_RATE = 1.0;

/**
 * Probabilistic sampling for error reduction
 */
export class ErrorSampler {
  /**
   * Sample rate for current environment
   * 0.0 = drop all, 0.1 = log 10%, 1.0 = log all
   */
  private sampleRate: number;

  /**
   * Total errors seen (for calculating effective rate)
   */
  private totalSeen = 0;

  /**
   * Total errors that passed sampling (were logged)
   */
  private totalSampled = 0;

  /**
   * Create sampler for given environment
   *
   * @param environment - 'development' or 'production'
   */
  constructor(environment: 'development' | 'production') {
    // Only sample in development to reduce noise
    // Production always logs all errors
    this.sampleRate =
      environment === 'development' ? DEV_SAMPLE_RATE : PROD_SAMPLE_RATE;
  }

  /**
   * Determine if this error should be sampled (logged)
   *
   * Uses probabilistic random sampling.
   * - Development: ~10% of errors pass sampling
   * - Production: 100% of errors pass sampling
   *
   * @returns true if should log, false if should drop
   */
  shouldSample(): boolean {
    this.totalSeen += 1;

    // Production: always sample
    if (this.sampleRate === PROD_SAMPLE_RATE) {
      this.totalSampled += 1;
      return true;
    }

    // Development: probabilistic sampling
    const sample = Math.random() < this.sampleRate;

    if (sample) {
      this.totalSampled += 1;
    }

    return sample;
  }

  /**
   * Get effective sampling rate
   *
   * Ratio of sampled to total seen.
   * Should be ~0.1 in development (10%) and 1.0 in production.
   *
   * @returns Number between 0.0 and 1.0
   */
  getEffectiveRate(): number {
    if (this.totalSeen === 0) {
      return 0;
    }
    return this.totalSampled / this.totalSeen;
  }

  /**
   * Get sampling statistics
   *
   * @returns Object with total_seen, total_sampled, and effective_rate
   */
  getStats(): {
    total_seen: number;
    total_sampled: number;
    effective_rate: number;
  } {
    return {
      total_seen: this.totalSeen,
      total_sampled: this.totalSampled,
      effective_rate: this.getEffectiveRate(),
    };
  }

  /**
   * Reset statistics (for testing)
   *
   * @internal
   */
  reset(): void {
    this.totalSeen = 0;
    this.totalSampled = 0;
  }
}
