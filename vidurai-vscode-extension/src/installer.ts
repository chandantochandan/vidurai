/**
 * Python and Vidurai SDK installer
 */
import * as vscode from 'vscode';
import { exec } from 'child_process';
import { promisify } from 'util';
import { findPython, checkModule, log } from './utils';

const execAsync = promisify(exec);

/**
 * Ensure Python and Vidurai are installed
 * Returns Python path or throws error
 */
export async function ensureVidurai(extensionPath: string): Promise<string> {
    log('info', 'Checking Python and Vidurai installation...');

    // Step 1: Find Python
    const pythonPath = await findPython(extensionPath);

    if (!pythonPath) {
        const choice = await vscode.window.showErrorMessage(
            '⚠️ Python 3.8+ not found. Vidurai requires Python.',
            'Download Python',
            'Manual Setup'
        );

        if (choice === 'Download Python') {
            vscode.env.openExternal(vscode.Uri.parse('https://python.org/downloads'));
        } else if (choice === 'Manual Setup') {
            vscode.env.openExternal(vscode.Uri.parse('https://docs.vidurai.ai/setup'));
        }

        throw new Error('Python not found');
    }

    log('info', `Found Python: ${pythonPath}`);

    // Step 2: Check if Vidurai installed
    const hasVidurai = await checkModule(pythonPath, 'vidurai');

    if (!hasVidurai) {
        log('warn', 'Vidurai SDK not installed');

        const choice = await vscode.window.showInformationMessage(
            '📦 Vidurai SDK not installed. Install now? (Requires internet)',
            'Install Automatically',
            'Install Manually',
            'Cancel'
        );

        if (choice === 'Install Automatically') {
            await installVidurai(pythonPath);
        } else if (choice === 'Install Manually') {
            await vscode.env.clipboard.writeText('pip install vidurai==1.6.1');
            vscode.window.showInformationMessage('✅ Command copied to clipboard: pip install vidurai==1.6.1');
            throw new Error('Manual installation required');
        } else {
            throw new Error('Installation cancelled');
        }
    } else {
        log('info', 'Vidurai SDK already installed');
    }

    return pythonPath;
}

/**
 * Install Vidurai SDK via pip
 */
async function installVidurai(pythonPath: string): Promise<void> {
    try {
        log('info', 'Installing Vidurai SDK...');

        await vscode.window.withProgress({
            location: vscode.ProgressLocation.Notification,
            title: 'Installing Vidurai SDK...',
            cancellable: false
        }, async () => {
            await execAsync(`${pythonPath} -m pip install vidurai==1.6.1 --user`);
        });

        log('info', 'Vidurai SDK installed successfully');
        vscode.window.showInformationMessage('✅ Vidurai SDK installed successfully!');

    } catch (error: any) {
        log('error', `Installation failed: ${error.message}`);

        vscode.window.showErrorMessage(
            `❌ Auto-install failed: ${error.message}\n\nPlease install manually: pip install vidurai==1.6.1`,
            'Copy Command',
            'View Docs'
        ).then(choice => {
            if (choice === 'Copy Command') {
                vscode.env.clipboard.writeText('pip install vidurai==1.6.1');
            } else if (choice === 'View Docs') {
                vscode.env.openExternal(vscode.Uri.parse('https://docs.vidurai.ai/installation'));
            }
        });

        throw new Error('Installation failed');
    }
}
