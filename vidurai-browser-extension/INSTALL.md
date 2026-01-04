# Quick Installation Guide - Vidurai Browser Extension

## Step 1: Start the Daemon

```bash
cd /home/user/vidurai/vidurai-daemon
python3 daemon.py &
```

Verify it's running:
```bash
curl http://localhost:7777/health
```

You should see:
```json
{"status": "alive", "version": "2.5.0", ...}
```

## Step 2: Install Extension in Chrome/Edge

### Chrome:
1. Open `chrome://extensions` in your browser
2. Enable **Developer mode** (toggle in top-right corner)
3. Click **Load unpacked** button
4. Navigate to: `/home/user/vidurai/vidurai-browser-extension`
5. Click **Select Folder**

### Edge:
1. Open `edge://extensions`
2. Enable **Developer mode**
3. Click **Load unpacked**
4. Select: `/home/user/vidurai/vidurai-browser-extension`

## Step 3: Verify Installation

1. Look for the Vidurai icon (3 Kosha) in your toolbar
2. Click the icon
3. Popup should show:
 - Status: **Daemon Connected** (green dot)
 - Projects: **5**
 - Files: **390** (or similar)

## Step 4: Test on AI Platform

### ChatGPT:
1. Go to https://chat.openai.com or https://chatgpt.com
2. Look for green dot in bottom-right corner (means Vidurai is active)
3. Type a test message: "Hello"
4. Click Send button
5. You should see:
 - Notification: " Context injected (ChatGPT)"
 - Your message now has `[VIDURAI CONTEXT - Current Project: ...]` prepended

### Claude.ai:
1. Go to https://claude.ai
2. Green dot should appear
3. Type and send a message
4. Purple notification: " Context injected (Claude.ai)"

### Gemini:
1. Go to https://gemini.google.com
2. Green dot appears
3. Send message
4. Blue notification: " Context injected (Gemini)"

## Troubleshooting

### Red dot in corner?
- Daemon is offline
- Check: `curl http://localhost:7777/health`
- Restart daemon: `cd /home/user/vidurai/vidurai-daemon && python3 daemon.py &`

### No notification when sending?
- Open DevTools (F12) → Console
- Look for: ` Vidurai Universal Extension loaded`
- Check for errors

### Extension not appearing?
- Make sure you selected the correct folder
- Check Chrome Extensions page for errors
- Try reloading the extension (click reload icon)

### Context not showing in message?
- Daemon must be connected (green dot)
- Check browser console for errors
- Verify daemon has projects: `curl http://localhost:7777/metrics`

## Uninstall

1. Go to `chrome://extensions`
2. Find "Vidurai - Universal AI Context"
3. Click **Remove**

## Supported Platforms

 ChatGPT (chat.openai.com, chatgpt.com)
 Claude.ai
 Google Gemini
 Perplexity AI
 Phind
 You.com

---

**Need help?** Check `/home/user/vidurai/vidurai-browser-extension/README.md` for detailed documentation.

विस्मृति भी विद्या है
