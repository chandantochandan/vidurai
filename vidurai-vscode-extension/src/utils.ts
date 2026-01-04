/**
 * Utility functions
 */
import * as vscode from 'vscode';
import * as path from 'path';
import * as fs from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

/**
 * Find Python executable
 * 1. Check for local venv (development)
 * 2. Try python3, python, py (system)
 */
export async function findPython(extensionPath?: string): Promise<string | null> {
    // First, check for local venv (for development/testing)
    if (extensionPath) {
        const venvPython = path.join(extensionPath, 'python-bridge', '.venv', 'bin', 'python');
        if (fs.existsSync(venvPython)) {
            log('info', `Found local venv Python: ${venvPython}`);
            return venvPython;
        }
    }

    // Fall back to system Python
    const candidates = process.platform === 'win32'
        ? ['py', 'python', 'python3']  // Windows: py launcher first
        : ['python3', 'python'];        // Unix: python3 first

    for (const cmd of candidates) {
        try {
            const { stdout } = await execAsync(`${cmd} --version`);
            if (stdout.includes('Python 3.')) {
                log('info', `Found system Python: ${cmd}`);
                return cmd;
            }
        } catch {
            // Command not found, try next
        }
    }

    return null;
}

/**
 * Check if Python module is installed
 */
export async function checkModule(pythonPath: string, moduleName: string): Promise<boolean> {
    try {
        await execAsync(`${pythonPath} -c "import ${moduleName}"`);
        return true;
    } catch {
        return false;
    }
}

/**
 * Get configuration value
 */
export function getConfig<T>(key: string, defaultValue: T): T {
    return vscode.workspace.getConfiguration('vidurai').get(key, defaultValue);
}

/**
 * Log message to output channel
 */
let outputChannel: vscode.OutputChannel;

export function getOutputChannel(): vscode.OutputChannel {
    if (!outputChannel) {
        outputChannel = vscode.window.createOutputChannel('Vidurai');
    }
    return outputChannel;
}

export function log(level: string, message: string): void {
    const configLevel = getConfig('logLevel', 'info');
    const levels = ['debug', 'info', 'warn', 'error'];

    if (levels.indexOf(level) >= levels.indexOf(configLevel)) {
        const timestamp = new Date().toISOString();
        getOutputChannel().appendLine(`[${timestamp}] [${level.toUpperCase()}] ${message}`);
    }
}
