/**
 * Vidurai Universal Content Script - PRODUCTION SOLUTION
 * Philosophy: विस्मृति भी विद्या है (Forgetting too is knowledge)
 *
 * Multi-method injection with graceful fallbacks
 * Consultant-approved architecture
 */

console.log('🧠 Vidurai v0.5.0 - MULTI-METHOD INJECTION - Production Ready');

// ============================================================================
// VIDURAI INJECTOR CLASS - Complete Solution
// ============================================================================

class ViduraiInjector {
    constructor() {
        this.platform = this.detectPlatform();

        // Prioritized injection methods (most reliable first)
        this.methods = [
            this.tryClipboardWithPaste,
            this.tryReactInjection,
            this.tryTypingSimulation,
            this.tryManualNotification
        ];
    }

    detectPlatform() {
        const hostname = window.location.hostname;
        if (hostname.includes('chatgpt') || hostname.includes('openai')) return 'ChatGPT';
        if (hostname.includes('claude')) return 'Claude';
        if (hostname.includes('gemini')) return 'Gemini';
        if (hostname.includes('perplexity')) return 'Perplexity';
        if (hostname.includes('phind')) return 'Phind';
        if (hostname.includes('you.com')) return 'You.com';
        return 'Unknown';
    }

    findInput() {
        // Try multiple selectors for different platforms
        const selectors = [
            'textarea[placeholder*="Message"]',
            'textarea[placeholder*="Ask"]',
            'textarea[placeholder*="Type"]',
            'textarea',
            '[contenteditable="true"]',
            '#prompt-textarea'
        ];

        for (const selector of selectors) {
            const input = document.querySelector(selector);
            if (input) {
                console.log('📍 Found input via:', selector);
                return input;
            }
        }

        console.warn('❌ No input found');
        return null;
    }

    // ========================================================================
    // METHOD 1: Clipboard + Auto-Paste (MOST RELIABLE)
    // ========================================================================
    async tryClipboardWithPaste(text) {
        console.log('📋 Method 1: Clipboard + Auto-Paste');

        try {
            const input = this.findInput();
            if (!input) return false;

            // Save user's clipboard
            let userClipboard = '';
            try {
                userClipboard = await navigator.clipboard.readText();
            } catch (e) {
                console.log('⚠️  Cannot read clipboard (permission), continuing anyway');
            }

            // Write our context to clipboard
            await navigator.clipboard.writeText(text);
            console.log('✓ Written to clipboard');

            // Focus input
            input.focus();

            // Get current value
            const currentValue = input.value || input.textContent || '';

            // Try execCommand paste (works in most browsers)
            const pasteSuccess = document.execCommand('paste');

            if (pasteSuccess) {
                console.log('✓ execCommand paste succeeded');

                // Restore user's clipboard after a moment
                setTimeout(async () => {
                    if (userClipboard) {
                        await navigator.clipboard.writeText(userClipboard);
                        console.log('✓ User clipboard restored');
                    }
                }, 500);

                return true;
            }

            // If execCommand failed, manually set value and trigger events
            console.log('⚠️  execCommand failed, using manual method');
            const newValue = text + '\n\n' + currentValue;

            // Set value using native setter (bypasses React)
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                'value'
            )?.set;

            if (nativeInputValueSetter) {
                nativeInputValueSetter.call(input, newValue);
            } else {
                input.value = newValue;
            }

            // NOW trigger React's onChange by finding the React component
            let reactTriggered = false;
            let current = input;

            while (current && !reactTriggered) {
                const fiberKey = Object.keys(current).find(k => k.startsWith('__reactFiber'));
                if (fiberKey) {
                    console.log('⚛️  Found React on:', current.tagName);
                    let fiber = current[fiberKey];

                    while (fiber && !reactTriggered) {
                        if (fiber.memoizedProps?.onChange) {
                            try {
                                fiber.memoizedProps.onChange({
                                    target: input,
                                    currentTarget: input,
                                    nativeEvent: new InputEvent('input', { bubbles: true })
                                });
                                console.log('✓ React onChange triggered');
                                reactTriggered = true;
                            } catch (e) {
                                console.warn('onChange failed:', e.message);
                            }
                        }
                        fiber = fiber.return;
                    }
                    break;
                }
                current = current.parentElement;
            }

            // Trigger DOM events as fallback
            input.dispatchEvent(new InputEvent('input', {
                bubbles: true,
                inputType: 'insertText',
                data: text
            }));
            input.dispatchEvent(new Event('change', { bubbles: true }));

            // Focus the input
            input.focus();

            // Restore user's clipboard
            setTimeout(async () => {
                if (userClipboard) {
                    await navigator.clipboard.writeText(userClipboard);
                }
            }, 500);

            console.log('✓ Manual paste with React trigger completed');
            return true;

        } catch (error) {
            console.warn('❌ Clipboard method failed:', error.message);
            return false;
        }
    }

    // ========================================================================
    // METHOD 2: React Injection (For controlled components)
    // ========================================================================
    async tryReactInjection(text) {
        console.log('⚛️  Method 2: React Injection');

        try {
            const input = this.findInput();
            if (!input) return false;

            const currentValue = input.value || input.textContent || '';
            const newValue = text + '\n\n' + currentValue;

            // Set value using native setter
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                'value'
            )?.set;

            if (nativeInputValueSetter) {
                nativeInputValueSetter.call(input, newValue);
                console.log('✓ Value set via native setter');
            } else {
                input.value = newValue;
            }

            // Find React component by walking up DOM tree
            let current = input;
            let reactComponent = null;

            while (current && !reactComponent) {
                const fiberKey = Object.keys(current).find(k => k.startsWith('__reactFiber'));
                if (fiberKey) {
                    reactComponent = { element: current, fiber: current[fiberKey] };
                    console.log('✓ Found React component on:', current.tagName);
                    break;
                }
                current = current.parentElement;
            }

            if (reactComponent) {
                // Walk React fiber tree to find handlers
                let curr = reactComponent.fiber;
                let foundHandler = false;

                while (curr && !foundHandler) {
                    const props = curr.memoizedProps;

                    // Try all possible React handlers
                    const handlers = ['onChange', 'onInput', 'onKeyUp', 'onKeyDown'];
                    for (const handlerName of handlers) {
                        if (props?.[handlerName]) {
                            try {
                                props[handlerName]({
                                    target: input,
                                    currentTarget: input,
                                    type: handlerName.toLowerCase().replace('on', ''),
                                    nativeEvent: new InputEvent('input', { bubbles: true })
                                });
                                console.log(`✓ Triggered React ${handlerName}`);
                                foundHandler = true;
                                break;
                            } catch (e) {
                                console.warn(`Failed ${handlerName}:`, e.message);
                            }
                        }
                    }

                    curr = curr.return;
                }

                if (foundHandler) {
                    // Dispatch additional events for good measure
                    input.dispatchEvent(new Event('input', { bubbles: true }));
                    input.dispatchEvent(new Event('change', { bubbles: true }));
                    input.focus();

                    console.log('✓ React injection complete');
                    return true;
                }
            }

            console.warn('⚠️  No React handlers found');
            return false;

        } catch (error) {
            console.warn('❌ React injection failed:', error.message);
            return false;
        }
    }

    // ========================================================================
    // METHOD 3: Typing Simulation (Slow but works everywhere)
    // ========================================================================
    async tryTypingSimulation(text) {
        console.log('⌨️  Method 3: Typing Simulation');

        try {
            const input = this.findInput();
            if (!input) return false;

            input.focus();

            // For long text, don't simulate every character (too slow)
            // Instead, chunk it and use paste simulation
            const chunks = text.match(/.{1,50}/g) || [text];

            for (let i = 0; i < chunks.length; i++) {
                const chunk = chunks[i];

                // Set the chunk
                const currentValue = input.value || input.textContent || '';
                const newValue = currentValue + chunk;

                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype,
                    'value'
                )?.set;

                if (nativeInputValueSetter) {
                    nativeInputValueSetter.call(input, newValue);
                } else {
                    input.value = newValue;
                }

                // Simulate input event for this chunk
                input.dispatchEvent(new InputEvent('input', {
                    bubbles: true,
                    inputType: 'insertText',
                    data: chunk
                }));

                // Small delay between chunks (simulate human typing speed)
                if (i < chunks.length - 1) {
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
            }

            // Add newlines
            const finalValue = input.value + '\n\n';
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                'value'
            )?.set;

            if (nativeInputValueSetter) {
                nativeInputValueSetter.call(input, finalValue);
            } else {
                input.value = finalValue;
            }

            // Final events
            input.dispatchEvent(new Event('input', { bubbles: true }));
            input.dispatchEvent(new Event('change', { bubbles: true }));

            // Move cursor to end
            input.selectionStart = input.value.length;
            input.selectionEnd = input.value.length;

            console.log('✓ Typing simulation complete');
            return true;

        } catch (error) {
            console.warn('❌ Typing simulation failed:', error.message);
            return false;
        }
    }

    // ========================================================================
    // METHOD 4: Manual Notification (Last Resort)
    // ========================================================================
    async tryManualNotification(text) {
        console.log('💬 Method 4: Manual Notification');

        try {
            // Copy to clipboard
            await navigator.clipboard.writeText(text);

            // Show notification to user
            this.showNotification('Vidurai context ready! Press Ctrl+V to paste it.');

            console.log('✓ Context copied to clipboard, user notified');
            return true;

        } catch (error) {
            console.warn('❌ Manual notification failed:', error.message);
            return false;
        }
    }

    // ========================================================================
    // MAIN INJECTION METHOD
    // ========================================================================
    async inject(contextText) {
        console.log('🚀 Vidurai injection starting...');
        console.log('📊 Context length:', contextText.length, 'chars');
        console.log('🎯 Platform:', this.platform);

        // Try each method in order
        for (const method of this.methods) {
            try {
                console.log('---');
                const success = await method.call(this, contextText);
                if (success) {
                    console.log('✅ Injection successful with:', method.name);
                    this.showSuccessIndicator();
                    return true;
                }
            } catch (error) {
                console.warn(`Method ${method.name} failed:`, error);
            }
        }

        console.error('❌ All injection methods failed');
        return false;
    }

    // ========================================================================
    // HELPER METHODS
    // ========================================================================

    showNotification(message) {
        // Create notification element
        const notification = document.createElement('div');
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #10b981;
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
            z-index: 999999;
            font-family: system-ui, -apple-system, sans-serif;
            font-size: 14px;
            font-weight: 500;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(notification);

        // Remove after 5 seconds
        setTimeout(() => {
            notification.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => notification.remove(), 300);
        }, 5000);
    }

    showSuccessIndicator() {
        // Quick flash to indicate success
        const flash = document.createElement('div');
        flash.textContent = '✅';
        flash.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 64px;
            z-index: 999999;
            animation: fadeInOut 0.8s ease-out;
        `;

        document.body.appendChild(flash);
        setTimeout(() => flash.remove(), 800);
    }
}

// ============================================================================
// DAEMON CONNECTION
// ============================================================================

let daemonStatus = 'checking';

async function checkDaemon() {
    try {
        const res = await fetch('http://localhost:7777/health');
        if (res.ok) {
            daemonStatus = 'connected';
            return true;
        }
    } catch (e) {}
    daemonStatus = 'disconnected';
    return false;
}

async function getIntelligentContext(prompt = '') {
    try {
        // Determine platform-specific format
        let platform = 'chatgpt_web';  // default
        if (injector.platform === 'Claude') {
            platform = 'claude_code';
        } else if (injector.platform === 'ChatGPT') {
            platform = 'chatgpt_web';
        }

        // First, try the new smart context endpoint (Project Brain)
        try {
            const res = await fetch('http://localhost:7777/context/smart', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    user_prompt: prompt,
                    platform: platform
                })
            });
            const data = await res.json();
            if (data.status === 'success') {
                console.log(`🧠 Smart Context: ${data.length} chars (intent: ${data.intent})`);
                return data.context;
            }
        } catch (e) {
            console.log('Smart context unavailable, falling back to legacy...');
        }

        // Fallback to legacy context endpoint
        const res = await fetch('http://localhost:7777/context/prepare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_prompt: prompt,
                ai_platform: injector.platform
            })
        });
        const data = await res.json();
        if (data.status === 'success') {
            console.log(`🧠 Legacy Context: ${data.length} chars (state: ${data.user_state})`);
            return data.context;
        }
    } catch (e) {
        console.warn('Context fetch failed:', e);
    }
    return '';
}

// ============================================================================
// INITIALIZE
// ============================================================================

const injector = new ViduraiInjector();

// Keyboard shortcut: Ctrl+Shift+V
document.addEventListener('keydown', async (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'V') {
        e.preventDefault();
        console.log('⌨️  Manual injection (Ctrl+Shift+V)');

        if (daemonStatus !== 'connected') {
            injector.showNotification('Vidurai daemon is offline. Please start the daemon.');
            return;
        }

        const context = await getIntelligentContext();
        if (context) {
            await injector.inject(context);
        } else {
            injector.showNotification('No context available');
        }
    }
});

// Status indicator
const indicator = document.createElement('div');
indicator.style.cssText = `
    position: fixed; bottom: 20px; right: 20px;
    width: 12px; height: 12px; border-radius: 50%;
    z-index: 999999; transition: background 0.3s;
`;
document.body.appendChild(indicator);

function updateStatus() {
    indicator.style.background = daemonStatus === 'connected' ? '#10b981' : '#ef4444';
    indicator.title = daemonStatus === 'connected' ?
        'Vidurai: Connected (Ctrl+Shift+V)' : 'Vidurai: Offline';
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(400px); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(400px); opacity: 0; }
    }
    @keyframes fadeInOut {
        0% { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
        50% { opacity: 1; transform: translate(-50%, -50%) scale(1); }
        100% { opacity: 0; transform: translate(-50%, -50%) scale(0.5); }
    }
`;
document.head.appendChild(style);

// Init
checkDaemon().then(updateStatus);
setInterval(() => checkDaemon().then(updateStatus), 10000);

console.log('✅ Vidurai ready! Press Ctrl+Shift+V to inject context.');
