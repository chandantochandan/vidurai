# ⚠️ STATUS: EXPERIMENTAL
> This component is an early prototype (v0.5.1). Use the VS Code extension for production.

# Vidurai Universal Browser Extension 🌉

**Version:** 0.3.0
**Phase 2.5 - Day 3: "The Bridge"**

## Overview

Universal browser extension that injects project context from the Ghost Daemon into any AI chat interface. Works with ChatGPT, Claude.ai, Gemini, Perplexity, Phind, You.com, and more.

## Features

 **Universal AI Platform Support**
- ChatGPT (chat.openai.com, chatgpt.com)
- Claude.ai
- Google Gemini
- Perplexity AI
- Phind
- You.com

 **Real-time Daemon Connection**
- WebSocket connection to Ghost Daemon (port 7777)
- Live status indicator in bottom-right corner
- Automatic reconnection on disconnect

 **Smart Context Injection**
- Auto-detects current project from daemon
- Prepends context before sending messages
- Shows notification on successful injection
- Non-intrusive: only activates when daemon is connected

 **Beautiful Popup Interface**
- Live daemon status
- Project & file count metrics
- Quick access to dashboard
- Responsive design with gradient UI

## Architecture

### Files

```
vidurai-browser-extension/
├── manifest.json (51 lines) - Extension configuration
├── background.js (115 lines) - Service worker, WebSocket connection
├── content.js (309 lines) - Universal AI platform injection
├── popup/
│ ├── popup.html (172 lines) - Extension popup UI
│ └── popup.js (53 lines) - Popup logic & metrics
└── icons/
 ├── icon16.png (508 bytes) - 3 Kosha icon
 ├── icon48.png (1.2 KB) - 3 Kosha icon
 └── icon128.png (2.7 KB) - 3 Kosha icon
```

**Total:** 700 lines of code

### Platform Detection

The extension automatically detects which AI platform you're on and adapts:

- **ChatGPT**: Detects `textarea[data-id]` for input
- **Claude.ai**: Detects `div[contenteditable="true"]` for input
- **Gemini**: Uses Google's contenteditable divs
- **Others**: Configurable selectors in AI_PLATFORMS object

### Context Format

When you send a message, Vidurai prepends:

```
[VIDURAI CONTEXT - Current Project: vidurai]
Files monitored: 390
Recent activity: 1647945 changes
[END CONTEXT]

Your original message here...
```

## Installation

### 1. Ensure Daemon is Running

```bash
cd /home/user/vidurai/vidurai-daemon
python3 daemon.py &
```

Verify it's running:
```bash
curl http://localhost:7777/health
```

### 2. Load Extension in Chrome/Edge

1. Open `chrome://extensions` (or `edge://extensions`)
2. Enable **Developer mode** (top-right toggle)
3. Click **Load unpacked**
4. Select: `/home/user/vidurai/vidurai-browser-extension`

### 3. Verify Installation

- Extension icon appears in toolbar (3 Kosha icon)
- Click icon to see popup
- Status should show "Daemon Connected" (green dot)
- Projects & Files metrics should appear

## Testing

### Test on Multiple AI Platforms

1. **ChatGPT** - Visit https://chat.openai.com
 - Type a message (don't send)
 - Click send button
 - Should see: " Context injected (ChatGPT)" notification
 - Green dot in bottom-right corner

2. **Claude.ai** - Visit https://claude.ai
 - Same behavior as above
 - Color: purple (#8b5cf6)

3. **Gemini** - Visit https://gemini.google.com
 - Same behavior
 - Color: blue (#4285f4)

### Expected Behavior

 Green dot in bottom-right = Daemon connected
 Red dot = Daemon offline (context injection disabled)
 Orange dot = Checking daemon status

 Notification appears when context is injected
 Message includes [VIDURAI CONTEXT] prefix
 Popup shows live metrics

### Debugging

Open browser DevTools Console (F12) to see:
- ` Vidurai Universal Extension loaded`
- ` Vidurai active on ChatGPT` (or other platform)
- ` Vidurai interception ready for ChatGPT`
- `📨 Received from daemon: {...}` (WebSocket events)

## WebSocket Events

The extension receives real-time events from the daemon:

```javascript
{
 "event": "file_changed",
 "path": "/home/user/vidurai/test.txt",
 "project": "/home/user/vidurai",
 "filename": "test.txt",
 "timestamp": "2025-11-19T20:40:00.000000"
}
```

These events are logged to console and could be used for live notifications.

## API Integration

### Background ↔ Daemon

- **WebSocket**: `ws://localhost:7777/ws` (real-time events)
- **HTTP**: `http://localhost:7777/health` (status checks)
- **HTTP**: `http://localhost:7777/metrics` (project context)

### Content Script ↔ Background

- `CHECK_DAEMON` - Request daemon status
- `GET_CONTEXT` - Fetch project metrics
- `DAEMON_STATUS` - Status update broadcast
- `DAEMON_EVENT` - File change event broadcast

## Security

- Only connects to localhost (daemon)
- CORS properly configured on daemon
- No external network requests
- Context injection only when user sends message

## Platform-Specific Notes

### ChatGPT (chat.openai.com)
- Uses `textarea[data-id]` selector
- Submit button: `button[data-testid="send-button"]`
- Input type: textarea

### Claude.ai
- Uses `div[contenteditable="true"]` selector
- Submit button: `button[aria-label="Send Message"]`
- Input type: contenteditable
- Requires textContent manipulation

### Gemini (gemini.google.com)
- Uses `div[contenteditable="true"]` selector
- Submit button: `button[aria-label*="Send"]` (wildcard match)
- Input type: contenteditable

### Adding New Platforms

Edit `content.js` and add to `AI_PLATFORMS` object:

```javascript
'example.com': {
 name: 'Example AI',
 color: '#ff00ff',
 selectors: {
 input: 'textarea',
 submit: 'button[type="submit"]',
 inputType: 'textarea'
 }
}
```

Then add to `manifest.json` permissions and content_scripts.

## Daemon Requirements

The daemon must expose these endpoints:

- `GET /health` - Returns `{status, version, watched_projects, metrics}`
- `GET /metrics` - Returns `{projects_list, files_watched, changes_detected}`
- `WS /ws` - WebSocket for real-time events

Current daemon version: **2.5.0** 

## Known Limitations

1. **Input Detection**: Some AI platforms change their DOM frequently, selectors may need updating
2. **Send Interception**: Uses click event capture, may conflict with platform's own handlers
3. **Context Size**: No limit on context injection, large projects could exceed token limits
4. **Single Project**: Always uses first project from daemon's list

## Future Enhancements (Day 4+)

- [ ] Multi-project selector in popup
- [ ] Context preview before sending
- [ ] Token count estimation
- [ ] Smart context filtering (only include relevant files)
- [ ] Keyboard shortcut to toggle injection
- [ ] File change notifications in UI
- [ ] Support for more AI platforms

---

विस्मृति भी विद्या है
**"Forgetting too is knowledge"**

**Day 3 Status:** COMPLETE - The Bridge is built! 🌉
