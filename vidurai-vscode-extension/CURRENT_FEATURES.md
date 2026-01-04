# Vidurai VS Code Extension - Current Features (v0.1.1)

**Last Updated:** November 18, 2024
**Extension Version:** 0.1.1
**Vidurai SDK:** v1.6.1
**Status:** Production-ready, tested

---

## Core Extension Features

### 1. **Automatic Context Tracking**
- **File Edit Tracking**: Monitors all file changes in workspace
 - Debounced to 2000ms (configurable)
 - Ignores specified paths (node_modules, .git, dist, build, out, .venv)
 - Max file size limit (51200 bytes, configurable)
 - Real-time tracking via `FileWatcher`

- **Terminal Output Tracking**: Captures terminal commands and output
 - Command execution tracking
 - Exit code monitoring
 - Output capture (stdout/stderr)
 - Configurable on/off (`vidurai.trackTerminal`)
 - Implemented via `TerminalWatcher`

- **Diagnostic Tracking**: Monitors errors and warnings
 - Language server diagnostics
 - Compile errors
 - Linter warnings
 - Severity classification (Error, Warning, Info)
 - Configurable on/off (`vidurai.trackDiagnostics`)
 - Implemented via `DiagnosticWatcher`

### 2. **Intelligent Memory Management**
- **Salience Classification**: 5-level importance system
 - CRITICAL: Errors, secrets detected
 - HIGH: Failed commands, test files, config changes
 - MEDIUM: Normal code edits, successful commands
 - LOW: Documentation changes
 - NOISE: Progress bars, ignored files, spam

- **Automatic Gist Extraction**: Semantic compression
 - File edits: Function/class detection
 - Terminal: Command summary with exit code
 - Diagnostics: Error message extraction
 - 59% token reduction validated

- **Memory Storage**: Local session persistence
 - Session files: `~/.vidurai/sessions/default.pkl`
 - Cross-project isolation
 - Automatic save on shutdown
 - No cloud sync (privacy-first)

### 3. **Security & Privacy**
- **Secrets Detection**: Pattern-based scanning
 - API keys (OpenAI, Anthropic, GitHub, AWS)
 - Database URLs (PostgreSQL, MySQL)
 - Private keys (RSA, DSA, EC, OpenSSH)
 - JWTs
 - Passwords
 - Environment variables

- **Automatic Redaction**: Content sanitization
 - Replaces detected secrets with `[REDACTED]`
 - Warnings logged for secret detection
 - Configurable ignored files (.env, credentials.json, etc.)

- **Local-Only Processing**
 - All processing happens on your machine
 - No telemetry or cloud sync
 - Works completely offline

### 4. **Python Bridge Architecture**
- **Robust IPC**: stdin/stdout JSON protocol
 - Unbuffered I/O for real-time communication
 - Request/response with ID tracking
 - Error handling and recovery
 - Graceful shutdown (SIGTERM, SIGINT)

- **Auto Installation**
 - Python detection (3.8+)
 - Virtual environment creation (python-bridge/.venv)
 - Vidurai SDK auto-install (v1.6.1)
 - Dependencies: detect-secrets, pyyaml

- **Health Monitoring**
 - Crash detection (max 3 retries)
 - Auto-restart on failure
 - Status bar health indicator
 - Bridge restart command

---

## 🎨 User Interface Features

### 1. **Status Bar Indicator**
- Real-time memory count display
- Click to copy context
- Offline/error states
- Auto-updates every 10 seconds
- Visual feedback for bridge status

### 2. **Memory TreeView (Sidebar)**
- **Activity Bar Icon**: 3 Kosha design
- **Categories**:
 - 🕐 Recent (24h): Last 20 memories
 - 🔥 Critical: CRITICAL salience only
 - ⚡ High Priority: HIGH salience only
 - 📊 Statistics: Memory counts by salience

- **Memory Details**:
 - Salience icons (🔥 CRITICAL, ⚡ HIGH, 📝 MEDIUM, 💬 LOW, 🔇 NOISE)
 - Gist preview (60 chars)
 - Age display (minutes, hours, days)
 - Tooltips with full details

- **Actions**:
 - Refresh button
 - Click memory to view details
 - Copy individual memory to clipboard
 - Webview panel for detailed view

### 3. **Commands**
- `Vidurai: Copy Relevant Context`: Export all memories as markdown
- `Vidurai: Restart Python Bridge`: Restart crashed bridge
- `Vidurai: Show Logs`: View extension output logs
- `Refresh Memories`: Update TreeView
- `Show Memory Details`: Open memory in webview
- `Copy to Clipboard`: Copy individual memory

---

## ⚙️ Configuration Options

All configurable via VS Code settings (`vidurai.*`):

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `vidurai.enabled` | boolean | true | Enable/disable extension |
| `vidurai.debounceMs` | number | 2000 | File edit debounce (500-10000ms) |
| `vidurai.pythonPath` | string | "" | Python path (auto-detected if empty) |
| `vidurai.logLevel` | enum | "info" | Logging level (debug/info/warn/error) |
| `vidurai.maxFileSize` | number | 51200 | Max file size to track (0=unlimited) |
| `vidurai.trackTerminal` | boolean | true | Track terminal commands |
| `vidurai.trackDiagnostics` | boolean | true | Track errors/warnings |
| `vidurai.ignoredPaths` | array | [see below] | Paths to ignore |

**Default Ignored Paths:**
- `node_modules`
- `.git`
- `dist`
- `build`
- `out`
- `.venv`

---

## 🔧 Python Bridge API

### Event Types Supported

#### Input Events (VS Code → Bridge)
1. **file_edit**: Track file modification
 ```json
 {"type": "file_edit", "file": "/path/to/file.ts", "content": "..."}
 ```

2. **terminal_output**: Track terminal command
 ```json
 {"type": "terminal_output", "command": "npm test", "output": "...", "exitCode": 1}
 ```

3. **diagnostic**: Track error/warning
 ```json
 {"type": "diagnostic", "file": "/path/to/file.ts", "severity": "Error", "message": "..."}
 ```

4. **recall_context**: Retrieve memories
 ```json
 {"type": "recall_context", "query": "", "top_k": 10}
 ```

5. **get_stats**: Get session statistics
 ```json
 {"type": "get_stats"}
 ```

6. **ping**: Health check
 ```json
 {"type": "ping"}
 ```

#### Database Query Events (v2.0 - Prepared)
7. **get_recent_activity**: Recent memories for project
8. **recall_memories**: Query memories by salience
9. **get_statistics**: Database stats
10. **get_context_for_ai**: Formatted AI context

#### Response Format
```json
{
 "status": "ok|error",
 "memory_id": "05cea478749c4996",
 "salience": "HIGH",
 "gist": "Updated test file: test_memory.py",
 "secrets_detected": false,
 "_id": "request-id-123"
}
```

---

## 📊 Validated Performance Metrics

From production testing (VALIDATION_REPORT.md):

| Metric | Before Vidurai | After Vidurai | Improvement |
|--------|----------------|---------------|-------------|
| Context gathering time | 60 seconds | 5 seconds | **90% faster** |
| Tokens per prompt | 1,247 tokens | 512 tokens | **59% reduction** |
| AI understanding | Manual context | 100% accuracy | **Perfect recall** |
| Integration score | N/A | 95.6/100 | **Production-ready** |

---

## 🏗️ Architecture Components

### TypeScript (VS Code Extension)
- `extension.ts`: Main entry point, lifecycle management
- `pythonBridge.ts`: Bridge communication layer
- `statusBar.ts`: Status bar UI component
- `installer.ts`: Python/Vidurai auto-installer
- `fileWatcher.ts`: File change monitoring
- `terminalWatcher.ts`: Terminal output capture
- `diagnosticWatcher.ts`: Error/warning tracking
- `views/memoryTreeView.ts`: Sidebar TreeView implementation
- `utils.ts`: Logging, configuration helpers

### Python (Bridge Process)
- `bridge.py`: Main bridge process, stdin/stdout handler
- `event_processor.py`: Salience classification, secrets detection
- `gist_extractor.py`: Semantic gist extraction
- `vidurai_manager.py`: Vidurai SDK wrapper, session management

### Dependencies
- **TypeScript**: VS Code API 1.80.0+, Node 18.0+
- **Python**: 3.8+, Vidurai SDK 1.6.1, detect-secrets, pyyaml

---

## 🧪 Testing Status

### Manual Testing (All Passing)
- Extension installation
- Python bridge initialization
- File edit tracking
- Terminal output tracking
- Diagnostic tracking
- Context recall
- Memory persistence
- Secrets detection
- Bridge crash recovery

### Automated Testing
- CI/CD: GitHub Actions workflow configured
- Platforms: Ubuntu, Windows, macOS
- Node versions: 18, 20
- Python versions: 3.8, 3.11
- Tests: 18/18 passing (vidurai-sdk)

---

## Active Project Integration (v2.0 Feature)

Writes active project path to `~/.vidurai/active-project.txt` for:
- MCP server integration
- Browser extensions (ChatGPT, Claude)
- Cross-tool context sharing
- Real-time workspace tracking

---

## 📝 Documentation Assets

- `README.md`: Marketplace landing page (192 lines)
- `CHANGELOG.md`: Version history (33 lines)
- `CONTRIBUTING.md`: Open source guidelines (723 lines)
- `LICENSE.txt`: MIT license
- `docs/VALIDATION_REPORT.md`: Production test results (387 lines)
- `docs/CASE_STUDY.md`: Flask debugging example (461 lines)
- `docs/MARKETPLACE_DESCRIPTION.md`: Publishing template (225 lines)
- `docs/ROADMAP.md`: Future development plans (403 lines)

---

## 🎯 Feature Completeness

### Fully Implemented
- Automatic context tracking (files, terminal, diagnostics)
- Salience-based classification
- Gist extraction
- Secrets detection
- Local session storage
- Copy context command
- Status bar indicator
- Python bridge with auto-install
- Memory TreeView
- Cross-project isolation
- Configurable settings
- Health monitoring

### 🚧 Partially Implemented (v2.0 prepared)
- Database storage (API ready, not enabled)
- Query commands (get_recent_activity, recall_memories, get_statistics)
- Active project tracking (writes to file, not consumed yet)

### Not Implemented (Roadmap)
- One-click AI context injection
- Custom salience rules UI
- Multi-IDE support
- Team sync features
- Analytics dashboard
- Browser extension integration (consuming active-project.txt)

---

## Known Limitations

1. **Status Bar Icon**: Uses default database icon (VS Code API limitation - cannot use custom PNG/SVG)
2. **Database Mode**: Disabled by default (session-only mode active)
3. **Gist Extraction**: Rule-based only (no LLM summarization)
4. **Memory Search**: Basic query matching (no semantic search)
5. **Cross-Project Recall**: Not implemented (each project isolated)

---

## 💾 File Structure

```
vidurai-vscode-extension/
├── src/ # TypeScript source
│ ├── extension.ts
│ ├── pythonBridge.ts
│ ├── statusBar.ts
│ ├── fileWatcher.ts
│ ├── terminalWatcher.ts
│ ├── diagnosticWatcher.ts
│ ├── installer.ts
│ ├── utils.ts
│ └── views/
│ └── memoryTreeView.ts
├── python-bridge/ # Python bridge
│ ├── bridge.py
│ ├── event_processor.py
│ ├── gist_extractor.py
│ ├── vidurai_manager.py
│ └── .venv/ # Auto-created virtualenv
├── assets/ # Icons
│ ├── icon.png # Extension icon (128x128)
│ └── icon.svg # 3 Kosha design
├── docs/ # Documentation
│ ├── VALIDATION_REPORT.md
│ ├── CASE_STUDY.md
│ ├── MARKETPLACE_DESCRIPTION.md
│ └── ROADMAP.md
├── .github/ # GitHub templates
│ ├── workflows/test.yml
│ ├── ISSUE_TEMPLATE/
│ └── pull_request_template.md
├── package.json # Extension manifest
├── README.md # Marketplace README
├── CHANGELOG.md # Version history
├── CONTRIBUTING.md # Contribution guide
└── LICENSE.txt # MIT license
```

---

## Package Information

- **Name**: vidurai
- **Display Name**: Vidurai Memory Manager
- **Version**: 0.1.1
- **Publisher**: vidurai
- **Repository**: https://github.com/chandantochandan/vidurai-vscode-extension
- **License**: MIT
- **Category**: Other
- **Keywords**: ai, memory, claude, chatgpt, copilot, context, token-optimization, productivity, vidurai

---

## 🎓 Philosophical Foundation

**विस्मृति भी विद्या है** — *"Forgetting too is knowledge"*

Based on:
- **Fuzzy-Trace Theory**: Gist vs. verbatim memory
- **Vedantic Three-Kosha Architecture**: Body → Mind → Spirit mapping
- **Passive Decay**: Natural forgetting over time
- **Active Unlearning**: Intentional context compression

---

## 🚦 Next Steps for Planning

Based on ROADMAP.md, potential next versions:

**v0.2.0 (Q1 2025)**: Enhanced UX
- Custom salience rules UI
- One-click AI injection
- Memory search & filtering

**v1.0.0 (Q2 2025)**: Production Stable
- LLM-based gist extraction
- Multi-workspace support
- Performance optimizations

**v2.0.0 (Q3 2025)**: Multi-IDE
- JetBrains plugin
- Sublime Text plugin
- Universal CLI tool

---

**End of Current Features Document**
