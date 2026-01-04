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

// =============================================================================
// IPC PROTOCOL (v2.1 - Named Pipe Transport)
// =============================================================================

/**
 * IPC Protocol Version
 * Used for backward compatibility checks
 */
export const IPC_PROTOCOL_VERSION = 1;

/**
 * IPC Event Types - Lightweight for Named Pipe transport
 */
export type IPCEventType =
  | 'ping'
  | 'pong'
  | 'heartbeat'
  | 'handshake'       // v2.2.0: Phase 7.0 Handshake Protocol (send on connect)
  | 'handshake_ack'   // v2.2.0: Server acknowledgement of handshake
  | 'file_edit'
  | 'terminal'
  | 'diagnostic'
  | 'recall'
  | 'stats'
  | 'context'
  | 'error'
  | 'ack'
  | 'request'     // v2.1: Request-response pattern (Oracle API)
  | 'response'    // v2.1: Response from daemon
  | 'pin'         // v2.2: Pin a memory
  | 'unpin'       // v2.2: Unpin a memory
  | 'get_pinned'  // v2.2: Get pinned memories
  | 'set_config'  // v2.3: Set daemon config (profile switching)
  | 'focus'       // v2.7: User focus update (file, line, selection)
  | 'get_focus'   // v2.7: Get current user focus state
  | 'resolve_path'; // v2.7: Resolve fuzzy/partial path to absolute

/**
 * Lightweight IPC Event for Named Pipe transport
 *
 * Optimized for bandwidth: uses short field names and numeric version
 *
 * Format: {"v":1,"type":"file_edit","ts":1701234567890,"data":{...}}\n
 *
 * @example
 * ```typescript
 * const event: IPCEvent = {
 *   v: 1,
 *   type: 'file_edit',
 *   ts: Date.now(),
 *   data: { file: 'auth.py', gist: 'Updated login validation' }
 * };
 * socket.write(JSON.stringify(event) + '\n');
 * ```
 */
export interface IPCEvent<TData = unknown> {
  /** Protocol version (always 1 for v2.1) */
  v: number;

  /** Event type */
  type: IPCEventType;

  /** Unix timestamp in milliseconds */
  ts: number;

  /** Optional request ID for request-response correlation */
  id?: string;

  /** Event-specific data payload */
  data?: TData;
}

/**
 * IPC Response format
 */
export interface IPCResponse<TData = unknown> {
  /** Protocol version */
  v: number;

  /** Response type (usually 'ack' or 'error') */
  type: 'ack' | 'error' | IPCEventType;

  /** Unix timestamp */
  ts: number;

  /** Request ID this is responding to */
  id?: string;

  /** Response status */
  ok: boolean;

  /** Response data or error message */
  data?: TData;

  /** Error message if ok is false */
  error?: string;
}

// -------------------------------------------------------------------------
// IPC Data Payloads
// -------------------------------------------------------------------------

/**
 * File edit data for IPC
 */
export interface IPCFileEditData {
  /** File path (relative to project root) */
  file: string;

  /** Semantic gist (already sanitized by Gatekeeper) */
  gist: string;

  /** Change type */
  change: 'open' | 'save' | 'modify' | 'rename' | 'delete';

  /** Language identifier */
  lang?: string;

  /** Line count */
  lines?: number;

  /** Content hash (for dedup) */
  hash?: string;
}

/**
 * Terminal event data for IPC
 */
export interface IPCTerminalData {
  /** Command executed */
  cmd: string;

  /** Exit code */
  code?: number;

  /** Output excerpt (sanitized) */
  out?: string;

  /** Error excerpt (sanitized) */
  err?: string;

  /** Duration in milliseconds */
  dur?: number;
}

/**
 * Diagnostic event data for IPC
 */
export interface IPCDiagnosticData {
  /** File path */
  file: string;

  /** Severity: 0=error, 1=warning, 2=info, 3=hint */
  sev: 0 | 1 | 2 | 3;

  /** Message */
  msg: string;

  /** Line number */
  ln?: number;

  /** Source (e.g., 'typescript', 'eslint') */
  src?: string;
}

/**
 * Context request data for IPC
 */
export interface IPCContextRequestData {
  /** Query string for context retrieval */
  query?: string;

  /** Maximum tokens to return */
  maxTokens?: number;

  /** Minimum salience level */
  minSalience?: 'critical' | 'high' | 'medium' | 'low';
}

/**
 * Context response data for IPC
 */
export interface IPCContextResponseData {
  /** Formatted context string */
  context: string;

  /** Number of memories included */
  count: number;

  /** Token count estimate */
  tokens: number;
}

/**
 * Pin request data for IPC (v2.2)
 */
export interface IPCPinData {
  /** Memory ID to pin */
  memory_id: string;

  /** Reason for pinning */
  reason?: string;
}

/**
 * Unpin request data for IPC (v2.2)
 */
export interface IPCUnpinData {
  /** Memory ID to unpin */
  memory_id: string;
}

/**
 * Get pinned request data for IPC (v2.2)
 */
export interface IPCGetPinnedData {
  /** Optional project path filter */
  project_path?: string;
}

/**
 * Pinned memories response data for IPC (v2.2)
 */
export interface IPCPinnedResponseData {
  /** List of pinned memory records */
  pinned: Array<{
    memory_id: string;
    pinned_at: string;
    reason?: string;
    pinned_by?: string;
  }>;

  /** Number of pinned memories */
  count: number;
}

/**
 * Focus update data for IPC (v2.7 - StateLinker)
 */
export interface IPCFocusData {
  /** File path being viewed */
  file: string;

  /** Current line number (1-indexed) */
  line?: number;

  /** Current column number (1-indexed) */
  column?: number;

  /** Selected text (if any) */
  selection?: string;

  /** Project root path */
  project_root?: string;
}

/**
 * Focus response data for IPC (v2.7)
 */
export interface IPCFocusResponseData {
  /** Currently active file path */
  active_file: string | null;

  /** Current line number */
  active_line: number | null;

  /** Selected text */
  selection: string | null;

  /** Recently viewed files */
  recent_files: string[];

  /** Focus tracking stats */
  stats: {
    total_focus_updates: number;
    unique_files_viewed: number;
  };
}

/**
 * Resolve path request data for IPC (v2.7)
 */
export interface IPCResolvePathData {
  /** Partial or fuzzy path to resolve */
  path: string;
}

/**
 * Resolve path response data for IPC (v2.7)
 */
export interface IPCResolvePathResponseData {
  /** Original partial path */
  partial: string;

  /** Resolved absolute path (null if not found) */
  resolved: string | null;

  /** Whether resolution was successful */
  found: boolean;
}

// -------------------------------------------------------------------------
// IPC Helper Functions
// -------------------------------------------------------------------------

/**
 * Create an IPC event with defaults
 */
export function createIPCEvent<TData>(
  type: IPCEventType,
  data?: TData,
  id?: string
): IPCEvent<TData> {
  return {
    v: IPC_PROTOCOL_VERSION,
    type,
    ts: Date.now(),
    id,
    data,
  };
}

/**
 * Create an IPC success response
 */
export function createIPCResponse<TData>(
  type: IPCEventType,
  data?: TData,
  id?: string
): IPCResponse<TData> {
  return {
    v: IPC_PROTOCOL_VERSION,
    type,
    ts: Date.now(),
    id,
    ok: true,
    data,
  };
}

/**
 * Create an IPC error response
 */
export function createIPCError(
  error: string,
  id?: string,
  type: IPCEventType = 'error'
): IPCResponse<undefined> {
  return {
    v: IPC_PROTOCOL_VERSION,
    type,
    ts: Date.now(),
    id,
    ok: false,
    error,
  };
}

/**
 * Parse NDJSON line into IPC event
 * Returns null if parsing fails
 */
export function parseIPCEvent(line: string): IPCEvent | null {
  try {
    const event = JSON.parse(line.trim());
    if (typeof event.v === 'number' && typeof event.type === 'string') {
      return event as IPCEvent;
    }
    return null;
  } catch {
    return null;
  }
}

/**
 * Serialize IPC event to NDJSON line
 */
export function serializeIPCEvent(event: IPCEvent): string {
  return JSON.stringify(event) + '\n';
}
