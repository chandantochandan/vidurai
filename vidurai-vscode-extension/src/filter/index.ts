/**
 * Filter Module
 *
 * Provides traffic control and filtering before events reach IPC transport.
 */

export {
  EdgeFilter,
  EdgeFilterOptions,
  FilterableEvent,
  FilterableEventType,
  FilterStats,
  getEdgeFilter,
  resetEdgeFilter,
  shouldIgnoreFile,
  getIgnorePatterns,
} from './EdgeFilter';
