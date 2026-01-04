/**
 * Focus Watcher - Phase 5 Reality Grounding
 * Tracks user focus (cursor position, selection) with debouncing
 * v2.7 - StateLinker integration via IPC
 *
 * Glass Box Protocol: Focus events are critical for Reality Grounding.
 * Debounce at 500ms to avoid flooding daemon during rapid navigation.
 */
import * as vscode from 'vscode';
import * as path from 'path';
import { IPCClient } from './ipc';
import { log, getConfig } from './utils';
import { IPCFocusData } from './shared/events';
import { sanitize } from './security';

const FOCUS_DEBOUNCE_MS = 500; // Phase 5 directive: 500ms debounce

export class FocusWatcher {
    private client: IPCClient;
    private focusTimer: NodeJS.Timeout | null = null;
    private disposables: vscode.Disposable[] = [];
    private lastSentFocus: string | null = null; // Dedup: file:line key

    constructor(client: IPCClient) {
        this.client = client;
    }

    /**
     * Start watching focus events
     */
    start(): void {
        log('info', 'Starting focus watcher (500ms debounce)');

        // Watch cursor/selection changes
        this.disposables.push(
            vscode.window.onDidChangeTextEditorSelection((event) => {
                this.onSelectionChange(event);
            })
        );

        // Watch active editor changes (file switch)
        this.disposables.push(
            vscode.window.onDidChangeActiveTextEditor((editor) => {
                this.onActiveEditorChange(editor);
            })
        );

        // Send initial focus if there's an active editor
        if (vscode.window.activeTextEditor) {
            this.sendFocusEvent(vscode.window.activeTextEditor);
        }

        log('info', 'Focus watcher started');
    }

    /**
     * Stop watching
     */
    stop(): void {
        log('info', 'Stopping focus watcher');

        // Clear debounce timer
        if (this.focusTimer) {
            clearTimeout(this.focusTimer);
            this.focusTimer = null;
        }

        // Dispose event handlers
        this.disposables.forEach(d => d.dispose());
        this.disposables = [];
    }

    /**
     * Handle selection change (cursor move, text selection)
     * Debounced to avoid flooding during rapid navigation
     */
    private onSelectionChange(event: vscode.TextEditorSelectionChangeEvent): void {
        const editor = event.textEditor;

        // Skip non-file documents
        if (editor.document.uri.scheme !== 'file') {
            return;
        }

        // Skip ignored paths
        if (this.shouldIgnoreFile(editor.document.uri.fsPath)) {
            return;
        }

        // Debounce: Clear existing timer
        if (this.focusTimer) {
            clearTimeout(this.focusTimer);
        }

        // Set new timer with 500ms debounce
        this.focusTimer = setTimeout(() => {
            this.sendFocusEvent(editor);
            this.focusTimer = null;
        }, FOCUS_DEBOUNCE_MS);
    }

    /**
     * Handle active editor change (file switch)
     * Send immediately when user switches files
     */
    private onActiveEditorChange(editor: vscode.TextEditor | undefined): void {
        if (!editor) {
            return;
        }

        // Skip non-file documents
        if (editor.document.uri.scheme !== 'file') {
            return;
        }

        // Skip ignored paths
        if (this.shouldIgnoreFile(editor.document.uri.fsPath)) {
            return;
        }

        // Clear any pending debounced update
        if (this.focusTimer) {
            clearTimeout(this.focusTimer);
            this.focusTimer = null;
        }

        // File switch is important - send immediately
        this.sendFocusEvent(editor, true);
    }

    /**
     * Send focus event via IPC
     * v2.7: StateLinker integration for Reality Grounding
     *
     * SECURITY: Selected text is sanitized via Gatekeeper before transmission.
     */
    private sendFocusEvent(editor: vscode.TextEditor, immediate: boolean = false): void {
        try {
            const document = editor.document;
            const selection = editor.selection;
            const filePath = document.uri.fsPath;

            // Get line and column (1-indexed for human readability)
            const line = selection.active.line + 1;
            const column = selection.active.character + 1;

            // Dedup check: Skip if same file:line (unless immediate)
            const focusKey = `${filePath}:${line}`;
            if (!immediate && focusKey === this.lastSentFocus) {
                log('debug', `Focus unchanged, skipping: ${focusKey}`);
                return;
            }
            this.lastSentFocus = focusKey;

            // Get selected text (truncate for bandwidth)
            let selectedText = '';
            if (!selection.isEmpty) {
                selectedText = document.getText(selection);
                if (selectedText.length > 500) {
                    selectedText = selectedText.substring(0, 500) + '...';
                }

                // SECURITY: Sanitize selected text via Gatekeeper
                // User may have selected text containing API keys, secrets, etc.
                const sanitized = sanitize(selectedText);
                selectedText = sanitized.sanitized;

                if (sanitized.totalRedactions > 0) {
                    log('info', `[Gatekeeper] Redacted ${sanitized.totalRedactions} secret(s) from selected text`);
                }
            }

            // Get project root
            const workspaceFolder = vscode.workspace.getWorkspaceFolder(document.uri);
            const projectRoot = workspaceFolder?.uri.fsPath;

            // Create focus data
            const data: IPCFocusData = {
                file: filePath,
                line,
                column,
                selection: selectedText || undefined,
                project_root: projectRoot
            };

            log('debug', `Sending focus: ${path.basename(filePath)}:${line}`);

            // Send via IPC (fire-and-forget, with offline buffer)
            const sent = this.client.sendEvent('focus', data);

            if (sent) {
                log('debug', `Focus sent: ${data.file}:${data.line}`);
            } else {
                log('debug', `Focus buffered (daemon offline): ${data.file}:${data.line}`);
            }

        } catch (error: any) {
            log('error', `Error sending focus: ${error.message}`);
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
