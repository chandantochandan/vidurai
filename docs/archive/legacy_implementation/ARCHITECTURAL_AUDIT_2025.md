# VIDURAI ARCHITECTURAL AUDIT REPORT

**Date:** December 14, 2024
**Auditor:** Claude Code
**SDK Version:** 2.1.0
**Scope:** Full codebase deep scan

---

## EXECUTIVE SUMMARY

Vidurai is a **distributed local-first AI memory system** with a hub-and-spoke architecture. The project consists of:

| Component | Type | Version | Status |
|-----------|------|---------|--------|
| Main SDK | Python Package | 2.1.0 | ✅ Active |
| Daemon | Python/FastAPI | 2.1.0 | ✅ Active |
| VSCode Extension | TypeScript | 2.1.0 | ✅ Active |
| Browser Extension | JavaScript | 2.1.0 | ✅ Active |
| Proxy | Python/FastAPI | **1.6.1** | ⛔ BROKEN |

**Critical Finding:** The architecture shows signs of organic evolution with:
- **Overlapping concerns** (4 context retrieval implementations)
- **Redundant engines** (4 decay/forgetting systems)
- **Version mismatch** (Proxy requires SDK 1.6.1, but SDK is 2.1.0)
- **Triple memory models** (v1.5, v2.0, v3.0 coexist)

---

## 1. THE PHYSICAL STRUCTURE

### Directory Tree (Depth 3)

```
vidurai/                              # ROOT PROJECT
├── vidurai/                          # 📦 MAIN SDK (Python Package)
│   ├── core/                         # 🧠 Intelligence modules (38+ files)
│   │   ├── ingestion/                # Event ingestion pipeline
│   │   ├── data_structures_v2.py     # ⚠️ LEGACY memory model
│   │   ├── data_structures_v3.py     # ✅ CURRENT memory model
│   │   ├── koshas.py                 # ⚠️ LEGACY Three Kosha (v1.5)
│   │   ├── oracle.py                 # ✅ Context oracle (NEW)
│   │   ├── memory_pinning.py         # Memory pinning system
│   │   ├── retention_policy.py       # Retention management
│   │   ├── passive_decay.py          # ⚠️ DECAY ENGINE 1
│   │   ├── active_unlearning.py      # ⚠️ DECAY ENGINE 2
│   │   ├── intelligent_decay_v2.py   # ⚠️ DECAY ENGINE 3
│   │   ├── vismriti.py               # ⚠️ DECAY ENGINE 4 (legacy)
│   │   └── ... (18+ more modules)
│   ├── storage/
│   │   └── database.py               # SQLite backend (Queue-Actor)
│   ├── clients/
│   │   ├── jupyter_client.py         # Jupyter integration
│   │   └── magics.py                 # IPython magics
│   ├── config/                       # Configuration modules
│   ├── integrations/
│   │   └── langchain.py              # LangChain adapter
│   ├── vismriti_memory.py            # 🎯 MAIN UNIFIED API
│   ├── cli.py                        # CLI interface
│   └── mcp_server.py                 # MCP server
│
├── vidurai-daemon/                   # 🔌 STANDALONE SERVICE
│   ├── daemon.py                     # Entry point (1,833 LOC)
│   ├── intelligence/                 # ⚠️ DUPLICATES SDK LOGIC
│   │   └── context_mediator.py       # Context formatting (24KB)
│   ├── project_brain/                # Project scanning
│   ├── ipc/                          # Named pipe server
│   └── archiver/                     # State archiving
│
├── vidurai-proxy/                    # ⛔ BROKEN SERVICE
│   ├── src/
│   │   └── main.py                   # Entry point
│   └── requirements.txt              # requires vidurai==1.6.1 ❌
│
├── vidurai-vscode-extension/         # 🔌 VS CODE EXTENSION
│   ├── src/
│   │   ├── extension.ts              # Entry point
│   │   └── views/                    # UI components
│   └── python-bridge/                # SDK subprocess
│
├── vidurai-browser-extension/        # 🔌 BROWSER EXTENSION
│   ├── background.js                 # Service worker
│   └── content.js                    # Context injection
│
└── archive/                          # 🗑️ DEAD CODE
    ├── v1_docs/
    ├── old_scripts/
    └── junk/
```

### Classification

| Type | Folders | Assessment |
|------|---------|------------|
| **Core Logic** | `vidurai/core/`, `vidurai/storage/` | ✅ Belongs in SDK |
| **Standalone Services** | `vidurai-daemon/`, `vidurai-proxy/` | ⚠️ Review needed |
| **Extensions** | `vidurai-vscode-extension/`, `vidurai-browser-extension/` | ✅ Correct as separate |
| **Dead Code** | `archive/`, `*.bak` files | 🗑️ Delete |

---

## 2. THE DAEMON (The Body)

### Entry Point
```
/home/user/vidurai/vidurai-daemon/daemon.py
```

### Dependencies & Responsibilities

```python
# daemon.py imports
from vidurai.vismriti_memory import VismritiMemory  # ← SDK dependency
from vidurai.storage.database import MemoryDatabase
from vidurai.core.memory_pinning import MemoryPinManager

# Internal modules
from intelligence.context_mediator import ContextMediator  # ⚠️ DUPLICATES Oracle
from intelligence.event_adapter import EventAdapter
from project_brain.scanner import ProjectScanner
from project_brain.context_builder import ContextBuilder
from ipc.server import IPCServer
```

### Current Responsibilities

| Responsibility | Module | LOC | Notes |
|----------------|--------|-----|-------|
| HTTP API | `daemon.py` (FastAPI) | 500+ | `/health`, `/api/rpc`, `/context` |
| IPC Server | `ipc/server.py` | ~200 | Named pipe for VS Code |
| Context Formatting | `intelligence/context_mediator.py` | 800+ | ⚠️ DUPLICATES SDK's Oracle |
| Event Processing | `intelligence/event_adapter.py` | 300 | Converts IPC → SDK |
| Project Scanning | `project_brain/scanner.py` | 600+ | File system watching |
| State Archiving | `archiver/` | ~200 | Session persistence |

### Plugin/Module System Analysis

**CRITICAL CHECK:** Does the daemon have a plugin system?

**Answer: NO** - The daemon has a **monolithic architecture**:

```python
# daemon.py - All components hardcoded
class ViduraiDaemon:
    def __init__(self):
        self.memory = VismritiMemory()           # Hardcoded
        self.mediator = ContextMediator()         # Hardcoded
        self.scanner = ProjectScanner()           # Hardcoded
        self.ipc_server = IPCServer()             # Hardcoded
```

**Implication:** Every new feature requires modifying `daemon.py` or adding new internal modules. No dynamic loading.

**Recommendation:** Consider a simple plugin registry:
```python
# Proposed plugin system
class DaemonPlugin:
    def on_event(self, event): pass
    def on_shutdown(self): pass

daemon.register_plugin(MyCustomPlugin())
```

---

## 3. THE SDK (Three Kosha Wisdom)

### Three Kosha Structure (Legacy v1.5)

The original architecture was based on Vedantic philosophy:

```
┌─────────────────────────────────────────────┐
│           Vijnanamaya Kosha                 │  ← Wisdom/Archival
│           (Long-term Patterns)              │
├─────────────────────────────────────────────┤
│           Manomaya Kosha                    │  ← Episodic Memory
│           (Historical Events)               │
├─────────────────────────────────────────────┤
│           Annamaya Kosha                    │  ← Working Memory
│           (Current Context)                 │
└─────────────────────────────────────────────┘
```

**Implemented in:** `vidurai/core/koshas.py` (23KB, 700 LOC)

**Status:** DEPRECATED but still exported for backwards compatibility.

### Current Architecture (v2.0+)

The SDK has evolved to use **VismritiMemory** as the unified API:

```
┌──────────────────────────────────────────────────────────────┐
│                    VismritiMemory                            │
│                  (Unified Entry Point)                       │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   remember() │  │    recall()  │  │   forget()   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                  │               │
│         ▼                 ▼                  ▼               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              SQLite Database (WAL Mode)             │    │
│  │              storage/database.py                     │    │
│  └─────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow: Daemon → SDK → Daemon

```
VS Code Extension                    Daemon                      SDK
     │                                │                           │
     │ IPC: file_changed             │                           │
     │ ──────────────────────────►   │                           │
     │                                │ EventAdapter.process()    │
     │                                │ ──────────────────────►   │
     │                                │                           │ VismritiMemory.remember()
     │                                │                           │ ──────────────────────►
     │                                │                           │        Database
     │                                │                           │ ◄──────────────────────
     │                                │                           │
     │                                │ ContextMediator.format()  │
     │                                │ ◄──────────────────────   │
     │ HTTP: /context                 │                           │
     │ ◄──────────────────────────   │                           │
```

**Problem:** The daemon's `ContextMediator` duplicates the SDK's `Oracle`. Data is formatted twice.

### Orphan Files Outside SDK Structure

| File | Location | Should Be In | Action |
|------|----------|--------------|--------|
| `oracle.py` | `vidurai/core/` | ✅ Correct | Keep |
| `context_mediator.py` | `vidurai-daemon/intelligence/` | Should use Oracle | **MERGE** |
| `koshas.py` | `vidurai/core/` | `vidurai/legacy/` | **MOVE** |
| `data_structures_v2.py` | `vidurai/core/` | `vidurai/legacy/` | **DEPRECATE** |
| `vismriti.py` | `vidurai/core/` | `vidurai/legacy/` | **DEPRECATE** |
| `langchain.py` | `vidurai/integrations/` | EMPTY FILE | **DELETE** |

---

## 4. THE BLOAT DETECTION

### 4.1 Configuration Files Audit

#### pyproject.toml
```toml
version = "2.1.0"  # ✅ Correct
requires-python = ">=3.9"  # ✅ Correct
```

#### requirements.txt Issues

| Issue | Line | Problem |
|-------|------|---------|
| Duplicate | 40, 42 | `pyarrow>=14.0.0` listed twice |
| Competing Frameworks | - | Both LangChain AND LlamaIndex installed |
| Heavy NLP | - | spaCy + sentence-transformers (100MB+) |

```txt
# DUPLICATES FOUND:
pyarrow>=14.0.0          # Line 40
pyarrow>=14.0.0          # Line 42 (DUPLICATE!)

# COMPETING FRAMEWORKS:
langchain>=0.1.0         # RAG Framework 1
llama-index>=0.9.0       # RAG Framework 2 (DO WE NEED BOTH?)

# HEAVY DEPENDENCIES:
spacy>=3.7.0             # ~50MB
sentence-transformers    # ~50MB
faiss-cpu               # ~20MB
```

**Question:** Are both LangChain AND LlamaIndex actively used? If not, remove one (~50MB saved).

#### vidurai-proxy/requirements.txt

```txt
vidurai==1.6.1           # ⛔ CRITICAL: SDK is 2.1.0!
```

This causes immediate import failure when proxy starts.

### 4.2 Docker Analysis

#### docker-compose.yml

```yaml
services:
  vidurai-daemon:
    build: ./vidurai-daemon
    ports:
      - "7777:7777"
    volumes:
      - ./vidurai:/app/vidurai  # Mounts SDK

  vidurai-proxy:
    build: ./vidurai-proxy
    ports:
      - "9999:9999"
    depends_on:
      - vidurai-daemon
```

**Issues:**
1. **Proxy depends on daemon but uses HTTP** - No service mesh, just HTTP polling
2. **Both containers install SDK** - Duplicated 50MB+ in each image
3. **No health checks defined** - Container could be running but broken

**Could Proxy Be a Module?**

```python
# Current: Separate container
# vidurai-proxy/src/main.py
from vidurai import VismritiMemory  # Imports SDK

# Proposed: Internal module
# vidurai/api/proxy_routes.py
@router.post("/v1/chat/completions")
async def openai_proxy(request):
    context = memory.get_context_for_ai()
    # ... forward to OpenAI
```

**Assessment:** Proxy could be a FastAPI router inside the daemon, not a separate service.

### 4.3 Duplicate Library Detection

| Function | Libraries | Used By | Recommendation |
|----------|-----------|---------|----------------|
| Embeddings | sentence-transformers, OpenAI | SDK | Keep sentence-transformers |
| RAG | LangChain, LlamaIndex | SDK | **REMOVE LlamaIndex** (unused) |
| NLP | spaCy, nltk | SDK | Keep spaCy only |
| Vector Search | faiss-cpu | SDK | Keep (essential) |
| HTTP | httpx, requests | Various | Standardize on httpx |

---

## 5. REDUNDANCY DEEP DIVE

### 5.1 Four Context Retrieval Implementations

| Implementation | Location | Purpose | LOC |
|----------------|----------|---------|-----|
| `VismritiMemory.get_context_for_ai()` | SDK | Direct API | 50 |
| `Oracle.get_context(audience)` | SDK | Audience-specific | 100 |
| `ContextMediator.get_formatted_context()` | Daemon | Event formatting | 300+ |
| `cli.py::get_context_json()` | CLI | JSON output | 30 |

**Problem:** Same data formatted 4 different ways with subtle differences.

**Solution:** Single source of truth:
```python
# Make Oracle the canonical implementation
class Oracle:
    def get_context(self, audience='developer', max_tokens=2000):
        # Single implementation here

# VismritiMemory delegates
class VismritiMemory:
    def get_context_for_ai(self, ...):
        return self.oracle.get_context(...)

# ContextMediator delegates
class ContextMediator:
    def get_formatted_context(self, ...):
        return self.oracle.get_context(...)
```

### 5.2 Four Decay/Forgetting Engines

| Engine | File | Status | Notes |
|--------|------|--------|-------|
| PassiveDecayEngine | `passive_decay.py` | ✅ Active | Time-based decay |
| ActiveUnlearningEngine | `active_unlearning.py` | ✅ Active | User-initiated |
| IntelligentDecayV2 | `intelligent_decay_v2.py` | ⚠️ Partial | Salience-based |
| VismritiEngine | `vismriti.py` | ⚠️ Legacy | Original impl |

**Solution:** Strategy pattern:
```python
class DecayEngine:
    strategies: List[DecayStrategy] = []

    def decay(self, memories):
        for strategy in self.strategies:
            memories = strategy.apply(memories)
        return memories
```

### 5.3 Three Memory Models

| Model | File | Fields | Status |
|-------|------|--------|--------|
| v1.5 (Kosha) | `koshas.py` | `working_memory`, `episodic` | ⚠️ DEPRECATED |
| v2.0 | `data_structures_v2.py` | `content`, `memory_type` | ⚠️ SUPERSEDED |
| v3.0 | `data_structures_v3.py` | `content`, `salience` | ✅ CURRENT |

**Problem:** Code importing from v2 gets different `Memory` than v3:
```python
from vidurai.core.data_structures_v2 import Memory  # memory_type field
from vidurai.core.data_structures_v3 import Memory  # salience field
```

**Solution:** Keep only v3, deprecate others.

---

## 6. SUGGESTED MERGES/DELETIONS

### 🗑️ DELETE (Dead Code)

| Item | Path | Reason |
|------|------|--------|
| Archive folder | `archive/` | Contains v1_docs, old_scripts, junk |
| Backup files | `vidurai/core/*.bak` | Stale backups |
| Old content.js | `vidurai-browser-extension/content-old-day4.js` | Old iteration |
| Empty langchain | `vidurai/integrations/langchain.py` | 0 LOC |
| Duplicate pyarrow | `requirements.txt` line 42 | Duplicate entry |

**Estimated cleanup: ~500KB, 5+ files**

### ⚠️ DEPRECATE (Move to legacy/)

| Item | Current Path | Action |
|------|--------------|--------|
| Three Kosha | `vidurai/core/koshas.py` | Move to `vidurai/legacy/` |
| Memory v2 | `vidurai/core/data_structures_v2.py` | Move to `vidurai/legacy/` |
| VismritiEngine | `vidurai/core/vismriti.py` | Move to `vidurai/legacy/` |
| Viveka | `vidurai/core/viveka.py` | Move to `vidurai/legacy/` |

### 🔄 MERGE (Consolidate)

| Source | Target | Reason |
|--------|--------|--------|
| `ContextMediator` (daemon) | `Oracle` (SDK) | Duplicate context logic |
| `IntelligentDecayV2` | `DecayEngine` with strategies | Consolidate decay |
| `vidurai-proxy` | `vidurai-daemon` as router | Reduce containers |

### 🔧 FIX (Critical Bugs)

| Issue | File | Fix |
|-------|------|-----|
| Version mismatch | `vidurai-proxy/requirements.txt` | Change `vidurai==1.6.1` to `>=2.1.0` |
| No health checks | `docker-compose.yml` | Add healthcheck config |

---

## 7. CRITICAL PATH FORWARD

### Phase 1: Emergency Fixes (1 day)

```bash
# Fix proxy version
sed -i 's/vidurai==1.6.1/vidurai>=2.1.0/' vidurai-proxy/requirements.txt

# Remove duplicate pyarrow
# Edit requirements.txt manually

# Delete dead code
rm -rf archive/
rm vidurai/core/*.bak
rm vidurai-browser-extension/content-old-day4.js
rm vidurai/integrations/langchain.py
```

### Phase 2: SDK Consolidation (1 week)

1. Create `vidurai/legacy/` folder
2. Move deprecated modules there
3. Update `__init__.py` with deprecation warnings
4. Consolidate decay engines into strategy pattern
5. Make Oracle the single context source

### Phase 3: Service Consolidation (1 week)

1. Merge proxy routes into daemon
2. Remove proxy container
3. Add health checks to docker-compose
4. Update browser extension to use unified endpoint

### Phase 4: Dependency Cleanup (2 days)

1. Remove LlamaIndex if unused
2. Audit spaCy usage (heavy)
3. Standardize on httpx for HTTP

---

## 8. ARCHITECTURE RECOMMENDATIONS

### Current State

```
┌─────────────────────────────────────────────────────────┐
│                    Browser Extension                     │
└──────────────────────────┬──────────────────────────────┘
                           │ HTTP
                           ▼
┌────────────────────────────────────────────────────────┐
│                       Daemon                            │
│  ┌─────────────────┐  ┌─────────────────────────────┐  │
│  │ ContextMediator │  │ EventAdapter                │  │ ← DUPLICATE LOGIC
│  └────────┬────────┘  └─────────────────────────────┘  │
│           │                                             │
│           ▼ imports                                     │
│  ┌─────────────────────────────────────────────────┐   │
│  │                   SDK                            │   │
│  │  ┌────────┐  ┌────────┐  ┌────────┐            │   │
│  │  │ Oracle │  │ v2 Mem │  │ v3 Mem │ ← 3 MODELS │   │
│  │  └────────┘  └────────┘  └────────┘            │   │
│  │  ┌──────────────────────────────────┐          │   │
│  │  │ 4 Decay Engines (redundant)      │          │   │
│  │  └──────────────────────────────────┘          │   │
│  └─────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────┘
        ┌───────────────────────────────────┐
        │           Proxy (BROKEN)          │ ← VERSION MISMATCH
        │       requires SDK 1.6.1          │
        └───────────────────────────────────┘
```

### Target State

```
┌─────────────────────────────────────────────────────────┐
│              Browser + VS Code Extensions                │
└──────────────────────────┬──────────────────────────────┘
                           │ IPC/HTTP
                           ▼
┌────────────────────────────────────────────────────────┐
│                  Unified Daemon                         │
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │               Routes (FastAPI)                  │    │
│  │  /context  /health  /v1/chat/completions       │    │ ← PROXY MERGED
│  └────────────────────────┬───────────────────────┘    │
│                           │                             │
│                           ▼                             │
│  ┌────────────────────────────────────────────────┐    │
│  │                    SDK 2.1.0                   │    │
│  │                                                 │    │
│  │  ┌────────────┐  ┌────────────────────────┐   │    │
│  │  │   Oracle   │  │ DecayEngine (Unified)  │   │    │ ← CONSOLIDATED
│  │  │ (Single    │  │  - PassiveStrategy     │   │    │
│  │  │  Context)  │  │  - ActiveStrategy      │   │    │
│  │  └────────────┘  └────────────────────────┘   │    │
│  │                                                 │    │
│  │  ┌────────────────────────────────────────┐   │    │
│  │  │     Memory v3 (Single Model)           │   │    │ ← SINGLE MODEL
│  │  └────────────────────────────────────────┘   │    │
│  └────────────────────────────────────────────────┘    │
│                                                         │
│  ┌────────────────────────────────────────────────┐    │
│  │              Plugin Registry                    │    │ ← NEW
│  │  daemon.register_plugin(CustomPlugin)          │    │
│  └────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────┘
```

---

## 9. FINAL CHECKLIST

### Must Fix (Blocking)

- [ ] Fix proxy version mismatch (`vidurai==1.6.1` → `>=2.1.0`)
- [ ] Remove duplicate pyarrow from requirements.txt
- [ ] Delete archive/ folder and backup files

### Should Fix (Technical Debt)

- [ ] Consolidate 4 context implementations into Oracle
- [ ] Consolidate 4 decay engines into strategy pattern
- [ ] Move legacy modules to `vidurai/legacy/`
- [ ] Merge proxy into daemon as router
- [ ] Add docker health checks

### Nice to Have (Optimization)

- [ ] Remove LlamaIndex if unused (~50MB saved)
- [ ] Add daemon plugin system
- [ ] Standardize HTTP library to httpx
- [ ] Add deprecation warnings for legacy imports

---

## APPENDIX: File Sizes & LOC

| Component | Files | LOC | Size |
|-----------|-------|-----|------|
| SDK (vidurai/) | 50+ | ~15,000 | 2MB |
| Daemon | 15 | ~4,000 | 500KB |
| VSCode Extension | 20 | ~3,000 | 300KB |
| Browser Extension | 5 | ~500 | 50KB |
| Proxy | 10 | ~1,000 | 100KB |
| Archive (dead) | 20+ | ~2,000 | 500KB |

**Total Active Code:** ~23,500 LOC
**Dead Code:** ~2,000 LOC (8.5%)

---

*Report generated by Claude Code Architectural Audit*
