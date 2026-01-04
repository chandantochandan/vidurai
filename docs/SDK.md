# 🧠 Vidurai Core SDK Documentation

> **विस्मृति भी विद्या है** — "Forgetting too is knowledge"

[![PyPI](https://img.shields.io/pypi/v/vidurai)](https://pypi.org/project/vidurai/)
[![License](https://img.shields.io/pypi/l/vidurai)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**Vidurai** (v2.2.0) is a sophisticated **Local-First AI Memory Infrastructure** that provides persistent context to AI tools without cloud dependencies. It acts as an intelligent memory layer between your development environment and AI assistants.

## 🎯 Core Philosophy

- **Local-First**: All data stays on your machine (`~/.vidurai/`)
- **Zero-Trust**: No cloud sync, no external dependencies for core functionality
- **Intelligent Forgetting**: SF-V2 smart compression with audit trails
- **Vedantic Approach**: Forgetting as a form of knowledge refinement

---

## 🚀 Quick Start

### Installation
```bash
# Recommended: Use pipx for isolation
pipx install vidurai

# Alternative: Direct pip install
pip install vidurai
```

### Basic Usage
```bash
# Start the memory system
vidurai start

# Check status
vidurai status

# Search your memories
vidurai recall --query "authentication bug"

# Get AI-ready context
vidurai context --query "login flow"

# View recent activity
vidurai recent --hours 24
```

---

## 🎛️ Command Reference

Vidurai provides **25 powerful commands** organized into logical groups:

### 🔧 System Management
| Command | Description |
|---------|-------------|
| `vidurai start` | Start the Vidurai Guardian daemon |
| `vidurai stop` | Stop the Guardian daemon |
| `vidurai status` | Show daemon status and health |
| `vidurai logs` | View or follow daemon logs (`-f` to follow) |
| `vidurai info` | Show installation and system information |

### 🧠 Memory Operations
| Command | Description |
|---------|-------------|
| `vidurai recall` | Search and recall memories from your project |
| `vidurai context` | Get formatted context for AI tools |
| `vidurai recent` | Show recent development activity |
| `vidurai stats` | Display memory statistics for a project |
| `vidurai hints` | Get proactive development hints |

### 📌 Memory Management (SF-V2)
| Command | Description |
|---------|-------------|
| `vidurai pin <id>` | Pin a memory to prevent forgetting |
| `vidurai unpin <id>` | Unpin a memory to allow forgetting |
| `vidurai pins` | List all pinned memories |
| `vidurai hygiene` | Review and archive low-utility memories |

### 🔍 Forgetting System Transparency
| Command | Description |
|---------|-------------|
| `vidurai forgetting-log` | Show forgetting event audit trail |
| `vidurai forgetting-stats` | Display forgetting statistics |

### 📊 Data Operations
| Command | Description |
|---------|-------------|
| `vidurai export` | Export memories to JSON/text/SQL |
| `vidurai ingest` | Import historical AI conversations |
| `vidurai get-context-json` | Get context as JSON (for piping) |
| `vidurai clear` | Clear all memories for a project |

### 🔌 Integration & Services
| Command | Description |
|---------|-------------|
| `vidurai server` | Start MCP server for AI tool integration |
| `vidurai mcp-install` | Install as MCP server for Claude Desktop |

### 🛠️ Development Tools
| Command | Description |
|---------|-------------|
| `vidurai chat` | Start interactive REPL session |
| `vidurai audit` | Audit code for security risks |
| `vidurai fix` | Safe code modification in shadow workspace |

---

## 🏗️ Architecture Overview

### Core Components
```
Vidurai Core SDK (31,442 lines)
├── CLI Interface (1,621 lines)     # 25 commands
├── Memory Engine (1,273 lines)     # VismritiMemory class
├── MCP Server (555 lines)          # Model Context Protocol
├── Interactive REPL (470 lines)    # Chat interface
├── SF-V2 Engine (18,884 lines)     # Smart Forgetting v2
├── Daemon Service (8 modules)      # Background intelligence
├── Storage Layer (780 lines)       # SQLite + Parquet
└── Integrations                    # LangChain, Jupyter, etc.
```

### SF-V2 Smart Forgetting Engine
The heart of Vidurai's intelligence:

```
Memory Lifecycle:
Input → Salience Classification → Entity Extraction → Role Classification
  ↓
Retention Scoring → Pinning Check → Consolidation → Archival
  ↓
Forgetting Ledger (Audit Trail) → Cold Storage (Parquet)
```

**Key Features:**
- **5-Level Salience**: CRITICAL → HIGH → MEDIUM → LOW → NOISE
- **15+ Entity Types**: Functions, classes, bugs, features, etc.
- **Memory Roles**: RESOLUTION, CAUSE, CONTEXT, EXPLORATION
- **Retention Scoring**: Multi-factor algorithm (0-200 range)
- **User Control**: Pin important memories, audit all changes
- **Transparency**: Complete forgetting audit trail

---

## 💾 Storage Architecture

### Data Hierarchy
```
~/.vidurai/
├── vidurai.db              # SQLite (Hot storage, WAL mode)
├── forgetting_ledger.jsonl # Audit trail (append-only)
├── daemon.pid             # Process management
├── vidurai.log           # Daemon logs (rotated)
└── archive/              # Cold storage
    └── YYYY/MM/          # Date-partitioned Parquet files
```

### Privacy & Security
- **Local-First**: All data stays on your machine
- **Zero Cloud Sync**: No external dependencies
- **PII Protection**: Automatic sanitization
- **ACID Compliance**: SQLite WAL mode for data integrity
- **Audit Trail**: Complete transparency in memory operations

---

## 🔌 Integration Examples

### Claude Desktop (MCP)
```bash
# Auto-install for Claude Desktop
vidurai mcp-install

# Manual configuration
# Add to ~/.config/claude/claude_desktop_config.json:
{
  "mcpServers": {
    "vidurai": {
      "command": "vidurai",
      "args": ["server"]
    }
  }
}
```

### VS Code Extension
Install the **Vidurai Memory Manager** extension from the marketplace for real-time telemetry capture.

### Python API
```python
from vidurai import VismritiMemory

# Initialize memory system
memory = VismritiMemory(project_path="/path/to/project")

# Store a memory
memory.store_memory(
    content="Fixed authentication bug in login.py",
    salience="HIGH",
    file_path="src/auth/login.py"
)

# Recall memories
memories = memory.recall_memories(
    query="authentication bug",
    limit=10
)

# Get AI-ready context
context = memory.get_context_for_ai(
    query="login flow",
    max_tokens=2000
)
```

### LangChain Integration
```python
from vidurai.integrations.langchain import ViduraiMemory
from langchain.chains import ConversationChain

# Create memory-enhanced chain
memory = ViduraiMemory(project_path="/path/to/project")
chain = ConversationChain(memory=memory)

# Conversations automatically stored and recalled
response = chain.predict(input="How does authentication work?")
```

---

## 🎯 Advanced Features

### Memory Pinning
```bash
# Pin critical memories
vidurai pin 123 --reason "Critical bug fix pattern"

# View pinned memories
vidurai pins --show-content

# Unpin when no longer needed
vidurai unpin 123
```

### Proactive Hints
```bash
# Get development hints based on history
vidurai hints --max-hints 5

# Filter by confidence level
vidurai hints --min-confidence 0.8

# Show detailed context
vidurai hints --show-context
```

### Memory Hygiene
```bash
# Review low-utility memories
vidurai hygiene

# Force cleanup without prompts
vidurai hygiene --force

# Check forgetting statistics
vidurai forgetting-stats --days 30
```

### Historical Data Import
```bash
# Import ChatGPT conversations
vidurai ingest conversations.json --type openai

# Import Claude conversations
vidurai ingest claude_export.json --type anthropic

# Preview before importing
vidurai ingest data.json --preview
```

---

## 🔧 Configuration

### Environment Variables
```bash
export VIDURAI_HOME="~/.vidurai"          # Data directory
export VIDURAI_LOG_LEVEL="INFO"           # Logging level
export VIDURAI_MAX_MEMORIES="10000"       # Memory limit per project
export VIDURAI_RETENTION_DAYS="365"       # Default retention period
```

### Configuration Files
```bash
# Daemon configuration
~/.vidurai/daemon.conf

# MCP server settings
~/.vidurai/mcp_config.json

# Retention policies
~/.vidurai/retention_policies.json
```

---

## 📊 Performance & Limits

### Performance Characteristics
- **CLI Startup**: < 0.5s (lazy loading architecture)
- **Memory Footprint**: ~50MB for daemon + extensions
- **Context Retrieval**: Sub-second for most queries
- **Storage Efficiency**: SQLite + Parquet compression

### Scalability Limits
- **Memories per Project**: 100,000+ (tested)
- **Projects**: Unlimited
- **Memory Pins**: 50 per project (user-controlled)
- **File Size**: Handles repositories up to 10GB+

---

## 🐛 Troubleshooting

### Common Issues

**Daemon won't start:**
```bash
# Check status and logs
vidurai status
vidurai logs -n 50

# Clean restart
vidurai stop
rm ~/.vidurai/daemon.pid
vidurai start
```

**Memory not being captured:**
```bash
# Verify daemon is running
vidurai status

# Check recent activity
vidurai recent --hours 1

# Restart with verbose logging
VIDURAI_LOG_LEVEL=DEBUG vidurai start
```

**Context too large:**
```bash
# Reduce context size
vidurai context --max-tokens 1000

# Run memory hygiene
vidurai hygiene

# Check memory statistics
vidurai stats
```

### Debug Commands
```bash
# System information
vidurai info

# Memory statistics
vidurai stats --project .

# Audit trail
vidurai forgetting-log --limit 20

# Interactive debugging
vidurai chat
```

---

## 🤝 Contributing

### Development Setup
```bash
# Clone repository
git clone https://github.com/your-org/vidurai.git
cd vidurai

# Install in development mode
pip install -e .

# Run tests
python -m pytest tests/

# Verify installation
vidurai --version
```

### Code Structure
- `vidurai/cli.py` - Command-line interface
- `vidurai/vismriti_memory.py` - Main memory engine
- `vidurai/core/` - SF-V2 smart forgetting engine
- `vidurai/daemon/` - Background service
- `tests/` - Comprehensive test suite

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

**Vidurai** draws inspiration from Vedantic philosophy, where forgetting is seen as a form of knowledge. The system embodies this principle through intelligent memory management that preserves what matters while gracefully letting go of the rest.

> *विस्मृति भी विद्या है* — "Forgetting too is knowledge"

---

*For more information, visit our [documentation](docs/) or join our community discussions.*
