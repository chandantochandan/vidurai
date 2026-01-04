# Vidurai Troubleshooting Guide

**Version:** 2.2.0

This guide helps you diagnose and fix common issues with Vidurai.

---

## Quick Diagnostic Commands

```bash
# Check if daemon is running
vidurai status

# View recent logs
vidurai logs -n 50

# Follow logs in real-time
vidurai logs -f

# Check installation
vidurai info
```

---

## Daemon Issues

### Daemon Won't Start

**Symptoms:**
- `vidurai start` shows error
- Status shows "Stopped" immediately after start

**Solutions:**

1. **Check for stale PID file:**
   ```bash
   rm ~/.vidurai/daemon.pid
   vidurai start
   ```

2. **Check log file for errors:**
   ```bash
   vidurai logs -n 100
   ```

3. **Port conflict (if using MCP server):**
   ```bash
   lsof -i :7777  # Check if port is in use
   ```

4. **Missing dependencies:**
   ```bash
   pip install --upgrade vidurai
   ```

### Daemon Crashes After Start

**Symptoms:**
- Daemon starts but stops within seconds
- Log shows import errors or exceptions

**Solutions:**

1. **Check Python version (requires 3.9+):**
   ```bash
   python3 --version
   ```

2. **Reinstall with all dependencies:**
   ```bash
   pip uninstall vidurai
   pip install vidurai
   ```

3. **Check disk space for ~/.vidurai:**
   ```bash
   df -h ~/.vidurai
   ```

### Stale Lock / Zombie Process

**Symptoms:**
- "Already running" but no process exists
- PID in daemon.pid doesn't match any process

**Solution:**
Vidurai v2.2.0 includes automatic stale lock detection via `psutil`. If you still encounter issues:

```bash
# Manual cleanup
rm ~/.vidurai/daemon.pid
vidurai start
```

---

## VS Code Extension Issues

### Extension Not Connecting

**Symptoms:**
- Status bar shows "Disconnected" (red)
- No context being captured

**Solutions:**

1. **Start the daemon first:**
   ```bash
   vidurai start
   vidurai status  # Should show "Running"
   ```

2. **Check IPC socket exists:**
   ```bash
   ls -la /tmp/vidurai-*.sock  # Linux/Mac
   ```

3. **Reload VS Code window:**
   - Command Palette > "Developer: Reload Window"

4. **Check extension logs:**
   - Output panel > Select "Vidurai"

### Extension Buffer Growing

**Symptoms:**
- `~/.vidurai/buffer-*.jsonl` files accumulating
- Extension shows "Offline" frequently

**Cause:** Daemon was unavailable, events buffered to disk.

**Solution:**
```bash
# Start daemon - buffers will drain automatically
vidurai start

# Verify buffers are processed
ls ~/.vidurai/buffer-*.jsonl  # Should be empty/gone
```

---

## Cursor Editor Issues

### Extension Not Installing

**Symptoms:**
- Drag-drop .vsix doesn't work
- Extension not appearing in Cursor

**Solution - Use CLI installation:**
```bash
cursor --install-extension vidurai-extension.vsix
```

### Cursor Not Connecting to Daemon

**Symptoms:**
- Same as VS Code connection issues

**Solutions:**

1. **Ensure daemon is running:**
   ```bash
   vidurai status
   ```

2. **Check Cursor is using correct extension:**
   - Cursor uses VS Code extension ecosystem
   - Ensure only one Vidurai extension is installed

3. **Restart Cursor completely:**
   - Close all Cursor windows
   - Kill any background processes
   - Restart

---

## Claude Desktop (MCP) Issues

### MCP Server Not Found

**Symptoms:**
- Claude Desktop doesn't show Vidurai tools
- Error: "Server vidurai not found"

**Solutions:**

1. **Verify config location:**
   - Linux/Mac: `~/.config/claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`

2. **Use auto-installer:**
   ```bash
   vidurai mcp-install --status  # Check current config
   vidurai mcp-install           # Install/repair
   ```

3. **Manual config:**
   ```json
   {
     "mcpServers": {
       "vidurai": {
         "command": "vidurai",
         "args": ["server"]
       }
     }
   }
   ```

4. **Restart Claude Desktop** after config changes.

### MCP Tools Not Working

**Symptoms:**
- Tools appear but return errors
- "Connection refused" errors

**Solution:**
Ensure daemon is running before starting Claude Desktop:
```bash
vidurai start
# Then start Claude Desktop
```

---

## Memory & Storage Issues

### Database Locked

**Symptoms:**
- "database is locked" errors
- Operations timeout

**Solutions:**

1. **Check for multiple daemon instances:**
   ```bash
   ps aux | grep vidurai
   # Kill duplicates if found
   ```

2. **Enable WAL mode (should be default):**
   ```bash
   sqlite3 ~/.vidurai/memory.db "PRAGMA journal_mode=WAL;"
   ```

### Disk Space Issues

**Symptoms:**
- Logs growing too large
- Archive folder filling up

**Solutions:**

1. **Check log rotation (should be automatic):**
   ```bash
   ls -la ~/.vidurai/vidurai.log*
   # Should see rotated files: vidurai.log, vidurai.log.1, etc.
   ```

2. **Clear old archives:**
   ```bash
   # Archives older than 90 days
   find ~/.vidurai/archive -type f -mtime +90 -delete
   ```

3. **Run hygiene to prune memories:**
   ```bash
   vidurai hygiene --force
   ```

---

## PII Concerns

### Sensitive Data in Logs

**Symptoms:**
- Worried about API keys in logs
- Need to verify PII redaction

**Verification:**
```bash
# Check logs for common patterns (should be redacted)
grep -E "(sk-|AKIA|password)" ~/.vidurai/vidurai.log
# Should return nothing or show <REDACTED> patterns
```

The Gatekeeper redacts 60+ patterns including:
- API keys (OpenAI, AWS, etc.)
- Passwords and secrets
- Email addresses
- Connection strings

See [SECURITY.md](SECURITY.md) for full list.

---

## Getting Help

If none of these solutions work:

1. **Collect diagnostic info:**
   ```bash
   vidurai info > vidurai-debug.txt
   vidurai logs -n 200 >> vidurai-debug.txt
   ```

2. **Open an issue:**
   - GitHub: https://github.com/chandantochandan/vidurai/issues
   - Include: Python version, OS, error messages, steps to reproduce

---

*Vidurai v2.2.0 - Troubleshooting Guide*
