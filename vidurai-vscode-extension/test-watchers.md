# Testing Watchers in Phase 3

This guide explains how to test the file, terminal, and diagnostic watchers.

## Setup

1. **Compile the extension:**
 ```bash
 cd ~/vidurai/vidurai-vscode-extension
 npm run compile
 ```

2. **Open VS Code:**
 ```bash
 code .
 ```

3. **Launch Extension Development Host:**
 - Press `F5`
 - Wait for extension to activate
 - Check status bar shows `$(database) 0`

## Test 1: File Edit Tracking

**Steps:**
1. In the Extension Development Host, create a new file: `test.js`
2. Type some code:
 ```javascript
 function hello() {
 console.log("Hello World");
 }
 ```
3. Wait 2 seconds (debounce delay)
4. Open Command Palette: `Ctrl+Shift+P`
5. Run: `Vidurai: Show Logs`
6. Look for: `[DEBUG] Sending file edit: .../test.js`
7. Run: `Vidurai: Copy Relevant Context`
8. Should see: ` Copied 1 memories to clipboard!`

**Expected Result:**
- Logs show file edit sent
- Status bar updates to `$(database) 1`
- Clipboard contains file edit gist

---

## Test 2: File Save Tracking

**Steps:**
1. Continue editing `test.js`
2. Press `Ctrl+S` to save
3. Check logs immediately (no 2-second wait)
4. Should see: `[DEBUG] File saved: .../test.js`

**Expected Result:**
- File save triggers immediate tracking (no debounce)
- New memory created

---

## Test 3: Large File Ignored

**Steps:**
1. Create a new file: `large.js`
2. Paste a very large text (>50KB)
3. Wait 2 seconds
4. Check logs
5. Should see: `[DEBUG] Ignoring large file: .../large.js (xxxxx bytes)`

**Expected Result:**
- Large files are ignored
- No memory created

---

## Test 4: Ignored Paths

**Steps:**
1. Create directory: `node_modules`
2. Create file: `node_modules/test.js`
3. Edit the file
4. Wait 2 seconds
5. Check logs

**Expected Result:**
- File in node_modules is ignored
- No memory created

---

## Test 5: Diagnostic Tracking (Errors)

**Steps:**
1. Create a new file: `error.js`
2. Type invalid JavaScript:
 ```javascript
 function broken() {
 console.log("missing semicolon"
 // Missing closing parenthesis
 }
 ```
3. Check logs for: `[DEBUG] Sending diagnostic: error in error.js`
4. Run: `Vidurai: Copy Relevant Context`
5. Should see error in memories

**Expected Result:**
- Error diagnostic tracked
- Memory shows error message with line number

---

## Test 6: Secrets Detection

**Steps:**
1. Create new file: `secrets.js`
2. Type:
 ```javascript
 const API_KEY = "sk-abcd1234567890abcd1234567890abcd1234567890abcd12";
 ```
3. Wait 2 seconds
4. Should see warning: `⚠️ Secrets detected in secrets.js - content sanitized`

**Expected Result:**
- Secrets detected
- Content sanitized before storing
- Warning notification shown

---

## Test 7: Multiple Files

**Steps:**
1. Create 3 files: `a.js`, `b.js`, `c.js`
2. Edit each file
3. Wait 2 seconds after each
4. Run: `Vidurai: Copy Relevant Context`
5. Should see: ` Copied 3 memories to clipboard!`

**Expected Result:**
- Status bar shows `$(database) 3` (or more)
- All 3 files tracked

---

## Test 8: Debouncing

**Steps:**
1. Create new file: `debounce.js`
2. Type continuously for 5 seconds without stopping
3. Check logs - should NOT see "Sending file edit" during typing
4. Stop typing for 2 seconds
5. NOW should see: `[DEBUG] Sending file edit`

**Expected Result:**
- File edit NOT sent while typing
- File edit sent 2 seconds after stopping

---

## Test 9: Terminal Tracking (Limited)

**Note:** VS Code API doesn't allow direct terminal output capture.

**Steps:**
1. Open terminal in Extension Development Host
2. Check logs for: `Terminal opened: bash` (or similar)
3. Close terminal
4. Check logs for: `Terminal closed: bash`

**Expected Result:**
- Terminal lifecycle tracked (open/close)
- Command output NOT tracked (API limitation)

---

## Test 10: Configuration Changes

**Steps:**
1. Open Settings: `Ctrl+,`
2. Search: `vidurai`
3. Change `Vidurai: Debounce Ms` from 2000 to 500
4. Edit a file
5. Should see tracking happen after 500ms instead of 2 seconds

**Expected Result:**
- Configuration changes take effect immediately

---

## Verification Checklist

After all tests:

- [ ] File edits tracked with debouncing
- [ ] File saves tracked immediately
- [ ] Large files ignored (>50KB)
- [ ] Ignored paths work (node_modules, .git, etc.)
- [ ] Diagnostics tracked (errors and warnings)
- [ ] Secrets detected and sanitized
- [ ] Status bar updates with memory count
- [ ] Copy Context shows tracked memories
- [ ] No performance issues during typing
- [ ] Logs show all events

---

## Troubleshooting

### Issue: File edits not tracked

**Check:**
- Is bridge running? (status bar should show number, not "Offline")
- Check logs for errors
- Verify file is not in ignored path
- Verify file size < 50KB

### Issue: Status bar not updating

**Check:**
- Is status bar update interval working? (updates every 10 seconds)
- Manually trigger update: Restart bridge
- Check bridge is responding: Run "Copy Context"

### Issue: Too many memories

**Solution:**
- Vidurai's intelligent forgetting will naturally prune low-salience memories
- Or clear session: Delete `~/.vidurai/sessions/default.pkl` and restart

---

## Performance Notes

- File edit debouncing prevents spam during typing
- Large files ignored to prevent memory issues
- Diagnostic tracking uses deduplication to prevent duplicates
- Status bar updates every 10 seconds (configurable)

---

## Next Steps

After successful Phase 3 testing:
1. Document any issues found
2. Tune debounce timing if needed
3. Adjust ignored paths if needed
4. Ready for Phase 4 (UI enhancements and packaging)
