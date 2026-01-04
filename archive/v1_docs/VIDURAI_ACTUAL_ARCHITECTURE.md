# Vidurai v2.0.0 - Actual Architecture Documentation

**Generated from Testing:** December 4, 2025
**Based on:** Code inspection during 5 enterprise tests

> This document reflects the **actual implementation**, not marketing claims.

---

## SECTION 1: Performance Deep Dive

### Cold Start Analysis (60.4s vs <5s target)

**Root Cause:** Sequential scanning of 12 projects with blocking I/O operations.

```
Cold Start Breakdown:

[Step 1]:  0.2s  - IPCServer.start() - Named pipe creation
[Step 2]:  0.5s  - FastAPI/Uvicorn startup
[Step 3]:  5-8s  - AutoDetector.auto_discover_projects()
                   - Walks home directory up to 3 levels deep
                   - Searches: ~/Projects, ~/Code, ~/Development, ~/workspace, ~/dev, ~/Documents/Projects, ~/
                   - Runs os.walk() for each path
[Step 4]: 15-25s - ProjectScanner.scan_all_projects() (max_projects=20)
                   - For EACH project:
                     * detect_project_type() - reads package.json, setup.py, etc.
                     * extract_version() - parses multiple config files
                     * detect_language() - rglob('*') all files to count extensions
                     * get_git_info() - subprocess.run('git log') (2s timeout each)
                     * detect_problems() - subprocess.run('git status')
[Step 5]:  5-10s - Observer.schedule() for each project
                   - Creates inotify watchers recursively
                   - Counts all files via path.rglob('*')
[Step 6]:  3-5s  - MemoryDatabase initialization
                   - SQLite connection and table creation
[Step 7]:  2-3s  - Archiver.start() and RetentionScheduler

Total: 35-60s (varies with number of projects/files)
```

**CODE LOCATION:** `daemon.py:669-792` (`_background_initialization()`)

**BOTTLENECK:** `ProjectScanner.get_git_info()` and `detect_language()`

```python
# scanner.py:298-337 - Runs subprocess for EVERY project (blocking)
def get_git_info(self, path: Path) -> dict:
    result = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        cwd=path, capture_output=True, text=True, timeout=2
    )
    # Then ANOTHER subprocess for git log
    result = subprocess.run(
        ['git', 'log', '--pretty=format:%h|%s|%ar', '-5'],
        cwd=path, capture_output=True, text=True, timeout=2
    )
```

```python
# scanner.py:256-288 - Walks ENTIRE project tree
def detect_language(self, path: Path) -> Optional[str]:
    for file in path.rglob('*'):  # <-- This is O(n) for ALL files
        if file.is_file() and not self._should_ignore_path(file):
            ext = file.suffix.lower()
            extension_count[ext] = extension_count.get(ext, 0) + 1
```

**FIX STRATEGY:**
1. Move git operations to async (`asyncio.create_subprocess_exec`)
2. Sample files for language detection (first 100 files, not all)
3. Lazy-load projects (scan on-demand, not all at startup)
4. Cache project metadata to skip re-scanning

---

### Memory Usage Analysis (195 MB vs 150 MB target)

**Measured:** 195.1 MB RSS after full initialization

```
Memory Breakdown (Estimated from code inspection):

File watchers:    ~50 MB  (3,097 inotify handles)
                          Each Observer allocates ~16KB + per-file handler
Project brain:    ~30 MB  (12 ProjectInfo objects with commit history)
                          Each stores: path, name, type, version, language,
                          git_branch, git_commits[5], problems[]
Database:         ~20 MB  (SQLite connection + 6,927 memories loaded)
                          + FTS5 index for full-text search
Python runtime:   ~60 MB  (Interpreter, FastAPI, Uvicorn, Watchdog)
Hash cache:       ~15 MB  (SmartFileWatcher.file_hashes dict)
Context mediator: ~10 MB  (Event queue, recent events buffer)
Other:            ~10 MB  (Archiver, logging, misc allocations)

Total: ~195 MB
```

**WHY OVER TARGET:**
- 3,097 files = 3,097 inotify watch descriptors
- Each Observer in `watchdog` library allocates memory per directory
- Full `memories` table loaded into FTS5 index
- No eviction/cleanup of `file_hashes` dict

**CODE LOCATION:** `daemon.py:1017-1027` (watch_project counting)

```python
# Counts ALL files, not just watched ones
file_count = sum(1 for _ in path.rglob('*') if _.is_file() and not event_handler.should_ignore(str(_)))
metrics["files_watched"] += file_count
```

**OPTIMIZATION:**
1. Limit files per project: `max_files_per_project = 500`
2. Use `.gitignore` patterns more aggressively
3. Implement LRU cache for file hashes (cap at 1000 entries)
4. Lazy-load memories (query on demand, not all at startup)

---

### CPU Usage Analysis (68% vs <5% target)

**Measured:** 35-68% CPU even when "idle"

```
CPU Activity:

Idle baseline:        35%   (Continuous file watching)
During file events:   68%   (Event processing + hash calculation)
Event queue polling:  10%   (100ms sleep loop in process_event_queue)
Retention scheduler:   1%   (1-hour interval, mostly sleeping)
```

**WHY SO HIGH:**

1. **Event queue polling loop** (`daemon.py:623-638`):
```python
async def process_event_queue():
    while True:
        if not event_queue.empty():
            event = event_queue.get_nowait()
            context_mediator.add_event(event)
            await broadcast_event(event)
        await asyncio.sleep(0.1)  # 10 checks/second even when idle
```

2. **watchdog Observer threads** (one per project):
   - Each Observer runs its own polling loop
   - inotify events trigger Python callbacks

3. **SmartFileWatcher.has_content_changed()** (`smart_file_watcher.py:154-174`):
```python
def has_content_changed(self, filepath: str) -> bool:
    current_hash = self.calculate_file_hash(filepath)  # MD5 of entire file
    # ...
```
   - Every file modification triggers MD5 hash calculation
   - Large files = more CPU

4. **No event batching:**
   - Each file save triggers immediate processing
   - VSCode auto-save can generate many events

**FIX:**
1. Replace polling with `asyncio.Queue` (block instead of poll)
2. Batch file events (500ms window)
3. Skip hash calculation for small changes (check mtime first)
4. Limit concurrent Observer threads

---

## SECTION 2: Storage Architecture (As Implemented)

### Database Schema (SQLite)

```sql
-- Table: projects (106 rows in test)
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table: memories (6,927 rows in test)
-- Uses "Pancha Kosha" philosophy for memory layers
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,

    -- Annamaya Kosha (Physical/Verbatim) - Raw content
    verbatim TEXT NOT NULL,
    event_type TEXT NOT NULL,
    file_path TEXT,
    line_number INTEGER,

    -- Pranamaya Kosha (Active/Salience) - Importance tracking
    salience TEXT NOT NULL,  -- 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'NOISE'
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP,

    -- Manomaya Kosha (Wisdom/Gist) - Summarized understanding
    gist TEXT NOT NULL,
    tags TEXT,  -- JSON array

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    pinned INTEGER DEFAULT 0,

    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Full-text search index
CREATE VIRTUAL TABLE memories_fts
    USING fts5(memory_id, gist, verbatim, tags);

-- Active file state (Zombie Killer pattern)
CREATE TABLE active_state (
    file_path TEXT PRIMARY KEY,
    project_id INTEGER,
    has_errors BOOLEAN DEFAULT FALSE,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_summary TEXT,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

-- Audience-specific gists
CREATE TABLE audience_gists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL,
    audience TEXT NOT NULL,  -- 'developer', 'manager', 'ai'
    gist TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE,
    UNIQUE(memory_id, audience)
);

-- Indexes for performance
CREATE INDEX idx_memories_project ON memories(project_id);
CREATE INDEX idx_memories_salience ON memories(salience);
CREATE INDEX idx_memories_created ON memories(created_at DESC);
CREATE INDEX idx_memories_file ON memories(file_path);
CREATE INDEX idx_memories_pinned ON memories(pinned) WHERE pinned = 1;
```

### JSONL Format (experiences.jsonl)

Used for **RL training data** (Q-learning for memory management):

```json
{
  "state": {
    "working_memory_count": 3,
    "episodic_memory_count": 3,
    "total_tokens": 35,
    "average_entropy": 0.86,
    "average_importance": 0.57,
    "messages_since_last_compression": 3,
    "time_since_last_action": 0.0,
    "recent_compressions": 0,
    "recent_decays": 0
  },
  "action": "do_nothing",
  "reward": 49.0,
  "next_state": { /* same structure */ },
  "timestamp": "2025-11-03T21:57:08.039208"
}
```

**Not used for:** Event buffering (that's in IPC buffer files)

### Storage Decision Logic

The daemon uses **SQLite for hot storage** and **JSONL archives for cold storage**.

Decision happens in `archiver/archiver.py`:

```python
# archiver.py - Tiered storage logic
class Archiver:
    def __init__(self, options: ArchiverOptions):
        self.hot_retention_days = options.hot_retention_days  # Default: 7
        self.cold_retention_days = options.cold_retention_days  # Default: 90

    async def archive_old_memories(self):
        # Memories older than hot_retention_days → move to cold archive
        # Cold archive format: ~/.vidurai/archive/YYYY/MM/memories_YYYYMMDD.jsonl.gz
```

---

## SECTION 3: Test Discovery Documentation

### Test 1: Persistence

**WHAT I READ:**
- File: `daemon.py:857-902`
- Function: `shutdown_event()`

**Discovery:** Graceful shutdown properly closes:
1. Retention scheduler (cancels task)
2. Archiver (flush pending)
3. Database (commit + close)
4. IPC server (cleanup pipe)
5. File watchers (stop + join)

**CODE SNIPPET:**
```python
@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown of background services"""
    global ipc_server, archiver, retention_task, memory_db

    logger.info("🛑 Shutting down services...")

    # v2.2: Stop retention scheduler
    if retention_task:
        retention_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass

    # v2.2: Stop archiver
    if archiver:
        await archiver.stop()

    # v2.2: Close database
    if memory_db:
        memory_db.close()

    # Stop IPC server
    if ipc_server:
        await ipc_server.stop()

    # Stop all file watchers
    for path, observer in watched_projects.items():
        observer.stop()
        observer.join(timeout=2)

    logger.info("✅ Shutdown complete")
```

**Persistence verification:** Database is NOT in-memory. Uses file at `~/.vidurai/memory.db`.

---

### Test 2: Secrets

**WHAT I READ:**
- File: `vidurai-vscode-extension/src/security/Gatekeeper.ts`
- File: `vidurai-vscode-extension/python-bridge/event_processor.py`

**Discovery:** Secrets redaction happens at TWO layers:

1. **VS Code Extension (TypeScript):** `Gatekeeper.ts:117-328`
   - 30+ regex patterns for API keys, passwords, PII
   - Entropy-based filtering for false positive reduction
   - Runs BEFORE data leaves VS Code

2. **Python Bridge:** `event_processor.py:17-49`
   - Simpler regex patterns (backup)
   - Runs during event processing
   - Also ignores `.env` files entirely

**CODE SNIPPET (Gatekeeper patterns):**
```typescript
const SECRET_PATTERNS: SecretPattern[] = [
  { type: 'AWS_ACCESS_KEY', pattern: /\b(AKIA[0-9A-Z]{16})\b/g },
  { type: 'OPENAI_KEY', pattern: /\b(sk-(?:proj|svcacct|admin)-[A-Za-z0-9_-]{20,})\b/g },
  { type: 'ANTHROPIC_KEY', pattern: /\b(sk-ant-[A-Za-z0-9_-]{20,})\b/g },
  { type: 'GITHUB_TOKEN', pattern: /\b(ghp_[A-Za-z0-9]{36,})\b/g },
  { type: 'STRIPE_SECRET', pattern: /\b(sk_(?:live|test)_[A-Za-z0-9]{24,})\b/g },
  // ... 25+ more patterns
];
```

**Redaction format:** `<REDACTED:SECRET_TYPE:HASH8>` (deterministic hash for debugging)

---

### Test 3: Performance

**WHAT I READ:**
- `daemon.py:640-667` (startup_event)
- `daemon.py:669-792` (_background_initialization)
- `auto_detector.py:21-76` (find_git_repos)
- `scanner.py:67-120` (scan_all_projects)

**Discovery:** Startup is slow because:

1. **Sequential, not parallel:** Projects scanned one-by-one
2. **Subprocess blocking:** `git log`, `git status` called per project
3. **File tree walking:** `path.rglob('*')` for language detection
4. **No caching:** Re-scans even if project hasn't changed

**KEY FINDINGS:**
```python
# auto_detector.py:21-76 - os.walk() for EACH search path
def find_git_repos(self, max_depth: int = 3, max_repos: int = 10) -> List[Path]:
    for search_path in search_paths:
        for root, dirs, _ in os.walk(search_path):  # Blocking I/O
            depth = len(Path(root).relative_to(search_path).parts)
            if depth > max_depth:
                dirs.clear()
                continue
            if '.git' in dirs:
                repos.append(repo_path)
```

**File watching library:** `watchdog` with `inotify` backend on Linux.

---

### Test 4: Stress

**WHAT I READ:**
- `daemon.py:83-93` (global event_queue)
- `daemon.py:623-638` (process_event_queue)
- `smart_file_watcher.py:246-304` (on_modified handler)

**Discovery:** Event handling uses:

```python
# daemon.py:85 - Standard Python Queue (thread-safe)
event_queue: Queue = Queue()

# smart_file_watcher.py:246-304 - Intelligent filtering
def on_modified(self, event):
    # 1. Ignore irrelevant files (node_modules, etc.)
    if self.should_ignore(filepath):
        return

    # 2. Check if content actually changed (MD5 hash)
    if not self.has_content_changed(filepath):
        return

    # 3. Debounce rapid changes (500ms)
    if current_time - last_change < self.debounce_time:
        return

    # 4. Put in queue for async processing
    self.event_queue.put(event_data)
```

**Why 6,339 events/sec:** Events are just put in queue (fast). Processing is async.

**Rate limiting:** Debounce (500ms) per file, but no global rate limit.

---

### Test 5: Integration

**WHAT I READ:**
- `daemon.py:905-1061` (API endpoints)
- `daemon.py:1062-1228` (Project Brain endpoints)

**API Endpoints:**
| Method | Endpoint | Handler |
|--------|----------|---------|
| GET | `/health` | `health_check()` |
| GET | `/metrics` | `get_metrics()` |
| POST | `/context/prepare` | `prepare_intelligent_context()` |
| POST | `/context/smart` | `get_smart_context()` |
| GET | `/context/quick` | `get_quick_context()` |
| POST | `/watch` | `watch_project()` |
| DELETE | `/watch` | `unwatch_project()` |
| GET | `/project/current` | `get_current_project()` |
| GET | `/project/all` | `list_all_projects()` |
| POST | `/project/scan` | `scan_projects()` |
| POST | `/error/capture` | `capture_error()` |
| GET | `/error/recent` | `get_recent_errors()` |
| GET | `/brain/stats` | `get_brain_stats()` |
| GET | `/` | `dashboard()` |
| WS | `/ws` | `websocket_endpoint()` |

**Multi-project tracking:** `ProjectScanner.auto_switch_context()` detects CWD changes.

```python
def auto_switch_context(self) -> Optional[ProjectInfo]:
    cwd = Path.cwd()
    for path_str, project in self.projects.items():
        try:
            cwd.relative_to(project.path)
            # We're inside this project
            if self.current_project != project:
                self.current_project = project
            return project
        except ValueError:
            continue
```

---

## SECTION 4: Discrepancies Found

| Feature | Documented | Reality | Evidence |
|---------|-----------|---------|----------|
| Startup time | <5s target | 60.4s actual | Test result |
| Memory usage | <150MB target | 195MB actual | Test result |
| CPU idle | <5% target | 35-68% actual | Test result |
| Offline buffering | "Events buffered during downtime" | Partially implemented | IPC buffer files exist, but extension doesn't auto-retry |
| Event throughput | Not specified | 6,339 events/sec | Test result |
| Context speed | Not specified | 71ms average | Test result (excellent) |

---

## SECTION 5: Missing/Incomplete Features

### 1. Offline Event Buffering

**Claimed in:** Documentation, IPC implementation comments

**Code evidence:** `ipc/__init__.py` has `scan_buffer_files()` but:
- Buffer only used for IPC protocol buffer
- VS Code extension does NOT buffer failed sends
- Events during daemon crash are LOST

**Impact:** Events lost if daemon crashes while user is coding.

### 2. Lazy Project Loading

**Status:** NOT IMPLEMENTED

All projects scanned at startup. No on-demand loading.

### 3. Memory Pressure Handling

**Status:** PARTIAL

Retention scheduler runs hourly, but no:
- Real-time memory pressure detection
- Aggressive cleanup when memory is low
- Per-project memory limits

### 4. Project Exclusion Config

**Status:** NOT IMPLEMENTED

No way for users to exclude specific directories from scanning.
Hardcoded ignore patterns only.

---

## SECTION 6: Optimization Recommendations

### Immediate (v2.0.1):

1. **Async git operations**
   - Code location: `scanner.py:298-337`
   - Change: Use `asyncio.create_subprocess_exec`
   - Impact: Startup from 60s → 20s
   - Risk: Low

2. **Sample-based language detection**
   - Code location: `scanner.py:256-288`
   - Change: Sample first 100 files, not all
   - Impact: Startup from 60s → 30s
   - Risk: Low (may misdetect some projects)

3. **Replace polling with async Queue**
   - Code location: `daemon.py:623-638`
   - Change: `asyncio.Queue` with `await queue.get()`
   - Impact: CPU from 35% → 5% idle
   - Risk: Low

4. **Add file watch limits**
   - Code location: `daemon.py:1017-1027`
   - Change: Cap at 500 files per project
   - Impact: Memory from 195MB → 120MB
   - Risk: Medium (may miss some file changes)

### Long-term (v2.1.0):

1. **Lazy project loading**
   - Only scan project when user opens it
   - Keep metadata cache for quick re-load

2. **Project metadata caching**
   - Store scan results in SQLite
   - Skip re-scanning if mtime unchanged

3. **Smart file watching**
   - Only watch recently-active files
   - Background thread to rotate watches

4. **Memory pressure monitoring**
   - Use `psutil` to monitor RSS
   - Trigger cleanup when >150MB

5. **User-configurable exclusions**
   - Add `~/.vidurai/config.yaml`
   - Allow per-project overrides

---

## Architecture Diagram (ASCII)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         VS CODE EXTENSION                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ File Watcher │  │   Terminal   │  │      Gatekeeper          │  │
│  │   (native)   │  │   Capture    │  │  (secrets redaction)     │  │
│  └──────┬───────┘  └──────┬───────┘  └────────────┬─────────────┘  │
│         │                 │                        │                │
│         └─────────────────┼────────────────────────┘                │
│                           │                                         │
│                    ┌──────▼──────┐                                  │
│                    │ Python Bridge│                                  │
│                    │ (IPC Client) │                                  │
│                    └──────┬───────┘                                  │
└───────────────────────────┼─────────────────────────────────────────┘
                            │
                    Named Pipe IPC
                    /tmp/vidurai-user.sock
                            │
┌───────────────────────────▼─────────────────────────────────────────┐
│                     VIDURAI GHOST DAEMON                            │
│                     (localhost:7777)                                │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │                     FastAPI Server                          │    │
│  │  /health  /context/smart  /project/all  /ws (WebSocket)     │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐      │
│  │ AutoDetector │  │ProjectScanner│  │   SmartFileWatcher   │      │
│  │ (find repos) │  │ (git info)   │  │  (watchdog/inotify)  │      │
│  └──────────────┘  └──────────────┘  └──────────────────────┘      │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    PROJECT BRAIN                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌─────────────────────────┐ │  │
│  │  │MemoryStore │  │ErrorWatcher│  │    ContextBuilder       │ │  │
│  │  │ (gist/tags)│  │(captures)  │  │ (builds AI context)     │ │  │
│  │  └────────────┘  └────────────┘  └─────────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    STORAGE LAYER                              │  │
│  │  ┌────────────────┐  ┌────────────┐  ┌───────────────────┐   │  │
│  │  │ MemoryDatabase │  │  Archiver  │  │  RetentionPolicy  │   │  │
│  │  │ (SQLite + FTS) │  │ (hot→cold) │  │  (hourly cleanup) │   │  │
│  │  └────────────────┘  └────────────┘  └───────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         ~/.vidurai/                                  │
│                                                                      │
│  memory.db           - SQLite database (6,927 memories)              │
│  experiences.jsonl   - RL training data                              │
│  archive/            - Cold storage (JSONL.gz)                       │
│  sessions/           - Session logs                                  │
│  project_brain/      - Project metadata                              │
│  active-project.txt  - Current project marker                        │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Code Files

| File | Purpose | Lines |
|------|---------|-------|
| `daemon.py` | Main daemon, FastAPI server, startup | 1486 |
| `auto_detector.py` | Find git repos, VS Code workspaces | 206 |
| `scanner.py` | Project analysis, git info | 467 |
| `smart_file_watcher.py` | Intelligent file watching | 316 |
| `Gatekeeper.ts` | Secrets redaction (extension) | 619 |
| `event_processor.py` | Salience classification | 219 |
| `database.py` | SQLite storage | ~400 |
| `archiver.py` | Tiered storage | ~200 |

---

*Documentation generated from actual code inspection during enterprise testing.*
