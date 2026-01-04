/**
 * Universal AI Input Injector
 * Detects and injects context into ANY AI platform's input field
 *
 * Supported input types:
 * 1. Standard <textarea> (ChatGPT, Perplexity)
 * 2. ContentEditable <div> (Various platforms)
 * 3. ProseMirror editor (Claude)
 * 4. CodeMirror (some code-focused AIs)
 * 5. Monaco Editor (GitHub Copilot Chat)
 * 6. Custom React components (various)
 *
 * Philosophy: विस्मृति भी विद्या है - Work with frameworks, not against them
 */

class UniversalAIInjector {
    constructor() {
        this.platform = this.detectPlatform();
        this.inputElement = null;
        this.injectionMethod = null;
        this.lastInjectionTime = 0;
        this.injectionCooldown = 2000; // Prevent spam (2 seconds)
        this.reactVersion = this.detectReactVersion();

        console.log(`🧠 Universal Injector initialized for: ${this.platform}`);
        console.log(`🔧 React version: ${this.reactVersion}`);

        // Start monitoring for input fields
        this.startInputMonitoring();
    }

    detectPlatform() {
        const hostname = window.location.hostname;

        const platformMap = {
            'chat.openai.com': 'ChatGPT',
            'chatgpt.com': 'ChatGPT',
            'claude.ai': 'Claude',
            'gemini.google.com': 'Gemini',
            'perplexity.ai': 'Perplexity',
            'poe.com': 'Poe',
            'you.com': 'You.com',
            'bard.google.com': 'Bard',
            'copilot.microsoft.com': 'Copilot',
        };

        return platformMap[hostname] || 'Unknown';
    }

    detectReactVersion() {
        if (window.__REACT_DEVTOOLS_GLOBAL_HOOK__) {
            const hook = window.__REACT_DEVTOOLS_GLOBAL_HOOK__;
            if (hook.renderers && hook.renderers.size > 0) {
                for (const [id, renderer] of hook.renderers) {
                    if (renderer.version) {
                        return renderer.version;
                    }
                }
            }
        }
        return 'unknown';
    }

    startInputMonitoring() {
        // Initial search
        this.findInputElement();

        // Watch for DOM mutations (dynamic inputs)
        const observer = new MutationObserver(() => {
            if (!this.inputElement || !document.contains(this.inputElement)) {
                this.findInputElement();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });

        // Retry periodically if not found
        setInterval(() => {
            if (!this.inputElement || !document.contains(this.inputElement)) {
                this.findInputElement();
            }
        }, 3000);
    }

    findInputElement() {
        // Platform-specific selectors (try these first)
        const platformSelectors = {
            'ChatGPT': [
                'textarea[data-id]',
                '#prompt-textarea',
                'textarea[placeholder*="Message"]',
                'textarea[placeholder*="Send a message"]'
            ],
            'Claude': [
                '.ProseMirror',
                '[contenteditable="true"][role="textbox"]',
                'div[contenteditable="true"]'
            ],
            'Gemini': [
                'textarea[aria-label*="prompt"]',
                'rich-textarea textarea',
                'textarea'
            ],
            'Perplexity': [
                'textarea[placeholder*="Ask"]',
                'textarea'
            ],
            'Poe': [
                'textarea[class*="TextArea"]',
                'textarea'
            ]
        };

        const selectors = platformSelectors[this.platform] || [];

        // Try platform-specific selectors first
        for (const selector of selectors) {
            const element = document.querySelector(selector);
            if (element && this.isValidInput(element)) {
                this.inputElement = element;
                this.injectionMethod = this.detectInputType(element);
                console.log(`✅ Input found: ${selector} (${this.injectionMethod})`);
                return element;
            }
        }

        // Fallback: Heuristic search
        const found = this.findInputByHeuristics();
        if (found) {
            this.inputElement = found;
            this.injectionMethod = this.detectInputType(found);
            console.log(`✅ Input found via heuristics (${this.injectionMethod})`);
            return found;
        }

        return null;
    }

    findInputByHeuristics() {
        // Find large, visible, editable elements
        const candidates = [];

        // Check all textareas
        document.querySelectorAll('textarea').forEach(el => {
            if (this.isValidInput(el)) {
                candidates.push({
                    element: el,
                    score: this.scoreInputCandidate(el)
                });
            }
        });

        // Check contenteditable divs
        document.querySelectorAll('[contenteditable="true"]').forEach(el => {
            if (this.isValidInput(el)) {
                candidates.push({
                    element: el,
                    score: this.scoreInputCandidate(el)
                });
            }
        });

        // Sort by score and return best candidate
        if (candidates.length > 0) {
            candidates.sort((a, b) => b.score - a.score);
            return candidates[0].element;
        }

        return null;
    }

    isValidInput(element) {
        // Check if element is visible and editable
        const rect = element.getBoundingClientRect();
        const style = window.getComputedStyle(element);

        return rect.width > 100 &&
               rect.height > 30 &&
               style.display !== 'none' &&
               style.visibility !== 'hidden' &&
               !element.disabled &&
               !element.readOnly;
    }

    scoreInputCandidate(element) {
        let score = 0;

        // Prefer larger elements
        const rect = element.getBoundingClientRect();
        score += Math.min(rect.width / 10, 100);
        score += Math.min(rect.height / 2, 50);

        // Prefer elements with relevant attributes
        if (element.placeholder &&
            (element.placeholder.toLowerCase().includes('message') ||
             element.placeholder.toLowerCase().includes('ask') ||
             element.placeholder.toLowerCase().includes('prompt'))) {
            score += 50;
        }

        // Prefer elements near bottom of page (common for chat inputs)
        const viewportHeight = window.innerHeight;
        const relativePosition = rect.top / viewportHeight;
        if (relativePosition > 0.7) {
            score += 30;
        }

        return score;
    }

    detectInputType(element) {
        // ProseMirror detection
        if (element.classList.contains('ProseMirror') ||
            element.querySelector('.ProseMirror')) {
            return 'prosemirror';
        }

        // CodeMirror detection
        if (element.classList.contains('CodeMirror') ||
            element.closest('.CodeMirror')) {
            return 'codemirror';
        }

        // Monaco editor detection
        if (element.classList.contains('monaco-editor') ||
            element.closest('.monaco-editor')) {
            return 'monaco';
        }

        // React controlled component (has React fiber)
        const fiberKey = Object.keys(element).find(k =>
            k.startsWith('__reactFiber') ||
            k.startsWith('__reactInternalInstance')
        );
        if (fiberKey) {
            return 'react-controlled';
        }

        // ContentEditable
        if (element.contentEditable === 'true') {
            return 'contenteditable';
        }

        // Standard textarea
        if (element.tagName === 'TEXTAREA') {
            return 'textarea';
        }

        return 'unknown';
    }

    async injectContext(context) {
        // Check cooldown
        const now = Date.now();
        if (now - this.lastInjectionTime < this.injectionCooldown) {
            console.log('⏳ Injection cooldown active');
            return false;
        }

        // Find input if not already found
        if (!this.inputElement || !document.contains(this.inputElement)) {
            this.findInputElement();
        }

        if (!this.inputElement) {
            console.warn('❌ No input element found');
            return false;
        }

        console.log(`🎯 Injecting via ${this.injectionMethod}...`);

        let success = false;

        // Try method-specific injection
        switch (this.injectionMethod) {
            case 'prosemirror':
                success = this.injectIntoProseMirror(this.inputElement, context);
                break;
            case 'codemirror':
                success = this.injectIntoCodeMirror(this.inputElement, context);
                break;
            case 'monaco':
                success = this.injectIntoMonaco(this.inputElement, context);
                break;
            case 'react-controlled':
                success = this.injectIntoReactComponent(this.inputElement, context);
                break;
            case 'contenteditable':
                success = this.injectIntoContentEditable(this.inputElement, context);
                break;
            case 'textarea':
                success = this.injectIntoTextarea(this.inputElement, context);
                break;
            default:
                // Try all methods as fallback
                success = this.injectWithFallbacks(this.inputElement, context);
        }

        if (success) {
            this.lastInjectionTime = now;
            console.log('✅ Context injected successfully');
        } else {
            console.warn('⚠️  Injection failed, trying fallbacks');
            success = this.injectWithFallbacks(this.inputElement, context);
        }

        return success;
    }

    injectIntoTextarea(element, context) {
        try {
            const currentValue = element.value || '';
            const newValue = context + '\n\n' + currentValue;

            // Use native setter
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype,
                'value'
            ).set;
            nativeInputValueSetter.call(element, newValue);

            // Dispatch events
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));

            return true;
        } catch (error) {
            console.error('Textarea injection failed:', error);
            return false;
        }
    }

    injectIntoContentEditable(element, context) {
        try {
            const currentText = element.textContent || '';
            element.textContent = context + '\n\n' + currentText;

            // Dispatch events
            element.dispatchEvent(new Event('input', { bubbles: true }));
            element.dispatchEvent(new Event('change', { bubbles: true }));

            // Move cursor to end
            const range = document.createRange();
            const sel = window.getSelection();
            range.selectNodeContents(element);
            range.collapse(false);
            sel.removeAllRanges();
            sel.addRange(range);

            return true;
        } catch (error) {
            console.error('ContentEditable injection failed:', error);
            return false;
        }
    }

    injectIntoProseMirror(element, context) {
        try {
            // ProseMirror stores state on the element
            const pmView = element.__view;

            if (pmView && pmView.state && pmView.dispatch) {
                const { state, dispatch } = pmView;
                const tr = state.tr.insertText(context + '\n\n', 0);
                dispatch(tr);
                return true;
            }

            // Fallback to contenteditable method
            return this.injectIntoContentEditable(element, context);
        } catch (error) {
            console.error('ProseMirror injection failed:', error);
            return this.injectIntoContentEditable(element, context);
        }
    }

    injectIntoCodeMirror(element, context) {
        try {
            // CodeMirror instance is stored on parent
            const cmParent = element.closest('.CodeMirror');
            const cm = cmParent?.CodeMirror;

            if (cm) {
                const currentValue = cm.getValue();
                cm.setValue(context + '\n\n' + currentValue);
                return true;
            }

            return false;
        } catch (error) {
            console.error('CodeMirror injection failed:', error);
            return false;
        }
    }

    injectIntoMonaco(element, context) {
        try {
            // Monaco stores model on editor instance
            const monacoParent = element.closest('.monaco-editor');

            // Try to find monaco instance
            if (window.monaco && monacoParent) {
                const editor = monacoParent.editor;
                if (editor && editor.setValue) {
                    const currentValue = editor.getValue();
                    editor.setValue(context + '\n\n' + currentValue);
                    return true;
                }
            }

            return false;
        } catch (error) {
            console.error('Monaco injection failed:', error);
            return false;
        }
    }

    injectIntoReactComponent(element, context) {
        try {
            // Find React Fiber
            const fiberKey = Object.keys(element).find(k =>
                k.startsWith('__reactFiber') ||
                k.startsWith('__reactInternalInstance')
            );

            if (!fiberKey) return false;

            const fiber = element[fiberKey];
            let currentFiber = fiber;

            // Walk up fiber tree to find onChange
            while (currentFiber) {
                if (currentFiber.memoizedProps?.onChange) {
                    const onChange = currentFiber.memoizedProps.onChange;

                    // Get current value
                    const currentValue = element.value || element.textContent || '';
                    const newValue = context + '\n\n' + currentValue;

                    // Set value
                    if (element.tagName === 'TEXTAREA') {
                        const nativeValueSetter = Object.getOwnPropertyDescriptor(
                            window.HTMLTextAreaElement.prototype,
                            'value'
                        ).set;
                        nativeValueSetter.call(element, newValue);
                    } else {
                        element.textContent = newValue;
                    }

                    // Trigger onChange
                    onChange({
                        target: element,
                        currentTarget: element,
                        nativeEvent: new InputEvent('input', { bubbles: true }),
                        preventDefault: () => {},
                        stopPropagation: () => {},
                        persist: () => {},
                        type: 'change',
                        bubbles: true
                    });

                    console.log('✅ React Fiber injection successful');
                    return true;
                }
                currentFiber = currentFiber.return;
            }

            return false;
        } catch (error) {
            console.error('React injection failed:', error);
            return false;
        }
    }

    injectWithFallbacks(element, context) {
        // Try all methods in order
        const methods = [
            () => this.injectIntoReactComponent(element, context),
            () => this.injectIntoProseMirror(element, context),
            () => this.injectIntoTextarea(element, context),
            () => this.injectIntoContentEditable(element, context),
            () => this.injectViaClipboard(context),
            () => this.injectViaExecCommand(element, context)
        ];

        for (const method of methods) {
            try {
                if (method()) {
                    return true;
                }
            } catch (error) {
                continue;
            }
        }

        return false;
    }

    injectViaClipboard(context) {
        try {
            // Copy to clipboard and notify user
            navigator.clipboard.writeText(context);
            console.log('📋 Context copied to clipboard');
            return true;
        } catch (error) {
            console.error('Clipboard injection failed:', error);
            return false;
        }
    }

    injectViaExecCommand(element, context) {
        try {
            element.focus();
            document.execCommand('insertText', false, context + '\n\n');
            return true;
        } catch (error) {
            console.error('execCommand injection failed:', error);
            return false;
        }
    }

    forceInject(context) {
        // Force injection, bypassing cooldown
        this.lastInjectionTime = 0;
        return this.injectContext(context);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = UniversalAIInjector;
}
