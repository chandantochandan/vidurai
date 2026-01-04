/**
 * Vidurai VS Code Extension
 * Main entry point
 * v2.1 - IPC Named Pipe Transport (replaces legacy PythonBridge)
 */
import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';
import { IPCClient, getIPCClient } from './ipc';
import { StatusBarManager } from './statusBar';
import { log, getConfig, getOutputChannel } from './utils';
import { FileWatcher } from './fileWatcher';
import { TerminalWatcher } from './terminalWatcher';
import { DiagnosticWatcher } from './diagnosticWatcher';
import { FocusWatcher } from './focusWatcher';
import { registerMemoryTreeView } from './views/memoryTreeView';
import { PinDecorator } from './decorators/PinDecorator';
import { ContextPanelProvider, ContextPanelData } from './views/ContextPanel';

let ipcClient: IPCClient | null = null;
let statusBar: StatusBarManager | null = null;
let fileWatcher: FileWatcher | null = null;
let terminalWatcher: TerminalWatcher | null = null;
let diagnosticWatcher: DiagnosticWatcher | null = null;
let focusWatcher: FocusWatcher | null = null;
let memoryTreeView: vscode.TreeView<any> | null = null;
let pinDecorator: PinDecorator | null = null;
let contextPanelProvider: ContextPanelProvider | null = null;
let contextPollInterval: NodeJS.Timeout | null = null;

/**
 * Extension activation
 */
export async function activate(context: vscode.ExtensionContext) {
    log('info', 'Vidurai extension activating...');

    // Check if first run
    const isFirstRun = !context.globalState.get('vidurai.hasRun');

    if (isFirstRun) {
        await showWelcome(context);
    }

    // Check if enabled
    const enabled = getConfig('enabled', true);
    if (!enabled) {
        log('info', 'Vidurai is disabled in settings');
        return;
    }

    try {
        // v2.1: Initialize IPC Client (connects to daemon via Named Pipe)
        ipcClient = getIPCClient({ debug: getConfig('debug', false) });

        // Set up IPC event handlers
        ipcClient.on('connected', () => {
            log('info', 'Connected to Vidurai daemon');
            statusBar?.update();
        });

        ipcClient.on('disconnected', (error) => {
            log('warn', `Disconnected from daemon: ${error?.message || 'unknown'}`);
            statusBar?.update();
        });

        ipcClient.on('error', (error) => {
            log('error', `IPC error: ${error.message}`);
        });

        ipcClient.on('heartbeat', (ts) => {
            log('debug', `Heartbeat received: ${ts}`);
        });

        // Attempt connection (non-blocking - will auto-reconnect)
        ipcClient.connect().catch((error) => {
            log('warn', `Initial connection failed (daemon may not be running): ${error.message}`);
            vscode.window.showWarningMessage(
                '⚠️ Vidurai daemon not detected. Events will be buffered until daemon starts.',
                'View Logs'
            ).then(choice => {
                if (choice === 'View Logs') {
                    getOutputChannel().show();
                }
            });
        });

        // Start status bar
        statusBar = new StatusBarManager(ipcClient);
        statusBar.startUpdates();

        // Register commands
        registerCommands(context);

        // v2.0: Register TreeView
        memoryTreeView = registerMemoryTreeView(context, ipcClient);
        log('info', 'Memory TreeView registered');

        // v2.2: Register Pin Decorator
        pinDecorator = new PinDecorator();
        context.subscriptions.push(
            vscode.window.registerFileDecorationProvider(pinDecorator)
        );
        log('info', 'Pin Decorator registered');

        // Sync pins from daemon on startup
        syncPinsFromDaemon();

        // v2.2: Register Context Panel (Glass Box Dashboard)
        contextPanelProvider = new ContextPanelProvider(context.extensionUri);
        context.subscriptions.push(
            vscode.window.registerWebviewViewProvider(
                ContextPanelProvider.viewType,
                contextPanelProvider
            )
        );
        log('info', 'Context Panel registered');

        // Start context polling (every 5 seconds)
        startContextPolling();

        // Start watchers (now using IPC transport)
        fileWatcher = new FileWatcher(ipcClient);
        fileWatcher.start();

        terminalWatcher = new TerminalWatcher(ipcClient);
        terminalWatcher.start();

        diagnosticWatcher = new DiagnosticWatcher(ipcClient);
        diagnosticWatcher.start();

        // v2.7 Phase 5: Focus watcher for Reality Grounding (StateLinker)
        focusWatcher = new FocusWatcher(ipcClient);
        focusWatcher.start();

        // v2.0 Phase 2: Write active project for MCP server/ChatGPT extension
        writeActiveProject();
        context.subscriptions.push(
            vscode.workspace.onDidChangeWorkspaceFolders(writeActiveProject)
        );

        // Drain any orphaned buffers from previous sessions
        if (ipcClient.isConnected()) {
            ipcClient.drainOrphanedBuffers().then((result) => {
                if (result.events > 0) {
                    log('info', `Drained ${result.events} events from ${result.files} orphaned buffer(s)`);
                }
            });
        }

        log('info', 'Vidurai extension activated successfully (v2.1 IPC transport)');

    } catch (error: any) {
        log('error', `Activation failed: ${error.message}`);

        vscode.window.showWarningMessage(
            `⚠️ Vidurai failed to start: ${error.message}`,
            'View Logs',
            'Disable Extension'
        ).then(choice => {
            if (choice === 'View Logs') {
                getOutputChannel().show();
            } else if (choice === 'Disable Extension') {
                vscode.workspace.getConfiguration('vidurai').update('enabled', false, true);
            }
        });
    }
}

/**
 * Extension deactivation
 */
export function deactivate() {
    log('info', 'Vidurai extension deactivating...');

    // Stop watchers
    if (fileWatcher) {
        fileWatcher.stop();
        fileWatcher = null;
    }

    if (terminalWatcher) {
        terminalWatcher.stop();
        terminalWatcher = null;
    }

    if (diagnosticWatcher) {
        diagnosticWatcher.stop();
        diagnosticWatcher = null;
    }

    // v2.7: Stop focus watcher
    if (focusWatcher) {
        focusWatcher.stop();
        focusWatcher = null;
    }

    // v2.1: Disconnect IPC client (does not stop daemon)
    if (ipcClient) {
        ipcClient.disconnect();
        ipcClient = null;
    }

    if (statusBar) {
        statusBar.dispose();
        statusBar = null;
    }

    if (memoryTreeView) {
        memoryTreeView.dispose();
        memoryTreeView = null;
    }

    if (pinDecorator) {
        pinDecorator.dispose();
        pinDecorator = null;
    }

    // v2.2: Stop context polling
    if (contextPollInterval) {
        clearInterval(contextPollInterval);
        contextPollInterval = null;
    }

    contextPanelProvider = null;
}

/**
 * Write active project path for MCP server and browser extensions
 * v2.0 Phase 2
 */
function writeActiveProject() {
    const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
    if (!projectPath) {
        log('debug', 'No workspace folder open, skipping active project write');
        return;
    }

    try {
        const viduraiDir = path.join(os.homedir(), '.vidurai');
        const activeFile = path.join(viduraiDir, 'active-project.txt');

        // Ensure directory exists
        if (!fs.existsSync(viduraiDir)) {
            fs.mkdirSync(viduraiDir, { recursive: true });
        }

        // Write project path
        fs.writeFileSync(activeFile, projectPath, 'utf-8');

        log('info', `Active project updated: ${projectPath}`);
    } catch (error: any) {
        log('error', `Failed to write active project: ${error.message}`);
    }
}

/**
 * Show welcome message on first run
 */
async function showWelcome(context: vscode.ExtensionContext) {
    const choice = await vscode.window.showInformationMessage(
        '👋 Welcome to Vidurai! Set up intelligent AI memory management?',
        'Quick Setup',
        'Manual Setup',
        'Later'
    );

    if (choice === 'Quick Setup') {
        // v2.1: Daemon runs separately - just mark as run
        context.globalState.update('vidurai.hasRun', true);
    } else if (choice === 'Manual Setup') {
        vscode.env.openExternal(vscode.Uri.parse('https://docs.vidurai.ai/setup'));
        context.globalState.update('vidurai.hasRun', true);
    }
}

/**
 * Register commands
 */
function registerCommands(context: vscode.ExtensionContext) {
    // Command: Copy Context
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.copyContext', async () => {
            await copyContext();
        })
    );

    // Command: Reconnect IPC
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.restartBridge', async () => {
            if (ipcClient) {
                ipcClient.disconnect();
                try {
                    await ipcClient.connect();
                    vscode.window.showInformationMessage('✅ Reconnected to Vidurai daemon');
                } catch (error: any) {
                    vscode.window.showWarningMessage(`⚠️ Failed to reconnect: ${error.message}`);
                }
            }
        })
    );

    // Command: Show Logs
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.showLogs', () => {
            getOutputChannel().show();
        })
    );

    // v2.1: Command: Get Current State (Oracle)
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.getContext', async () => {
            await getProjectContext();
        })
    );

    // v2.1: Command: Get AI Context (XML format for AI assistants)
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.getAIContext', async () => {
            await getProjectContext('ai');
        })
    );

    // v2.2: Command: Get Manager Summary
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.copyContextManager', async () => {
            await getProjectContext('manager');
        })
    );

    // v2.2: Command: Pin File
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.pinFile', async (uri?: vscode.Uri) => {
            await pinFile(uri);
        })
    );

    // v2.2: Command: Unpin File
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.unpinFile', async (uri?: vscode.Uri) => {
            await unpinFile(uri);
        })
    );

    // v2.2: Command: Refresh Context Panel
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.refreshContextPanel', async () => {
            await refreshContextPanel();
        })
    );

    // v2.3: Command: Switch Profile (Memory HUD)
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.switchProfile', async () => {
            if (statusBar) {
                await statusBar.showProfileSwitcher();
            }
        })
    );

    // v2.3: Command: Generate Standup (Standup Generator)
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.generateStandup', async () => {
            await generateStandup();
        })
    );

    // v2.5: Command: Generate Manager Report (opens in new document)
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.generateManagerReport', async () => {
            await generateReport('manager');
        })
    );

    // v2.5: Command: Generate AI Context XML (opens in new document)
    context.subscriptions.push(
        vscode.commands.registerCommand('vidurai.generateAIContext', async () => {
            await generateReport('ai');
        })
    );
}

/**
 * Copy relevant context to clipboard
 */
async function copyContext() {
    if (!ipcClient || !ipcClient.isConnected()) {
        vscode.window.showErrorMessage('⚠️ Not connected to Vidurai daemon');
        return;
    }

    try {
        // v2.5: Context Guard - Always inject project_path for proper routing
        // Rule: Handle undefined gracefully (send undefined, don't throw)
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? undefined;

        // Recall memories via IPC
        const response = await ipcClient.send<{
            query: string;
            maxTokens?: number;
            project_path?: string;
        }, {
            context: string;
            count: number;
            tokens: number;
        }>('context', { query: '', maxTokens: 4000, project_path: projectPath });

        if (!response.ok || !response.data) {
            vscode.window.showErrorMessage(`❌ Failed to recall context: ${response.error || 'Unknown error'}`);
            return;
        }

        // Format as markdown
        let markdown = '# Vidurai Context\n\n';
        markdown += '_Automatically generated from your recent work_\n\n';
        markdown += response.data.context;
        markdown += `\n\n---\n_${response.data.count} memories, ~${response.data.tokens} tokens_\n`;

        // Copy to clipboard
        await vscode.env.clipboard.writeText(markdown);

        vscode.window.showInformationMessage(
            `✅ Copied ${response.data.count} memories to clipboard!`
        );

    } catch (error: any) {
        log('error', `Copy context failed: ${error.message}`);
        vscode.window.showErrorMessage(`❌ Failed to copy context: ${error.message}`);
    }
}

/**
 * Get project context from Oracle and display in Output Panel
 * v2.1: Uses request/response pattern with Oracle API
 */
async function getProjectContext(audience: string = 'developer') {
    if (!ipcClient || !ipcClient.isConnected()) {
        vscode.window.showErrorMessage('⚠️ Not connected to Vidurai daemon');
        return;
    }

    try {
        // v2.5: Context Guard - Handle undefined gracefully
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? undefined;

        log('info', `Requesting ${audience} context from Oracle...`);

        // Send request to Oracle via IPC
        const response = await ipcClient.send<{
            method: string;
            params: {
                audience: string;
                project_path?: string;
                include_raw?: boolean;
            };
        }, {
            context: string;
            files_with_errors: number;
            total_errors: number;
            total_warnings: number;
            audience: string;
            timestamp: string;
        }>('request', {
            method: 'get_context',
            params: {
                audience,
                project_path: projectPath,
                include_raw: false
            }
        });

        if (!response.ok || !response.data) {
            vscode.window.showErrorMessage(`❌ Oracle error: ${response.error || 'Unknown error'}`);
            return;
        }

        const data = response.data;

        // Show in Output Panel
        const output = getOutputChannel();
        output.clear();
        output.appendLine('═══════════════════════════════════════════════════════════');
        output.appendLine(`  VIDURAI CONTEXT ORACLE (${data.audience.toUpperCase()})`);
        output.appendLine(`  Generated: ${new Date(data.timestamp).toLocaleString()}`);
        output.appendLine('═══════════════════════════════════════════════════════════');
        output.appendLine('');
        output.appendLine(data.context);
        output.appendLine('');
        output.appendLine('───────────────────────────────────────────────────────────');
        output.appendLine(`  Files with issues: ${data.files_with_errors}`);
        output.appendLine(`  Total errors: ${data.total_errors}`);
        output.appendLine(`  Total warnings: ${data.total_warnings}`);
        output.appendLine('═══════════════════════════════════════════════════════════');
        output.show();

        // Also show notification
        if (data.files_with_errors > 0) {
            vscode.window.showWarningMessage(
                `⚠️ ${data.files_with_errors} file(s) with issues (${data.total_errors} errors, ${data.total_warnings} warnings)`
            );
        } else {
            vscode.window.showInformationMessage('✅ Project is clean! No active errors.');
        }

        // If AI audience, also copy to clipboard
        if (audience === 'ai') {
            await vscode.env.clipboard.writeText(data.context);
            vscode.window.showInformationMessage('📋 AI context copied to clipboard');
        }

    } catch (error: any) {
        log('error', `Get context failed: ${error.message}`);
        vscode.window.showErrorMessage(`❌ Failed to get context: ${error.message}`);
    }
}

/**
 * Pin a file to Vidurai context
 * v2.2: Sends pin request to daemon via IPC
 */
async function pinFile(uri?: vscode.Uri) {
    // Get URI from parameter or active editor
    const fileUri = uri || vscode.window.activeTextEditor?.document.uri;

    if (!fileUri || fileUri.scheme !== 'file') {
        vscode.window.showWarningMessage('⚠️ No file selected to pin');
        return;
    }

    if (!ipcClient || !ipcClient.isConnected()) {
        vscode.window.showErrorMessage('⚠️ Not connected to Vidurai daemon');
        return;
    }

    const filePath = fileUri.fsPath;

    // Check if already pinned
    if (pinDecorator?.isPinned(filePath)) {
        vscode.window.showInformationMessage('📌 File is already pinned');
        return;
    }

    try {
        log('info', `Pinning file: ${filePath}`);

        // Get project path for context
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';

        // Send pin request to daemon using file_path (triggers upsert logic)
        // Rule III (Upsert): Daemon will create placeholder if memory doesn't exist
        const response = await ipcClient.send<{
            file_path: string;
            project_path: string;
            reason?: string;
        }, {
            pinned: boolean;
            file_path: string;
        }>('pin', {
            file_path: filePath,
            project_path: projectPath,
            reason: 'Pinned from VS Code'
        });

        if (response.ok) {
            // Update local decorator
            pinDecorator?.addPin(filePath);
            vscode.window.showInformationMessage(`📌 Pinned: ${path.basename(filePath)}`);
            log('info', `File pinned: ${filePath}`);
        } else {
            vscode.window.showWarningMessage(`⚠️ Failed to pin: ${response.error || 'Unknown error'}`);
            log('warn', `Pin failed: ${response.error}`);
        }

    } catch (error: any) {
        log('error', `Pin failed: ${error.message}`);
        vscode.window.showErrorMessage(`❌ Failed to pin file: ${error.message}`);
    }
}

/**
 * Unpin a file from Vidurai context
 * v2.2: Sends unpin request to daemon via IPC
 */
async function unpinFile(uri?: vscode.Uri) {
    // Get URI from parameter or active editor
    const fileUri = uri || vscode.window.activeTextEditor?.document.uri;

    if (!fileUri || fileUri.scheme !== 'file') {
        vscode.window.showWarningMessage('⚠️ No file selected to unpin');
        return;
    }

    if (!ipcClient || !ipcClient.isConnected()) {
        vscode.window.showErrorMessage('⚠️ Not connected to Vidurai daemon');
        return;
    }

    const filePath = fileUri.fsPath;

    // Check if pinned
    if (!pinDecorator?.isPinned(filePath)) {
        vscode.window.showInformationMessage('📌 File is not pinned');
        return;
    }

    try {
        log('info', `Unpinning file: ${filePath}`);

        // Get project path for context
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath || '';

        // Send unpin request to daemon using file_path
        const response = await ipcClient.send<{
            file_path: string;
            project_path: string;
        }, {
            unpinned: boolean;
            file_path: string;
        }>('unpin', {
            file_path: filePath,
            project_path: projectPath
        });

        if (response.ok) {
            // Update local decorator
            pinDecorator?.removePin(filePath);
            vscode.window.showInformationMessage(`📌 Unpinned: ${path.basename(filePath)}`);
            log('info', `File unpinned: ${filePath}`);
        } else {
            vscode.window.showWarningMessage(`⚠️ Failed to unpin: ${response.error || 'Unknown error'}`);
            log('warn', `Unpin failed: ${response.error}`);
        }

    } catch (error: any) {
        log('error', `Unpin failed: ${error.message}`);
        vscode.window.showErrorMessage(`❌ Failed to unpin file: ${error.message}`);
    }
}

/**
 * Sync pinned files from daemon on startup
 * v2.2: Populates the pin decorator with existing pins
 */
async function syncPinsFromDaemon() {
    if (!ipcClient || !ipcClient.isConnected()) {
        log('debug', 'Cannot sync pins - not connected to daemon');
        return;
    }

    try {
        // v2.5: Context Guard - Handle undefined gracefully
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? undefined;

        log('debug', 'Syncing pins from daemon...');

        const response = await ipcClient.send<{
            project_path?: string;
        }, {
            pinned: Array<{
                memory_id: string | number;
                file_path?: string;
                pinned_at: string;
                reason?: string;
            }>;
            count: number;
        }>('get_pinned', {
            project_path: projectPath
        });

        if (response.ok && response.data) {
            // Extract file paths from pinned memories
            const pinnedPaths: string[] = [];
            for (const pin of response.data.pinned) {
                if (pin.file_path) {
                    pinnedPaths.push(pin.file_path);
                }
            }

            if (pinnedPaths.length > 0) {
                pinDecorator?.updatePins(pinnedPaths);
                log('info', `Synced ${pinnedPaths.length} pinned file(s) from daemon`);
            } else {
                log('debug', 'No pinned files found');
            }
        } else {
            log('debug', `Get pinned response: ${response.error || 'empty'}`);
        }

    } catch (error: any) {
        log('debug', `Sync pins failed (non-fatal): ${error.message}`);
    }
}

/**
 * Start polling for context updates
 * v2.2: Glass Box Dashboard - polls daemon every 5 seconds for context state
 */
function startContextPolling() {
    // Initial poll
    refreshContextPanel();

    // Poll every 5 seconds
    contextPollInterval = setInterval(() => {
        refreshContextPanel();
    }, 5000);

    log('debug', 'Context polling started (5s interval)');
}

/**
 * Refresh the context panel with latest data from daemon
 * v2.2: Fetches pinned items, active errors, and token budget
 */
async function refreshContextPanel() {
    if (!contextPanelProvider) {
        return;
    }

    if (!ipcClient || !ipcClient.isConnected()) {
        log('debug', 'Cannot refresh context panel - not connected');
        return;
    }

    try {
        // v2.5: Context Guard - Handle undefined gracefully
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? undefined;

        // Request context state from daemon
        const response = await ipcClient.send<{
            method: string;
            params: {
                project_path?: string;
            };
        }, {
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
        }>('request', {
            method: 'get_dashboard_state',
            params: {
                project_path: projectPath
            }
        });

        if (response.ok && response.data) {
            const data: ContextPanelData = {
                pinned: response.data.pinned || [],
                active_errors: response.data.active_errors || [],
                token_budget: response.data.token_budget || { used: 0, total: 8000 },
                last_updated: new Date().toISOString()
            };

            contextPanelProvider.updateData(data);

            // v2.5: Smart Pin Sync with Dirty Check (IRONCLAD RULE II)
            // Only update decorator if pins actually changed to prevent UI flicker
            if (pinDecorator) {
                const pinnedPaths = data.pinned.map(p => p.file_path);
                const pinsChanged = pinDecorator.updatePins(pinnedPaths);
                if (pinsChanged) {
                    log('debug', `Pin sync: ${pinnedPaths.length} pin(s) updated`);
                }
                // If pinsChanged is false, the decorator skipped the update (no flicker)
            }
        }
    } catch (error: any) {
        log('debug', `Context panel refresh failed: ${error.message}`);
    }
}

/**
 * Generate Standup Report
 * v2.3: Standup Generator - Gets manager context and displays/copies to clipboard
 */
async function generateStandup() {
    if (!ipcClient || !ipcClient.isConnected()) {
        vscode.window.showErrorMessage('Not connected to Vidurai daemon');
        return;
    }

    try {
        // v2.5: Context Guard - Handle undefined gracefully
        const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? undefined;
        const projectName = projectPath ? path.basename(projectPath) : 'Project';

        log('info', 'Generating standup report...');

        // Request manager context from Oracle via IPC
        const response = await ipcClient.send<{
            method: string;
            params: {
                audience: string;
                project_path?: string;
                include_raw?: boolean;
            };
        }, {
            context: string;
            files_with_errors: number;
            total_errors: number;
            total_warnings: number;
            audience: string;
            timestamp: string;
        }>('request', {
            method: 'get_context',
            params: {
                audience: 'manager',
                project_path: projectPath,
                include_raw: false
            }
        });

        if (!response.ok || !response.data) {
            vscode.window.showErrorMessage(`Failed to generate standup: ${response.error || 'Unknown error'}`);
            return;
        }

        const data = response.data;
        const timestamp = new Date(data.timestamp).toLocaleString();

        // Format as Markdown standup report
        let markdown = `# Standup Report - ${projectName}\n\n`;
        markdown += `*Generated: ${timestamp}*\n\n`;
        markdown += `---\n\n`;
        markdown += data.context;
        markdown += `\n\n---\n`;
        markdown += `*Generated by Vidurai Memory Manager*\n`;

        // Offer choices: Copy to Clipboard or Show in Preview
        const choice = await vscode.window.showQuickPick([
            {
                label: '$(clippy) Copy to Clipboard',
                description: 'Copy standup report to clipboard',
                action: 'copy'
            },
            {
                label: '$(preview) Show Preview',
                description: 'Display in Output panel',
                action: 'preview'
            },
            {
                label: '$(copy) Both',
                description: 'Copy to clipboard and show preview',
                action: 'both'
            }
        ], {
            placeHolder: 'What do you want to do with the standup report?',
            title: 'Vidurai Standup Generator'
        });

        if (!choice) {
            return; // User cancelled
        }

        if (choice.action === 'copy' || choice.action === 'both') {
            await vscode.env.clipboard.writeText(markdown);
            vscode.window.showInformationMessage('Standup report copied to clipboard!');
        }

        if (choice.action === 'preview' || choice.action === 'both') {
            // Show in Output panel
            const output = getOutputChannel();
            output.clear();
            output.appendLine('============================================================');
            output.appendLine(`  STANDUP REPORT - ${projectName.toUpperCase()}`);
            output.appendLine(`  Generated: ${timestamp}`);
            output.appendLine('============================================================');
            output.appendLine('');
            output.appendLine(data.context);
            output.appendLine('');
            output.appendLine('------------------------------------------------------------');
            output.appendLine('  Summary:');
            output.appendLine(`  - Files with issues: ${data.files_with_errors}`);
            output.appendLine(`  - Total errors: ${data.total_errors}`);
            output.appendLine(`  - Total warnings: ${data.total_warnings}`);
            output.appendLine('============================================================');
            output.show();
        }

        log('info', 'Standup report generated successfully');

    } catch (error: any) {
        log('error', `Standup generation failed: ${error.message}`);
        vscode.window.showErrorMessage(`Failed to generate standup: ${error.message}`);
    }
}

/**
 * Generate Report and open in new document
 * v2.5: Opens untitled document for Manager or AI reports
 * IRONCLAD RULE IV: Graceful Fallback - always handle undefined/error responses
 */
async function generateReport(audience: 'manager' | 'ai') {
    // Rule IV: Check connection first
    if (!ipcClient || !ipcClient.isConnected()) {
        vscode.window.showErrorMessage('⚠️ Not connected to Vidurai daemon. Please start the daemon first.');
        return;
    }

    const reportType = audience === 'manager' ? 'Manager Report' : 'AI Context XML';

    // Show progress indicator (Rule II in hallucination check - don't block UI)
    await vscode.window.withProgress({
        location: vscode.ProgressLocation.Notification,
        title: `Generating ${reportType}...`,
        cancellable: false
    }, async (progress) => {
        try {
            // v2.5: Context Guard - Handle undefined gracefully
            const projectPath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? undefined;
            const projectName = projectPath ? path.basename(projectPath) : 'Project';

            progress.report({ message: 'Requesting context from daemon...' });

            log('info', `Generating ${reportType} for ${projectName}...`);

            // Request context from Oracle via IPC
            const response = await ipcClient!.send<{
                method: string;
                params: {
                    audience: string;
                    project_path?: string;
                    include_raw?: boolean;
                };
            }, {
                context: string;
                files_with_errors: number;
                total_errors: number;
                total_warnings: number;
                audience: string;
                timestamp: string;
            }>('request', {
                method: 'get_context',
                params: {
                    audience,
                    project_path: projectPath,
                    include_raw: false
                }
            });

            // Rule IV: Graceful Fallback - handle empty/error responses
            if (!response.ok) {
                throw new Error(response.error || 'Unknown error from daemon');
            }

            if (!response.data) {
                throw new Error('Empty report received from daemon');
            }

            if (!response.data.context) {
                throw new Error('Report context is empty');
            }

            progress.report({ message: 'Formatting report...' });

            const data = response.data;
            const timestamp = new Date(data.timestamp).toLocaleString();

            // Format content based on audience
            let content: string;
            let language: string;

            if (audience === 'manager') {
                // Manager Report: Markdown format
                content = `# ${reportType} - ${projectName}\n\n`;
                content += `*Generated: ${timestamp}*\n\n`;
                content += `---\n\n`;
                content += data.context;
                content += `\n\n---\n\n`;
                content += `## Summary\n`;
                content += `- **Files with issues:** ${data.files_with_errors}\n`;
                content += `- **Total errors:** ${data.total_errors}\n`;
                content += `- **Total warnings:** ${data.total_warnings}\n`;
                content += `\n*Generated by Vidurai Memory Manager v2.1.0*\n`;
                language = 'markdown';
            } else {
                // AI Context: XML format
                content = `<!-- AI Context for ${projectName} -->\n`;
                content += `<!-- Generated: ${timestamp} -->\n\n`;
                content += data.context;
                language = 'xml';
            }

            progress.report({ message: 'Opening document...' });

            // Open new untitled document
            const doc = await vscode.workspace.openTextDocument({
                content,
                language
            });

            await vscode.window.showTextDocument(doc, {
                preview: false,
                viewColumn: vscode.ViewColumn.Beside
            });

            log('info', `${reportType} generated successfully`);
            vscode.window.showInformationMessage(`✅ ${reportType} generated! Edit and copy as needed.`);

        } catch (error: any) {
            // Rule IV: Always show user-friendly error
            log('error', `${reportType} generation failed: ${error.message}`);
            vscode.window.showErrorMessage(`❌ Vidurai could not generate ${reportType}: ${error.message}`);
        }
    });
}
