/**
 * ContextPanel - Glass Box Dashboard
 *
 * v2.2: Webview Panel that visualizes the daemon's internal state.
 * Shows pinned context, active errors, and AI context budget.
 *
 * "Trust through transparency" - Users can see exactly what the AI sees.
 */

import * as vscode from 'vscode';

/**
 * Data structure for context updates
 */
export interface ContextPanelData {
    pinned: Array<{
        file_path: string;
        reason?: string;
        pinned_at?: string;
    }>;
    active_errors: Array<{
        file_path: string;
        error_count: number;
        warning_count: number;
        error_summary?: string;
    }>;
    token_budget: {
        used: number;
        total: number;
    };
    last_updated: string;
}

/**
 * WebviewViewProvider for the Context Dashboard
 */
export class ContextPanelProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'vidurai.contextView';

    private _view?: vscode.WebviewView;
    private _data: ContextPanelData = {
        pinned: [],
        active_errors: [],
        token_budget: { used: 0, total: 8000 },
        last_updated: new Date().toISOString()
    };

    constructor(private readonly _extensionUri: vscode.Uri) {}

    /**
     * Resolve the webview view
     */
    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlContent();

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage((message) => {
            switch (message.type) {
                case 'refresh':
                    vscode.commands.executeCommand('vidurai.refreshContextPanel');
                    break;
                case 'openFile':
                    if (message.path) {
                        vscode.workspace.openTextDocument(message.path).then(doc => {
                            vscode.window.showTextDocument(doc);
                        });
                    }
                    break;
                case 'unpin':
                    if (message.path) {
                        vscode.commands.executeCommand('vidurai.unpinFile', vscode.Uri.file(message.path));
                    }
                    break;
            }
        });
    }

    /**
     * Update the panel with new data
     */
    public updateData(data: Partial<ContextPanelData>): void {
        this._data = { ...this._data, ...data, last_updated: new Date().toISOString() };

        if (this._view) {
            this._view.webview.postMessage({
                type: 'update',
                data: this._data
            });
        }
    }

    /**
     * Refresh the HTML content
     */
    public refresh(): void {
        if (this._view) {
            this._view.webview.html = this._getHtmlContent();
        }
    }

    /**
     * Get current data
     */
    public getData(): ContextPanelData {
        return this._data;
    }

    /**
     * Generate HTML content for the webview
     */
    private _getHtmlContent(): string {
        const data = this._data;
        const tokenPercent = Math.min(100, Math.round((data.token_budget.used / data.token_budget.total) * 100));
        const tokenColor = tokenPercent > 80 ? '#e74c3c' : tokenPercent > 50 ? '#f39c12' : '#27ae60';

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vidurai Context</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background-color: var(--vscode-sideBar-background);
            padding: 12px;
            line-height: 1.4;
        }

        .section {
            margin-bottom: 16px;
            background: var(--vscode-editor-background);
            border-radius: 6px;
            padding: 12px;
            border: 1px solid var(--vscode-widget-border);
        }

        .section-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 10px;
            font-weight: 600;
            font-size: 13px;
        }

        .section-icon {
            font-size: 16px;
        }

        .badge {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 11px;
            margin-left: auto;
        }

        .item {
            display: flex;
            align-items: center;
            padding: 6px 8px;
            margin: 4px 0;
            background: var(--vscode-list-hoverBackground);
            border-radius: 4px;
            cursor: pointer;
            transition: background 0.15s;
        }

        .item:hover {
            background: var(--vscode-list-activeSelectionBackground);
        }

        .item-icon {
            margin-right: 8px;
            opacity: 0.8;
        }

        .item-text {
            flex: 1;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 12px;
        }

        .item-meta {
            font-size: 11px;
            opacity: 0.7;
            margin-left: 8px;
        }

        .item-action {
            opacity: 0;
            margin-left: 8px;
            cursor: pointer;
            padding: 2px 4px;
            border-radius: 3px;
        }

        .item:hover .item-action {
            opacity: 0.7;
        }

        .item-action:hover {
            opacity: 1 !important;
            background: var(--vscode-button-background);
        }

        .error-item {
            border-left: 3px solid #e74c3c;
        }

        .warning-item {
            border-left: 3px solid #f39c12;
        }

        .progress-container {
            margin-top: 8px;
        }

        .progress-bar {
            height: 8px;
            background: var(--vscode-progressBar-background);
            border-radius: 4px;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            transition: width 0.3s ease;
        }

        .progress-text {
            display: flex;
            justify-content: space-between;
            font-size: 11px;
            margin-top: 4px;
            opacity: 0.8;
        }

        .empty-state {
            text-align: center;
            padding: 16px;
            opacity: 0.6;
            font-size: 12px;
        }

        .empty-state-icon {
            font-size: 24px;
            margin-bottom: 8px;
        }

        .refresh-btn {
            display: block;
            width: 100%;
            padding: 8px;
            margin-top: 12px;
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }

        .refresh-btn:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }

        .timestamp {
            font-size: 10px;
            opacity: 0.5;
            text-align: center;
            margin-top: 8px;
        }
    </style>
</head>
<body>
    <!-- AI Context Budget -->
    <div class="section">
        <div class="section-header">
            <span class="section-icon">🧠</span>
            <span>AI Context Budget</span>
        </div>
        <div class="progress-container">
            <div class="progress-bar">
                <div class="progress-fill" id="tokenProgress" style="width: ${tokenPercent}%; background: ${tokenColor};"></div>
            </div>
            <div class="progress-text">
                <span id="tokenUsed">${data.token_budget.used.toLocaleString()} tokens used</span>
                <span id="tokenTotal">${data.token_budget.total.toLocaleString()} max</span>
            </div>
        </div>
    </div>

    <!-- Pinned Context -->
    <div class="section">
        <div class="section-header">
            <span class="section-icon">📌</span>
            <span>Pinned Context</span>
            <span class="badge" id="pinnedCount">${data.pinned.length}</span>
        </div>
        <div id="pinnedList">
            ${data.pinned.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-icon">📌</div>
                    <div>No pinned files</div>
                    <div style="margin-top: 4px; font-size: 11px;">Right-click a file to pin it</div>
                </div>
            ` : data.pinned.map(pin => `
                <div class="item" onclick="openFile('${this._escapeHtml(pin.file_path)}')">
                    <span class="item-icon">📄</span>
                    <span class="item-text" title="${this._escapeHtml(pin.file_path)}">${this._getFileName(pin.file_path)}</span>
                    ${pin.reason ? `<span class="item-meta">${this._escapeHtml(pin.reason)}</span>` : ''}
                    <span class="item-action" onclick="event.stopPropagation(); unpinFile('${this._escapeHtml(pin.file_path)}')" title="Unpin">✕</span>
                </div>
            `).join('')}
        </div>
    </div>

    <!-- Active Errors -->
    <div class="section">
        <div class="section-header">
            <span class="section-icon">🔴</span>
            <span>Active Errors</span>
            <span class="badge" id="errorCount">${data.active_errors.length}</span>
        </div>
        <div id="errorList">
            ${data.active_errors.length === 0 ? `
                <div class="empty-state">
                    <div class="empty-state-icon">✅</div>
                    <div>No active errors</div>
                    <div style="margin-top: 4px; font-size: 11px;">Your project is clean!</div>
                </div>
            ` : data.active_errors.map(error => `
                <div class="item ${error.error_count > 0 ? 'error-item' : 'warning-item'}" onclick="openFile('${this._escapeHtml(error.file_path)}')">
                    <span class="item-icon">${error.error_count > 0 ? '❌' : '⚠️'}</span>
                    <span class="item-text" title="${this._escapeHtml(error.file_path)}">${this._getFileName(error.file_path)}</span>
                    <span class="item-meta">
                        ${error.error_count > 0 ? `${error.error_count} error${error.error_count > 1 ? 's' : ''}` : ''}
                        ${error.warning_count > 0 ? `${error.warning_count} warning${error.warning_count > 1 ? 's' : ''}` : ''}
                    </span>
                </div>
            `).join('')}
        </div>
    </div>

    <button class="refresh-btn" onclick="refresh()">🔄 Refresh</button>
    <div class="timestamp" id="timestamp">Updated: ${new Date(data.last_updated).toLocaleTimeString()}</div>

    <script>
        const vscode = acquireVsCodeApi();

        function refresh() {
            vscode.postMessage({ type: 'refresh' });
        }

        function openFile(path) {
            vscode.postMessage({ type: 'openFile', path: path });
        }

        function unpinFile(path) {
            vscode.postMessage({ type: 'unpin', path: path });
        }

        // Handle updates from extension
        window.addEventListener('message', event => {
            const message = event.data;
            if (message.type === 'update') {
                updateUI(message.data);
            }
        });

        function updateUI(data) {
            // Update token budget
            const tokenPercent = Math.min(100, Math.round((data.token_budget.used / data.token_budget.total) * 100));
            const tokenColor = tokenPercent > 80 ? '#e74c3c' : tokenPercent > 50 ? '#f39c12' : '#27ae60';
            document.getElementById('tokenProgress').style.width = tokenPercent + '%';
            document.getElementById('tokenProgress').style.background = tokenColor;
            document.getElementById('tokenUsed').textContent = data.token_budget.used.toLocaleString() + ' tokens used';
            document.getElementById('tokenTotal').textContent = data.token_budget.total.toLocaleString() + ' max';

            // Update counts
            document.getElementById('pinnedCount').textContent = data.pinned.length;
            document.getElementById('errorCount').textContent = data.active_errors.length;

            // Update timestamp
            document.getElementById('timestamp').textContent = 'Updated: ' + new Date(data.last_updated).toLocaleTimeString();
        }
    </script>
</body>
</html>`;
    }

    /**
     * Escape HTML special characters
     */
    private _escapeHtml(str: string): string {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;')
            .replace(/\\/g, '\\\\');
    }

    /**
     * Get just the filename from a path
     */
    private _getFileName(filePath: string): string {
        return filePath.split(/[/\\]/).pop() || filePath;
    }
}
