/**
 * Diagnostic Watcher
 * Tracks errors and warnings from VS Code diagnostics
 * v2.1 - Uses IPC Named Pipe transport
 */
import * as vscode from 'vscode';
import * as path from 'path';
import { IPCClient } from './ipc';
import { log, getConfig } from './utils';
import { IPCDiagnosticData } from './shared/events';

export class DiagnosticWatcher {
    private client: IPCClient;
    private disposables: vscode.Disposable[] = [];
    private processedDiagnostics: Set<string> = new Set();

    constructor(client: IPCClient) {
        this.client = client;
    }

    /**
     * Start watching diagnostics
     */
    start(): void {
        const trackDiagnostics = getConfig('trackDiagnostics', true);

        if (!trackDiagnostics) {
            log('info', 'Diagnostic tracking disabled in settings');
            return;
        }

        log('info', 'Starting diagnostic watcher');

        // Watch diagnostic changes
        this.disposables.push(
            vscode.languages.onDidChangeDiagnostics((event) => {
                this.onDiagnosticsChanged(event);
            })
        );

        log('info', 'Diagnostic watcher started');
    }

    /**
     * Stop watching
     */
    stop(): void {
        log('info', 'Stopping diagnostic watcher');

        this.processedDiagnostics.clear();
        this.disposables.forEach(d => d.dispose());
        this.disposables = [];
    }

    /**
     * Handle diagnostic changes
     */
    private onDiagnosticsChanged(event: vscode.DiagnosticChangeEvent): void {
        for (const uri of event.uris) {
            // Only process file URIs
            if (uri.scheme !== 'file') {
                continue;
            }

            const diagnostics = vscode.languages.getDiagnostics(uri);
            this.processDiagnostics(uri, diagnostics);
        }
    }

    /**
     * Process diagnostics for a file
     */
    private processDiagnostics(uri: vscode.Uri, diagnostics: vscode.Diagnostic[]): void {
        const filePath = uri.fsPath;

        for (const diagnostic of diagnostics) {
            // Only track errors and warnings (ignore info/hints)
            if (diagnostic.severity > vscode.DiagnosticSeverity.Warning) {
                continue;
            }

            // Create unique ID for this diagnostic
            const diagId = `${filePath}:${diagnostic.range.start.line}:${diagnostic.message}`;

            // Skip if already processed
            if (this.processedDiagnostics.has(diagId)) {
                continue;
            }

            // Mark as processed
            this.processedDiagnostics.add(diagId);

            // Send to bridge
            this.sendDiagnosticEvent(filePath, diagnostic);

            // Clean up old processed diagnostics (keep last 1000)
            if (this.processedDiagnostics.size > 1000) {
                const toDelete = Array.from(this.processedDiagnostics).slice(0, 100);
                toDelete.forEach(id => this.processedDiagnostics.delete(id));
            }
        }
    }

    /**
     * Send diagnostic event via IPC
     * v2.1: Uses Named Pipe transport with offline buffering
     */
    private sendDiagnosticEvent(
        filePath: string,
        diagnostic: vscode.Diagnostic
    ): void {
        try {
            // Map VS Code severity to IPC severity (0=error, 1=warning, 2=info, 3=hint)
            const severityMap: Record<vscode.DiagnosticSeverity, 0 | 1 | 2 | 3> = {
                [vscode.DiagnosticSeverity.Error]: 0,
                [vscode.DiagnosticSeverity.Warning]: 1,
                [vscode.DiagnosticSeverity.Information]: 2,
                [vscode.DiagnosticSeverity.Hint]: 3,
            };

            const data: IPCDiagnosticData = {
                file: filePath,
                sev: severityMap[diagnostic.severity],
                msg: diagnostic.message,
                ln: diagnostic.range.start.line + 1,
                src: diagnostic.source,
            };

            log('debug', `Sending diagnostic: sev=${data.sev} in ${path.basename(filePath)}`);

            const sent = this.client.sendEvent('diagnostic', data);

            if (sent) {
                log('debug', `Diagnostic sent: ${data.msg.slice(0, 50)}...`);
            } else {
                log('warn', `Diagnostic buffered (daemon offline): ${path.basename(filePath)}`);
            }

        } catch (error: any) {
            log('error', `Error sending diagnostic: ${error.message}`);
        }
    }
}
