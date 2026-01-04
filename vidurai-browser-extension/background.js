/**
 * Vidurai Browser Extension - Background Service Worker
 * Manages WebSocket connection to daemon
 */

console.log('🧠 Vidurai background service worker loaded');

let daemonConnection = null;
const DAEMON_WS = 'ws://localhost:7777/ws';
const DAEMON_HTTP = 'http://localhost:7777';

// Connect to daemon
function connectToDaemon() {
  try {
    daemonConnection = new WebSocket(DAEMON_WS);

    daemonConnection.onopen = () => {
      console.log('✅ Connected to Vidurai Daemon');
      chrome.storage.local.set({ daemonStatus: 'connected' });

      // Notify all tabs
      chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
          chrome.tabs.sendMessage(tab.id, {
            type: 'DAEMON_STATUS',
            status: 'connected'
          }).catch(() => {}); // Ignore errors for tabs without content script
        });
      });
    };

    daemonConnection.onmessage = (event) => {
      const data = JSON.parse(event.data);
      console.log('📨 Received from daemon:', data);

      // Forward to all content scripts
      chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
          chrome.tabs.sendMessage(tab.id, {
            type: 'DAEMON_EVENT',
            data: data
          }).catch(() => {});
        });
      });
    };

    daemonConnection.onerror = (error) => {
      console.warn('⚠️  Daemon connection error:', error);
      chrome.storage.local.set({ daemonStatus: 'error' });
    };

    daemonConnection.onclose = () => {
      console.log('🔌 Daemon disconnected, reconnecting in 5s...');
      chrome.storage.local.set({ daemonStatus: 'disconnected' });

      // Notify tabs
      chrome.tabs.query({}, (tabs) => {
        tabs.forEach(tab => {
          chrome.tabs.sendMessage(tab.id, {
            type: 'DAEMON_STATUS',
            status: 'disconnected'
          }).catch(() => {});
        });
      });

      // Retry connection
      setTimeout(connectToDaemon, 5000);
    };
  } catch (error) {
    console.error('Failed to connect to daemon:', error);
    setTimeout(connectToDaemon, 5000);
  }
}

// Start connection on install/startup
chrome.runtime.onInstalled.addListener(() => {
  console.log('🚀 Vidurai extension installed');
  connectToDaemon();
});

chrome.runtime.onStartup.addListener(() => {
  console.log('🚀 Vidurai extension started');
  connectToDaemon();
});

// Handle messages from content scripts
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'GET_CONTEXT') {
    // Fetch context from daemon
    fetch(`${DAEMON_HTTP}/metrics`)
      .then(res => res.json())
      .then(data => {
        sendResponse({ success: true, data: data });
      })
      .catch(error => {
        sendResponse({ success: false, error: error.message });
      });
    return true; // Will respond asynchronously
  }

  if (request.type === 'CHECK_DAEMON') {
    fetch(`${DAEMON_HTTP}/health`)
      .then(res => res.json())
      .then(data => {
        sendResponse({ success: true, status: 'connected', data: data });
      })
      .catch(error => {
        sendResponse({ success: false, status: 'disconnected' });
      });
    return true;
  }
});

// Initialize
connectToDaemon();
