/**
 * Edge Filter - Traffic Control Before IPC
 *
 * Filters and rate-limits events before they reach the IPC transport layer.
 * Implements debouncing, deduplication, and intelligent filtering to reduce
 * noise and prevent overwhelming the daemon.
 *
 * Features:
 * - Debounce: Groups rapid file edits (e.g., typing) into single events
 * - Deduplication: Prevents duplicate events within time window
 * - Rate Limiting: Caps events per second to prevent flooding
 * - Smart Filtering: Ignores temp files, build artifacts, node_modules
 * - Batch Coalescing: Combines multiple small changes into batches
 *
 * @module filter/EdgeFilter
 * @version 2.1.0
 */

import { EventEmitter } from 'events';

// =============================================================================
// TYPES
// =============================================================================

/**
 * Event types that can be filtered
 */
export type FilterableEventType =
  | 'file_edit'
  | 'file_create'
  | 'file_delete'
  | 'file_rename'
  | 'terminal'
  | 'diagnostic'
  | 'selection'
  | 'focus';

/**
 * An event to be filtered
 */
export interface FilterableEvent {
  type: FilterableEventType;
  file?: string;
  data?: Record<string, unknown>;
  timestamp?: number;
}

/**
 * Filter configuration options
 */
export interface EdgeFilterOptions {
  /** Debounce delay for file edits in ms (default: 500) */
  debounceDelay?: number;

  /** Deduplication window in ms (default: 1000) */
  dedupeWindow?: number;

  /** Max events per second (default: 10) */
  maxEventsPerSecond?: number;

  /** Enable smart file filtering (default: true) */
  enableSmartFilter?: boolean;

  /** Enable batch coalescing (default: true) */
  enableBatching?: boolean;

  /** Batch window in ms (default: 100) */
  batchWindow?: number;

  /** Max batch size (default: 50) */
  maxBatchSize?: number;

  /** Enable debug logging (default: false) */
  debug?: boolean;
}

/**
 * Filter statistics
 */
export interface FilterStats {
  received: number;
  passed: number;
  debounced: number;
  deduplicated: number;
  rateLimited: number;
  filtered: number;
  batched: number;
}

/**
 * Debounce entry for tracking pending events
 */
interface DebounceEntry {
  event: FilterableEvent;
  timer: NodeJS.Timeout;
  count: number;
}

/**
 * Rate limiter bucket
 */
interface RateBucket {
  count: number;
  resetTime: number;
}

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Default configuration
 */
const DEFAULT_OPTIONS: Required<EdgeFilterOptions> = {
  debounceDelay: 500,
  dedupeWindow: 1000,
  maxEventsPerSecond: 10,
  enableSmartFilter: true,
  enableBatching: true,
  batchWindow: 100,
  maxBatchSize: 50,
  debug: false,
};

/**
 * Patterns for files to ignore (smart filter)
 */
const IGNORE_PATTERNS: RegExp[] = [
  // Build artifacts
  /[\\/]dist[\\/]/,
  /[\\/]build[\\/]/,
  /[\\/]out[\\/]/,
  /[\\/]\.next[\\/]/,
  /[\\/]\.nuxt[\\/]/,
  /[\\/]\.output[\\/]/,

  // Dependencies
  /[\\/]node_modules[\\/]/,
  /[\\/]vendor[\\/]/,
  /[\\/]\.venv[\\/]/,
  /[\\/]venv[\\/]/,
  /[\\/]__pycache__[\\/]/,
  /[\\/]\.pip[\\/]/,

  // Version control
  /[\\/]\.git[\\/]/,
  /[\\/]\.svn[\\/]/,
  /[\\/]\.hg[\\/]/,

  // IDE/Editor
  /[\\/]\.idea[\\/]/,
  /[\\/]\.vscode[\\/](?!settings\.json|launch\.json|tasks\.json)/,
  /[\\/]\.vs[\\/]/,

  // Temp files
  /\.tmp$/i,
  /\.temp$/i,
  /\.swp$/i,
  /\.swo$/i,
  /~$/,
  /\.bak$/i,

  // Lock files (frequent updates)
  /package-lock\.json$/,
  /yarn\.lock$/,
  /pnpm-lock\.yaml$/,
  /Cargo\.lock$/,
  /poetry\.lock$/,
  /Gemfile\.lock$/,

  // Generated files
  /\.min\.js$/,
  /\.min\.css$/,
  /\.map$/,
  /\.d\.ts$/,

  // Binary/Media (shouldn't have text edits anyway)
  /\.(png|jpg|jpeg|gif|ico|svg|webp)$/i,
  /\.(mp3|mp4|wav|avi|mov)$/i,
  /\.(zip|tar|gz|rar|7z)$/i,
  /\.(pdf|doc|docx|xls|xlsx)$/i,

  // Log files
  /\.log$/i,
  /[\\/]logs[\\/]/,
];

/**
 * Event types that should be debounced
 */
const DEBOUNCE_TYPES: Set<FilterableEventType> = new Set<FilterableEventType>([
  'file_edit',
  'selection',
  'diagnostic',
]);

/**
 * Event types that should be deduplicated
 */
const DEDUPE_TYPES: Set<FilterableEventType> = new Set<FilterableEventType>([
  'file_edit',
  'file_create',
  'file_delete',
  'terminal',
  'focus',
]);

// =============================================================================
// EDGE FILTER CLASS
// =============================================================================

/**
 * Edge Filter for traffic control
 *
 * @example
 * ```typescript
 * const filter = new EdgeFilter();
 *
 * filter.on('event', (event) => {
 *   // Send to IPC
 *   ipcClient.sendEvent(event.type, event.data);
 * });
 *
 * filter.on('batch', (events) => {
 *   // Send batch to IPC
 *   ipcClient.sendEvent('batch', { events });
 * });
 *
 * // Submit events to filter
 * filter.submit({ type: 'file_edit', file: '/path/to/file.ts', data: {...} });
 * ```
 */
export class EdgeFilter extends EventEmitter {
  private options: Required<EdgeFilterOptions>;
  private stats: FilterStats;
  private debounceMap: Map<string, DebounceEntry> = new Map();
  private dedupeCache: Map<string, number> = new Map();
  private rateBucket: RateBucket;
  private batchQueue: FilterableEvent[] = [];
  private batchTimer: NodeJS.Timeout | null = null;

  constructor(options: EdgeFilterOptions = {}) {
    super();
    this.options = { ...DEFAULT_OPTIONS, ...options };
    this.stats = {
      received: 0,
      passed: 0,
      debounced: 0,
      deduplicated: 0,
      rateLimited: 0,
      filtered: 0,
      batched: 0,
    };
    this.rateBucket = {
      count: 0,
      resetTime: Date.now() + 1000,
    };
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Submit an event to the filter
   *
   * @param event Event to filter
   * @returns true if event will be processed (may be debounced/batched)
   */
  submit(event: FilterableEvent): boolean {
    this.stats.received++;
    event.timestamp = event.timestamp || Date.now();

    // Step 1: Smart file filtering
    if (this.options.enableSmartFilter && event.file) {
      if (this.shouldIgnoreFile(event.file)) {
        this.stats.filtered++;
        this.log(`Filtered (ignore pattern): ${event.file}`);
        return false;
      }
    }

    // Step 2: Rate limiting
    if (!this.checkRateLimit()) {
      this.stats.rateLimited++;
      this.log(`Rate limited: ${event.type}`);
      return false;
    }

    // Step 3: Debouncing (before deduplication to allow coalescing)
    if (DEBOUNCE_TYPES.has(event.type)) {
      this.debounce(event);
      return true;
    }

    // Step 4: Deduplication (only for non-debounced events)
    if (DEDUPE_TYPES.has(event.type)) {
      const dedupeKey = this.getDedupeKey(event);
      if (this.isDuplicate(dedupeKey)) {
        this.stats.deduplicated++;
        this.log(`Deduplicated: ${event.type} ${event.file || ''}`);
        return false;
      }
      this.markSeen(dedupeKey);
    }

    // Step 5: Batching or immediate emit
    if (this.options.enableBatching) {
      this.addToBatch(event);
    } else {
      this.emitEvent(event);
    }

    return true;
  }

  /**
   * Flush all pending events immediately
   */
  flush(): void {
    // Flush debounced events
    const debounceEntries = Array.from(this.debounceMap.entries());
    for (let i = 0; i < debounceEntries.length; i++) {
      const [key, entry] = debounceEntries[i];
      clearTimeout(entry.timer);
      this.emitEvent(entry.event);
    }
    this.debounceMap.clear();

    // Flush batch queue
    this.flushBatch();
  }

  /**
   * Get filter statistics
   */
  getStats(): FilterStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics
   */
  resetStats(): void {
    this.stats = {
      received: 0,
      passed: 0,
      debounced: 0,
      deduplicated: 0,
      rateLimited: 0,
      filtered: 0,
      batched: 0,
    };
  }

  /**
   * Clear all pending events and caches
   */
  clear(): void {
    // Clear debounce timers
    const debounceEntries = Array.from(this.debounceMap.values());
    for (let i = 0; i < debounceEntries.length; i++) {
      clearTimeout(debounceEntries[i].timer);
    }
    this.debounceMap.clear();

    // Clear batch timer
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }
    this.batchQueue = [];

    // Clear dedupe cache
    this.dedupeCache.clear();
  }

  /**
   * Destroy the filter
   */
  destroy(): void {
    this.clear();
    this.removeAllListeners();
  }

  // ---------------------------------------------------------------------------
  // Smart File Filtering
  // ---------------------------------------------------------------------------

  /**
   * Check if a file should be ignored
   */
  private shouldIgnoreFile(filePath: string): boolean {
    // Normalize path separators
    const normalized = filePath.replace(/\\/g, '/');

    for (let i = 0; i < IGNORE_PATTERNS.length; i++) {
      if (IGNORE_PATTERNS[i].test(normalized) || IGNORE_PATTERNS[i].test(filePath)) {
        return true;
      }
    }

    return false;
  }

  // ---------------------------------------------------------------------------
  // Rate Limiting
  // ---------------------------------------------------------------------------

  /**
   * Check if event passes rate limit
   */
  private checkRateLimit(): boolean {
    const now = Date.now();

    // Reset bucket if window expired
    if (now >= this.rateBucket.resetTime) {
      this.rateBucket.count = 0;
      this.rateBucket.resetTime = now + 1000;
    }

    // Check limit
    if (this.rateBucket.count >= this.options.maxEventsPerSecond) {
      return false;
    }

    this.rateBucket.count++;
    return true;
  }

  // ---------------------------------------------------------------------------
  // Deduplication
  // ---------------------------------------------------------------------------

  /**
   * Generate deduplication key for an event
   */
  private getDedupeKey(event: FilterableEvent): string {
    const parts: string[] = [event.type];

    if (event.file) {
      parts.push(event.file);
    }

    // Include relevant data fields for dedup
    if (event.data) {
      if (event.data.change) {
        parts.push(String(event.data.change));
      }
      if (event.data.command) {
        parts.push(String(event.data.command));
      }
    }

    return parts.join(':');
  }

  /**
   * Check if event is a duplicate
   */
  private isDuplicate(key: string): boolean {
    const lastSeen = this.dedupeCache.get(key);
    if (!lastSeen) {
      return false;
    }

    const elapsed = Date.now() - lastSeen;
    return elapsed < this.options.dedupeWindow;
  }

  /**
   * Mark event as seen for deduplication
   */
  private markSeen(key: string): void {
    this.dedupeCache.set(key, Date.now());

    // Cleanup old entries periodically
    if (this.dedupeCache.size > 1000) {
      this.cleanupDedupeCache();
    }
  }

  /**
   * Remove expired entries from dedupe cache
   */
  private cleanupDedupeCache(): void {
    const now = Date.now();
    const cutoff = now - this.options.dedupeWindow;

    const entries = Array.from(this.dedupeCache.entries());
    for (let i = 0; i < entries.length; i++) {
      const [key, timestamp] = entries[i];
      if (timestamp < cutoff) {
        this.dedupeCache.delete(key);
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Debouncing
  // ---------------------------------------------------------------------------

  /**
   * Debounce an event
   */
  private debounce(event: FilterableEvent): void {
    const key = this.getDebounceKey(event);
    const existing = this.debounceMap.get(key);

    if (existing) {
      // Update existing entry
      clearTimeout(existing.timer);
      existing.event = event;
      existing.count++;
      this.stats.debounced++;
      this.log(`Debounced (${existing.count}x): ${event.type} ${event.file || ''}`);
    }

    // Set new timer
    const timer = setTimeout(() => {
      const entry = this.debounceMap.get(key);
      if (entry) {
        this.debounceMap.delete(key);

        // Add debounce count to event data
        if (entry.count > 1) {
          entry.event.data = {
            ...entry.event.data,
            _debounceCount: entry.count,
          };
        }

        if (this.options.enableBatching) {
          this.addToBatch(entry.event);
        } else {
          this.emitEvent(entry.event);
        }
      }
    }, this.options.debounceDelay);

    this.debounceMap.set(key, {
      event,
      timer,
      count: existing ? existing.count : 1,
    });
  }

  /**
   * Generate debounce key for an event
   */
  private getDebounceKey(event: FilterableEvent): string {
    // Debounce by type + file
    return `${event.type}:${event.file || 'global'}`;
  }

  // ---------------------------------------------------------------------------
  // Batching
  // ---------------------------------------------------------------------------

  /**
   * Add event to batch queue
   */
  private addToBatch(event: FilterableEvent): void {
    this.batchQueue.push(event);
    this.stats.batched++;

    // Flush if batch is full
    if (this.batchQueue.length >= this.options.maxBatchSize) {
      this.flushBatch();
      return;
    }

    // Start batch timer if not running
    if (!this.batchTimer) {
      this.batchTimer = setTimeout(() => {
        this.flushBatch();
      }, this.options.batchWindow);
    }
  }

  /**
   * Flush the batch queue
   */
  private flushBatch(): void {
    if (this.batchTimer) {
      clearTimeout(this.batchTimer);
      this.batchTimer = null;
    }

    if (this.batchQueue.length === 0) {
      return;
    }

    // Emit single event directly, multiple as batch
    if (this.batchQueue.length === 1) {
      this.emitEvent(this.batchQueue[0]);
    } else {
      this.log(`Emitting batch of ${this.batchQueue.length} events`);
      this.emit('batch', [...this.batchQueue]);
    }

    this.batchQueue = [];
  }

  // ---------------------------------------------------------------------------
  // Event Emission
  // ---------------------------------------------------------------------------

  /**
   * Emit a filtered event
   */
  private emitEvent(event: FilterableEvent): void {
    this.stats.passed++;
    this.log(`Emitting: ${event.type} ${event.file || ''}`);
    this.emit('event', event);
  }

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  /**
   * Debug logging
   */
  private log(message: string): void {
    if (this.options.debug) {
      console.log(`[EdgeFilter] ${message}`);
    }
  }
}

// =============================================================================
// SINGLETON EXPORT
// =============================================================================

/**
 * Default EdgeFilter instance
 */
let defaultFilter: EdgeFilter | null = null;

/**
 * Get or create the default EdgeFilter
 */
export function getEdgeFilter(options?: EdgeFilterOptions): EdgeFilter {
  if (!defaultFilter) {
    defaultFilter = new EdgeFilter(options);
  }
  return defaultFilter;
}

/**
 * Reset the default EdgeFilter
 */
export function resetEdgeFilter(): void {
  if (defaultFilter) {
    defaultFilter.destroy();
    defaultFilter = null;
  }
}

// =============================================================================
// UTILITY EXPORTS
// =============================================================================

/**
 * Check if a file path should be ignored
 *
 * @param filePath Path to check
 * @returns true if file should be ignored
 */
export function shouldIgnoreFile(filePath: string): boolean {
  const normalized = filePath.replace(/\\/g, '/');

  for (let i = 0; i < IGNORE_PATTERNS.length; i++) {
    if (IGNORE_PATTERNS[i].test(normalized) || IGNORE_PATTERNS[i].test(filePath)) {
      return true;
    }
  }

  return false;
}

/**
 * Get the list of ignore patterns
 */
export function getIgnorePatterns(): RegExp[] {
  return [...IGNORE_PATTERNS];
}
