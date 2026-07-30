import * as vscode from 'vscode';
import { IPCClient } from '../ipc/Client';
import { log } from '../utils';
import { IPCResponse } from '../shared/events';

const TOKEN_SECRET_KEY = 'vidurai.ipc.token';

interface PairAckData {
    token?: string;
    message?: string;
}

export class PairingManager {
    private secrets: vscode.SecretStorage;
    private client: IPCClient;
    private currentToken: string | null = null;
    
    constructor(context: vscode.ExtensionContext, client: IPCClient) {
        this.secrets = context.secrets;
        this.client = client;
        
        // Listen to client connected events to authenticate
        this.client.on('connected', async () => {
            await this.authenticate();
        });
    }

    /**
     * Authenticate with the daemon.
     * Checks if we have a token. If not, prompts the user to pair.
     */
    public async authenticate(): Promise<boolean> {
        this.currentToken = await this.secrets.get(TOKEN_SECRET_KEY) || null;
        
        if (this.currentToken) {
            // Test token with a ping
            try {
                // Attach token temporarily for the test ping
                this.client.setToken(this.currentToken);
                const res = await this.client.send('ping');
                if (res.ok) {
                    log('info', 'Successfully authenticated with daemon using stored token.');
                    return true;
                } else {
                    log('warn', `Token rejected by daemon: ${res.error}`);
                    this.client.setToken(null);
                    await this.secrets.delete(TOKEN_SECRET_KEY);
                    this.currentToken = null;
                }
            } catch (err) {
                log('error', `Authentication test failed: ${err}`);
                this.client.setToken(null);
            }
        }

        // If we reach here, we need to pair
        return await this.initiatePairingFlow();
    }

    /**
     * Initiate the interactive pairing flow with the user
     */
    public async initiatePairingFlow(): Promise<boolean> {
        const code = await vscode.window.showInputBox({
            prompt: 'Vidurai Daemon is running but unpaired. Enter the 6-character Pairing Code shown in the daemon terminal.',
            placeHolder: 'e.g. A1B2C3',
            ignoreFocusOut: true
        });

        if (!code) {
            log('warn', 'User cancelled pairing flow');
            vscode.window.showWarningMessage('Vidurai is disconnected until paired.');
            return false;
        }

        try {
            const response = await this.client.send<any, PairAckData>('pair_request', { code: code.trim().toUpperCase() });

            if (response.ok && response.data?.token) {
                this.currentToken = response.data.token;
                await this.secrets.store(TOKEN_SECRET_KEY, this.currentToken!);
                this.client.setToken(this.currentToken);
                log('info', 'Successfully paired and securely stored token.');
                vscode.window.showInformationMessage('Vidurai successfully paired with local daemon.');
                return true;
            } else {
                log('warn', `Pairing rejected: ${response.data?.message || response.error}`);
                vscode.window.showErrorMessage(`Pairing failed: ${response.data?.message || 'Invalid code or expired'}`);
                return false;
            }
        } catch (err) {
            log('error', `Pairing request failed: ${err}`);
            vscode.window.showErrorMessage(`Pairing request failed: ${err}`);
            return false;
        }
    }

    /**
     * Revoke the current pairing
     */
    public async revokePairing(): Promise<void> {
        await this.secrets.delete(TOKEN_SECRET_KEY);
        this.currentToken = null;
        this.client.setToken(null);
        log('info', 'Pairing token revoked locally.');
        vscode.window.showInformationMessage('Vidurai pairing revoked. You must pair again to connect.');
    }
}
