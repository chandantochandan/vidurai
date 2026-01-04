/**
 * IPC Client - Named Pipe Transport for Vidurai
 *
 * Connects to the Vidurai Daemon via Named Pipe (Windows) or Unix Socket (Mac/Linux).
 * Uses NDJSON protocol for bidirectional communication.
 *
 * Architecture:
 * - Does NOT spawn daemon process (assumes daemon is running)
 * - Offline Buffer: When disconnected, events are written to ~/.vidurai/buffer-{sessionId}.jsonl
 * - Rotation Strategy: When buffer > 10MB, rename to .bak and create new file (O(1) operation)
 * - Drain on Reconnect: Buffer is sent to daemon when connection is restored
 * - Supports request-response correlation via message IDs
 * - Receives heartbeats from daemon every 5 seconds
 *
 * @module ipc/Client
 * @version 2.1.0
 */

import * as net from 'net';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import { EventEmitter } from 'events';
import {
  IPCEvent,
  IPCResponse,
  IPCEventType,
  createIPCEvent,
  parseIPCEvent,
  serializeIPCEvent,
  IPC_PROTOCOL_VERSION,
} from '../shared/events';

// =============================================================================
// TYPES
// =============================================================================

/**
 * Connection state machine states
 */
export type ConnectionState =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'draining';

/**
 * Client configuration options
 */
export interface IPCClientOptions {
  /** Custom pipe path (overrides default) */
  pipePath?: string;

  /** Connection timeout in ms (default: 5000) */
  connectTimeout?: number;

  /** Request timeout in ms (default: 30000) */
  requestTimeout?: number;

  /** Auto-reconnect on disconnect (default: true) */
  autoReconnect?: boolean;

  /** Reconnect delay in ms (default: 2000) */
  reconnectDelay?: number;

  /** Max reconnect attempts (default: 10) */
  maxReconnectAttempts?: number;

  /** Enable debug logging (default: false) */
  debug?: boolean;

  /** Enable offline buffering (default: true) */
  enableBuffer?: boolean;

  /** Buffer directory path (default: ~/.vidurai) */
  bufferDir?: string;

  /** Max buffer size in bytes before rotation (default: 10MB) */
  maxBufferSize?: number;
}

/**
 * Pending request tracker
 */
interface PendingRequest {
  resolve: (response: IPCResponse) => void;
  reject: (error: Error) => void;
  timeout: NodeJS.Timeout;
}

/**
 * Client events
 */
export interface IPCClientEvents {
  connected: () => void;
  disconnected: (error?: Error) => void;
  error: (error: Error) => void;
  heartbeat: (ts: number) => void;
  message: (event: IPCEvent) => void;
  stateChange: (state: ConnectionState) => void;
  bufferDrained: (stats: { count: number; errors: number }) => void;
}

// =============================================================================
// CONSTANTS
// =============================================================================

/** Max buffer size: 10MB */
const MAX_BUFFER_SIZE = 10 * 1024 * 1024;

/**
 * Get the default pipe path for the current platform
 */
function getDefaultPipePath(): string {
  const uid = process.env.USER || process.env.USERNAME || 'default';

  if (process.platform === 'win32') {
    return `\\\\.\\pipe\\vidurai-${uid}`;
  } else {
    // Unix socket
    return path.join(os.tmpdir(), `vidurai-${uid}.sock`);
  }
}

/**
 * Get the default buffer directory (~/.vidurai)
 */
function getDefaultBufferDir(): string {
  return path.join(os.homedir(), '.vidurai');
}

/**
 * Generate a unique session ID
 */
function generateSessionId(): string {
  const timestamp = Date.now().toString(36);
  const random = Math.random().toString(36).substring(2, 8);
  return `${timestamp}-${random}`;
}

/**
 * Default configuration values
 */
const DEFAULT_OPTIONS: Required<IPCClientOptions> = {
  pipePath: getDefaultPipePath(),
  connectTimeout: 5000,
  requestTimeout: 30000,
  autoReconnect: true,
  reconnectDelay: 2000,
  maxReconnectAttempts: 10,
  debug: false,
  enableBuffer: true,
  bufferDir: getDefaultBufferDir(),
  maxBufferSize: MAX_BUFFER_SIZE,
};

// =============================================================================
// IPC CLIENT CLASS
// =============================================================================

/**
 * IPC Client for Vidurai Daemon communication
 *
 * Provides a robust, event-driven interface to the daemon over Named Pipes.
 *
 * @example
 * ```typescript
 * const client = new IPCClient();
 *
 * client.on('connected', () => console.log('Connected!'));
 * client.on('heartbeat', (ts) => console.log(`Heartbeat at ${ts}`));
 * client.on('error', (err) => console.error('Connection error:', err));
 *
 * await client.connect();
 *
 * const response = await client.send({ type: 'ping' });
 * console.log(response); // { type: 'pong', ok: true, ... }
 * ```
 */
export class IPCClient extends EventEmitter {
  private socket: net.Socket | null = null;
  private options: Required<IPCClientOptions>;
  private state: ConnectionState = 'disconnected';
  private receiveBuffer: string = '';
  private pendingRequests: Map<string, PendingRequest> = new Map();
  private requestCounter: number = 0;
  private reconnectAttempts: number = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private lastHeartbeat: number = 0;

  // Offline buffer properties
  private sessionId: string;
  private bufferPath: string;
  private bufferBackupPath: string;
  private isDraining: boolean = false;

  constructor(options: IPCClientOptions = {}) {
    super();
    this.options = { ...DEFAULT_OPTIONS, ...options };

    // Initialize offline buffer paths
    this.sessionId = generateSessionId();
    this.bufferPath = path.join(this.options.bufferDir, `buffer-${this.sessionId}.jsonl`);
    this.bufferBackupPath = `${this.bufferPath}.bak`;

    // Ensure buffer directory exists
    if (this.options.enableBuffer) {
      this.ensureBufferDir();
    }
  }

  /**
   * Ensure the buffer directory exists
   */
  private ensureBufferDir(): void {
    try {
      if (!fs.existsSync(this.options.bufferDir)) {
        fs.mkdirSync(this.options.bufferDir, { recursive: true });
        this.log(`Created buffer directory: ${this.options.bufferDir}`);
      }
    } catch (err) {
      this.log(`Failed to create buffer directory: ${err}`);
    }
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------

  /**
   * Get current connection state
   */
  getState(): ConnectionState {
    return this.state;
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.state === 'connected';
  }

  /**
   * Get pipe path being used
   */
  getPipePath(): string {
    return this.options.pipePath;
  }

  /**
   * Get last heartbeat timestamp
   */
  getLastHeartbeat(): number {
    return this.lastHeartbeat;
  }

  /**
   * Get session ID
   */
  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * Get buffer file path
   */
  getBufferPath(): string {
    return this.bufferPath;
  }

  /**
   * Check if buffer has pending events
   */
  hasBufferedEvents(): boolean {
    try {
      return fs.existsSync(this.bufferPath) && fs.statSync(this.bufferPath).size > 0;
    } catch {
      return false;
    }
  }

  /**
   * Get buffered event count (approximate, counts lines)
   */
  getBufferedEventCount(): number {
    try {
      if (!fs.existsSync(this.bufferPath)) {
        return 0;
      }
      const content = fs.readFileSync(this.bufferPath, 'utf-8');
      return content.split('\n').filter((line) => line.trim()).length;
    } catch {
      return 0;
    }
  }

  /**
   * Connect to the daemon
   *
   * @returns Promise that resolves when connected
   * @throws Error if connection fails
   */
  async connect(): Promise<void> {
    if (this.state === 'connected' || this.state === 'connecting') {
      this.log('Already connected or connecting');
      return;
    }

    this.setState('connecting');
    this.reconnectAttempts = 0;

    return this.doConnect();
  }

  /**
   * Disconnect from the daemon
   */
  disconnect(): void {
    this.log('Disconnecting...');

    // Clear reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    // Reject all pending requests
    const entries = Array.from(this.pendingRequests.entries());
    for (let i = 0; i < entries.length; i++) {
      const [, pending] = entries[i];
      clearTimeout(pending.timeout);
      pending.reject(new Error('Client disconnected'));
    }
    this.pendingRequests.clear();

    // Close socket
    if (this.socket) {
      this.socket.removeAllListeners();
      this.socket.destroy();
      this.socket = null;
    }

    this.setState('disconnected');
    this.emit('disconnected');
  }

  /**
   * Send an event to the daemon (fire-and-forget)
   *
   * If disconnected and buffering is enabled, writes to offline buffer.
   *
   * @param type Event type
   * @param data Event data
   * @returns true if sent/buffered, false if failed
   */
  sendEvent<TData>(type: IPCEventType, data?: TData): boolean {
    const event = createIPCEvent(type, data);

    if (this.isConnected()) {
      return this.writeToSocket(event);
    }

    // Write to offline buffer if enabled
    if (this.options.enableBuffer) {
      return this.writeToBuffer(event);
    }

    this.emit('error', new Error('Not connected and buffering disabled'));
    return false;
  }

  /**
   * Send a request and wait for response
   *
   * @param type Event type
   * @param data Event data
   * @returns Promise resolving to the response
   */
  async send<TData, TResponseData = unknown>(
    type: IPCEventType,
    data?: TData
  ): Promise<IPCResponse<TResponseData>> {
    if (!this.isConnected()) {
      throw new Error('Not connected');
    }

    const id = this.generateRequestId();
    const event = createIPCEvent(type, data, id);

    return new Promise((resolve, reject) => {
      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Request timeout: ${type}`));
      }, this.options.requestTimeout);

      // Store pending request
      this.pendingRequests.set(id, {
        resolve: resolve as (response: IPCResponse) => void,
        reject,
        timeout,
      });

      // Send the event
      this.writeToSocket(event);
    });
  }

  /**
   * Send a ping and wait for pong
   *
   * @returns Promise resolving to true if pong received
   */
  async ping(): Promise<boolean> {
    try {
      const response = await this.send('ping');
      return response.ok && response.type === 'pong';
    } catch {
      return false;
    }
  }

  // ---------------------------------------------------------------------------
  // Connection Management
  // ---------------------------------------------------------------------------

  private async doConnect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const pipePath = this.options.pipePath;
      this.log(`Connecting to ${pipePath}...`);

      // Create socket
      this.socket = new net.Socket();

      // Connection timeout
      const connectTimeout = setTimeout(() => {
        if (this.socket) {
          this.socket.destroy();
          this.socket = null;
        }
        const error = new Error(`Connection timeout: ${pipePath}`);
        this.handleConnectionError(error);
        reject(error);
      }, this.options.connectTimeout);

      // Handle successful connection
      this.socket.once('connect', async () => {
        clearTimeout(connectTimeout);
        this.log('Connected!');
        this.setState('connected');
        this.reconnectAttempts = 0;
        this.emit('connected');

        // Phase 7.0: Send handshake immediately after connect
        this.sendEvent('handshake', {
          client_name: 'VSCode',
          version: '2.1.0',
        });
        this.log('Sent handshake');

        // Drain any buffered events
        if (this.options.enableBuffer && this.hasBufferedEvents()) {
          // Use setImmediate to not block the connect resolution
          setImmediate(() => this.drainBuffer());
        }

        resolve();
      });

      // Handle connection error
      this.socket.once('error', (err: Error) => {
        clearTimeout(connectTimeout);
        this.log(`Connection error: ${err.message}`);
        this.handleConnectionError(err);
        reject(err);
      });

      // Set up data handling
      this.socket.on('data', (data) => this.handleData(data));

      // Handle socket close
      this.socket.on('close', (hadError) => {
        this.log(`Socket closed, hadError: ${hadError}`);
        this.handleDisconnect(hadError ? new Error('Socket closed with error') : undefined);
      });

      // Connect to pipe
      this.socket.connect(pipePath);
    });
  }

  private handleConnectionError(error: Error): void {
    this.socket = null;

    if (this.options.autoReconnect && this.reconnectAttempts < this.options.maxReconnectAttempts) {
      this.scheduleReconnect();
    } else {
      this.setState('disconnected');
      this.emit('error', error);
      this.emit('disconnected', error);
    }
  }

  private handleDisconnect(error?: Error): void {
    this.socket = null;

    // Reject pending requests
    const pendingEntries = Array.from(this.pendingRequests.entries());
    for (let i = 0; i < pendingEntries.length; i++) {
      const [, pending] = pendingEntries[i];
      clearTimeout(pending.timeout);
      pending.reject(new Error('Disconnected'));
    }
    this.pendingRequests.clear();

    if (this.state === 'connected' && this.options.autoReconnect) {
      this.scheduleReconnect();
    } else {
      this.setState('disconnected');
      this.emit('disconnected', error);
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return; // Already scheduled
    }

    this.reconnectAttempts++;
    this.setState('reconnecting');

    const delay = this.options.reconnectDelay * Math.min(this.reconnectAttempts, 5);
    this.log(`Scheduling reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.options.maxReconnectAttempts})`);

    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;

      try {
        await this.doConnect();
      } catch (err) {
        // doConnect will schedule another reconnect if appropriate
      }
    }, delay);
  }

  // ---------------------------------------------------------------------------
  // Data Handling
  // ---------------------------------------------------------------------------

  private handleData(data: Buffer): void {
    // Add to receive buffer
    this.receiveBuffer += data.toString();

    // Process complete lines (NDJSON)
    let newlineIndex: number;
    while ((newlineIndex = this.receiveBuffer.indexOf('\n')) !== -1) {
      const line = this.receiveBuffer.slice(0, newlineIndex).trim();
      this.receiveBuffer = this.receiveBuffer.slice(newlineIndex + 1);

      if (line) {
        this.processLine(line);
      }
    }
  }

  private processLine(line: string): void {
    const event = parseIPCEvent(line);

    if (!event) {
      this.log(`Failed to parse event: ${line.slice(0, 100)}`);
      return;
    }

    this.log(`Received: ${event.type}`);

    // Handle heartbeat
    if (event.type === 'heartbeat') {
      this.lastHeartbeat = event.ts;
      this.emit('heartbeat', event.ts);
      return;
    }

    // Handle response to pending request
    if (event.id && this.pendingRequests.has(event.id)) {
      const pending = this.pendingRequests.get(event.id)!;
      this.pendingRequests.delete(event.id);
      clearTimeout(pending.timeout);
      pending.resolve(event as IPCResponse);
      return;
    }

    // Emit as generic message
    this.emit('message', event);
  }

  // ---------------------------------------------------------------------------
  // Socket Writing
  // ---------------------------------------------------------------------------

  private writeToSocket(event: IPCEvent): boolean {
    if (!this.socket || !this.isConnected()) {
      return false;
    }

    const data = serializeIPCEvent(event);
    this.log(`Sending: ${event.type}`);

    try {
      return this.socket.write(data);
    } catch (err) {
      this.log(`Write error: ${err}`);
      return false;
    }
  }

  // ---------------------------------------------------------------------------
  // Offline Buffer Management
  // ---------------------------------------------------------------------------

  /**
   * Write an event to the offline buffer file
   *
   * Implements rotation strategy:
   * - If buffer > maxBufferSize (10MB), rotate to .bak
   * - All operations are O(1)
   */
  private writeToBuffer(event: IPCEvent): boolean {
    try {
      // Check if rotation is needed before writing
      this.rotateBufferIfNeeded();

      // Serialize and append to buffer file
      const data = serializeIPCEvent(event);
      fs.appendFileSync(this.bufferPath, data);
      this.log(`Buffered: ${event.type}`);
      return true;
    } catch (err) {
      this.log(`Buffer write error: ${err}`);
      this.emit('error', new Error(`Buffer write failed: ${err}`));
      return false;
    }
  }

  /**
   * Rotate buffer file if it exceeds max size
   *
   * Strategy (O(1) operations):
   * 1. Check current file size
   * 2. If > maxBufferSize:
   *    - Delete .bak file if exists
   *    - Rename current buffer to .bak
   *    - New writes go to fresh buffer file
   *
   * Result: We keep between 10MB and 20MB of history
   */
  private rotateBufferIfNeeded(): void {
    try {
      if (!fs.existsSync(this.bufferPath)) {
        return; // No buffer to rotate
      }

      const stats = fs.statSync(this.bufferPath);
      if (stats.size < this.options.maxBufferSize) {
        return; // Under limit, no rotation needed
      }

      this.log(`Buffer rotation triggered (size: ${stats.size} bytes)`);

      // Delete old backup if exists
      if (fs.existsSync(this.bufferBackupPath)) {
        fs.unlinkSync(this.bufferBackupPath);
        this.log('Deleted old backup buffer');
      }

      // Rename current buffer to backup
      fs.renameSync(this.bufferPath, this.bufferBackupPath);
      this.log('Rotated buffer to backup');
    } catch (err) {
      this.log(`Buffer rotation error: ${err}`);
    }
  }

  /**
   * Drain buffered events to the daemon on reconnect
   *
   * Reads buffer file line by line and sends to socket.
   * Deletes buffer file after successful drain.
   */
  private async drainBuffer(): Promise<void> {
    if (!this.options.enableBuffer || this.isDraining) {
      return;
    }

    // Check both buffer and backup files
    const filesToDrain: string[] = [];
    if (fs.existsSync(this.bufferBackupPath)) {
      filesToDrain.push(this.bufferBackupPath);
    }
    if (fs.existsSync(this.bufferPath)) {
      filesToDrain.push(this.bufferPath);
    }

    if (filesToDrain.length === 0) {
      this.log('No buffered events to drain');
      return;
    }

    this.isDraining = true;
    this.setState('draining');
    this.log(`Draining ${filesToDrain.length} buffer file(s)...`);

    let totalDrained = 0;
    let totalErrors = 0;

    for (const filePath of filesToDrain) {
      try {
        const content = fs.readFileSync(filePath, 'utf-8');
        const lines = content.split('\n').filter((line) => line.trim());

        this.log(`Draining ${lines.length} events from ${path.basename(filePath)}`);

        for (const line of lines) {
          const event = parseIPCEvent(line);
          if (event && this.socket) {
            try {
              this.socket.write(serializeIPCEvent(event));
              totalDrained++;
            } catch (err) {
              totalErrors++;
              this.log(`Drain write error: ${err}`);
            }
          }
        }

        // Delete the drained file
        fs.unlinkSync(filePath);
        this.log(`Deleted drained buffer: ${path.basename(filePath)}`);
      } catch (err) {
        this.log(`Drain error for ${filePath}: ${err}`);
      }
    }

    this.isDraining = false;
    this.setState('connected');
    this.log(`Drain complete: ${totalDrained} sent, ${totalErrors} errors`);
    this.emit('bufferDrained', { count: totalDrained, errors: totalErrors });
  }

  /**
   * Clear all buffer files (for testing/cleanup)
   */
  clearBuffer(): void {
    try {
      if (fs.existsSync(this.bufferPath)) {
        fs.unlinkSync(this.bufferPath);
      }
      if (fs.existsSync(this.bufferBackupPath)) {
        fs.unlinkSync(this.bufferBackupPath);
      }
      this.log('Cleared buffer files');
    } catch (err) {
      this.log(`Clear buffer error: ${err}`);
    }
  }

  /**
   * Scan and drain orphaned buffer files from previous sessions
   *
   * Called on startup to recover any events that were buffered
   * before a crash or unclean shutdown.
   */
  async drainOrphanedBuffers(): Promise<{ files: number; events: number }> {
    if (!this.options.enableBuffer || !this.isConnected()) {
      return { files: 0, events: 0 };
    }

    try {
      const bufferDir = this.options.bufferDir;
      if (!fs.existsSync(bufferDir)) {
        return { files: 0, events: 0 };
      }

      // Find all buffer-*.jsonl files except current session
      const files = fs.readdirSync(bufferDir).filter((f) => {
        return (
          f.startsWith('buffer-') &&
          (f.endsWith('.jsonl') || f.endsWith('.jsonl.bak')) &&
          !f.includes(this.sessionId)
        );
      });

      if (files.length === 0) {
        return { files: 0, events: 0 };
      }

      this.log(`Found ${files.length} orphaned buffer file(s)`);
      let totalEvents = 0;

      for (const file of files) {
        const filePath = path.join(bufferDir, file);
        try {
          const content = fs.readFileSync(filePath, 'utf-8');
          const lines = content.split('\n').filter((line) => line.trim());

          for (const line of lines) {
            const event = parseIPCEvent(line);
            if (event && this.socket) {
              this.socket.write(serializeIPCEvent(event));
              totalEvents++;
            }
          }

          // Delete the processed file
          fs.unlinkSync(filePath);
          this.log(`Drained orphaned buffer: ${file} (${lines.length} events)`);
        } catch (err) {
          this.log(`Error draining ${file}: ${err}`);
        }
      }

      return { files: files.length, events: totalEvents };
    } catch (err) {
      this.log(`Error scanning orphaned buffers: ${err}`);
      return { files: 0, events: 0 };
    }
  }

  // ---------------------------------------------------------------------------
  // Utilities
  // ---------------------------------------------------------------------------

  private setState(state: ConnectionState): void {
    if (this.state !== state) {
      this.log(`State: ${this.state} -> ${state}`);
      this.state = state;
      this.emit('stateChange', state);
    }
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${this.requestCounter++}`;
  }

  private log(message: string): void {
    if (this.options.debug) {
      console.log(`[IPCClient] ${message}`);
    }
  }
}

// =============================================================================
// SINGLETON EXPORT
// =============================================================================

/**
 * Default IPC client instance
 */
let defaultClient: IPCClient | null = null;

/**
 * Get or create the default IPC client
 */
export function getIPCClient(options?: IPCClientOptions): IPCClient {
  if (!defaultClient) {
    defaultClient = new IPCClient(options);
  }
  return defaultClient;
}

/**
 * Reset the default IPC client (for testing)
 */
export function resetIPCClient(): void {
  if (defaultClient) {
    defaultClient.disconnect();
    defaultClient = null;
  }
}
