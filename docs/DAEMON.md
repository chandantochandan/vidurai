# 👻 Vidurai Daemon Service Documentation

> **The Invisible Infrastructure Layer** — Background intelligence for AI-assisted development

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![WebSocket](https://img.shields.io/badge/WebSocket-supported-orange.svg)](https://websockets.readthedocs.io/)

The **Vidurai Daemon** is a background service that runs invisibly on your system, providing universal context intelligence to all AI tools and development environments. It acts as the central nervous system of the Vidurai memory infrastructure.

## 🎯 Core Purpose

The daemon serves as the **invisible infrastructure layer** that:
- Monitors development activity across all tools
- Provides real-time context to AI assistants
- Manages memory consolidation and archival
- Bridges between extensions and the core SDK
- Ensures data consistency and availability

---

## 🏗️ Architecture Overview

### Service Architecture
```
Vidurai Daemon (9,859 lines)
├── 👻 Core Server (79,885 lines)
│   ├── FastAPI Application              # HTTP/WebSocket endpoints
│   ├── IPC Server                       # Extension communication
│   ├── Auto-Detection                   # AI platform discovery
│   └── Metrics Collection               # Performance monitoring
├── 🧠 Intelligence Layer
│   ├── Context Mediator                 # AI platform bridging
│   ├── Memory Bridge                    # SDK integration
│   ├── Human-AI Whisperer              # Interaction optimization
│   └── State Projector                 # Context state management
├── 📊 Project Brain
│   ├── Scanner                         # Code analysis
│   ├── Context Builder                 # Context assembly
│   ├── Error Watcher                   # Error monitoring
│   └── Memory Store                    # In-memory cache
├── 🗄️ Data Management
│   ├── Archiver                        # SQLite → Parquet migration
│   ├── Stabilizer                      # Data consistency
│   └── Smart File Watcher             # Intelligent file monitoring
└── 🔌 Communication
    ├── IPC Server                      # Named pipes/sockets
    ├── MCP Bridge                      # Model Context Protocol
    └── WebSocket Manager               # Real-time connections
```

### Data Flow
```
Development Tools → Extensions → IPC → Daemon → Core SDK → Storage
                                   ↓
                            WebSocket/HTTP API
                                   ↓
                            AI Tools & Clients
```

---

## 🚀 Quick Start

### Starting the Daemon
```bash
# Start daemon (recommended)
vidurai start

# Start with custom configuration
vidurai start --port 7777 --log-level DEBUG

# Check daemon status
vidurai status

# View daemon logs
vidurai logs -f
```

### Manual Daemon Control
```bash
# Start daemon directly
python -m vidurai.daemon

# Start with environment variables
VIDURAI_PORT=8888 python -m vidurai.daemon

# Background process (Linux/Mac)
nohup python -m vidurai.daemon &
```

---

## 🔌 API Endpoints

### HTTP Endpoints

#### Core Context API
```http
POST /smart-context
Content-Type: application/json

{
  "project_path": "/path/to/project",
  "query": "authentication bug",
  "max_tokens": 2000,
  "audience": "developer"
}

Response:
{
  "context": "Formatted context for AI...",
  "memories_count": 15,
  "token_count": 1847,
  "salience_breakdown": {
    "CRITICAL": 2,
    "HIGH": 5,
    "MEDIUM": 8
  }
}
```

#### Error Reporting
```http
POST /report-error
Content-Type: application/json

{
  "project_path": "/path/to/project",
  "error_message": "TypeError: Cannot read property 'id' of undefined",
  "file_path": "src/components/UserProfile.tsx",
  "line_number": 42,
  "stack_trace": "...",
  "context": "User was editing authentication flow"
}

Response:
{
  "memory_id": 12345,
  "salience": "HIGH",
  "related_memories": [12340, 12341],
  "suggestions": ["Check null safety", "Validate user object"]
}
```

#### Project Management
```http
POST /watch/{project_path}
# Start watching a project for changes

DELETE /unwatch/{project_path}
# Stop watching a project

GET /metrics
# Get daemon performance metrics
```

### WebSocket Endpoints

#### Real-time Context Stream
```javascript
// Connect to daemon WebSocket
const ws = new WebSocket('ws://localhost:7777/ws');

// Subscribe to project events
ws.send(JSON.stringify({
  type: 'subscribe',
  project_path: '/path/to/project',
  events: ['memory_created', 'error_detected', 'context_updated']
}));

// Receive real-time updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Memory event:', data);
};
```

#### Event Types
```json
{
  "type": "memory_created",
  "memory_id": 12345,
  "salience": "HIGH",
  "gist": "Fixed authentication bug in login flow",
  "timestamp": "2025-12-22T00:30:00Z"
}

{
  "type": "error_detected",
  "file_path": "src/auth.py",
  "error_type": "TypeError",
  "severity": "HIGH",
  "suggestions": ["Check null safety"]
}

{
  "type": "context_updated",
  "project_path": "/path/to/project",
  "memories_count": 1247,
  "recent_activity": "User fixed authentication bug"
}
```

---

## 🧠 Intelligence Subsystems

### Context Mediator
**Purpose**: Bridges between AI platforms and project context
**Location**: `vidurai/daemon/intelligence/context_mediator.py`

```python
# Example usage
from vidurai.daemon.intelligence.context_mediator import ContextMediator

mediator = ContextMediator()

# Get context for specific AI platform
context = await mediator.get_context_for_platform(
    platform="claude",
    project_path="/path/to/project",
    query="recent bug fixes",
    format="mcp"  # or "openai", "anthropic"
)
```

### Memory Bridge
**Purpose**: Integrates with core SDK memory operations
**Location**: `vidurai/daemon/intelligence/memory_bridge.py`

```python
# Bridge between daemon and SDK
from vidurai.daemon.intelligence.memory_bridge import MemoryBridge

bridge = MemoryBridge()

# Store memory through daemon
memory_id = await bridge.store_memory(
    content="Fixed authentication timeout issue",
    project_path="/path/to/project",
    salience="HIGH",
    metadata={"file": "auth.py", "line": 42}
)

# Retrieve memories
memories = await bridge.recall_memories(
    project_path="/path/to/project",
    query="authentication",
    limit=10
)
```

### Human-AI Whisperer
**Purpose**: Optimizes human-AI interactions
**Location**: `vidurai/daemon/intelligence/human_ai_whisperer.py`

Features:
- **Context Optimization**: Formats context for maximum AI understanding
- **Token Efficiency**: Reduces token usage while preserving meaning
- **Interaction Patterns**: Learns from successful AI conversations
- **Prompt Enhancement**: Automatically improves prompt quality

---

## 📊 Project Brain System

### Scanner
**Purpose**: Analyzes project structure and code patterns
**Location**: `vidurai/daemon/project_brain/scanner.py`

```python
# Project analysis
from vidurai.daemon.project_brain.scanner import ProjectScanner

scanner = ProjectScanner("/path/to/project")

# Scan project structure
structure = await scanner.analyze_structure()
# Returns: file types, dependencies, architecture patterns

# Identify key files
key_files = await scanner.identify_key_files()
# Returns: entry points, configuration files, critical modules
```

### Context Builder
**Purpose**: Assembles relevant context from project analysis
**Location**: `vidurai/daemon/project_brain/context_builder.py`

```python
# Context assembly
from vidurai.daemon.project_brain.context_builder import ContextBuilder

builder = ContextBuilder("/path/to/project")

# Build context for specific query
context = await builder.build_context(
    query="authentication flow",
    include_files=True,
    include_dependencies=True,
    max_tokens=2000
)
```

### Error Watcher
**Purpose**: Monitors and analyzes development errors
**Location**: `vidurai/daemon/project_brain/error_watcher.py`

Features:
- **Error Pattern Recognition**: Identifies recurring error patterns
- **Solution Tracking**: Links errors to their resolutions
- **Proactive Warnings**: Predicts potential issues
- **Learning System**: Improves suggestions over time

---

## 🗄️ Data Management

### Archiver
**Purpose**: Manages SQLite to Parquet migration for cold storage
**Location**: `vidurai/daemon/archiver/archiver.py`

```python
# Archive old memories
from vidurai.daemon.archiver.archiver import MemoryArchiver

archiver = MemoryArchiver()

# Archive memories older than 90 days
archived_count = await archiver.archive_old_memories(
    days_old=90,
    min_salience="LOW"
)

# Restore archived memories
restored = await archiver.restore_memories(
    date_range=("2025-01-01", "2025-01-31"),
    project_path="/path/to/project"
)
```

### Stabilizer
**Purpose**: Ensures data consistency and integrity
**Location**: `vidurai/daemon/stabilizer/stabilizer.py`

Features:
- **Data Validation**: Ensures memory schema compliance
- **Consistency Checks**: Validates relationships between memories
- **Corruption Recovery**: Repairs damaged data structures
- **Performance Optimization**: Maintains database performance

### Smart File Watcher
**Purpose**: Intelligent file system monitoring
**Location**: `vidurai/daemon/smart_file_watcher.py`

```python
# File watching with intelligence
from vidurai.daemon.smart_file_watcher import SmartFileWatcher

watcher = SmartFileWatcher()

# Watch project with filters
await watcher.watch_project(
    project_path="/path/to/project",
    include_patterns=["*.py", "*.js", "*.ts"],
    exclude_patterns=["node_modules/**", "*.pyc"],
    debounce_ms=500
)

# Get file change events
async for event in watcher.get_events():
    print(f"File changed: {event.file_path}")
    print(f"Change type: {event.change_type}")
    print(f"Content diff: {event.diff}")
```

---

## 🔧 Configuration

### Environment Variables
```bash
# Daemon configuration
export VIDURAI_DAEMON_PORT=7777          # HTTP/WebSocket port
export VIDURAI_DAEMON_HOST="localhost"   # Bind address
export VIDURAI_LOG_LEVEL="INFO"          # Logging level
export VIDURAI_MAX_CONNECTIONS=100       # Max WebSocket connections
export VIDURAI_ENABLE_CORS=true          # Enable CORS for web clients

# Storage configuration
export VIDURAI_HOME="~/.vidurai"         # Data directory
export VIDURAI_DB_PATH="~/.vidurai/vidurai.db"  # Database path
export VIDURAI_LOG_PATH="~/.vidurai/daemon.log" # Log file path

# Performance tuning
export VIDURAI_WORKER_THREADS=4          # Background worker threads
export VIDURAI_MEMORY_LIMIT="512MB"      # Memory usage limit
export VIDURAI_CACHE_SIZE=1000           # In-memory cache size
```

### Configuration File
```yaml
# ~/.vidurai/daemon.yaml
daemon:
  port: 7777
  host: "localhost"
  log_level: "INFO"
  enable_cors: true
  max_connections: 100

storage:
  database_path: "~/.vidurai/vidurai.db"
  archive_path: "~/.vidurai/archive"
  log_path: "~/.vidurai/daemon.log"
  max_log_size: "50MB"
  log_rotation_count: 5

intelligence:
  context_cache_size: 1000
  max_context_tokens: 4000
  enable_proactive_hints: true
  learning_rate: 0.01

project_brain:
  scan_interval: 300  # seconds
  max_file_size: "10MB"
  exclude_patterns:
    - "node_modules/**"
    - "*.pyc"
    - ".git/**"
    - "dist/**"

performance:
  worker_threads: 4
  memory_limit: "512MB"
  gc_interval: 3600  # seconds
  metrics_retention: 7  # days
```

---

## 📊 Monitoring & Metrics

### Health Endpoints
```http
GET /health
# Basic health check

GET /metrics
# Prometheus-compatible metrics

GET /status
# Detailed daemon status
```

### Performance Metrics
```json
{
  "daemon": {
    "uptime": 86400,
    "memory_usage": "245MB",
    "cpu_usage": "2.3%",
    "active_connections": 15
  },
  "storage": {
    "database_size": "1.2GB",
    "total_memories": 15420,
    "archived_memories": 8930,
    "cache_hit_rate": 0.87
  },
  "intelligence": {
    "contexts_served": 1247,
    "avg_response_time": "120ms",
    "cache_efficiency": 0.92,
    "learning_accuracy": 0.89
  },
  "project_brain": {
    "projects_watched": 5,
    "files_monitored": 2847,
    "errors_detected": 23,
    "patterns_learned": 156
  }
}
```

### Logging
```python
# Structured logging with correlation IDs
import logging
# from vidurai.daemon.utils (removed) import get_correlation_id

logger = logging.getLogger("vidurai.daemon")

# Log with correlation ID
correlation_id = get_correlation_id()
logger.info(
    "Context request processed",
    extra={
        "correlation_id": correlation_id,
        "project_path": "/path/to/project",
        "memories_count": 15,
        "response_time_ms": 120
    }
)
```

---

## 🔒 Security & Privacy

### Security Features
- **Local-Only Operation**: No external network dependencies
- **Process Isolation**: Runs as user process, not system service
- **Data Encryption**: Optional encryption for sensitive projects
- **Access Control**: Project-based access restrictions
- **Audit Logging**: Complete operation audit trail

### Privacy Protection
- **PII Sanitization**: Automatic removal of sensitive data
- **Local Storage**: All data stays on user's machine
- **No Telemetry**: No usage data sent to external servers
- **User Control**: Complete control over data retention

### Configuration
```yaml
# Security configuration
security:
  enable_encryption: false
  encryption_key_path: "~/.vidurai/keys/daemon.key"
  max_session_duration: 3600  # seconds
  enable_audit_log: true
  audit_log_path: "~/.vidurai/audit.log"

privacy:
  enable_pii_protection: true
  pii_patterns:
    - "email"
    - "phone"
    - "ssn"
    - "credit_card"
  data_retention_days: 365
  auto_cleanup_enabled: true
```

---

## 🐛 Troubleshooting

### Common Issues

**Daemon won't start:**
```bash
# Check port availability
netstat -an | grep 7777

# Check logs for errors
vidurai logs -n 50

# Start with debug logging
VIDURAI_LOG_LEVEL=DEBUG vidurai start
```

**High memory usage:**
```bash
# Check daemon metrics
curl http://localhost:7777/metrics

# Reduce cache size
export VIDURAI_CACHE_SIZE=500

# Run garbage collection
curl -X POST http://localhost:7777/admin/gc
```

**WebSocket connection issues:**
```bash
# Test WebSocket connection
wscat -c ws://localhost:7777/ws

# Check firewall settings
sudo ufw status

# Verify CORS settings
curl -H "Origin: http://localhost:3000" http://localhost:7777/health
```

**IPC communication failures:**
```bash
# Check IPC socket/pipe
ls -la ~/.vidurai/daemon.sock  # Linux/Mac
dir \\.\pipe\vidurai-daemon    # Windows

# Test IPC connection
python -c "
# from vidurai.daemon.ipc.client (see daemon.ipc.server) import IPCClient
client = IPCClient()
print(client.ping())
"
```

### Debug Commands
```bash
# Daemon diagnostics
curl http://localhost:7777/debug/info

# Memory diagnostics
curl http://localhost:7777/debug/memory

# Performance diagnostics
curl http://localhost:7777/debug/performance

# Connection diagnostics
curl http://localhost:7777/debug/connections
```

---

## 🚀 Performance Optimization

### Tuning Parameters
```bash
# Increase worker threads for high-load scenarios
export VIDURAI_WORKER_THREADS=8

# Optimize cache size based on available memory
export VIDURAI_CACHE_SIZE=2000

# Adjust database connection pool
export VIDURAI_DB_POOL_SIZE=20

# Enable performance monitoring
export VIDURAI_ENABLE_METRICS=true
```

### Scaling Considerations
- **Memory Usage**: ~50MB base + ~100KB per active project
- **CPU Usage**: < 5% during normal operation
- **Disk I/O**: Optimized with SQLite WAL mode
- **Network**: WebSocket connections are lightweight
- **Concurrency**: Handles 100+ concurrent connections

---

## 🤝 Development

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-org/vidurai.git
cd vidurai

# Install in development mode
pip install -e .

# Start daemon in development mode
python -m vidurai.daemon --dev

# Run daemon tests
python -m pytest vidurai/daemon/tests/
```

### Adding New Endpoints
```python
# vidurai/daemon/server.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/my-endpoint")
async def my_endpoint(request: MyRequest):
    """Custom endpoint implementation"""
    return {"status": "success"}

# Register router
app.include_router(router, prefix="/api/v1")
```

### Custom Intelligence Modules
```python
# vidurai/daemon/intelligence/my_module.py
# from vidurai.daemon.intelligence.base (removed) import IntelligenceModule

class MyIntelligenceModule(IntelligenceModule):
    async def process(self, context: dict) -> dict:
        """Custom intelligence processing"""
        return enhanced_context

# Register module
from vidurai.daemon.intelligence import register_module
register_module("my_module", MyIntelligenceModule)
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

The Vidurai Daemon embodies the principle of invisible infrastructure - working silently in the background to enhance your development experience without getting in your way.

**Special thanks to:**
- FastAPI team for the excellent async framework
- WebSocket protocol contributors
- The Python asyncio community
- Beta testers who helped refine the daemon

---

*The daemon runs silently, remembers everything, and forgets wisely - just like the best assistants should.*
