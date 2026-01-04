/**
 * ReactInjector - Bulletproof React state manipulation
 * Works with all React versions (15, 16, 17, 18)
 */

class ReactInjector {
    constructor() {
        this.reactVersion = this.detectReactVersion();
        console.log(`🧠 React version detected: ${this.reactVersion}`);
    }

    /**
     * Detect React version from DevTools hook
     */
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

    /**
     * Main injection method - tries all strategies
     */
    inject(selector, contextText) {
        const element = document.querySelector(selector);
        if (!element) {
            console.log('❌ Element not found:', selector);
            return false;
        }

        console.log('🎯 Attempting React injection...');

        // Method 1: Direct React Fiber manipulation (React 16+)
        if (this.injectViaFiber(element, contextText)) {
            return true;
        }

        // Method 2: Legacy React (React 15 and below)
        if (this.injectViaLegacyReact(element, contextText)) {
            return true;
        }

        // Method 3: Universal synthetic event (fallback)
        return this.injectViaSyntheticEvent(element, contextText);
    }

    /**
     * Method 1: React Fiber manipulation (most reliable for modern React)
     */
    injectViaFiber(element, contextText) {
        // Find React Fiber internal key
        const fiberKey = Object.keys(element).find(k =>
            k.startsWith('__reactFiber') ||
            k.startsWith('__reactInternalInstance')
        );

        if (!fiberKey) {
            console.log('⚠️  Not a React component (no fiber key)');
            return false;
        }

        const fiber = element[fiberKey];

        // Walk up the fiber tree to find onChange handler
        let currentFiber = fiber;
        while (currentFiber) {
            if (currentFiber.memoizedProps && currentFiber.memoizedProps.onChange) {
                console.log('✅ Found React onChange handler in fiber tree');

                const onChange = currentFiber.memoizedProps.onChange;

                // Get current value
                const currentValue = element.value || '';
                const newValue = contextText + '\n\n' + currentValue;

                // Update DOM value
                const nativeValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype,
                    'value'
                ).set;
                nativeValueSetter.call(element, newValue);

                // Create React synthetic event
                const syntheticEvent = {
                    target: element,
                    currentTarget: element,
                    nativeEvent: new InputEvent('input', { bubbles: true }),
                    preventDefault: () => {},
                    stopPropagation: () => {},
                    persist: () => {},
                    type: 'change',
                    bubbles: true
                };

                // Trigger React's onChange
                onChange(syntheticEvent);

                console.log('✅ Context injected via React Fiber');
                return true;
            }
            currentFiber = currentFiber.return;  // Go up the tree
        }

        console.log('⚠️  onChange handler not found in fiber tree');
        return false;
    }

    /**
     * Method 2: Legacy React (React 15 and below)
     */
    injectViaLegacyReact(element, contextText) {
        const key = Object.keys(element).find(k =>
            k.startsWith('__reactInternalInstance')
        );

        if (!key) return false;

        const instance = element[key];
        if (instance._currentElement && instance._currentElement.props) {
            const props = instance._currentElement.props;
            if (props.onChange) {
                const currentValue = element.value || '';
                element.value = contextText + '\n\n' + currentValue;
                props.onChange({ target: element });
                console.log('✅ Context injected via Legacy React');
                return true;
            }
        }

        return false;
    }

    /**
     * Method 3: Universal synthetic event (works with most React versions)
     */
    injectViaSyntheticEvent(element, contextText) {
        console.log('🔄 Using synthetic event method...');

        const currentValue = element.value || '';
        const newValue = contextText + '\n\n' + currentValue;

        // Step 1: Update textarea value using native setter
        const nativeValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype,
            'value'
        ).set;
        nativeValueSetter.call(element, newValue);

        // Step 2: Create input event
        const inputEvent = new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            composed: true,
            data: newValue,
            inputType: 'insertText'
        });

        // Step 3: Dispatch input event
        element.dispatchEvent(inputEvent);

        // Step 4: Also trigger change event (some React versions need this)
        const changeEvent = new Event('change', {
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(changeEvent);

        // Step 5: Trigger at document level (React event delegation)
        setTimeout(() => {
            element.focus();
            element.blur();
            element.focus();
        }, 10);

        console.log('✅ Context injected via Synthetic Event');
        return true;
    }
}

// Export for use in content.js
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ReactInjector;
}
