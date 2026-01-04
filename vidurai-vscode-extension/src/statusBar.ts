/**
 * Status Bar Indicator
 * v2.3 - Memory HUD with Profile Switching (Developer Cockpit Phase 3)
 */
import * as vscode from 'vscode';
import { IPCClient } from './ipc';
import { log } from './utils';

/**
 * Profile configuration for the Memory HUD
 */
type MemoryProfile = 'cost_focused' | 'balanced' | 'quality_focused';

interface ProfileOption {
    label: string;
    profile: MemoryProfile;
    description: string;
    icon: string;
}

const PROFILE_OPTIONS: ProfileOption[] = [
    {
        label: '$(dashboard) Cost Focused',
        profile: 'cost_focused',
        description: 'Minimize token usage, aggressive pruning',
        icon: '💰'
    },
    {
        label: '$(symbol-event) Balanced',
        profile: 'balanced',
        description: 'Default mode - balance cost and quality',
        icon: '⚖️'
    },
    {
        label: '$(star-full) Quality Focused',
        profile: 'quality_focused',
        description: 'Maximum context retention',
        icon: '✨'
    }
];

const PROFILE_DISPLAY: Record<MemoryProfile, string> = {
    'cost_focused': 'Cost',
    'balanced': 'Balanced',
    'quality_focused': 'Quality'
};

export class StatusBarManager {
    private statusBarItem: vscode.StatusBarItem;
    private client: IPCClient;
    private updateInterval: NodeJS.Timeout | null = null;
    private currentProfile: MemoryProfile = 'balanced';

    constructor(client: IPCClient) {
        this.client = client;

        this.statusBarItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );

        // v2.3: Memory HUD - Show brain icon with profile
        this.statusBarItem.text = '$(sync~spin) Vidurai';
        this.statusBarItem.tooltip = 'Vidurai: Initializing...';
        this.statusBarItem.command = 'vidurai.switchProfile';  // Changed: Now opens profile switcher
        this.statusBarItem.show();

        // First update after small delay to allow IPC connection
        setTimeout(() => this.update(), 500);
    }

    /**
     * Show profile switcher QuickPick
     * v2.3: Memory HUD - Switch between Cost/Balanced/Quality profiles
     */
    async showProfileSwitcher(): Promise<void> {
        const items = PROFILE_OPTIONS.map(opt => ({
            label: opt.label,
            description: opt.description,
            detail: this.currentProfile === opt.profile ? '$(check) Current' : '',
            profile: opt.profile
        }));

        const selected = await vscode.window.showQuickPick(items, {
            placeHolder: 'Select Memory Profile',
            title: 'Vidurai Memory HUD - Profile Switcher'
        });

        if (selected && selected.profile !== this.currentProfile) {
            await this.setProfile(selected.profile);
        }
    }

    /**
     * Set the memory profile via IPC
     * v2.3: Sends set_config to daemon
     */
    async setProfile(profile: MemoryProfile): Promise<void> {
        if (!this.client.isConnected()) {
            vscode.window.showWarningMessage('⚠️ Not connected to Vidurai daemon');
            return;
        }

        try {
            log('info', `Switching profile to: ${profile}`);

            const response = await this.client.send<{
                profile: string;
            }, {
                ok: boolean;
                profile: string;
                previous_profile: string;
            }>('set_config', { profile });

            if (response.ok && response.data) {
                this.currentProfile = profile;
                const displayName = PROFILE_DISPLAY[profile];
                vscode.window.showInformationMessage(`$(brain) Vidurai: Switched to ${displayName} mode`);
                log('info', `Profile switched: ${response.data.previous_profile} -> ${profile}`);
                this.update();
            } else {
                vscode.window.showErrorMessage(`❌ Failed to switch profile: ${response.error || 'Unknown error'}`);
            }
        } catch (error: any) {
            log('error', `Profile switch failed: ${error.message}`);
            vscode.window.showErrorMessage(`❌ Failed to switch profile: ${error.message}`);
        }
    }

    /**
     * Get current profile
     */
    getProfile(): MemoryProfile {
        return this.currentProfile;
    }

    /**
     * Start periodic updates
     */
    startUpdates(): void {
        if (this.updateInterval) {
            return;
        }

        // Update every 10 seconds
        this.updateInterval = setInterval(() => {
            this.update();
        }, 10000);
    }

    /**
     * Stop periodic updates
     */
    stopUpdates(): void {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    /**
     * Update status bar
     * v2.3: Memory HUD - Shows brain icon with current profile
     */
    async update(): Promise<void> {
        try {
            const state = this.client.getState();

            if (state === 'disconnected') {
                this.statusBarItem.text = '$(brain) Vidurai: Offline';
                this.statusBarItem.tooltip = 'Daemon not connected\nClick to reconnect';
                this.statusBarItem.command = 'vidurai.restartBridge';
                return;
            }

            if (state === 'connecting' || state === 'reconnecting') {
                this.statusBarItem.text = '$(sync~spin) Vidurai: Connecting...';
                this.statusBarItem.tooltip = 'Connecting to daemon...';
                this.statusBarItem.command = 'vidurai.showLogs';
                return;
            }

            if (state === 'draining') {
                this.statusBarItem.text = '$(sync~spin) Vidurai: Syncing...';
                this.statusBarItem.tooltip = 'Syncing buffered events...';
                this.statusBarItem.command = 'vidurai.showLogs';
                return;
            }

            // v2.3: Memory HUD - Show brain icon with profile
            const profileDisplay = PROFILE_DISPLAY[this.currentProfile];
            this.statusBarItem.text = `$(brain) Vidurai: ${profileDisplay}`;
            this.statusBarItem.tooltip = `Memory Profile: ${profileDisplay}\nClick to switch profiles`;
            this.statusBarItem.command = 'vidurai.switchProfile';

        } catch (error: any) {
            log('warn', `Status update failed: ${error.message}`);
            this.statusBarItem.text = '$(brain) Vidurai: Error';
            this.statusBarItem.tooltip = 'Failed to get status\nClick to reconnect';
            this.statusBarItem.command = 'vidurai.restartBridge';
        }
    }

    /**
     * Dispose status bar
     */
    dispose(): void {
        this.stopUpdates();
        this.statusBarItem.dispose();
    }
}
