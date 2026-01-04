/**
 * File Watcher
 * Tracks file edits with debouncing and filtering
 * v2.1 - Uses IPC Named Pipe transport
 */
import * as vscode from 'vscode';
import * as path from 'path';
import { IPCClient } from './ipc';
import { log, getConfig } from './utils';
import { IPCFileEditData } from './shared/events';

export class FileWatcher {
    private client: IPCClient;
    private editTimers: Map<string, NodeJS.Timeout> = new Map();
    private disposables: vscode.Disposable[] = [];

    constructor(client: IPCClient) {
        this.client = client;
    }

    /**
     * Start watching file events
     */
    start(): void {
        log('info', 'Starting file watcher');

        // Watch text document changes (edits)
        this.disposables.push(
            vscode.workspace.onDidChangeTextDocument((event) => {
                this.onFileEdit(event);
            })
        );

        // Watch file saves
        this.disposables.push(
            vscode.workspace.onDidSaveTextDocument((document) => {
                this.onFileSave(document);
            })
        );

        log('info', 'File watcher started');
    }

    /**
     * Stop watching
     */
    stop(): void {
        log('info', 'Stopping file watcher');

        // Clear all debounce timers
        this.editTimers.forEach(timer => clearTimeout(timer));
        this.editTimers.clear();

        // Dispose event handlers
        this.disposables.forEach(d => d.dispose());
        this.disposables = [];
    }

    /**
     * Handle file edit (with debouncing)
     */
    private onFileEdit(event: vscode.TextDocumentChangeEvent): void {
        const document = event.document;

        // Skip untitled/unsaved documents
        if (document.uri.scheme !== 'file') {
            return;
        }

        const filePath = document.uri.fsPath;

        // Check if should ignore
        if (this.shouldIgnoreFile(filePath)) {
            return;
        }

        // Check file size
        const maxSize = getConfig('maxFileSize', 51200);
        const content = document.getText();

        if (maxSize > 0 && content.length > maxSize) {
            log('debug', `Ignoring large file: ${filePath} (${content.length} bytes)`);
            return;
        }

        // Debounce: Only send event after user stops typing
        const debounceMs = getConfig('debounceMs', 2000);

        // Clear existing timer for this file
        const existingTimer = this.editTimers.get(filePath);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        // Set new timer
        const timer = setTimeout(() => {
            this.sendFileEditEvent(filePath, content);
            this.editTimers.delete(filePath);
        }, debounceMs);

        this.editTimers.set(filePath, timer);
    }

    /**
     * Handle file save (immediate, no debounce)
     */
    private onFileSave(document: vscode.TextDocument): void {
        if (document.uri.scheme !== 'file') {
            return;
        }

        const filePath = document.uri.fsPath;

        if (this.shouldIgnoreFile(filePath)) {
            return;
        }

        log('debug', `File saved: ${filePath}`);

        // File save is important, send immediately
        // (This will also clear any pending debounced edit)
        const existingTimer = this.editTimers.get(filePath);
        if (existingTimer) {
            clearTimeout(existingTimer);
            this.editTimers.delete(filePath);
        }

        const content = document.getText();
        this.sendFileEditEvent(filePath, content);
    }

    /**
     * Send file edit event via IPC
     * v2.1: Uses Named Pipe transport with offline buffering
     */
    private sendFileEditEvent(filePath: string, content: string): void {
        try {
            log('debug', `Sending file edit: ${filePath}`);

            // Get project root from workspace
            const workspaceFolder = vscode.workspace.getWorkspaceFolder(vscode.Uri.file(filePath));
            const projectRoot = workspaceFolder?.uri.fsPath;

            // Detect language from file extension
            const ext = path.extname(filePath).toLowerCase();
            const languageMap: Record<string, string> = {
                '.ts': 'typescript', '.tsx': 'typescriptreact',
                '.js': 'javascript', '.jsx': 'javascriptreact',
                '.py': 'python', '.rb': 'ruby', '.go': 'go',
                '.rs': 'rust', '.java': 'java', '.cpp': 'cpp',
                '.c': 'c', '.cs': 'csharp', '.php': 'php',
                '.swift': 'swift', '.kt': 'kotlin',
                '.json': 'json', '.yaml': 'yaml', '.yml': 'yaml',
                '.md': 'markdown', '.html': 'html', '.css': 'css',
            };
            const language = languageMap[ext] || undefined;

            // Create lightweight IPC event data
            const data: IPCFileEditData = {
                file: projectRoot ? path.relative(projectRoot, filePath) : filePath,
                gist: `Edited ${path.basename(filePath)}`,  // Will be replaced by daemon
                change: 'save',
                lang: language,
                lines: content.split('\n').length,
            };

            // Send via IPC (fire-and-forget, with offline buffer)
            const sent = this.client.sendEvent('file_edit', data);

            if (sent) {
                log('debug', `File edit sent: ${data.file}`);
            } else {
                log('warn', `File edit buffered (daemon offline): ${data.file}`);
            }

        } catch (error: any) {
            log('error', `Error sending file edit: ${error.message}`);
        }
    }

    /**
     * Check if file should be ignored
     */
    private shouldIgnoreFile(filePath: string): boolean {
        const ignoredPaths = getConfig<string[]>('ignoredPaths', [
            'node_modules', '.git', 'dist', 'build', 'out', '.venv'
        ]);

        const normalized = filePath.replace(/\\/g, '/');

        for (const ignored of ignoredPaths) {
            if (normalized.includes(`/${ignored}/`) || normalized.includes(`/${ignored}`)) {
                return true;
            }
        }

        return false;
    }
}
