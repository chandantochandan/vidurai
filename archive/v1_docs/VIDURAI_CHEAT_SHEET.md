# Vidurai v2.0.0 - Quick Reference Cheat Sheet

## 1. Performance Tuning Commands

### Environment Variables (NOT YET IMPLEMENTED - Future)

```bash
# These are PROPOSED variables - not currently supported
# Listed here for future implementation reference

# Limit file watching per project
export VIDURAI_MAX_FILES_PER_PROJECT=500

# Enable lazy project loading
export VIDURAI_LAZY_LOAD=1

# Reduce startup scan depth
export VIDURAI_SCAN_DEPTH=2

# Disable auto-project scanning
export VIDURAI_NO_AUTO_SCAN=1
```

### Currently Working Commands

```bash
# Check daemon status
curl -s http://localhost:7777/health | jq

# Get detailed metrics
curl -s http://localhost:7777/metrics | jq

# List all watched projects
curl -s http://localhost:7777/project/all | jq '.projects[].name'

# Get current project context
curl -s http://localhost:7777/project/current | jq

# Manually trigger project scan
curl -X POST http://localhost:7777/project/scan

# Watch a specific project
curl -X POST "http://localhost:7777/watch?project_path=/path/to/project"

# Unwatch a project
curl -X DELETE "http://localhost:7777/watch?project_path=/path/to/project"
```

---

## 2. Troubleshooting High CPU

### Diagnose

```bash
# Find daemon PID
PID=$(ps aux | grep 'vidurai-daemon/daemon.py' | grep -v grep | awk '{print $2}')

# Check CPU usage (sample 5 times)
for i in {1..5}; do ps -o %cpu= -p $PID; sleep 2; done

# Check memory usage
ps -o rss= -p $PID | awk '{print $1/1024 " MB"}'

# Check number of files being watched
curl -s http://localhost:7777/health | jq '.metrics.files_watched'

# Check inotify watches (Linux)
cat /proc/$PID/fd | wc -l

# Check system inotify limit
cat /proc/sys/fs/inotify/max_user_watches
```

### Reduce CPU Usage

```bash
# 1. Reduce number of watched projects
# Stop watching less-used projects:
curl -X DELETE "http://localhost:7777/watch?project_path=/path/to/unused/project"

# 2. Restart daemon (clears event queue)
pkill -f "vidurai-daemon/daemon.py"
cd ~/vidurai && python3 vidurai-daemon/daemon.py &

# 3. Check for runaway file changes
# (log file being written continuously, etc.)
tail -f /tmp/daemon-restart.log | grep "File changed"

# 4. Increase system inotify limit if needed
echo 'fs.inotify.max_user_watches=524288' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

---

## 3. Database Commands

```bash
# Database location
DB=~/.vidurai/memory.db

# Check database size
ls -lh $DB

# Count memories
sqlite3 $DB "SELECT COUNT(*) FROM memories;"

# Count by salience
sqlite3 $DB "SELECT salience, COUNT(*) FROM memories GROUP BY salience;"

# Recent memories
sqlite3 $DB "SELECT datetime(created_at), gist FROM memories ORDER BY created_at DESC LIMIT 10;"

# Memories with errors
sqlite3 $DB "SELECT file_path, error_summary FROM active_state WHERE has_errors = 1;"

# Search memories (FTS)
sqlite3 $DB "SELECT gist FROM memories_fts WHERE memories_fts MATCH 'error';"

# Clean up old memories (manual)
sqlite3 $DB "DELETE FROM memories WHERE created_at < datetime('now', '-30 days');"

# Vacuum database (reclaim space)
sqlite3 $DB "VACUUM;"
```

---

## 4. API Quick Reference

### Health & Metrics

```bash
# Health check (minimal)
curl http://localhost:7777/health

# Full metrics
curl http://localhost:7777/metrics

# Brain statistics
curl http://localhost:7777/brain/stats
```

### Context Generation

```bash
# Smart context (for AI tools)
curl -X POST http://localhost:7777/context/smart \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "help me fix the bug", "platform": "claude_code"}'

# Quick context (one-liner)
curl http://localhost:7777/context/quick

# Prepare context (with AI platform info)
curl -X POST http://localhost:7777/context/prepare \
  -H "Content-Type: application/json" \
  -d '{"user_prompt": "explain this code", "ai_platform": "chatgpt"}'
```

### Error Management

```bash
# Recent errors
curl "http://localhost:7777/error/recent?limit=5"

# Capture error manually
curl -X POST http://localhost:7777/error/capture \
  -H "Content-Type: application/json" \
  -d '{"error_text": "TypeError: undefined is not a function", "command": "npm run build"}'
```

---

## 5. Daemon Management

### Start/Stop/Restart

```bash
# Start daemon (foreground)
cd ~/vidurai && python3 vidurai-daemon/daemon.py

# Start daemon (background)
cd ~/vidurai && nohup python3 vidurai-daemon/daemon.py > /tmp/vidurai.log 2>&1 &

# Stop daemon (graceful)
pkill -TERM -f "vidurai-daemon/daemon.py"

# Stop daemon (force)
pkill -9 -f "vidurai-daemon/daemon.py"

# Check if running
ps aux | grep "vidurai-daemon/daemon.py" | grep -v grep

# View logs
tail -f /tmp/vidurai.log
```

### Systemd Service (Recommended for Production)

```bash
# Create service file
sudo cat > /etc/systemd/system/vidurai.service << 'EOF'
[Unit]
Description=Vidurai Ghost Daemon
After=network.target

[Service]
Type=simple
User=your_username
WorkingDirectory=/home/your_username/vidurai
ExecStart=/usr/bin/python3 vidurai-daemon/daemon.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable vidurai
sudo systemctl start vidurai

# Check status
sudo systemctl status vidurai

# View logs
journalctl -u vidurai -f
```

---

## 6. File Locations

```
~/.vidurai/
├── memory.db              # SQLite database (main storage)
├── memory.db-wal          # Write-ahead log
├── memory.db-shm          # Shared memory
├── experiences.jsonl      # RL training data
├── active-project.txt     # Current active project
├── archive/               # Cold storage
│   └── YYYY/MM/           # Monthly archives
├── sessions/              # Session logs
├── project_brain/         # Project metadata cache
├── consolidation_metrics/ # Memory consolidation stats
└── q_table.json          # Q-learning table

/tmp/
├── vidurai-user.sock      # IPC named pipe
└── daemon-*.log           # Daemon logs
```

---

## 7. Common Issues

### Issue: Daemon won't start

```bash
# Check if port 7777 is in use
lsof -i :7777

# Check if IPC pipe exists (stale)
ls -la /tmp/vidurai-*.sock
rm -f /tmp/vidurai-*.sock  # Remove stale pipes

# Check Python dependencies
pip3 list | grep -E "fastapi|uvicorn|watchdog"
```

### Issue: High memory usage

```bash
# Check file count
curl -s http://localhost:7777/health | jq '.metrics.files_watched'

# Unwatch large projects
curl -X DELETE "http://localhost:7777/watch?project_path=/path/to/large/project"

# Clean old memories
sqlite3 ~/.vidurai/memory.db "DELETE FROM memories WHERE created_at < datetime('now', '-7 days');"
sqlite3 ~/.vidurai/memory.db "VACUUM;"
```

### Issue: Slow startup

```bash
# Check how many projects are being scanned
ls -d ~/Projects/*/.git ~/Code/*/.git ~/dev/*/.git 2>/dev/null | wc -l

# Workaround: Start daemon first, then scan
# (Currently not supported - feature request)
```

### Issue: Extension not connecting

```bash
# Check IPC pipe exists
ls -la /tmp/vidurai-$(whoami).sock

# Check daemon is listening
curl http://localhost:7777/health

# Restart extension (VS Code)
# Ctrl+Shift+P → "Developer: Reload Window"
```

---

## 8. Performance Targets vs Reality

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| Cold start | <5s | 60s | Needs optimization |
| Memory | <150MB | 195MB | Over budget |
| CPU idle | <5% | 35% | Needs optimization |
| Context speed | <1000ms | 71ms | Excellent |
| Health check | <100ms | 36ms | Excellent |
| Event throughput | N/A | 6339/s | Excellent |

---

## 9. Architecture Diagram (Simplified)

```
  VS Code Extension
         │
         │ IPC (Named Pipe)
         ▼
  ┌──────────────────┐
  │  Vidurai Daemon  │ ◄── localhost:7777
  │                  │
  │  ┌────────────┐  │
  │  │ ProjectBrain│  │ ◄── Scans git repos
  │  └────────────┘  │
  │  ┌────────────┐  │
  │  │FileWatcher │  │ ◄── inotify (3000+ files)
  │  └────────────┘  │
  │  ┌────────────┐  │
  │  │  SQLite DB │  │ ◄── ~/.vidurai/memory.db
  │  └────────────┘  │
  └──────────────────┘
```

---

## 10. Quick Diagnostics Script

Save as `~/vidurai-check.sh`:

```bash
#!/bin/bash
echo "=== Vidurai Diagnostics ==="
echo ""

# Check daemon
echo "[Daemon]"
if curl -s http://localhost:7777/health > /dev/null 2>&1; then
    echo "  Status: RUNNING"
    echo "  Uptime: $(curl -s http://localhost:7777/health | jq -r '.uptime_human')"
    echo "  Files watched: $(curl -s http://localhost:7777/health | jq '.metrics.files_watched')"
else
    echo "  Status: NOT RUNNING"
fi
echo ""

# Check database
echo "[Database]"
if [ -f ~/.vidurai/memory.db ]; then
    echo "  Size: $(ls -lh ~/.vidurai/memory.db | awk '{print $5}')"
    echo "  Memories: $(sqlite3 ~/.vidurai/memory.db 'SELECT COUNT(*) FROM memories;')"
else
    echo "  Status: NOT FOUND"
fi
echo ""

# Check resources
echo "[Resources]"
PID=$(ps aux | grep 'vidurai-daemon/daemon.py' | grep -v grep | awk '{print $2}')
if [ -n "$PID" ]; then
    echo "  PID: $PID"
    echo "  Memory: $(ps -o rss= -p $PID | awk '{printf "%.1f MB", $1/1024}')"
    echo "  CPU: $(ps -o %cpu= -p $PID)%"
fi
echo ""

echo "=== Done ==="
```

Make executable: `chmod +x ~/vidurai-check.sh`

---

*Last updated: December 4, 2025*
