/**
 * PinDecorator - File Decoration Provider for Pinned Memories
 *
 * v2.2: Shows visual indicator (pin badge) on files that are pinned in Vidurai context.
 *
 * Usage:
 *   const decorator = new PinDecorator();
 *   context.subscriptions.push(
 *     vscode.window.registerFileDecorationProvider(decorator)
 *   );
 *
 *   // Update pins from daemon
 *   decorator.updatePins(['/path/to/file1.ts', '/path/to/file2.py']);
 */

import * as vscode from 'vscode';

/**
 * File Decoration Provider for pinned files
 */
export class PinDecorator implements vscode.FileDecorationProvider {
    private pinnedPaths: Set<string> = new Set();

    private _onDidChangeFileDecorations = new vscode.EventEmitter<vscode.Uri | vscode.Uri[] | undefined>();
    readonly onDidChangeFileDecorations = this._onDidChangeFileDecorations.event;

    /**
     * Provide file decoration for a URI
     */
    provideFileDecoration(
        uri: vscode.Uri,
        _token: vscode.CancellationToken
    ): vscode.ProviderResult<vscode.FileDecoration> {
        // Only handle file scheme
        if (uri.scheme !== 'file') {
            return undefined;
        }

        // Check if this path is pinned
        const filePath = uri.fsPath;

        if (this.pinnedPaths.has(filePath)) {
            return {
                badge: '\u{1F4CC}', // Unicode pin emoji
                tooltip: 'Pinned by Vidurai - Always included in AI context',
                color: new vscode.ThemeColor('charts.yellow'),
                propagate: false
            };
        }

        return undefined;
    }

    /**
     * Update the set of pinned paths
     * v2.5: IRONCLAD RULE II - State Sync with Dirty Check
     * Only fires decoration change event if the data actually changed.
     * This prevents UI flicker from unnecessary re-renders.
     *
     * @param newPins Array of file paths that are currently pinned
     * @returns true if pins changed, false if no change
     */
    updatePins(newPins: string[]): boolean {
        const newPinSet = new Set(newPins);

        // DIRTY CHECK: Compare new pins with current pins
        if (this.setsAreEqual(this.pinnedPaths, newPinSet)) {
            // No change - skip update to prevent UI flicker
            return false;
        }

        // Pins changed - update and fire event
        this.pinnedPaths = newPinSet;
        this._onDidChangeFileDecorations.fire(undefined);
        return true;
    }

    /**
     * Compare two sets for equality
     * @param setA First set
     * @param setB Second set
     * @returns true if sets contain the same elements
     */
    private setsAreEqual(setA: Set<string>, setB: Set<string>): boolean {
        if (setA.size !== setB.size) {
            return false;
        }
        for (const item of setA) {
            if (!setB.has(item)) {
                return false;
            }
        }
        return true;
    }

    /**
     * Add a single pinned path
     * @param filePath Path to pin
     */
    addPin(filePath: string): void {
        if (!this.pinnedPaths.has(filePath)) {
            this.pinnedPaths.add(filePath);
            this._onDidChangeFileDecorations.fire(vscode.Uri.file(filePath));
        }
    }

    /**
     * Remove a single pinned path
     * @param filePath Path to unpin
     */
    removePin(filePath: string): void {
        if (this.pinnedPaths.has(filePath)) {
            this.pinnedPaths.delete(filePath);
            this._onDidChangeFileDecorations.fire(vscode.Uri.file(filePath));
        }
    }

    /**
     * Check if a path is pinned
     * @param filePath Path to check
     */
    isPinned(filePath: string): boolean {
        return this.pinnedPaths.has(filePath);
    }

    /**
     * Get all pinned paths
     */
    getPinnedPaths(): string[] {
        return Array.from(this.pinnedPaths);
    }

    /**
     * Clear all pins
     */
    clearPins(): void {
        this.pinnedPaths.clear();
        this._onDidChangeFileDecorations.fire(undefined);
    }

    /**
     * Get the number of pinned files
     */
    get pinCount(): number {
        return this.pinnedPaths.size;
    }

    /**
     * Dispose of the decorator
     */
    dispose(): void {
        this._onDidChangeFileDecorations.dispose();
    }
}
