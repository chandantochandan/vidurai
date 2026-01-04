/**
 * Memory TreeView for VS Code Sidebar
 * v2.1 - Uses IPC Named Pipe transport
 */
import * as vscode from 'vscode';
import { IPCClient } from '../ipc';

interface Memory {
    id: number;
    gist: string;
    salience: string;
    created_at: string;
    file_path?: string;
    event_type: string;
}

export class MemoryTreeDataProvider implements vscode.TreeDataProvider<MemoryTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<MemoryTreeItem | undefined | null | void> =
        new vscode.EventEmitter<MemoryTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<MemoryTreeItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    constructor(
        private context: vscode.ExtensionContext,
        private client: IPCClient
    ) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: MemoryTreeItem): vscode.TreeItem {
        return element;
    }

    async getChildren(element?: MemoryTreeItem): Promise<MemoryTreeItem[]> {
        if (!vscode.workspace.workspaceFolders) {
            return [];
        }

        if (!element) {
            // Root level: show categories
            return [
                new MemoryTreeItem('🕐 Recent (24h)', 'recent', vscode.TreeItemCollapsibleState.Expanded),
                new MemoryTreeItem('🔥 Critical', 'critical', vscode.TreeItemCollapsibleState.Collapsed),
                new MemoryTreeItem('⚡ High Priority', 'high', vscode.TreeItemCollapsibleState.Collapsed),
                new MemoryTreeItem('📊 Statistics', 'stats', vscode.TreeItemCollapsibleState.None),
            ];
        }

        // Get memories for category
        if (element.category === 'stats') {
            return await this.getStatisticsItems();
        }

        const memories = await this.getMemoriesForCategory(element.category);
        return memories.map(mem => new MemoryTreeItem(
            this.formatMemoryLabel(mem),
            'memory',
            vscode.TreeItemCollapsibleState.None,
            mem
        ));
    }

    private async getMemoriesForCategory(category: string): Promise<Memory[]> {
        if (!this.client.isConnected()) {
            return [];
        }

        try {
            // v2.1: Use IPC recall endpoint with category filter
            const response = await this.client.send<{
                category: string;
                limit: number;
            }, { memories: Memory[] }>('recall', {
                category,
                limit: category === 'recent' ? 20 : 10,
            });

            if (response.ok && response.data?.memories) {
                return response.data.memories;
            }

            return [];
        } catch (error: any) {
            console.error('Error fetching memories:', error);
            return [];
        }
    }

    private async getStatisticsItems(): Promise<MemoryTreeItem[]> {
        if (!this.client.isConnected()) {
            return [new MemoryTreeItem(
                'Not connected to daemon',
                'stat',
                vscode.TreeItemCollapsibleState.None
            )];
        }

        try {
            const response = await this.client.send<void, {
                count: number;
                by_salience?: Record<string, number>;
            }>('stats');

            if (response.ok && response.data) {
                const stats = response.data;
                const items: MemoryTreeItem[] = [];

                // Total
                items.push(new MemoryTreeItem(
                    `Total Memories: ${stats.count}`,
                    'stat',
                    vscode.TreeItemCollapsibleState.None
                ));

                // By salience
                if (stats.by_salience) {
                    Object.entries(stats.by_salience).forEach(([salience, count]) => {
                        items.push(new MemoryTreeItem(
                            `${this.getSalienceIcon(salience)} ${salience}: ${count}`,
                            'stat',
                            vscode.TreeItemCollapsibleState.None
                        ));
                    });
                }

                return items;
            }

            return [];
        } catch (error: any) {
            console.error('Error fetching statistics:', error);
            return [];
        }
    }

    private formatMemoryLabel(mem: Memory): string {
        const ageStr = this.calculateAgeString(mem.created_at);
        return `${this.getSalienceIcon(mem.salience)} ${mem.gist.substring(0, 60)}... (${ageStr})`;
    }

    private getSalienceIcon(salience: string): string {
        const icons: Record<string, string> = {
            'CRITICAL': '🔥',
            'HIGH': '⚡',
            'MEDIUM': '📝',
            'LOW': '💬',
            'NOISE': '🔇'
        };
        return icons[salience] || '📌';
    }

    private calculateAgeString(createdAt: string): string {
        const created = new Date(createdAt);
        const now = new Date();
        const diffMs = now.getTime() - created.getTime();
        const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

        if (diffDays === 0) {
            const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
            if (diffHours === 0) {
                const diffMins = Math.floor(diffMs / (1000 * 60));
                return `${diffMins}m ago`;
            }
            return `${diffHours}h ago`;
        } else if (diffDays === 1) {
            return '1d ago';
        } else {
            return `${diffDays}d ago`;
        }
    }
}

export class MemoryTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly category: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly memory?: Memory
    ) {
        super(label, collapsibleState);

        if (memory) {
            this.tooltip = this.formatTooltip(memory);
            this.contextValue = 'memory';
            this.command = {
                command: 'vidurai.showMemoryDetails',
                title: 'Show Details',
                arguments: [memory]
            };
        } else if (category === 'stat') {
            this.contextValue = 'stat';
        } else {
            this.contextValue = 'category';
        }
    }

    private formatTooltip(mem: Memory): string {
        let tooltip = `${mem.gist}\n\n`;
        tooltip += `Salience: ${mem.salience}\n`;
        if (mem.file_path) {
            tooltip += `File: ${mem.file_path}\n`;
        }
        tooltip += `Created: ${new Date(mem.created_at).toLocaleString()}`;
        return tooltip;
    }
}

export function registerMemoryTreeView(
    context: vscode.ExtensionContext,
    client: IPCClient
): vscode.TreeView<MemoryTreeItem> {
    const treeDataProvider = new MemoryTreeDataProvider(context, client);
    const treeView = vscode.window.createTreeView('viduraiMemory', {
        treeDataProvider,
        showCollapseAll: true
    });

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.refreshMemories', () => {
            treeDataProvider.refresh();
        }),

        vscode.commands.registerCommand('vidurai.showMemoryDetails', (memory: Memory) => {
            showMemoryDetailsPanel(memory, context);
        }),

        vscode.commands.registerCommand('vidurai.copyMemoryContext', async (memory: Memory) => {
            await vscode.env.clipboard.writeText(memory.gist);
            vscode.window.showInformationMessage('Memory copied to clipboard');
        })
    );

    return treeView;
}

function showMemoryDetailsPanel(memory: Memory, context: vscode.ExtensionContext) {
    const panel = vscode.window.createWebviewPanel(
        'viduraiMemoryDetails',
        `Memory: ${memory.gist.substring(0, 50)}...`,
        vscode.ViewColumn.Two,
        { enableScripts: true }
    );

    panel.webview.html = getMemoryDetailsHTML(memory);
}

function getMemoryDetailsHTML(memory: Memory): string {
    return `<!DOCTYPE html>
<html>
<head>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
        }
        h1 { color: var(--vscode-textLink-foreground); }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .critical { background: #ff4444; color: white; }
        .high { background: #ff9800; color: white; }
        .medium { background: #2196f3; color: white; }
        .low { background: #4caf50; color: white; }
        .section { margin: 20px 0; }
        .label { font-weight: bold; color: var(--vscode-textLink-foreground); }
        pre {
            background: var(--vscode-textBlockQuote-background);
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <h1>${memory.gist}</h1>
    <span class="badge ${memory.salience.toLowerCase()}">${memory.salience}</span>

    <div class="section">
        <div class="label">Type:</div>
        ${memory.event_type}
    </div>

    ${memory.file_path ? `
    <div class="section">
        <div class="label">File:</div>
        <code>${memory.file_path}</code>
    </div>
    ` : ''}

    <div class="section">
        <div class="label">Created:</div>
        ${new Date(memory.created_at).toLocaleString()}
    </div>
</body>
</html>`;
}
