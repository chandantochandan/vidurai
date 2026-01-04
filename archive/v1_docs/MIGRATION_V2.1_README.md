# Vidurai v2.1 Migration Plan: Resilient Mesh Architecture

> **"Spinal Transplant"** - Replacing stdio/HTTP with Named Pipes/IPC

## Executive Summary

| Aspect | Current (v2.0.0) | Target (v2.1.0) |
|--------|------------------|-----------------|
| **Transport** | Subprocess + Stdio | Named Pipe (IPC) |
| **Protocol** | JSON-RPC over stdin/stdout | NDJSON over Named Pipe |
| **Resilience** | Crash = Data Loss | Offline Buffer + Auto-Recovery |
| **Security** | Secrets leak to backend | Edge Redaction (Gatekeeper) |
| **Filtering** | Backend-only | Edge + Backend (Stabilizer) |
| **Storage** | Unbounded SQLite | Archiver with Parquet export |

---

## Dependency Analysis & Conflicts

### Current Dependencies

**VS Code Extension (`package.json`):**
```json
{
  "@types/node": "^18.0.0",
  "@types/vscode": "^1.80.0",
  "typescript": "^5.1.0"
}
```

**Python Backend (`requirements.txt`):**
```
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0
watchdog>=3.0.0
```

### Required New Dependencies

| Phase | Package | Purpose | Conflict Risk |
|-------|---------|---------|---------------|
| Phase 4 | `pyarrow>=14.0.0` | Parquet export with ZSTD | None |
| Phase 4 | `pandas>=2.0.0` | DataFrame for archival | Already in vscode-ext venv |
| Phase 1 | Node.js `net` module | Named Pipe client | Built-in, no install |
| Phase 0 | None | Pure TypeScript regex | None |

### Platform-Specific Notes

| Platform | Named Pipe Path | asyncio Method |
|----------|-----------------|----------------|
| **Windows** | `\\.\pipe\vidurai-{uid}` | `asyncio.start_server()` with proactor |
| **macOS/Linux** | `/tmp/vidurai-{uid}.sock` | `asyncio.start_unix_server()` |

---

## Architecture Transformation

### Before (v2.0.0 - Fragile)
```
┌─────────────┐     spawn      ┌──────────────┐     stdin/stdout    ┌─────────────┐
│   VS Code   │ ───────────────→ │ bridge.py    │ ←─────────────────→ │ vidurai SDK │
│  Extension  │    subprocess   │ (subprocess) │     JSON-RPC        │   (memory)  │
└─────────────┘                 └──────────────┘                      └─────────────┘
       │
       │ HTTP polling
       ↓
┌─────────────┐
│   Daemon    │
│  (:7777)    │
└─────────────┘
```

**Problems:**
- Subprocess crash = extension crash
- No offline resilience
- Secrets leak in raw content
- No input validation
- HTTP polling overhead

### After (v2.1.0 - Resilient Mesh)
```
┌─────────────┐                 ┌──────────────────────────────────────────────┐
│   VS Code   │                 │              Daemon (Background)              │
│  Extension  │                 │  ┌─────────────┐  ┌──────────────────────┐   │
│             │                 │  │ IPC Server  │  │ Intelligence Layer   │   │
│ ┌─────────┐ │    Named Pipe   │  │ (asyncio)   │  │ ├─ Stabilizer        │   │
│ │Gatekeeper│─┼────────────────┼──┼─────────────┼──┼─├─ Context Mediator  │   │
│ │(sanitize)│ │  NDJSON        │  │             │  │ └─ Memory Bridge     │   │
│ └─────────┘ │                 │  └──────┬──────┘  └──────────┬───────────┘   │
│             │                 │         │                    │               │
│ ┌─────────┐ │                 │         ↓                    ↓               │
│ │EdgeFilter│ │                │  ┌──────────────┐    ┌──────────────────┐   │
│ │(throttle)│ │                │  │ Event Queue  │    │   Archiver       │   │
│ └─────────┘ │                 │  └──────┬───────┘    │  (lifecycle)     │   │
│             │                 │         │            └────────┬─────────┘   │
│ ┌─────────┐ │                 │         ↓                     │             │
│ │ Offline │ │  on reconnect   │  ┌──────────────┐             │             │
│ │ Buffer  │─┼─────────────────┼──┼─ Buffer      │             │             │
│ │(.jsonl) │ │                 │  │  Scanner     │             │             │
│ └─────────┘ │                 │  └──────────────┘             │             │
└─────────────┘                 └───────────────────────────────┼─────────────┘
                                                                │
                                                                ↓
                                              ┌─────────────────────────────┐
                                              │  ~/.vidurai/                │
                                              │  ├── memory.db (SQLite)     │
                                              │  ├── buffer-*.jsonl         │
                                              │  └── archive/YYYY-MM.parquet│
                                              └─────────────────────────────┘
```

---

## File Operations Summary

### Files to DELETE (KILL)
```
vidurai-vscode-extension/
├── python-bridge/           # ENTIRE DIRECTORY
│   ├── bridge.py
│   ├── event_processor.py
│   ├── vidurai_manager.py
│   └── test_bridge.py
└── src/
    └── pythonBridge.ts      # Old subprocess bridge
```

### Files to CREATE
```
vidurai-vscode-extension/
└── src/
    ├── security/
    │   └── Gatekeeper.ts    # Phase 0: PII/Secrets redaction
    ├── ipc/
    │   └── Client.ts        # Phase 1: Named Pipe client
    └── utils/
        └── EdgeFilter.ts    # Phase 3: Rate limiting & git awareness

vidurai-daemon/
├── ipc/
│   └── server.py            # Phase 1: Named Pipe server
├── intelligence/
│   └── stabilizer.py        # Phase 3: Debounce & flap detection
└── storage/
    └── archiver.py          # Phase 4: Parquet archival
```

### Files to MODIFY
```
vidurai-daemon/
└── daemon.py                # Phase 1: Add IPC server, keep HTTP for browser ext

vidurai-vscode-extension/
└── src/
    └── extension.ts         # Wire up Gatekeeper, Client, EdgeFilter
```

### Files to KEEP (No Changes)
```
vidurai/                     # ENTIRE SDK - DO NOT TOUCH
├── core/                    # Memory logic untouched
├── storage/database.py      # SQLite backend
└── vismriti_memory.py       # Main API
```

---

## Phase Implementation Details

### Phase 0: The Shield (Security)

**Goal:** Stop shipping secrets to backend.

**Files:**
- CREATE: `src/security/Gatekeeper.ts`

**Test Criteria:**
```typescript
// Must pass:
Gatekeeper.sanitize('sk-proj-1234567890abcdef')
  → '<REDACTED:OPENAI_KEY:a1b2c3>'

Gatekeeper.sanitize('print("hello")')
  → 'print("hello")'  // No false positive
```

---

### Phase 1: The Nervous System (IPC)

**Goal:** Replace subprocess with persistent Named Pipe.

**Files:**
- CREATE: `src/ipc/Client.ts`
- CREATE: `vidurai-daemon/ipc/server.py`
- MODIFY: `vidurai-daemon/daemon.py`

**Protocol:** NDJSON (Newline-Delimited JSON)
```json
{"v":1,"type":"file_edit","ts":1701234567890,"data":{...}}\n
{"v":1,"type":"heartbeat","ts":1701234567895}\n
```

**Test Criteria:**
```bash
# Terminal 1: Start daemon
python -m vidurai_daemon.daemon

# Terminal 2: Test client
node -e "
const net = require('net');
const client = net.createConnection('\\\\.\\pipe\\vidurai-test');
client.on('data', d => console.log(d.toString()));
client.write('{\"type\":\"ping\"}\\n');
"
# Expect: {"type":"pong"} + heartbeat within 5s
```

---

### Phase 2: The Circuit Breaker (Resilience)

**Goal:** Zero data loss when daemon is down.

**Files:**
- MODIFY: `src/ipc/Client.ts` (add offline buffer)
- MODIFY: `vidurai-daemon/daemon.py` (add startup scanner)

**State Machine:**
```
┌──────────────┐
│  CONNECTED   │ ←── Write to socket
└──────┬───────┘
       │ socket error
       ↓
┌──────────────┐
│ DISCONNECTED │ ←── Append to ~/.vidurai/buffer-{session}.jsonl
└──────┬───────┘
       │ reconnect success
       ↓
┌──────────────┐
│  DRAINING    │ ←── Read buffer → Send → Delete file
└──────────────┘
```

**Test Criteria:**
```bash
# 1. Kill daemon
# 2. Trigger event in VS Code
# 3. Assert: buffer-*.jsonl exists
# 4. Start daemon
# 5. Assert: buffer file deleted, daemon logs "Ingested X offline events"
```

---

### Phase 3: Intelligence (Stabilization)

**Goal:** Filter noise at edge, stabilize at daemon.

**Files:**
- CREATE: `src/utils/EdgeFilter.ts`
- CREATE: `vidurai-daemon/intelligence/stabilizer.py`

**Edge Filter Rules:**
- Max 10 events/sec per file path
- During git operations (`.git/index.lock` exists): buffer into single CONTEXT_SWITCH

**Stabilizer Rules:**
- `on_save` → Commit immediately
- `keystroke` → Wait 2.0s, reset timer on new keystroke
- Flapping detection: A→B→A within 1s = discard B

**Test Criteria:**
```bash
# Spam test: Send 50 edit events in 1 second
# Assert: Daemon receives max 10 OR logs "Stabilizer coalesced N events"

# Typo test: Send "print(x,,)" then "print(x)" within 1s
# Assert: Only "print(x)" in database
```

---

### Phase 4: The Archiver (Storage Lifecycle)

**Goal:** Prevent 10GB database.

**Files:**
- CREATE: `vidurai-daemon/storage/archiver.py`

**Trigger Conditions:**
- `memory.db` > 100MB
- OR time is 03:00 AM local

**Archive Process:**
1. SELECT memories WHERE created_at < (now - 30 days)
2. Write to `~/.vidurai/archive/YYYY-MM.parquet` (ZSTD compression)
3. DELETE from SQLite
4. VACUUM database

**Test Criteria:**
```python
# Mock 60-day-old data in DB
archiver.run_now()
# Assert: DB is empty/small
# Assert: archive/*.parquet exists
# Assert: Data readable from Parquet
```

---

## Migration Checklist

### Pre-Migration
- [ ] Backup `~/.vidurai/memory.db`
- [ ] Document current extension version
- [ ] Ensure daemon is stopped

### Phase 0
- [ ] Create `src/security/Gatekeeper.ts`
- [ ] Add regex patterns for AWS, OpenAI, private keys
- [ ] Implement entropy check for large files
- [ ] Write unit tests

### Phase 1
- [ ] Create `src/ipc/Client.ts`
- [ ] Create `vidurai-daemon/ipc/server.py`
- [ ] Modify `daemon.py` to start IPC server
- [ ] Add heartbeat mechanism
- [ ] Test cross-platform (Windows/Mac/Linux)

### Phase 2
- [ ] Add offline buffer to Client.ts
- [ ] Add buffer scanner to daemon.py
- [ ] Test disconnect/reconnect scenarios

### Phase 3
- [ ] Create EdgeFilter.ts
- [ ] Create stabilizer.py
- [ ] Wire into event pipeline
- [ ] Test spam protection

### Phase 4
- [ ] Add pyarrow to requirements.txt
- [ ] Create archiver.py
- [ ] Schedule archival job
- [ ] Test Parquet read/write

### Post-Migration
- [ ] DELETE `python-bridge/` directory
- [ ] DELETE `pythonBridge.ts`
- [ ] Update extension version to 2.1.0
- [ ] Update README documentation

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Windows Named Pipe issues | Medium | High | Test on Windows early; fallback to localhost TCP |
| Offline buffer grows too large | Low | Medium | Cap buffer at 10MB, drop oldest |
| Archiver corrupts data | Low | High | Transaction + backup before archive |
| Extension breaks during migration | Medium | High | Feature flag for new IPC; keep old code until stable |

---

## Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Extension crash rate | ~5%/week | <0.1%/week |
| Data loss on daemon crash | 100% | 0% |
| Secrets leaked to backend | Unknown | 0 |
| DB size after 6 months | Unbounded | <500MB |
| Event latency | ~50ms (HTTP) | <5ms (IPC) |

---

## Questions for Clarification

1. **Heartbeat Interval:** Plan says 5s. Is this acceptable, or should it be configurable?

2. **Buffer Size Limit:** Should we cap offline buffer at 10MB? What happens when exceeded - drop oldest or newest?

3. **Archival Retention:** Archive files stored forever, or delete after N months?

4. **FastAPI Coexistence:** Keep HTTP endpoints for browser extension, or migrate browser to WebSocket only?

5. **Windows Testing:** Do you have a Windows environment for testing Named Pipes?

---

*Generated: 2025-12-02*
*Author: Claude Code Auditor*
