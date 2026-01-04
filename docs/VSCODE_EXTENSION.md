# 🧠 Vidurai Memory Manager for VS Code

> **विस्मृति भी विद्या है** — "Forgetting too is knowledge"

[![VS Code](https://img.shields.io/badge/VS%20Code-1.80+-blue.svg)](https://code.visualstudio.com/)
[![Version](https://img.shields.io/badge/version-2.2.0-green.svg)](https://marketplace.visualstudio.com/items?itemName=vidurai.vidurai)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

**Telemetry agent for VS Code.** Captures low-latency file and terminal events for the Vidurai Daemon. Automatically tracks your coding context—files, commands, errors—and makes it instantly available for **any AI assistant**: Claude, ChatGPT, GitHub Copilot, Cursor, and more.

## 🎯 Current Status: Production Ready (v2.2.0)

The extension is a **production-ready telemetry agent** that:
- Captures real-time development events
- Communicates with Vidurai Daemon via IPC
- Provides context dashboard and memory tree view
- Offers 16 commands for memory management
- Supports file pinning and context generation

### ✅ What Works Now
- **Real-time telemetry capture** - Files, terminal, diagnostics
- **IPC communication** - Direct daemon connection (no Python bridge dependency)
- **Context dashboard** - WebView-based context visualization
- **Memory tree view** - Browse and manage captured memories
- **File pinning** - Pin important files to context
- **Multiple context formats** - XML, Manager Summary, Standup Reports
- **Zero-config setup** - Auto-detects Python and installs SDK

---

## 🏗️ Architecture Overview

### Extension Components (7,821 lines TypeScript)
```
Vidurai VS Code Extension (v2.2.0)
├── 📁 Core Extension
│   └── extension.ts (35,189 lines)       # Main entry point with IPC client
├── 📁 Telemetry Watchers
│   ├── fileWatcher.ts (6,194 lines)      # File change monitoring
│   ├── terminalWatcher.ts (9,671 lines)  # Command & output tracking
│   ├── diagnosticWatcher.ts (4,484)      # Error/warning capture
│   └── focusWatcher.ts (7,015 lines)     # User focus tracking
├── 📁 Communication Layer
│   └── ipc/Client.ts                     # Direct daemon IPC (no Python bridge)
├── 📁 User Interface
│   ├── views/ContextPanel.ts             # WebView context dashboard
│   ├── views/memoryTreeView.ts           # Memory browser tree
│   ├── statusBar.ts (6,792 lines)       # Status indicator
│   └── decorators/PinDecorator.ts        # File pinning UI
├── 📁 Intelligence & Security
│   ├── filter/EdgeFilter.ts              # Noise reduction
│   └── security/Gatekeeper.ts            # PII protection
└── 📁 Python Bridge (Legacy Support)
    ├── bridge.py (14,695 lines)         # Python SDK integration
    ├── vidurai_manager.py (6,939 lines) # Memory management
    └── event_processor.py (6,548 lines) # Event handling
```

### Data Flow (v2.2.0)
```
VS Code Events → Watchers → Edge Filter → Gatekeeper → IPC Client → Daemon
                                                                      ↓
                                                               Core SDK Storage
                                                                      ↓
                                                          Context Dashboard ← User
                                                          Memory Tree View ← User
```

---

## 🎯 Commands & Usage

### 16 Extension Commands (v2.2.0)

#### Core Context Commands
| Command | Description | Shortcut |
|---------|-------------|----------|
| `Vidurai: Copy Relevant Context` | Copy AI-ready context to clipboard | - |
| `Vidurai: Show Project Status` | Display project memory status | - |
| `Vidurai: Copy AI Context (XML)` | Copy context in XML format | - |
| `Vidurai: Copy Manager Summary` | Copy manager-level summary | - |
| `Vidurai: Generate AI Context XML` | Generate structured XML context | - |

#### Memory Management
| Command | Description | Icon |
|---------|-------------|------|
| `Vidurai: Refresh Memories` | Refresh memory tree view | 🔄 |
| `Vidurai: Show Memory Details` | View detailed memory information | - |
| `Vidurai: Copy to Clipboard` | Copy memory to clipboard | 📋 |

#### File Operations
| Command | Description | Icon |
|---------|-------------|------|
| `Vidurai: Pin to Context` | Pin file to prevent forgetting | 📌 |
| `Vidurai: Unpin` | Unpin file from context | 📍 |

#### Reports & Analytics
| Command | Description | Icon |
|---------|-------------|------|
| `Vidurai: Generate Standup Report` | Create daily standup summary | ✅ |
| `Vidurai: Generate Manager Report` | Create manager-level report | 📊 |
| `Vidurai: Switch Memory Profile` | Switch between memory profiles | 🧠 |

#### System Management
| Command | Description | Icon |
|---------|-------------|------|
| `Vidurai: Restart Python Bridge` | Restart Python bridge connection | 🔄 |
| `Vidurai: Show Logs` | View extension logs | 📝 |
| `Vidurai: Refresh Context Dashboard` | Refresh WebView dashboard | 🔄 |

### Usage Examples
```bash
# Start daemon first
vidurai start

# In VS Code:
# 1. Ctrl+Shift+P → "Vidurai: Copy AI Context (XML)"
# 2. Paste into Claude/ChatGPT
# 3. Get enhanced AI responses with full project context
```

---

## 🔧 Configuration

### Extension Settings (v2.2.0)
```json
{
  "vidurai.enabled": true,                    // Enable/disable context tracking
  "vidurai.debounceMs": 2000,                // File edit debounce (500-10000ms)
  "vidurai.pythonPath": "",                  // Python executable path (auto-detected)
  "vidurai.logLevel": "info",                // Logging: debug|info|warn|error
  "vidurai.maxFileSize": 51200,              // Max file size to track (bytes)
  "vidurai.trackTerminal": true,             // Track terminal commands
  "vidurai.trackDiagnostics": true,          // Track errors and warnings
  "vidurai.ignoredPaths": [                  // Paths to ignore
    "node_modules",
    ".git", 
    "dist",
    "build",
    "out",
    ".venv"
  ]
}
```

### Activity Bar Integration
The extension adds a **Vidurai Memory** activity bar with:
- **Context Dashboard** (WebView) - Visual context overview
- **Project Memory** (Tree View) - Browse captured memories

### Menu Integration
- **Explorer Context Menu**: Pin/Unpin files
- **Editor Title**: Pin current file
- **Memory Tree**: Copy memory context

---

## 🚀 Quick Start

### 1. Prerequisites
- **VS Code**: 1.80.0 or higher
- **Python**: 3.8+ (auto-detected by extension)
- **Vidurai SDK**: Auto-installed by extension

### 2. Installation
```bash
# From VS Code Marketplace
ext install vidurai.vidurai

# Or from command line
code --install-extension vidurai.vidurai
```

### 3. Setup Process
1. **Install Extension** - From VS Code Marketplace
2. **Reload VS Code** - Extension activates on startup
3. **Auto-Setup** - Extension detects Python and installs SDK
4. **Start Daemon** - Run `vidurai start` in terminal
5. **Open Project** - Extension begins capturing context

### 4. First Use
1. Open any project in VS Code
2. Make some file edits, run terminal commands
3. Press `Ctrl+Shift+P` → "Vidurai: Copy AI Context (XML)"
4. Paste into Claude/ChatGPT for enhanced AI assistance

---

## 🎨 User Interface

### Activity Bar Integration
The extension adds a **Vidurai Memory** section to the activity bar with two views:

#### Context Dashboard (WebView)
- **Visual Overview**: Project memory statistics
- **Recent Activity**: Latest captured events
- **Memory Health**: Storage and performance metrics
- **Quick Actions**: Copy context, generate reports

#### Project Memory (Tree View)
- **Memory Browser**: Hierarchical view of captured memories
- **Search & Filter**: Find specific memories
- **Memory Details**: View full context and metadata
- **Actions**: Copy, pin, or delete memories

### Status Bar Integration
- **🧠 Active**: Memory system capturing context
- **⚠️ Warning**: Connection issues or errors  
- **❌ Inactive**: Daemon not running or extension disabled

### Context Menus
- **Explorer**: Right-click files to pin/unpin
- **Editor**: Pin button in editor title bar
- **Memory Tree**: Copy memory context to clipboard

---

## 🔌 AI Tool Integrations

### Claude Desktop (Native MCP)
```bash
# Auto-install MCP integration
vidurai mcp-install

# Manual configuration in ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "vidurai": {
      "command": "vidurai",
      "args": ["server"]
    }
  }
}
```

### ChatGPT Integration
1. Use `Ctrl+Shift+V` to copy context
2. Paste into ChatGPT conversation
3. Context automatically formatted for optimal understanding

### GitHub Copilot Enhancement
The extension enhances Copilot suggestions by providing:
- Project-specific patterns and conventions
- Recent bug fixes and solutions
- Code style preferences
- Domain-specific knowledge

### Cursor Integration
1. Copy context using extension command
2. Paste into Cursor chat
3. Enhanced suggestions based on project memory

---

## 🛠️ Development & Debugging

### Extension Development
```bash
# Clone repository
git clone https://github.com/your-org/vidurai-vscode-extension.git
cd vidurai-vscode-extension

# Install dependencies
npm install

# Build extension
npm run compile

# Run in development mode
F5 (opens Extension Development Host)
```

### Python Bridge Development
```bash
# Navigate to Python bridge
cd python-bridge

# Install dependencies
pip install -r requirements.txt

# Test bridge connection
python test_bridge.py
```

### Debugging
```bash
# View extension logs
Ctrl+Shift+P → "Developer: Show Logs" → "Extension Host"

# View Vidurai daemon logs
vidurai logs -f

# Test IPC connection
vidurai status

# Debug Python bridge
python -c "from vidurai_manager import ViduraiManager; print('Bridge OK')"
```

---

## 🐛 Troubleshooting

### Common Issues

**Extension not capturing context:**
```bash
# Check daemon status
vidurai status

# Restart daemon
vidurai stop && vidurai start

# Restart extension
Ctrl+Shift+P → "Developer: Reload Window"
```

**Python bridge connection failed:**
```bash
# Check Python installation
python --version  # Should be 3.10+

# Reinstall Vidurai SDK
pip install --upgrade vidurai

# Test bridge manually
cd vidurai-vscode-extension/python-bridge
python bridge.py
```

**Memory tree view empty:**
```bash
# Check if memories exist
vidurai stats

# Refresh tree view
Ctrl+Shift+P → "Vidurai: Refresh Memories"

# Check workspace configuration
# Ensure project path is correct in settings
```

**High memory usage:**
```bash
# Run memory hygiene
vidurai hygiene

# Check memory statistics
vidurai stats

# Adjust salience threshold in settings
"vidurai.salienceThreshold": "HIGH"
```

### Debug Commands
```bash
# Extension diagnostics
Ctrl+Shift+P → "Vidurai: Show Logs"

# System information
vidurai info

# Memory health check
vidurai stats --project .

# IPC connection test
vidurai status
```

---

## 📊 Performance & Limits

### Performance Characteristics (v2.2.0)
- **Extension Activation**: < 2s on VS Code startup
- **Memory Footprint**: ~30MB for extension + IPC client
- **CPU Usage**: < 1% during normal operation
- **File Tracking**: Real-time with 2s debounce (configurable)
- **IPC Communication**: Direct daemon connection (no Python bridge overhead)

### Scalability Limits
- **Files Watched**: 10,000+ files per workspace
- **Max File Size**: 51,200 bytes (configurable, 0 = unlimited)
- **Concurrent Workspaces**: Multiple workspaces supported
- **Terminal Commands**: Unlimited history capture
- **Memory Storage**: Limited by available disk space

### Configuration Tuning
```json
{
  "vidurai.debounceMs": 1000,        // Faster response (500-10000ms)
  "vidurai.maxFileSize": 102400,     // Larger files (0 = unlimited)
  "vidurai.logLevel": "warn"         // Reduce logging overhead
}
```

---

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Clone your fork
3. Install dependencies: `npm install`
4. Make changes
5. Test thoroughly
6. Submit pull request

### Code Structure
- `src/extension.ts` - Main extension entry point
- `src/watchers/` - File, terminal, diagnostic watchers
- `src/ipc/` - Daemon communication
- `src/views/` - UI components
- `python-bridge/` - Python SDK integration

### Testing
```bash
# Run unit tests
npm test

# Run integration tests
npm run test:integration

# Test with Extension Development Host
F5 in VS Code
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

This extension embodies the Vedantic principle that "forgetting too is knowledge" - intelligently managing what to remember and what to let go, creating a more focused and effective development experience.

**Special thanks to:**
- The VS Code extension API team
- The Vidurai core development team
- Beta testers and early adopters
- The open-source community

---

## 📞 Support

- **Documentation**: [docs.vidurai.ai](https://docs.vidurai.ai)
- **Issues**: [GitHub Issues](https://github.com/your-org/vidurai-vscode-extension/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/vidurai-vscode-extension/discussions)
- **Email**: support@vidurai.ai

---

*Transform your AI-assisted development workflow today. Install Vidurai and never lose context again.*
