/**
 * Vidurai Extension Popup
 */

// Update status display
async function updateStatus() {
  try {
    const response = await chrome.runtime.sendMessage({ type: 'CHECK_DAEMON' });

    const statusEl = document.getElementById('status');
    const statusDot = document.getElementById('statusDot');
    const statusText = document.getElementById('statusText');

    if (response.success) {
      statusEl.className = 'status connected';
      statusDot.className = 'dot connected';
      statusText.textContent = 'Daemon Connected';

      // Update metrics
      if (response.data) {
        document.getElementById('projects').textContent =
          response.data.watched_projects || '0';
        document.getElementById('files').textContent =
          response.data.metrics?.files_watched || '0';
      }
    } else {
      statusEl.className = 'status disconnected';
      statusDot.className = 'dot disconnected';
      statusText.textContent = 'Daemon Offline';

      document.getElementById('projects').textContent = '-';
      document.getElementById('files').textContent = '-';
    }
  } catch (error) {
    console.error('Failed to update status:', error);
  }
}

// Open dashboard
document.getElementById('openDashboard').addEventListener('click', () => {
  chrome.tabs.create({ url: 'http://localhost:7777' });
});

// Refresh status
document.getElementById('refreshStatus').addEventListener('click', () => {
  updateStatus();
});

// Initialize
updateStatus();

// Auto-refresh every 5 seconds
setInterval(updateStatus, 5000);
