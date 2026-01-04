/**
 * IPC Module Index
 *
 * Exports IPC client and related utilities for the Vidurai VS Code extension.
 *
 * @module ipc
 */

export {
  IPCClient,
  getIPCClient,
  resetIPCClient,
  type ConnectionState,
  type IPCClientOptions,
  type IPCClientEvents,
} from './Client';
