# Vidurai v2.0.1 - Proof of Concept Master Manual

> **"विस्मृति भी विद्या है" - Forgetting too is knowledge**

**Status:** Production-Ready POC
**Version:** 2.0.1 (7 December 2025)
**Verified:** December 08, 2025

---

## Table of Contents

1. [The Narrative (Why & How)](#1-the-narrative-why--how)
2. [The Architecture (What)](#2-the-architecture-what)
3. [Independent Verification (Hacker's Guide)](#3-independent-verification-hackers-guide)
4. [Use Cases (The Value)](#4-use-cases-the-value)
5. [SDK Deep Dive](#5-sdk-deep-dive)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. The Narrative (Why & How)

### The Problem

Developers lose context constantly:

| Problem | Impact |
|---------|--------|
| **Context Switching** | You fix a bug, get interrupted, return and forget what you were doing |
| **Noisy Logs** | 1000 TypeScript errors for one missing semicolon |
| **AI Hallucinations** | LLMs optimize on recent noise, not actual project state |
| **Token Waste** | Same context sent to AI repeatedly, burning money |
| **Fragmented State** | VS Code, terminal, browser all have partial views |

### The Solution: A "Second Brain"

Vidurai is a **local-first cognitive layer** that:

1. **Watches** you code (file edits, terminal commands, diagnostics)
2. **Filters** the noise (Debounce - 500ms window for rapid saves)
3. **Understands** the state (Zombie Killer - clears resolved errors)
4. **Remembers** intelligently (Three-Kosha memory with decay)
5. **Serves** the right context to AI (Audience Profiles - developer/ai/manager)

### The Flow: Unified Cognitive Mesh

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER WRITES CODE                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                        VS CODE EXTENSION (Sensor)                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ FileWatcher │  │  Terminal   │  │ Diagnostics │  │   Debounce  │        │
│  │ (onSave)    │  │  (output)   │  │  (errors)   │  │  (500ms)    │        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘        │
│         └─────────────────┼─────────────────┼──────────────┘                │
│                           │                 │                               │
│                           ▼                 ▼                               │
│                    ┌─────────────────────────────┐                          │
│                    │   IPCClient (Named Pipe)    │                          │
│                    │  \\.\pipe\vidurai-daemon    │ (Windows)                │
│                    │  /tmp/vidurai-daemon.sock   │ (Unix)                   │
│                    └─────────────┬───────────────┘                          │
└──────────────────────────────────┼──────────────────────────────────────────┘
                                   │ Firewall Immune (no localhost:port)
                                   ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PYTHON DAEMON (Hub)                                  │
│                         localhost:7777                                       │
│                                                                             │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                   handle_ipc_message()                              │    │
│  │                                                                     │    │
│  │   file_edit ──► EventAdapter ──► VismritiMemory.remember()         │    │
│  │   diagnostic ──► Zombie Killer ──► active_state UPSERT/DELETE      │    │
│  │   terminal ──► EventAdapter ──► VismritiMemory.remember()          │    │
│  │   request:get_context ──► Oracle.get_context() ──► Response        │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                   │                                         │
│                                   ▼                                         │
│  ┌────────────────────────────────────────────────────────────────────┐    │
│  │                    VismritiMemory SDK (Brain)                       │    │
│  │                                                                     │    │
│  │   ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐      │    │
│  │   │ Salience  │  │  Passive  │  │  Active   │  │  Memory   │      │    │
│  │   │Classifier │  │   Decay   │  │ Unlearning│  │Aggregator │      │    │
│  │   │(Dopamine) │  │ (Pruning) │  │ (Forget)  │  │ (Dedup)   │      │    │
│  │   └───────────┘  └───────────┘  └───────────┘  └───────────┘      │    │
│  └────────────────────────────────────────────────────────────────────┘    │
│                                   │                                         │
└───────────────────────────────────┼─────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SQLITE DATABASE (Storage)                            │
│                         ~/.vidurai/memory.db                                 │
│                                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  projects   │  │  memories   │  │active_state │  │audience_gist│        │
│  │  (identity) │  │  (content)  │  │ (live errs) │  │ (per-role)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                                             │
│                    WAL Mode (Concurrent Reads + Writes)                     │
│                    Queue-Based Actor Pattern (Zero Lock Contention)         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Architecture (What)

### 2.1 Tech Stack

| Layer | Technology | Purpose | Why This Choice |
|-------|------------|---------|-----------------|
| **Sensor** | TypeScript (VS Code Extension) | Capture developer activity | Native IDE integration |
| **Transport** | Named Pipes (IPC) | Sensor → Daemon communication | **Firewall immune** - no network ports needed |
| **Hub** | Python 3.9+ (FastAPI + AsyncIO) | Event processing & orchestration | Async performance, ML ecosystem |
| **Brain** | VismritiMemory SDK | Intelligent memory management | Research-backed (104+ citations) |
| **Storage** | SQLite + WAL Mode | Persistent, concurrent storage | Single file, zero config, fast |
| **Archive** | Parquet + Snappy | Long-term compressed storage | 10x compression, columnar queries |

### 2.2 Database Schema (Verified)

```sql
-- Projects table (identity)
CREATE TABLE projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Memories table (the brain)
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    verbatim TEXT NOT NULL,      -- Raw content
    gist TEXT,                   -- Compressed summary
    salience TEXT NOT NULL,      -- CRITICAL/HIGH/MEDIUM/LOW/NOISE
    event_type TEXT,             -- file_edit/diagnostic/terminal
    file_path TEXT,
    line_number INTEGER,
    tags TEXT,                   -- JSON array
    created_at TIMESTAMP,
    expires_at TIMESTAMP,        -- Retention policy
    pinned INTEGER DEFAULT 0,    -- User-pinned (never decay)
    occurrence_count INTEGER DEFAULT 1,  -- Aggregation count
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Active state (live errors - Zombie Killer target)
CREATE TABLE active_state (
    file_path TEXT PRIMARY KEY,
    project_id INTEGER,
    has_errors BOOLEAN DEFAULT FALSE,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    last_error_msg TEXT,
    last_updated TIMESTAMP,
    gist TEXT
);

-- Audience-specific gists (Oracle output)
CREATE TABLE audience_gists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id INTEGER NOT NULL,
    audience TEXT NOT NULL,       -- 'developer', 'ai', 'manager'
    gist TEXT NOT NULL,
    FOREIGN KEY (memory_id) REFERENCES memories(id)
);
```

### 2.3 Salience Levels (Dopamine-Inspired)

| Level | Value | Retention | Biological Analog | Examples |
|-------|-------|-----------|-------------------|----------|
| **CRITICAL** | 100 | Forever | Strong dopamine release | API keys, explicit commands |
| **HIGH** | 75 | 90 days | Medium dopamine | Bug fixes, breakthroughs |
| **MEDIUM** | 50 | 30 days | Baseline dopamine | Normal file edits |
| **LOW** | 25 | 7 days | Weak dopamine | Casual interactions |
| **NOISE** | 5 | 1 day | No dopamine signal | Raw logs, debug output |

### 2.4 Daemon HTTP Endpoints (Verified from daemon.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check - `{"status": "healthy"}` |
| `/metrics` | GET | System metrics (memory, connections) |
| `/api/rpc` | POST | JSON-RPC gateway (get_context, standup) |
| `/brain/stats` | GET | SDK statistics |
| `/project/current` | GET | Current active project |
| `/project/all` | GET | All tracked projects |
| `/project/scan` | POST | Scan directory for projects |
| `/context/prepare` | POST | Prepare context (legacy) |
| `/context/smart` | POST | Smart context generation |
| `/context/quick` | GET | Quick context retrieval |
| `/error/capture` | POST | Manual error capture |
| `/error/recent` | GET | Recent errors |
| `/watch` | POST | WebSocket upgrade for streaming |

### 2.5 Audience Profiles (Oracle)

The Oracle delivers **audience-specific context**:

| Audience | Data Included | Salience Threshold | Use Case |
|----------|---------------|-------------------|----------|
| **developer** | Errors + Pins (no memories) | HIGH | Debugging, code review |
| **ai** | Everything | LOW | AI prompt injection |
| **manager** | Memories + Pins (no errors) | MEDIUM | Standup generation |

```python
AUDIENCE_PROFILES = {
    'developer': {'memories': False, 'errors': True,  'pins': True,  'salience': 'HIGH'},
    'manager':   {'memories': True,  'errors': False, 'pins': True,  'salience': 'MEDIUM'},
    'ai':        {'memories': True,  'errors': True,  'pins': True,  'salience': 'LOW'},
}
```

---

## 3. Independent Verification (Hacker's Guide)

**Goal:** Prove Vidurai works without using VS Code. Terminal-only verification.

### 3.1 Pre-requisites

```bash
# Ensure daemon is running
curl -s http://localhost:7777/health | python3 -m json.tool

# Expected output:
# {
#     "status": "healthy"
# }
```

### 3.2 Database Inspection (SQL)

```bash
# A. Check if database exists
ls -la ~/.vidurai/memory.db

# B. List all tracked projects
sqlite3 ~/.vidurai/memory.db "SELECT id, name, path FROM projects;"

# C. View active errors (Zombie Killer state)
sqlite3 ~/.vidurai/memory.db "SELECT file_path, error_count, warning_count, last_error_msg FROM active_state WHERE has_errors = 1;"

# D. View recent memories by salience
sqlite3 ~/.vidurai/memory.db "SELECT salience, gist, file_path, created_at FROM memories ORDER BY created_at DESC LIMIT 10;"

# E. View pinned memories (user-protected)
sqlite3 ~/.vidurai/memory.db "SELECT id, gist, file_path FROM memories WHERE pinned = 1;"

# F. Count memories by salience level
sqlite3 ~/.vidurai/memory.db "SELECT salience, COUNT(*) as count FROM memories GROUP BY salience ORDER BY count DESC;"

# G. Check WAL mode is enabled
sqlite3 ~/.vidurai/memory.db "PRAGMA journal_mode;"
# Expected: wal
```

### 3.3 Daemon Interrogation (CURL)

```bash
# A. Get brain statistics
curl -s http://localhost:7777/brain/stats | python3 -m json.tool

# B. Get current project
curl -s http://localhost:7777/project/current | python3 -m json.tool

# C. Get all tracked projects
curl -s http://localhost:7777/project/all | python3 -m json.tool

# D. Get recent errors
curl -s http://localhost:7777/error/recent | python3 -m json.tool

# E. RPC: Get context for AI audience
curl -s http://localhost:7777/api/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "data": {
      "method": "get_context",
      "params": {
        "audience": "ai",
        "project": "/path/to/your/project"
      }
    }
  }' | python3 -m json.tool

# F. RPC: Generate standup report
curl -s http://localhost:7777/api/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "data": {
      "method": "standup",
      "params": {
        "project": "/path/to/your/project"
      }
    }
  }' | python3 -m json.tool
```

### 3.4 SDK Direct Access (Python)

```bash
# A. Quick one-liner to get context
python3 -c "
from vidurai import VismritiMemory
mem = VismritiMemory(project_path='.')
print(mem.get_context_for_ai(query='auth', max_tokens=1000))
"

# B. Store a test memory
python3 -c "
from vidurai import VismritiMemory, SalienceLevel
mem = VismritiMemory(project_path='.')
m = mem.remember(
    'Test memory from CLI verification',
    metadata={'type': 'test', 'file': 'POC_README.md'},
    salience=SalienceLevel.MEDIUM
)
print(f'Stored: {m.engram_id[:8]} - {m.salience.name}')
"

# C. Recall memories
python3 -c "
from vidurai import VismritiMemory
mem = VismritiMemory(project_path='.')
for m in mem.recall('test', top_k=5):
    print(f'[{m.salience.name}] {m.gist[:50]}...')
"

# D. Get system statistics
python3 -c "
from vidurai import VismritiMemory
mem = VismritiMemory(project_path='.')
stats = mem.get_statistics()
import json
print(json.dumps(stats, indent=2, default=str))
"

# E. Run decay cycle (simulate sleep cleanup)
python3 -c "
from vidurai import VismritiMemory
mem = VismritiMemory(project_path='.', enable_decay=True)
stats = mem.run_decay_cycle()
print(f'Pruned: {stats.get(\"pruned\", 0)} memories')
"
```

### 3.5 Named Pipe Verification (Advanced)

```bash
# Unix: Check if daemon pipe exists
ls -la /tmp/vidurai-daemon.sock

# Send raw IPC message (Unix)
echo '{"type":"file_edit","file":"/test/file.py","gist":"Test edit","change":"save"}' | nc -U /tmp/vidurai-daemon.sock

# Windows (PowerShell):
# Get-ChildItem \\.\pipe\ | Where-Object { $_.Name -match "vidurai" }
```

---

## 4. Use Cases (The Value)

### 4.1 Developer: "Fixing a Bug"

**Scenario:** Developer sees TypeScript error, fixes it, error resolves.

**Vidurai's Role:**
1. **Capture:** VS Code extension sends `diagnostic` event (severity=0, error)
2. **Store:** Daemon stores in `active_state` table
3. **Track:** Error displayed in context (`get_context` with `audience=developer`)
4. **Resolve:** Developer fixes the bug, VS Code sends `diagnostic` with severity=2 (info)
5. **Zombie Killer:** Daemon DELETES the error from `active_state`
6. **Context Update:** Next `get_context` call shows clean state

```bash
# Before fix:
sqlite3 ~/.vidurai/memory.db "SELECT file_path, error_count FROM active_state WHERE error_count > 0;"
# auth.py|3

# After fix:
sqlite3 ~/.vidurai/memory.db "SELECT file_path, error_count FROM active_state WHERE error_count > 0;"
# (empty - zombie killed)
```

### 4.2 Manager: "Generating a Standup"

**Scenario:** Manager wants summary of developer's work.

**Vidurai's Role:**
1. **Aggregate:** All file edits, terminal commands stored with timestamps
2. **Filter:** Oracle selects MEDIUM+ salience memories (no noise)
3. **Summarize:** Whisperer generates natural language narrative
4. **Deliver:** Manager-friendly format (no technical errors)

```bash
# Generate standup via RPC
curl -s http://localhost:7777/api/rpc \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "data": {
      "method": "standup",
      "params": {"project": "/home/user/vidurai"}
    }
  }' | python3 -c "import sys,json; print(json.load(sys.stdin).get('standup','No standup'))"
```

### 4.3 AI Agent: "Context-Aware Coding"

**Scenario:** Claude Code needs project context for better suggestions.

**Vidurai's Role:**
1. **Gather:** All memories + errors + pins (audience=ai)
2. **Format:** Markdown with salience-ordered sections
3. **Inject:** Context prepended to AI prompt
4. **Result:** AI has full project state, not just current file

```python
# In your AI workflow
from vidurai import VismritiMemory

memory = VismritiMemory(project_path="/path/to/project")
context = memory.get_context_for_ai(
    query="authentication",
    max_tokens=2000,
    audience="ai"
)

# Inject into prompt
prompt = f"""
{context}

---
User Question: How do I fix the JWT validation bug?
"""
```

### 4.4 Analyst: "Jupyter Integration"

**Scenario:** Data scientist wants shared context across notebooks.

```python
# In Jupyter notebook
from vidurai import VismritiMemory, SalienceLevel

# Initialize with shared project
mem = VismritiMemory(project_path="/data/analysis-project")

# Store analysis findings
mem.remember(
    "Found correlation between user_age and purchase_frequency (r=0.73)",
    metadata={
        'type': 'finding',
        'notebook': 'exploration.ipynb',
        'tags': ['correlation', 'user_behavior']
    },
    salience=SalienceLevel.HIGH
)

# Later, in another notebook, recall findings
findings = mem.recall("correlation", top_k=5)
for f in findings:
    print(f"[{f.salience.name}] {f.gist}")
```

---

## 5. SDK Deep Dive

### 5.1 Two Memory Systems

Vidurai has **two parallel memory systems**:

| System | Entry Point | Purpose | Storage |
|--------|-------------|---------|---------|
| **VismritiMemory** | `vidurai.vismriti_memory` | v2.0+ main system | SQLite + in-memory |
| **ViduraiMemory** | `vidurai.core.koshas` | Legacy Three-Kosha | In-memory only |

**Recommendation:** Use `VismritiMemory` for all new code.

### 5.2 VismritiMemory API

```python
from vidurai import VismritiMemory, SalienceLevel

# Initialize
memory = VismritiMemory(
    enable_decay=True,           # Passive decay (synaptic pruning)
    enable_gist_extraction=False, # LLM gist (requires OpenAI key)
    enable_rl_agent=False,        # RL compression decisions
    enable_aggregation=True,      # Deduplication
    retention_policy="rule_based", # or "rl_based"
    enable_multi_audience=False,  # Audience-specific gists
    project_path="/path/to/project"
)

# Core Operations
memory.remember(content, metadata, salience)  # Store
memory.recall(query, min_salience, top_k)     # Retrieve
memory.forget(query, method, confirmation)     # Active unlearning
memory.run_decay_cycle()                       # Passive pruning
memory.get_context_for_ai(query, max_tokens)   # AI context
memory.get_ledger(include_pruned, format)      # Transparency
memory.get_statistics()                        # System stats
```

### 5.3 Three-Kosha Architecture (Legacy)

The traditional memory hierarchy inspired by Vedantic philosophy:

| Kosha | Sanskrit | Layer | Capacity | TTL |
|-------|----------|-------|----------|-----|
| **AnnamayaKosha** | अन्नमय | Working Memory | 10 items | 5 minutes |
| **ManomayaKosha** | मनोमय | Episodic Memory | 1000 items | Days/weeks (decay 0.95) |
| **VijnanamayaKosha** | विज्ञानमय | Wisdom Memory | Unlimited | Forever |

```python
from vidurai import create_memory_system

# Create legacy system
system = create_memory_system(
    working_capacity=10,      # AnnamayaKosha (5 min TTL)
    episodic_capacity=1000,   # ManomayaKosha (decay rate 0.95)
    aggressive_forgetting=False
)

# Use
system.remember("Some content", importance=0.7)
memories = system.recall(query="content", limit=10)
```

### 5.4 LangChain Integration

```python
from langchain.llms import OpenAI
from vidurai.integrations.langchain import ViduraiConversationChain

llm = OpenAI(temperature=0.7)

# Drop-in replacement for ConversationBufferMemory
chain = ViduraiConversationChain.create(
    llm,
    verbose=True,
    aggressive=True  # Fast forgetting
)

response = chain.predict(input="Hello, I'm working on auth bugs")
```

### 5.5 Core SDK Components (31 files in vidurai/core/)

| Component | File | Purpose |
|-----------|------|---------|
| **SalienceClassifier** | `salience_classifier.py` | Dopamine-inspired importance tagging |
| **PassiveDecayEngine** | `passive_decay.py` | Time-based synaptic pruning |
| **ActiveUnlearningEngine** | `active_unlearning.py` | Motivated forgetting |
| **VismritiEngine** | `vismriti.py` | Four Gates of Forgetting |
| **VivekaEngine** | `viveka.py` | Importance scoring (emotional, goal, novelty) |
| **VismritiRLAgent** | `rl_agent_v2.py` | Q-Learning compression decisions |
| **SemanticCompressor** | `semantic_compressor_v2.py` | LLM-based compression |
| **MemoryAggregator** | `memory_aggregator.py` | Deduplication, occurrence tracking |
| **MemoryPinManager** | `memory_pinning.py` | Pin/unpin important memories |
| **Oracle** | `oracle.py` | Audience-specific context generation |
| **EntityExtractor** | `entity_extractor.py` | Extract paths, symbols, errors |
| **EpisodeBuilder** | `episode_builder.py` | Build narrative episodes |
| **EventBus** | `event_bus.py` | Pub/sub for memory events |

---

## 6. Troubleshooting

### 6.1 Common Issues

| Issue | Diagnosis | Solution |
|-------|-----------|----------|
| Daemon not responding | `curl http://localhost:7777/health` fails | Start daemon: `python vidurai-daemon/daemon.py` |
| No memories in DB | `sqlite3 ~/.vidurai/memory.db "SELECT COUNT(*) FROM memories;"` returns 0 | Check VS Code extension is connected |
| Wrong project context | `/project/current` shows wrong path | Set `project_path` explicitly in SDK |
| Errors not clearing | Zombie Killer not triggering | Ensure diagnostic severity=2+ sent on fix |
| Lock contention | Slow writes, timeouts | Verify Queue-Based Actor is active (check logs) |

### 6.2 Log Locations

```bash
# Daemon logs (stdout when running)
# VS Code extension: Developer Tools → Console

# Enable debug logging
export VIDURAI_LOG_LEVEL=DEBUG
python vidurai-daemon/daemon.py
```

### 6.3 Reset Database

```bash
# Backup first!
cp ~/.vidurai/memory.db ~/.vidurai/memory.db.backup

# Reset (will lose all data)
rm ~/.vidurai/memory.db
# Restart daemon - will recreate schema
```

### 6.4 Verify IPC Connection

```bash
# Check VS Code extension status
# In VS Code: Ctrl+Shift+P → "Developer: Toggle Developer Tools" → Console

# Check for connection messages:
# "[Vidurai] Connected to daemon"
# "[Vidurai] Sent file_edit event"
```

---

## Summary

Vidurai is a **verifiable, transparent, local-first** cognitive layer for developers:

| Claim | Verification Command |
|-------|---------------------|
| "Data stays local" | `ls ~/.vidurai/memory.db` |
| "Daemon is running" | `curl localhost:7777/health` |
| "Memories are stored" | `sqlite3 ~/.vidurai/memory.db "SELECT COUNT(*) FROM memories;"` |
| "Errors are tracked" | `sqlite3 ~/.vidurai/memory.db "SELECT * FROM active_state;"` |
| "Context is served" | `curl localhost:7777/api/rpc -d '{"type":"request","data":{"method":"get_context","params":{}}}'` |
| "SDK works offline" | `python3 -c "from vidurai import VismritiMemory; print('OK')"` |
| "Pinning works" | `sqlite3 ~/.vidurai/memory.db "SELECT * FROM memories WHERE pinned=1;"` |
| "WAL mode active" | `sqlite3 ~/.vidurai/memory.db "PRAGMA journal_mode;"` |

**The system is observable, testable, and hackable.**

---

## File Structure Reference

```
vidurai/
├── vidurai/                      # Python SDK (THE BRAIN)
│   ├── __init__.py              # Exports VismritiMemory, SalienceLevel
│   ├── vismriti_memory.py       # Main entry point (1182 lines)
│   ├── version.py               # Version management
│   ├── core/                    # 31 intelligence modules
│   │   ├── koshas.py            # Three-Kosha architecture
│   │   ├── data_structures_v3.py # SalienceLevel, MemoryStatus
│   │   ├── oracle.py            # Audience Profiles
│   │   ├── vismriti.py          # Four Gates forgetting
│   │   ├── viveka.py            # Importance scoring
│   │   ├── rl_agent_v2.py       # Q-Learning
│   │   └── ...
│   ├── storage/
│   │   └── database.py          # SQLite backend (1567 lines)
│   └── integrations/
│       └── langchain.py         # LangChain drop-in
├── vidurai-daemon/               # Python Daemon (THE HUB)
│   ├── daemon.py                # FastAPI server
│   └── intelligence/
│       └── event_adapter.py     # IPC → SDK adapter
├── vidurai-vscode-extension/     # TypeScript Extension (THE SENSOR)
│   └── src/
│       ├── extension.ts         # Main entry
│       ├── ipc/                  # Named Pipe client
│       └── watchers/            # File, Diagnostic, Terminal
└── ~/.vidurai/                   # User Data
    └── memory.db                # SQLite database
```

---

*Generated: December 08, 2025*
*Version: Vidurai v2.0.1 POC Master Manual*
*Verified from actual source code audit*
