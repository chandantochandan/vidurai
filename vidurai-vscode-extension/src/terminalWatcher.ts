/**
 * Terminal Watcher
 * Tracks terminal commands and output
 * v2.1 - Uses IPC Named Pipe transport
 * v2.7 - Added shell integration events for command tracking (VS Code 1.93+)
 *
 * Phase 5: Reality Check integration - tracks command execution via shell integration
 */
import * as vscode from 'vscode';
import { IPCClient } from './ipc';
import { log, getConfig } from './utils';
import { IPCTerminalData } from './shared/events';
import { sanitize } from './security';

interface TerminalProcess {
    terminal: vscode.Terminal;
    command: string;
    output: string;
    startTime: number;
}

export class TerminalWatcher {
    private client: IPCClient;
    private disposables: vscode.Disposable[] = [];
    private activeProcesses: Map<number, TerminalProcess> = new Map();

    constructor(client: IPCClient) {
        this.client = client;
    }

    /**
     * Start watching terminal events
     */
    start(): void {
        const trackTerminal = getConfig('trackTerminal', true);

        if (!trackTerminal) {
            log('info', 'Terminal tracking disabled in settings');
            return;
        }

        log('info', 'Starting terminal watcher');

        // Watch terminal creation
        this.disposables.push(
            vscode.window.onDidOpenTerminal((terminal) => {
                this.onTerminalOpened(terminal);
            })
        );

        // Watch terminal close
        this.disposables.push(
            vscode.window.onDidCloseTerminal((terminal) => {
                this.onTerminalClosed(terminal);
            })
        );

        // v2.7 Phase 5: Shell integration events (VS Code 1.93+)
        // This API provides access to command execution without proposed APIs
        try {
            // Watch for command execution end (includes exit code)
            this.disposables.push(
                vscode.window.onDidEndTerminalShellExecution((event) => {
                    this.onCommandEnd(event);
                })
            );

            // Watch for command execution start
            this.disposables.push(
                vscode.window.onDidStartTerminalShellExecution((event) => {
                    this.onCommandStart(event);
                })
            );

            log('info', 'Terminal watcher started (shell integration enabled)');
        } catch (error: any) {
            // Shell integration API may not be available in older VS Code versions
            log('warn', `Shell integration API not available: ${error.message}`);
            log('info', 'Terminal watcher started (limited to terminal state)');
        }
    }

    /**
     * Stop watching
     */
    stop(): void {
        log('info', 'Stopping terminal watcher');

        this.activeProcesses.clear();
        this.disposables.forEach(d => d.dispose());
        this.disposables = [];
    }

    /**
     * Handle terminal opened
     */
    private onTerminalOpened(terminal: vscode.Terminal): void {
        log('debug', `Terminal opened: ${terminal.name}`);
    }

    /**
     * Handle terminal closed
     */
    private onTerminalClosed(terminal: vscode.Terminal): void {
        log('debug', `Terminal closed: ${terminal.name}`);
    }

    /**
     * v2.7 Phase 5: Handle command start (shell integration)
     * Tracks when a command begins execution
     */
    private async onCommandStart(event: vscode.TerminalShellExecutionStartEvent): Promise<void> {
        try {
            const execution = event.execution;
            const command = execution.commandLine?.value || '';

            if (!command) {
                return;
            }

            log('debug', `Command started: ${command}`);

            // Store start time for duration tracking
            // Use terminal processId as key (or name hash as fallback)
            const processId = await event.terminal.processId;
            const key = processId || event.terminal.name.length;
            this.activeProcesses.set(key, {
                terminal: event.terminal,
                command,
                output: '',
                startTime: Date.now()
            });
        } catch (error: any) {
            log('debug', `Command start tracking error: ${error.message}`);
        }
    }

    /**
     * v2.7 Phase 5: Handle command end (shell integration)
     * This is the main event for Reality Check - captures command + exit code
     */
    private async onCommandEnd(event: vscode.TerminalShellExecutionEndEvent): Promise<void> {
        try {
            const execution = event.execution;
            const command = execution.commandLine?.value || '';
            const exitCode = event.exitCode;

            if (!command) {
                return;
            }

            // Calculate duration if we tracked the start
            const processId = await event.terminal.processId;
            const key = processId || event.terminal.name.length;
            const startData = this.activeProcesses.get(key);
            const duration = startData ? Date.now() - startData.startTime : undefined;

            // Clean up tracking
            this.activeProcesses.delete(key);

            // Skip common noise commands
            if (this.isNoiseCommand(command)) {
                log('debug', `Skipping noise command: ${command}`);
                return;
            }

            log('debug', `Command ended: ${command} (exit: ${exitCode})`);

            // Try to read output using the read() API (VS Code 1.93+)
            let output = '';
            let errorOutput = '';

            try {
                // execution.read() returns an AsyncIterable of output strings
                const stream = execution.read();
                const chunks: string[] = [];

                for await (const chunk of stream) {
                    chunks.push(chunk);
                    // Limit output capture to prevent memory issues
                    if (chunks.join('').length > 2000) {
                        break;
                    }
                }

                const fullOutput = chunks.join('');

                // Split output and error based on exit code
                if (exitCode !== 0 && exitCode !== undefined) {
                    errorOutput = fullOutput.slice(0, 500);
                } else {
                    output = fullOutput.slice(0, 500);
                }
            } catch (readError: any) {
                // read() may not be available or may fail
                log('debug', `Could not read terminal output: ${readError.message}`);
            }

            // Send to daemon
            this.sendTerminalEvent(command, exitCode, output, errorOutput, duration);

        } catch (error: any) {
            log('error', `Command end tracking error: ${error.message}`);
        }
    }

    /**
     * Send terminal event via IPC
     * v2.7: Enhanced with shell integration data
     *
     * SECURITY: All output is sanitized via Gatekeeper before transmission.
     * No raw terminal output leaves the extension.
     */
    private sendTerminalEvent(
        command: string,
        exitCode: number | undefined,
        output: string,
        errorOutput: string,
        duration?: number
    ): void {
        try {
            // SECURITY: Sanitize command and output via Gatekeeper
            // This redacts API keys, secrets, PII before IPC transmission
            const sanitizedCmd = sanitize(command);
            const sanitizedOut = output ? sanitize(output) : { sanitized: '', totalRedactions: 0 };
            const sanitizedErr = errorOutput ? sanitize(errorOutput) : { sanitized: '', totalRedactions: 0 };

            // Log if secrets were redacted (for debugging/auditing)
            const totalRedactions = sanitizedCmd.totalRedactions + sanitizedOut.totalRedactions + sanitizedErr.totalRedactions;
            if (totalRedactions > 0) {
                log('info', `[Gatekeeper] Redacted ${totalRedactions} secret(s) from terminal event`);
            }

            const data: IPCTerminalData = {
                cmd: sanitizedCmd.sanitized,
                code: exitCode,
                out: sanitizedOut.sanitized || undefined,
                err: sanitizedErr.sanitized || undefined,
                dur: duration
            };

            const sent = this.client.sendEvent('terminal', data);

            if (sent) {
                log('debug', `Terminal event sent: ${sanitizedCmd.sanitized} (exit: ${exitCode})`);
            } else {
                log('warn', `Terminal event buffered (daemon offline): ${sanitizedCmd.sanitized}`);
            }

        } catch (error: any) {
            log('error', `Error sending terminal event: ${error.message}`);
        }
    }

    /**
     * Check if command is noise (common but not useful to track)
     */
    private isNoiseCommand(command: string): boolean {
        const noisePatterns = [
            /^cd\s*$/,       // cd without args
            /^ls$/,          // bare ls
            /^pwd$/,         // pwd
            /^clear$/,       // clear
            /^history/,      // history commands
            /^echo\s*$/,     // bare echo
        ];

        const trimmed = command.trim();
        return noisePatterns.some(pattern => pattern.test(trimmed));
    }

    /**
     * Manual command tracking (for backwards compatibility)
     * Users can call this via a command to log specific terminal commands
     * v2.1: Uses IPC Named Pipe transport with offline buffering
     */
    trackCommand(command: string, output: string, exitCode: number): void {
        this.sendTerminalEvent(command, exitCode, output, '', undefined);
    }
}
