# Vidurai Troubleshooting Guide

**Status:** v2.0.1
**Last Updated:** 7 December 2025
**Verified From:** Actual source code audit

This guide covers common issues when running the Vidurai Daemon, VS Code Extension, and SDK.

---

## Quick Health Check

Run this first to verify system status:

```bash
# 1. Is daemon running?
curl -s http://localhost:7777/health | python3 -m json.tool

# Expected output:
# {
#     "status": "alive",
#     "version": "2.0.1",
#     "uptime_seconds": 123.45,
#     "uptime_human": "0h 2m",
#     "ipc": {
#         "enabled": true,
#         "pipe_path": "/tmp/vidurai-user.sock",
#         "clients": 1
#     }
# }

# 2. Is database accessible?
sqlite3 ~/.vidurai/memory.db "SELECT COUNT(*) FROM memories;"

# 3. Is IPC pipe listening?
# Linux/Mac:
ls -la /tmp/vidurai-$USER.sock
# Windows (PowerShell):
# Get-ChildItem \\.\pipe\ | Where-Object { $_.Name -match "vidurai" }
```

---

## Startup Errors (Daemon)

### 1. `[Errno 98] Address already in use`

**Symptom:** The daemon crashes immediately on launch.

**Cause:** Another instance of Vidurai is already running. Vidurai is a **Singleton** system.

**Solution:**
```bash
# Check if daemon is already running
curl -s http://localhost:7777/health

# If it returns JSON, daemon is already running - you're good!
# If connection refused, find and kill the orphan:
lsof -i :7777
kill -9 <PID>

# Then restart
cd /home/user/vidurai/vidurai-daemon && python3 daemon.py
```

### 2. `ModuleNotFoundError: No module named 'vidurai'`

**Symptom:** Running `python daemon.py` fails with import errors.

**Cause:** Python cannot find the SDK source code.

**Solution:**
```bash
# Option A (User): Install the package properly
pip install vidurai

# Option B (Developer): Set PYTHONPATH to the project root
export PYTHONPATH=$PYTHONPATH:/home/user/vidurai
python3 vidurai-daemon/daemon.py

# Option C (Persistent): Add to ~/.bashrc
echo 'export PYTHONPATH=$PYTHONPATH:/home/user/vidurai' >> ~/.bashrc
source ~/.bashrc
```

### 3. `ModuleNotFoundError: No module named 'pyarrow'`

**Symptom:** The Daemon starts, but crashes when the "Archiver" runs (or logs a warning).

**Cause:** Cold Storage requires `pyarrow` C++ binaries.

**Solution:**
```bash
pip install pyarrow>=14.0.0
```

### 4. `sqlite3.OperationalError: database is locked`

**Symptom:** Random write failures, timeout errors.

**Cause:** Multiple processes trying to write simultaneously (shouldn't happen with Queue-Based Actor).

**Solution:**
```bash
# Check WAL mode is enabled
sqlite3 ~/.vidurai/memory.db "PRAGMA journal_mode;"
# Should return: wal

# If not, enable it:
sqlite3 ~/.vidurai/memory.db "PRAGMA journal_mode=WAL;"

# Restart daemon to ensure single writer thread
pkill -f "python.*daemon.py"
python3 vidurai-daemon/daemon.py
```

### 5. Daemon starts but IPC server fails

**Symptom:** HTTP endpoints work, but VS Code can't connect.

**Cause:** Socket file from previous session still exists.

**Solution:**
```bash
# Remove stale socket (Linux/Mac)
rm -f /tmp/vidurai-$USER.sock

# Restart daemon
pkill -f "python.*daemon.py"
python3 vidurai-daemon/daemon.py
```

---

## Connection Errors (VS Code / Cursor)

### 1. Status Bar Stuck on "Connecting..." (Yellow)

**Symptom:** The "Vidurai" status bar item never turns Green.

**Cause:** The Extension cannot reach the Named Pipe.

**Checklist:**
1. Is the Daemon running? (`curl http://localhost:7777/health`)
2. Is the socket file present?
   - **Linux/Mac:** `/tmp/vidurai-$USER.sock`
   - **Windows:** `\\.\pipe\vidurai-$USERNAME`

**Actual Pipe Path Logic** (from source code):
```typescript
// vidurai-vscode-extension/src/ipc/Client.ts:115-124
function getDefaultPipePath(): string {
  const uid = process.env.USER || process.env.USERNAME || 'default';
  if (process.platform === 'win32') {
    return `\\\\.\\pipe\\vidurai-${uid}`;
  } else {
    return path.join(os.tmpdir(), `vidurai-${uid}.sock`);
  }
}
```

**Fix:**
1. Restart the Daemon first
2. Reload VS Code window: `Ctrl+Shift+P` → "Developer: Reload Window"

### 2. "Vidurai: Show Logs" is Empty

**Symptom:** The Output Panel is blank.

**Cause:** You might be looking at the wrong channel.

**Solution:**
1. Open Output Panel: `View` → `Output`
2. Select "Vidurai" from the dropdown (not "Vidurai Server" or "Log (Extension Host)")

### 3. Offline Buffer Growing Large

**Symptom:** `~/.vidurai/buffer-*.jsonl` files are accumulating.

**Cause:** Extension can't reach daemon, so events are buffered locally.

**Solution:**
```bash
# Check buffer files
ls -la ~/.vidurai/buffer-*.jsonl

# If daemon is running, force drain by reloading VS Code
# Ctrl+Shift+P → "Developer: Reload Window"

# If daemon is NOT running, start it - buffer will auto-drain on connect
python3 vidurai-daemon/daemon.py
```

---

## Intelligence Errors (Data)

### 1. "Working on unknown" / Empty Manager Report

**Symptom:** You generate a report, but it says "Status for Unknown Project".

**Cause:** The Daemon didn't receive the `project_path` in the RPC call.

**Diagnosis:**
```bash
# Check current project in daemon
curl -s http://localhost:7777/project/current | python3 -m json.tool
```

**Solution:**
1. Ensure VS Code has a workspace folder open
2. Update to VS Code Extension v2.2.0+ (enforces context transmission)
3. Manually specify project in RPC call:
```bash
curl -s http://localhost:7777/api/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "data": {
      "method": "get_context",
      "params": {
        "project": "/path/to/your/project"
      }
    }
  }'
```

### 2. "Active Errors: 1" (But file is clean)

**Symptom:** The dashboard shows an error you already fixed.

**Cause:** The "Zombie Killer" missed the fix event (severity=2/info not sent).

**Diagnosis:**
```bash
# Check active_state table
sqlite3 ~/.vidurai/memory.db "SELECT file_path, error_count, last_error_msg FROM active_state WHERE has_errors = 1;"
```

**Solution:**
1. Save the file again (triggers a re-scan)
2. If that fails, manually clear:
```bash
sqlite3 ~/.vidurai/memory.db "DELETE FROM active_state WHERE file_path = '/path/to/your/file.ts';"
```
3. Or restart daemon (clears in-memory state)

### 3. Pinned Memory Not Appearing

**Symptom:** You pinned a memory, but it doesn't show in context.

**Diagnosis:**
```bash
# Check pinned memories
sqlite3 ~/.vidurai/memory.db "SELECT id, gist, pinned FROM memories WHERE pinned = 1;"

# Via CLI
vidurai pins
```

**Solution:**
1. Verify pin was successful (check DB query above)
2. Ensure you're querying the correct project path
3. Check pin limit (max 50 per project by default)

### 4. Memories Not Being Stored

**Symptom:** You edit files but `memories` table is empty.

**Diagnosis:**
```bash
# Check if events are reaching daemon
# Look for "Stored memory" in logs
tail -f /home/user/vidurai/vidurai-daemon/daemon.log | grep -i "stored\|memory\|remember"

# Check database directly
sqlite3 ~/.vidurai/memory.db "SELECT COUNT(*) FROM memories;"
```

**Cause:** Usually one of:
- VS Code extension not connected (check status bar)
- Daemon not running SDK integration
- NOISE salience (events being filtered out)

**Solution:**
1. Verify IPC connection (status bar shows Green)
2. Check daemon logs for EventAdapter activity
3. Try storing a HIGH salience event manually:
```python
from vidurai import VismritiMemory, SalienceLevel
mem = VismritiMemory(project_path='.')
mem.remember("Test memory", metadata={'type': 'test'}, salience=SalienceLevel.HIGH)
```

---

## SDK Errors

### 1. `ImportError: cannot import name 'SalienceLevel'`

**Symptom:** Old code fails after upgrade.

**Cause:** v2.0 changed import paths.

**Solution:**
```python
# Old (v1.x):
from vidurai.core.data_structures import SalienceLevel

# New (v2.0+):
from vidurai import SalienceLevel
# or
from vidurai.core.data_structures_v3 import SalienceLevel
```

### 2. `TimeoutError: DB Write Timeout after 10s`

**Symptom:** Database operations hang then fail.

**Cause:** Queue-Based Actor writer thread is stuck or dead.

**Solution:**
```python
# Restart the SDK instance
del mem
mem = VismritiMemory(project_path='.')
```

If persistent, restart daemon entirely.

### 3. `recall()` returns empty list

**Symptom:** You stored memories but can't retrieve them.

**Diagnosis:**
```python
from vidurai import VismritiMemory
mem = VismritiMemory(project_path='.')

# Check statistics
stats = mem.get_statistics()
print(stats)  # Should show memory counts

# Try without salience filter
results = mem.recall("", min_salience=None, top_k=100)
print(f"Total memories: {len(results)}")
```

**Common causes:**
- Wrong `project_path` (memories are project-scoped)
- `min_salience` filter too high
- Memories were pruned by decay

---

## Quick Diagnostic Commands

### System Health
```bash
# Full health check
curl -s http://localhost:7777/health | python3 -m json.tool

# Brain statistics
curl -s http://localhost:7777/brain/stats | python3 -m json.tool

# Current project
curl -s http://localhost:7777/project/current | python3 -m json.tool
```

### Database Inspection
```bash
# Count memories by salience
sqlite3 ~/.vidurai/memory.db "SELECT salience, COUNT(*) FROM memories GROUP BY salience;"

# Recent memories
sqlite3 ~/.vidurai/memory.db "SELECT salience, gist, created_at FROM memories ORDER BY created_at DESC LIMIT 5;"

# Active errors
sqlite3 ~/.vidurai/memory.db "SELECT file_path, error_count FROM active_state WHERE error_count > 0;"

# Pinned memories
sqlite3 ~/.vidurai/memory.db "SELECT id, gist FROM memories WHERE pinned = 1;"

# Check WAL mode
sqlite3 ~/.vidurai/memory.db "PRAGMA journal_mode;"
```

### IPC Verification
```bash
# Check socket exists (Linux/Mac)
ls -la /tmp/vidurai-$USER.sock

# Test pipe connection (Linux/Mac)
echo '{"type":"ping"}' | nc -U /tmp/vidurai-$USER.sock

# Check offline buffer
ls -la ~/.vidurai/buffer-*.jsonl 2>/dev/null || echo "No buffer files"
```

### Process Management
```bash
# Find daemon process
pgrep -f "python.*daemon.py"
lsof -i :7777

# Kill daemon
pkill -f "python.*daemon.py"

# Start daemon (foreground for debugging)
cd /home/user/vidurai/vidurai-daemon && python3 daemon.py

# Start daemon (background)
cd /home/user/vidurai/vidurai-daemon && nohup python3 daemon.py > daemon.log 2>&1 &
```

---

## Log Locations

| Component | Log Location |
|-----------|-------------|
| **Daemon** | `vidurai-daemon/daemon.log` (if started with redirect) or stdout |
| **VS Code Extension** | VS Code → Developer Tools → Console |
| **SDK** | Uses `loguru` - defaults to stderr |

### Enable Debug Logging

```bash
# Daemon
export VIDURAI_LOG_LEVEL=DEBUG
python3 vidurai-daemon/daemon.py

# SDK
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Reset & Recovery

### Soft Reset (Keep Data)
```bash
# Restart daemon only
pkill -f "python.*daemon.py"
rm -f /tmp/vidurai-$USER.sock
python3 vidurai-daemon/daemon.py
```

### Hard Reset (Clear Data)
```bash
# Backup first!
cp ~/.vidurai/memory.db ~/.vidurai/memory.db.backup

# Remove database and buffers
rm ~/.vidurai/memory.db
rm ~/.vidurai/buffer-*.jsonl 2>/dev/null

# Restart daemon (will recreate schema)
pkill -f "python.*daemon.py"
python3 vidurai-daemon/daemon.py
```

---

## Getting Help

Still stuck? File an issue at:
**https://github.com/chandantochandan/vidurai/issues**

Include:
1. Output of `curl http://localhost:7777/health`
2. Output of `sqlite3 ~/.vidurai/memory.db "SELECT COUNT(*) FROM memories;"`
3. VS Code extension version
4. Operating system
5. Relevant error messages

---

*Generated: December 08, 2025*
*Verified from actual source code in vidurai-daemon/ and vidurai-vscode-extension/*
