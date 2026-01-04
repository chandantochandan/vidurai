# 🧠 VIDURAI ARCHITECTURE (v2.2.0)

> **विस्मृति भी विद्या है** — "Forgetting too is knowledge"

## SYSTEM IDENTITY

**Vidurai** is a **Local-First AI Memory Infrastructure** that provides persistent context to AI tools without cloud dependencies. It acts as a distributed context middleware between IDE/Browser telemetry and LLM context windows.

**Core Philosophy:**
- **Local-First**: All data stays on user's machine (`~/.vidurai/`)
- **Zero-Trust**: No cloud sync, no external dependencies for core functionality  
- **Signal-to-Noise Optimization**: Intelligent forgetting and memory management
- **Vedantic Approach**: Forgetting as a form of knowledge

---

## 📊 PROJECT METRICS (v2.2.0)

| Component | Status | Lines of Code | Language | Purpose |
|-----------|--------|---------------|----------|---------|
| **Core SDK** | ✅ Production | 31,442 | Python | Memory engine & CLI |
| **VS Code Extension** | ✅ Production | ~3,000 | TypeScript | IDE integration |
| **Browser Extension** | ⚠️ Experimental | ~2,000 | JavaScript | Web AI integration |
| **Proxy Server** | ⚠️ Prototype | ~1,500 | Python | API interception |
| **Tests** | ✅ Complete | 8,514 | Python | Quality assurance |
| **Total** | - | **~46,456** | Multi-lang | Complete system |

---

## 🏗️ ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                    VIDURAI v2.2.0                          │
│                Local-First AI Memory                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VS Code       │    │   Browser       │    │   CLI Tools     │
│   Extension     │◄──►│   Extension     │◄──►│   & Scripts     │
│   (Production)  │    │   (Experimental)│    │   (Production)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  VIDURAI CORE SDK                          │
│                    (Python Engine)                         │
├─────────────────────────────────────────────────────────────┤
│  CLI Interface (25 commands)     │  MCP Server (JSON-RPC)   │
│  • recall, context, stats        │  • Claude Desktop        │
│  • pin, unpin, hints            │  • AI tool integration   │
│  • forgetting-log, hygiene      │  • HTTP/WebSocket        │
├─────────────────────────────────────────────────────────────┤
│                 SF-V2 Smart Forgetting Engine              │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Salience    │ │ Entity      │ │ Memory Role             ││
│  │ Classifier  │ │ Extractor   │ │ Classifier              ││
│  │ (5 levels)  │ │ (15+ types) │ │ (CAUSE/RESOLUTION/etc)  ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Retention   │ │ Memory      │ │ Semantic                ││
│  │ Scoring     │ │ Pinning     │ │ Consolidation           ││
│  │ (0-200)     │ │ (User Ctrl) │ │ (Smart Compression)     ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
├─────────────────────────────────────────────────────────────┤
│                    Storage Layer                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ SQLite      │ │ Forgetting  │ │ Parquet Archives        ││
│  │ (Hot Data)  │ │ Ledger      │ │ (Cold Storage)          ││
│  │ WAL Mode    │ │ (Audit)     │ │ Date Partitioned        ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  ~/.vidurai/    │
                    │  Local Storage  │
                    └─────────────────┘
```

---

## 🧬 CORE SDK ARCHITECTURE

### Main Components (vidurai/)

```
vidurai/
├── cli.py (1,621 lines)           # 25 CLI commands
├── vismriti_memory.py (1,273)     # Main memory interface
├── mcp_server.py (555)            # Model Context Protocol server
├── repl.py (470)                  # Interactive shell
├── __init__.py (113)              # Lazy loading architecture
├── core/ (18,884 lines)           # SF-V2 Engine
├── daemon/ (8 modules)            # Background service
├── storage/ (780 lines)           # SQLite database layer
├── integrations/                  # LangChain, etc.
└── shared/                        # Common utilities
```

### Core Engine Modules (vidurai/core/)

| Module | Lines | Purpose |
|--------|-------|---------|
| `data_structures_v3.py` | 400+ | Memory schemas & types |
| `salience_classifier.py` | 300+ | CRITICAL/HIGH/MEDIUM/LOW/NOISE |
| `memory_pinning.py` | 400+ | User-controlled memory pinning |
| `forgetting_ledger.py` | 450+ | Audit trail for all forgetting |
| `entity_extractor.py` | 530+ | Extract 15+ technical entities |
| `memory_role_classifier.py` | 320+ | RESOLUTION/CAUSE classification |
| `retention_score.py` | 400+ | Multi-factor retention scoring |
| `semantic_consolidation.py` | 972+ | Smart compression engine |
| `proactive_hints.py` | 700+ | Hint generation system |
| `episode_builder.py` | 450+ | Memory grouping & episodes |
| `event_bus.py` | 300+ | Async event system |

### Specialized Subsystems

```
core/
├── archival/           # SQLite → Parquet migration
├── constitution/       # Retention policies & hygiene
├── intelligence/       # Vector brain & embeddings  
├── verification/       # Code auditing & safety
├── shadow/            # Safe code modification
├── ingestion/         # Historical data import
├── analytics/         # Repository analysis
├── bridge/           # LangChain integration
├── controllers/      # Search & retrieval
├── sensors/          # Reality verification
├── safety/           # Flight recorder
├── state/            # User focus tracking
└── rl/               # Reinforcement learning
```

---

## 🔌 INTEGRATION ARCHITECTURE

### VS Code Extension (Production)
```
vidurai-vscode-extension/
├── src/
│   ├── extension.ts              # Main entry point
│   ├── fileWatcher.ts           # File change monitoring
│   ├── terminalWatcher.ts       # Command tracking
│   ├── diagnosticWatcher.ts     # Error capture
│   ├── views/memoryTreeView.ts  # Memory UI
│   ├── ipc/Client.ts           # Daemon communication
│   └── security/Gatekeeper.ts   # PII protection
├── python-bridge/               # Python integration
│   ├── bridge.py               # Main bridge
│   ├── event_processor.py      # Event handling
│   └── vidurai_manager.py      # SDK interface
└── package.json (v2.2.0)
```

### Browser Extension (Experimental)
```
vidurai-browser-extension/
├── manifest.json               # Chrome Extension v3
├── content.js                 # Universal injection
├── background.js              # Service worker
├── strategies/                # Platform-specific logic
└── injectors/                 # Context injection
```

### Daemon Service (Embedded)
```
vidurai/daemon/
├── server.py                  # FastAPI + WebSocket
├── intelligence/              # Context mediation
│   ├── context_mediator.py   # AI platform bridging
│   ├── memory_bridge.py      # SDK integration
│   └── human_ai_whisperer.py # Interaction optimization
├── project_brain/            # Project intelligence
│   ├── scanner.py           # Code scanning
│   ├── context_builder.py   # Context assembly
│   └── memory_store.py      # In-memory cache
└── ipc/                     # Inter-process communication
```

---

## 💾 DATA ARCHITECTURE

### Storage Hierarchy
```
~/.vidurai/
├── vidurai.db              # SQLite (Hot storage, WAL mode)
├── forgetting_ledger.jsonl # Audit trail (append-only)
├── daemon.pid             # Process management
├── vidurai.log           # Daemon logs (rotated)
└── archive/              # Cold storage
    └── YYYY/MM/          # Date-partitioned Parquet
```

### Memory Lifecycle
```
Input Event → Salience Classification → Entity Extraction
     ↓
Role Classification → Retention Scoring → Pinning Check
     ↓
Active Memory → Consolidation → Archival → Cold Storage
     ↓
Forgetting Ledger (Audit Trail)
```

### Data Flow
```
IDE/Browser → Extension → Daemon → Core SDK → SQLite
                ↓
            MCP Server → AI Tools (Claude, ChatGPT)
                ↓
            Context Injection → Enhanced AI Responses
```

---

## 🎯 API ENDPOINTS

### CLI Interface (25 Commands)
```bash
# Memory Operations
vidurai recall --query "auth bug" --limit 10
vidurai context --query "login flow" --audience developer
vidurai recent --hours 24
vidurai stats --project /path/to/project

# Memory Management  
vidurai pin 123 --reason "critical bug fix"
vidurai unpin 123
vidurai pins --show-content
vidurai hygiene --force

# Forgetting System
vidurai forgetting-log --limit 10
vidurai forgetting-stats --days 30

# Data Operations
vidurai export --format json --output memories.json
vidurai ingest conversations.json --type anthropic
vidurai clear --project /path/to/project

# Services
vidurai start                    # Start daemon
vidurai stop                     # Stop daemon  
vidurai status                   # Check status
vidurai server --port 8765       # Start MCP server
vidurai mcp-install              # Install for Claude
```

### MCP Server (JSON-RPC)
- **Endpoint**: `http://localhost:8765`
- **Protocol**: JSON-RPC over HTTP
- **Integration**: Claude Desktop, AI tools
- **Methods**: `get_context`, `search_memories`, `get_stats`

### Daemon Service (WebSocket)
- **HTTP**: `http://localhost:7777`
- **WebSocket**: `ws://localhost:7777`
- **Endpoints**: `/smart-context`, `/report-error`, `/metrics`

---

## 🔒 SECURITY & PRIVACY

### Local-First Architecture
- **Zero Cloud Sync**: All data stays on user's machine
- **PII Protection**: Regex-based sanitization in extensions
- **Audit Trail**: Complete transparency via forgetting ledger
- **User Control**: Memory pinning and manual overrides

### Data Protection
- **SQLite WAL Mode**: ACID compliance for all operations
- **Append-Only Ledger**: Immutable audit trail
- **Local Storage**: `~/.vidurai/` directory isolation
- **Process Isolation**: Daemon runs as user process

---

## 🚀 DEPLOYMENT STATUS

### Production Ready (v2.2.0)
- ✅ **Core Python SDK**: 25 CLI commands, SF-V2 engine
- ✅ **VS Code Extension**: Real-time telemetry capture
- ✅ **MCP Server**: Claude Desktop integration
- ✅ **Documentation**: CLI reference, troubleshooting guides

### Experimental/Prototype
- ⚠️ **Browser Extension**: Universal AI context injection
- ⚠️ **Proxy Server**: API interception for LLM calls

### Development Tools
- ✅ **Test Suite**: 28 test files, 8,514 lines
- ✅ **Scripts**: Verification, documentation generation
- ✅ **REPL**: Interactive memory exploration

---

## 🎯 UNIQUE VALUE PROPOSITIONS

1. **Local-First Privacy**: Zero cloud dependencies, complete data control
2. **Intelligent Forgetting**: SF-V2 smart compression with audit trails
3. **Universal Integration**: Works with Claude, ChatGPT, VS Code, browsers
4. **Real-time Context**: Live telemetry from development environment
5. **User Agency**: Memory pinning, manual overrides, transparency
6. **Vedantic Philosophy**: Forgetting as a form of knowledge refinement

---

## 📈 PERFORMANCE CHARACTERISTICS

- **CLI Startup**: < 0.5s (lazy loading architecture)
- **Memory Footprint**: ~50MB for daemon + extensions
- **Storage Efficiency**: SQLite + Parquet compression
- **Context Retrieval**: Sub-second for most queries
- **Scalability**: Handles projects with 100K+ memories

---

## 🔮 ROADMAP

### Immediate (v2.3.0)
- Browser extension stabilization
- Chrome Web Store publication
- VS Code Marketplace publication

### Near-term (v2.4.0)
- Proxy server production readiness
- Docker containerization
- CI/CD pipeline implementation

### Long-term (v3.0.0)
- Multi-project workspace support
- Advanced RL-based optimization
- Plugin ecosystem for custom integrations

---

*This architecture represents the current v2.2.0 Gold Master reality - a sophisticated local-first AI memory system combining Vedantic philosophy with cutting-edge technology to solve the context window problem for developers worldwide.*
