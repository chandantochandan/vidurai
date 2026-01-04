# Vidurai VS Code Extension - Testing Guide

## Pre-flight Checks

Before testing in VS Code, verify the setup:

```bash
cd ~/vidurai/vidurai-vscode-extension

# 1. Verify compiled output exists
ls out/*.js
# Should see: extension.js, pythonBridge.js, installer.js, statusBar.js, utils.js

# 2. Test Python bridge communication
node test-bridge.js
# Should see: Bridge test PASSED!

# 3. Verify Python has Vidurai installed
python-bridge/.venv/bin/python -c "import vidurai; print('Vidurai version:', vidurai.__version__)"
```

## Manual Testing in VS Code

### 1. Launch Extension Development Host

```bash
cd ~/vidurai/vidurai-vscode-extension
code .
```

In VS Code:
- Press **F5** (or Run → Start Debugging)
- A new window opens: `[Extension Development Host]`
- Wait ~5 seconds for activation

### 2. Test Checklist

#### Test 1: Extension Activation
**Steps:**
1. Look at bottom-right status bar
2. Should see: `$(database) 0` or `$(database) Vidurai: Offline`

**Expected Result:**
- Status bar item appears
- No error notifications

**Pass Criteria:** Status bar shows database icon

---

#### Test 2: Show Logs
**Steps:**
1. Press `Ctrl+Shift+P` (Mac: `Cmd+Shift+P`)
2. Type: `Vidurai: Show Logs`
3. Press Enter

**Expected Result:**
```
[2024-XX-XX...] [INFO] Vidurai extension activating...
[2024-XX-XX...] [INFO] Checking Python and Vidurai installation...
[2024-XX-XX...] [INFO] Found Python: python3
[2024-XX-XX...] [INFO] Vidurai SDK already installed
[2024-XX-XX...] [INFO] Starting Python bridge...
[2024-XX-XX...] [INFO] Bridge started successfully
[2024-XX-XX...] [INFO] Vidurai extension activated successfully
```

**Pass Criteria:** Logs show successful activation with no errors

---

#### Test 3: Copy Context Command
**Steps:**
1. Press `Ctrl+Shift+P`
2. Type: `Vidurai: Copy Relevant Context`
3. Press Enter

**Expected Result:**
- Notification: ` Copied 0 memories to clipboard!`
- (0 is expected - no files tracked yet)

**Pass Criteria:** Command executes without errors

---

#### Test 4: Restart Bridge
**Steps:**
1. Press `Ctrl+Shift+P`
2. Type: `Vidurai: Restart Python Bridge`
3. Press Enter

**Expected Result:**
- Notification: ` Vidurai bridge restarted`
- Status bar briefly shows "Offline" then returns to memory count
- Logs show: `Restarting bridge` → `Bridge started successfully`

**Pass Criteria:** Bridge restarts without errors

---

#### Test 5: Status Bar Interaction
**Steps:**
1. Click the status bar item: `$(database) 0`

**Expected Result:**
- Same as Test 3 (Copy Context)
- Notification: ` Copied 0 memories to clipboard!`

**Pass Criteria:** Click triggers copy context command

---

#### Test 6: Bridge Crash Recovery (Optional)
**Steps:**
1. Open terminal
2. Find bridge process: `ps aux | grep bridge.py`
3. Kill it: `kill -9 <PID>`
4. Watch status bar and logs

**Expected Result:**
- Status bar shows: `$(database) Vidurai: Error`
- Logs show: `Bridge exited with code: -9`
- Notification: `⚠️ Vidurai bridge crashed (attempt 1/3). Restarting...`
- Bridge auto-restarts after 2 seconds

**Pass Criteria:** Auto-recovery works

---

## Test Results Template

Copy and fill out:

```
## Vidurai Extension Test Results

**Date:** [YYYY-MM-DD]
**Tester:** [Your Name]
**Platform:** [Linux/Mac/Windows]
**VS Code Version:** [e.g., 1.85.0]

### Results:

- [ ] Test 1: Extension Activation - PASS/FAIL
- [ ] Test 2: Show Logs - PASS/FAIL
- [ ] Test 3: Copy Context - PASS/FAIL
- [ ] Test 4: Restart Bridge - PASS/FAIL
- [ ] Test 5: Status Bar Interaction - PASS/FAIL
- [ ] Test 6: Bridge Crash Recovery - PASS/FAIL (Optional)

### Issues Encountered:

[List any issues, errors, or unexpected behavior]

### Logs (if errors):

```
[Paste relevant log lines]
```

### Screenshots:

[Optional: Attach screenshots of status bar, notifications, etc.]

### Notes:

[Any additional observations]
```

---

## Troubleshooting

### Issue: "Python not found"

**Symptoms:** Error dialog on activation

**Solution:**
```bash
# Check Python installation
python3 --version
# or
python --version

# If not installed:
# Ubuntu/Debian: sudo apt install python3
# Mac: brew install python3
# Windows: Download from python.org
```

---

### Issue: "Vidurai SDK not installed"

**Symptoms:** Installation prompt appears

**Solution:**
- Click "Install Automatically" (requires internet)
- Wait for notification: ` Vidurai SDK installed successfully!`

**Manual Install:**
```bash
pip install vidurai==1.6.1
```

---

### Issue: Bridge won't start

**Symptoms:** Status bar shows "Offline", logs show errors

**Debug Steps:**
```bash
# 1. Test bridge manually
cd ~/vidurai/vidurai-vscode-extension
python-bridge/.venv/bin/python python-bridge/bridge.py

# 2. Send ping
echo '{"type":"ping"}' | python-bridge/.venv/bin/python python-bridge/bridge.py

# 3. Check Python module imports
python-bridge/.venv/bin/python -c "from vidurai import VismritiMemory; print('OK')"
```

---

### Issue: Commands not appearing in palette

**Symptoms:** Can't find "Vidurai: ..." commands

**Solution:**
1. Check extension is activated: Look for status bar item
2. Reload window: `Ctrl+Shift+P` → "Reload Window"
3. Check logs for activation errors

---

## Advanced Testing

### Test File Tracking (Phase 3+)

Not yet implemented. Will be added in Phase 3.

### Test Terminal Tracking (Phase 3+)

Not yet implemented. Will be added in Phase 3.

### Test Diagnostic Tracking (Phase 3+)

Not yet implemented. Will be added in Phase 3.

---

## Automated Tests

```bash
# Run bridge communication test
npm test # (Not yet implemented)

# Or use our custom test:
node test-bridge.js
```

---

## Performance Benchmarks

Track these metrics during testing:

- Extension activation time: ~1-2 seconds
- Bridge startup time: ~0.5 seconds
- Copy context response time: <1 second
- Status bar update frequency: Every 10 seconds
- Memory usage: ~50MB (extension + bridge)

---

## Next Steps

After successful testing:
1. Report results using template above
2. File any bugs found on GitHub
3. Ready for Phase 3 implementation (event tracking)
