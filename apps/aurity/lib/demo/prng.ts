/**
 * Free Intelligence - Seedable PRNG (Mulberry32)
 *
 * Deterministic random number generator for reproducible demo datasets.
 *
 * File: lib/demo/prng.ts
 * Card: FI-UI-FEAT-207
 * Created: 2025-10-30
 *
 * Philosophy AURITY:
 * - Reproducibilidad > aleatoriedad: un seed = un mundo
 * - 32-bit multiplication-based PRNG (fast, deterministic)
 */

/**
 * Mulberry32 PRNG - Simple, fast, deterministic
 * Source: https://github.com/bryc/code/blob/master/jshash/PRNGs.md
 */
export class PRNG {
  private state: number;
  private readonly originalSeed: string;

  constructor(seed: string) {
    this.originalSeed = seed;
    // Convert string seed to 32-bit number using simple hash
    this.state = this.hashSeed(seed);
  }

  /**
   * Hash string seed to 32-bit number
   */
  private hashSeed(seed: string): number {
    let hash = 0;
    for (let i = 0; i < seed.length; i++) {
      const char = seed.charCodeAt(i);
      hash = (hash << 5) - hash + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return Math.abs(hash) >>> 0; // Ensure unsigned 32-bit
  }

  /**
   * Generate next random float in range [0, 1)
   */
  next(): number {
    this.state |= 0;
    this.state = (this.state + 0x6d2b79f5) | 0;
    let t = Math.imul(this.state ^ (this.state >>> 15), 1 | this.state);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  /**
   * Generate random integer in range [min, max]
   */
  int(min: number, max: number): number {
    return Math.floor(this.next() * (max - min + 1)) + min;
  }

  /**
   * Pick random element from array
   */
  pick<T>(arr: T[]): T {
    return arr[this.int(0, arr.length - 1)];
  }

  /**
   * Shuffle array (Fisher-Yates) using this PRNG
   */
  shuffle<T>(arr: T[]): T[] {
    const shuffled = [...arr];
    for (let i = shuffled.length - 1; i > 0; i--) {
      const j = this.int(0, i);
      [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
    }
    return shuffled;
  }

  /**
   * Generate deterministic UUID-like ID
   */
  uuid(prefix: string = ''): string {
    const hex = () => this.int(0, 15).toString(16);
    const uuid = `${prefix}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}-${hex()}${hex()}${hex()}${hex()}-${hex()}${hex()}${hex()}${hex()}-${hex()}${hex()}${hex()}${hex()}-${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}${hex()}`;
    return uuid;
  }

  /**
   * Reset PRNG to original seed
   */
  reset(): void {
    this.state = this.hashSeed(this.originalSeed);
  }

  /**
   * Get current seed (for manifest)
   */
  getSeed(): string {
    return this.originalSeed;
  }
}
