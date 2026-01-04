/**
 * Vidurai Universal Content Script
 * Works with ChatGPT, Claude.ai, Gemini, Perplexity, Phind, and more
 * Day 4: React Injection Fix - Work WITH React, not against it
 */

console.log('🧠 Vidurai Universal Extension loaded');

// AI Platform configurations
const AI_PLATFORMS = {
  'chat.openai.com': {
    name: 'ChatGPT',
    color: '#10a37f',
    selectors: {
      input: 'textarea[data-id]',
      submit: 'button[data-testid="send-button"]',
      inputType: 'textarea'
    }
  },
  'chatgpt.com': {
    name: 'ChatGPT',
    color: '#10a37f',
    selectors: {
      input: 'textarea',
      submit: 'button[data-testid="send-button"]',
      inputType: 'textarea'
    }
  },
  'claude.ai': {
    name: 'Claude.ai',
    color: '#8b5cf6',
    selectors: {
      input: 'div[contenteditable="true"]',
      submit: 'button[aria-label="Send Message"]',
      inputType: 'contenteditable'
    }
  },
  'gemini.google.com': {
    name: 'Gemini',
    color: '#4285f4',
    selectors: {
      input: 'div[contenteditable="true"]',
      submit: 'button[aria-label*="Send"]',
      inputType: 'contenteditable'
    }
  },
  'perplexity.ai': {
    name: 'Perplexity',
    color: '#20808d',
    selectors: {
      input: 'textarea',
      submit: 'button[aria-label="Submit"]',
      inputType: 'textarea'
    }
  },
  'phind.com': {
    name: 'Phind',
    color: '#6366f1',
    selectors: {
      input: 'textarea',
      submit: 'button[type="submit"]',
      inputType: 'textarea'
    }
  },
  'you.com': {
    name: 'You.com',
    color: '#0084ff',
    selectors: {
      input: 'textarea',
      submit: 'button[type="submit"]',
      inputType: 'textarea'
    }
  }
};

const currentPlatform = AI_PLATFORMS[window.location.hostname];

if (!currentPlatform) {
  console.warn('⚠️  Vidurai: Unknown AI platform');
} else {
  console.log(`✅ Vidurai active on ${currentPlatform.name}`);
}

// State
let daemonStatus = 'checking';
let viduraiEnabled = true;
let contextInjected = false;

// ========================================
// REACT INJECTOR - INLINE VERSION
// ========================================

class ReactInjector {
    constructor() {
        this.reactVersion = this.detectReactVersion();
        console.log(`🧠 React version detected: ${this.reactVersion}`);
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

    injectViaFiber(element, contextText) {
        const fiberKey = Object.keys(element).find(k =>
            k.startsWith('__reactFiber') ||
            k.startsWith('__reactInternalInstance')
        );

        if (!fiberKey) {
            console.log('⚠️  Not a React component (no fiber key)');
            return false;
        }

        const fiber = element[fiberKey];

        let currentFiber = fiber;
        while (currentFiber) {
            if (currentFiber.memoizedProps && currentFiber.memoizedProps.onChange) {
                console.log('✅ Found React onChange handler in fiber tree');

                const onChange = currentFiber.memoizedProps.onChange;

                const currentValue = element.value || '';
                const newValue = contextText + '\n\n' + currentValue;

                const nativeValueSetter = Object.getOwnPropertyDescriptor(
                    window.HTMLTextAreaElement.prototype,
                    'value'
                ).set;
                nativeValueSetter.call(element, newValue);

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

                onChange(syntheticEvent);

                console.log('✅ Context injected via React Fiber');
                return true;
            }
            currentFiber = currentFiber.return;
        }

        console.log('⚠️  onChange handler not found in fiber tree');
        return false;
    }

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

    injectViaSyntheticEvent(element, contextText) {
        console.log('🔄 Using synthetic event method...');

        const currentValue = element.value || '';
        const newValue = contextText + '\n\n' + currentValue;

        const nativeValueSetter = Object.getOwnPropertyDescriptor(
            window.HTMLTextAreaElement.prototype,
            'value'
        ).set;
        nativeValueSetter.call(element, newValue);

        const inputEvent = new InputEvent('input', {
            bubbles: true,
            cancelable: true,
            composed: true,
            data: newValue,
            inputType: 'insertText'
        });

        element.dispatchEvent(inputEvent);

        const changeEvent = new Event('change', {
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(changeEvent);

        setTimeout(() => {
            element.focus();
            element.blur();
            element.focus();
        }, 10);

        console.log('✅ Context injected via Synthetic Event');
        return true;
    }
}

const reactInjector = new ReactInjector();

// ========================================
// DAEMON FUNCTIONS
// ========================================

// Check daemon status
async function checkDaemonStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'CHECK_DAEMON' });
    daemonStatus = response.success ? 'connected' : 'disconnected';
    updateStatusIndicator();
    return response.success;
  } catch (error) {
    daemonStatus = 'disconnected';
    updateStatusIndicator();
    return false;
  }
}

// Get project context from daemon
async function getProjectContext() {
    try {
        const response = await fetch('http://localhost:7777/metrics');
        const data = await response.json();

        if (data.projects_list && data.projects_list.length > 0) {
            const projectName = data.projects_list[0].split('/').pop();

            // Format context for AI (clean, concise)
            const context = `[VIDURAI CONTEXT]
Project: ${projectName}
Files: ${data.metrics?.files_watched || 0} monitored
Changes: ${data.metrics?.changes_detected || 0} detected
[END CONTEXT]`;

            return context;
        }
    } catch (error) {
        console.warn('Could not fetch context:', error);
    }
    return '';
}

// ========================================
// INTERCEPTION SETUP
// ========================================

function setupInterception() {
    if (!currentPlatform) return;

    const submitButton = document.querySelector(currentPlatform.selectors.submit);

    if (!submitButton) {
        setTimeout(setupInterception, 1000);
        return;
    }

    console.log(`✅ Vidurai interception ready for ${currentPlatform.name}`);

    const inputElement = document.querySelector(currentPlatform.selectors.input);

    if (inputElement) {
        // Strategy 1: Inject on focus
        inputElement.addEventListener('focus', async () => {
            if (!viduraiEnabled || daemonStatus !== 'connected') return;
            if (contextInjected) return;

            const context = await getProjectContext();

            if (context && context.trim()) {
                const success = reactInjector.inject(
                    currentPlatform.selectors.input,
                    context
                );

                if (success) {
                    contextInjected = true;
                    showNotification(
                        `Context ready (${currentPlatform.name})`,
                        'success'
                    );

                    setTimeout(() => {
                        contextInjected = false;
                    }, 5000);
                }
            }
        });

        // Strategy 2: Inject on first keypress (backup)
        inputElement.addEventListener('keydown', async (e) => {
            if (contextInjected) return;
            if (!viduraiEnabled || daemonStatus !== 'connected') return;

            if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
                const context = await getProjectContext();

                if (context && context.trim()) {
                    setTimeout(() => {
                        reactInjector.inject(
                            currentPlatform.selectors.input,
                            context
                        );
                        contextInjected = true;

                        showNotification(
                            `Context injected (${currentPlatform.name})`,
                            'success'
                        );
                    }, 50);
                }
            }
        }, { once: true });
    }
}

// ========================================
// UI FUNCTIONS
// ========================================

// Show notification
function showNotification(message, type = 'info') {
  const colors = {
    success: '#10b981',
    info: currentPlatform?.color || '#8b5cf6',
    warning: '#f59e0b',
    error: '#ef4444'
  };

  const notification = document.createElement('div');
  notification.textContent = `🧠 ${message}`;
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${colors[type]};
    color: white;
    padding: 12px 24px;
    border-radius: 8px;
    z-index: 999999;
    font-family: system-ui, -apple-system, sans-serif;
    font-size: 14px;
    font-weight: 500;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    animation: slideIn 0.3s ease;
    pointer-events: none;
  `;

  document.body.appendChild(notification);

  setTimeout(() => {
    notification.style.transition = 'opacity 0.5s, transform 0.5s';
    notification.style.opacity = '0';
    notification.style.transform = 'translateX(20px)';
    setTimeout(() => notification.remove(), 500);
  }, 3000);
}

// Status indicator in corner
function createStatusIndicator() {
  const indicator = document.createElement('div');
  indicator.id = 'vidurai-status';
  indicator.style.cssText = `
    position: fixed;
    bottom: 20px;
    right: 20px;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: #6b7280;
    z-index: 999998;
    transition: background 0.3s;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  `;

  indicator.title = 'Vidurai: Checking...';
  document.body.appendChild(indicator);

  return indicator;
}

function updateStatusIndicator() {
  let indicator = document.getElementById('vidurai-status');
  if (!indicator) {
    indicator = createStatusIndicator();
  }

  const statuses = {
    connected: { color: '#10b981', text: 'Vidurai: Connected' },
    disconnected: { color: '#ef4444', text: 'Vidurai: Daemon offline' },
    checking: { color: '#f59e0b', text: 'Vidurai: Checking...' }
  };

  const status = statuses[daemonStatus] || statuses.checking;
  indicator.style.background = status.color;
  indicator.title = status.text;
}

// Listen for messages from background script
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'DAEMON_STATUS') {
    daemonStatus = request.status;
    updateStatusIndicator();

    if (request.status === 'connected') {
      showNotification('Daemon connected', 'success');
    }
  }

  if (request.type === 'DAEMON_EVENT') {
    const event = request.data;

    if (event.event === 'file_changed') {
      console.log('📝 File changed:', event.filename);
      // Could show subtle notification here
    }
  }
});

// Initialize
checkDaemonStatus();
setupInterception();
updateStatusIndicator();

// Periodic status check
setInterval(checkDaemonStatus, 10000); // Every 10 seconds
