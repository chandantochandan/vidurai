/**
 * Vidurai Shared Event Schema - TypeScript
 *
 * Unified event model for all Vidurai frontend components (VS Code, Browser).
 * Mirrors the Python schema in vidurai/shared/events.py
 *
 * Schema Version: vidurai-events-v1
 *
 * Usage:
 *   import { ViduraiEvent, FileEditPayload } from './shared/events';
 *
 *   const event: ViduraiEvent<FileEditPayload> = {
 *     schema_version: 'vidurai-events-v1',
 *     event_id: crypto.randomUUID(),
 *     timestamp: new Date().toISOString(),
 *     source: 'vscode',
 *     channel: 'human',
 *     kind: 'file_edit',
 *     payload: { file_path: 'auth.py', change_type: 'save' }
 *   };
 */

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

/**
 * Source system that generated the event
 */
export type EventSource = 'vscode' | 'browser' | 'proxy' | 'daemon' | 'cli';

/**
 * Channel through which the event was generated
 * - human: Direct human action (typing, clicking, running commands)
 * - ai: AI-generated content or response
 * - system: Automated system events (file sync, background jobs)
 */
export type EventChannel = 'human' | 'ai' | 'system';

/**
 * Type of event - categorizes events by semantic meaning
 */
export type EventKind =
  | 'file_edit'
  | 'terminal_command'
  | 'diagnostic'
  | 'ai_message'
  | 'ai_response'
  | 'error_report'
  | 'memory_event'
  | 'hint_event'
  | 'metric_event'
  | 'system_event';

// =============================================================================
// CORE EVENT INTERFACE
// =============================================================================

/**
 * Core event model for all Vidurai events
 *
 * This is the canonical schema for events flowing through the Vidurai ecosystem.
 * All components (SDK, Daemon, VS Code, Browser) should emit events in this format.
 *
 * @template TPayload - Type of the payload object
 */
export interface ViduraiEvent<TPayload = unknown> {
  /** Event schema version for compatibility */
  schema_version: string; // "vidurai-events-v1"

  /** Unique identifier for this event (UUID) */
  event_id: string;

  /** ISO 8601 UTC timestamp */
  timestamp: string;

  /** Source system that generated this event */
  source: EventSource;

  /** Channel (human/ai/system) */
  channel: EventChannel;

  /** Type of event */
  kind: EventKind;

  /** Optional subtype for more granular classification */
  subtype?: string;

  /** Root path of the project */
  project_root?: string;

  /** Optional project identifier (hash or name) */
  project_id?: string;

  /** Optional session identifier for grouping related events */
  session_id?: string;

  /** Optional request identifier for tracing */
  request_id?: string;

  /** Event-specific payload data */
  payload: TPayload;
}

// =============================================================================
// SPECIALIZED PAYLOADS
// =============================================================================

/**
 * Payload for file edit events
 */
export interface FileEditPayload {
  /** Path to the edited file */
  file_path: string;

  /** Programming language of the file */
  language?: string;

  /** Type of change: open, save, modify, rename, delete */
  change_type: 'open' | 'save' | 'modify' | 'rename' | 'delete';

  /** Previous path for rename operations */
  old_path?: string | null;

  /** Number of lines in the file */
  line_count?: number;

  /** Content hash before change */
  hash_before?: string | null;

  /** Content hash after change */
  hash_after?: string | null;

  /** Brief excerpt of changed content */
  content_excerpt?: string;

  /** Editor used (vscode, vim, etc.) */
  editor?: string;
}

/**
 * Payload for hint events with multi-audience support
 *
 * Audiences:
 * - developer: Technical hints (code suggestions, debugging tips)
 * - ai: Context for AI assistants (relevant memories, patterns)
 * - manager: High-level progress summaries
 * - product: Feature/requirement insights
 * - stakeholder: Business impact summaries
 */
export interface HintEventPayload {
  /** Unique identifier for this hint */
  hint_id: string;

  /** Type of hint: relevant_context, follow_up, warning, suggestion */
  hint_type: string;

  /** Human-readable hint text */
  text: string;

  /** Target recipient: human or ai */
  target: 'human' | 'ai';

  /** Target audience */
  audience: 'developer' | 'ai' | 'manager' | 'product' | 'stakeholder';

  /** Delivery surface */
  surface: 'vscode' | 'browser' | 'cli' | 'dashboard';

  /** Whether the hint was accepted/used */
  accepted?: boolean;

  /** Time taken to generate this hint in milliseconds */
  latency_ms?: number;
}

/**
 * Payload for terminal command events
 */
export interface TerminalCommandPayload {
  /** The command that was executed */
  command: string;

  /** Exit code of the command */
  exit_code?: number;

  /** Working directory */
  cwd?: string;

  /** Shell used (bash, zsh, etc.) */
  shell?: string;

  /** Command execution time in milliseconds */
  duration_ms?: number;

  /** Brief excerpt of command output */
  output_excerpt?: string;

  /** Brief excerpt of error output */
  error_excerpt?: string;
}

/**
 * Payload for diagnostic events (errors, warnings from IDE)
 */
export interface DiagnosticPayload {
  /** Path to the file with diagnostic */
  file_path: string;

  /** Severity: error, warning, info, hint */
  severity: 'error' | 'warning' | 'info' | 'hint';

  /** Diagnostic message */
  message: string;

  /** Line number */
  line?: number;

  /** Column number */
  column?: number;

  /** Source of diagnostic (typescript, eslint, etc.) */
  source?: string;

  /** Diagnostic code */
  code?: string;
}

/**
 * Payload for AI message events
 */
export interface AIMessagePayload {
  /** AI platform: chatgpt, claude, gemini, etc. */
  platform: string;

  /** Type: user_prompt, ai_response, system_message */
  message_type: 'user_prompt' | 'ai_response' | 'system_message';

  /** Message text (may be truncated for privacy) */
  text?: string;

  /** Full length of message in characters */
  text_length?: number;

  /** Model used (gpt-4, claude-3, etc.) */
  model?: string;

  /** Input tokens (if available) */
  tokens_in?: number;

  /** Output tokens (if available) */
  tokens_out?: number;

  /** Whether Vidurai context was injected */
  context_injected?: boolean;
}

/**
 * Payload for error report events
 */
export interface ErrorReportPayload {
  /** Type of error (TypeError, SyntaxError, etc.) */
  error_type: string;

  /** Error message */
  error_message: string;

  /** Stack trace if available */
  stack_trace?: string;

  /** File where error occurred */
  file_path?: string;

  /** Line number */
  line?: number;

  /** Surrounding code context */
  context?: string;
}

/**
 * Payload for memory-related events
 */
export interface MemoryEventPayload {
  /** Action: create, recall, forget, consolidate, pin, unpin */
  action: 'create' | 'recall' | 'forget' | 'consolidate' | 'pin' | 'unpin';

  /** Memory identifier */
  memory_id?: string;

  /** Multiple memory identifiers (for batch operations) */
  memory_ids?: string[];

  /** Salience level: critical, high, medium, low, noise */
  salience?: 'critical' | 'high' | 'medium' | 'low' | 'noise';

  /** Brief summary of the memory */
  gist?: string;

  /** Reason for the action */
  reason?: string;
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Schema version constant
 */
export const VIDURAI_SCHEMA_VERSION = 'vidurai-events-v1';

/**
 * Generate a UUID for event_id
 * Uses a simple UUID v4 implementation that works in both Node.js and browsers
 */
export function generateEventId(): string {
  // Simple UUID v4 implementation that works everywhere
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

/**
 * Generate an ISO 8601 UTC timestamp
 */
export function generateTimestamp(): string {
  return new Date().toISOString();
}

/**
 * Create a ViduraiEvent with common defaults
 *
 * @param kind - Event type
 * @param source - Source system
 * @param channel - Channel (default: 'human')
 * @param payload - Event payload
 * @param options - Optional fields (project_root, session_id, etc.)
 */
export function createEvent<TPayload>(
  kind: EventKind,
  source: EventSource,
  payload: TPayload,
  options: {
    channel?: EventChannel;
    subtype?: string;
    project_root?: string;
    project_id?: string;
    session_id?: string;
    request_id?: string;
  } = {}
): ViduraiEvent<TPayload> {
  return {
    schema_version: VIDURAI_SCHEMA_VERSION,
    event_id: generateEventId(),
    timestamp: generateTimestamp(),
    source,
    channel: options.channel ?? 'human',
    kind,
    subtype: options.subtype,
    project_root: options.project_root,
    project_id: options.project_id,
    session_id: options.session_id,
    request_id: options.request_id,
    payload,
  };
}
