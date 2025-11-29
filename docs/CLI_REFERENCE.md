# 🖥️ Vidurai CLI Reference

Complete reference for the Vidurai command-line interface.

**Version:** 2.0.0
**Last Updated:** November 17, 2025

---

## Installation

```bash
# Install with CLI support
pip install vidurai[cli]

# Verify installation
vidurai --version
vidurai --help
```

---

## Global Options

All commands support these global options:

| Option | Description | Default |
|--------|-------------|---------|
| `--help` | Show command help | - |
| `--version` | Show Vidurai version | - |

---

## Commands Overview

| Command | Description |
|---------|-------------|
| [`stats`](#stats) | Show memory statistics for a project |
| [`recall`](#recall) | Search and recall memories |
| [`context`](#context) | Get AI-ready formatted context |
| [`recent`](#recent) | Show recent development activity |
| [`export`](#export) | Export memories to file |
| [`server`](#server) | Start MCP server |
| [`clear`](#clear) | Clear project memories |
| [`info`](#info) | Show installation information |

---

## Command Details

### `stats`

Show memory statistics for a project.

**Usage:**
```bash
vidurai stats [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project` | PATH | `.` (current directory) | Project path to query |

**Examples:**

```bash
# Show stats for current project
vidurai stats

# Show stats for specific project
vidurai stats --project /path/to/my-project

# Show stats with absolute path
vidurai stats --project ~/code/my-app
```

**Output:**

```
 Vidurai Memory Statistics
Project: /home/user/my-project

Total Memories: 342
 • Critical: 12
 • High: 45
 • Medium: 128
 • Low: 89
 • Noise: 68

Recent Activity (24h): 23 memories
Oldest Memory: 2025-10-15 14:32:11
Newest Memory: 2025-11-17 09:45:23
```

---

### `recall`

Search and recall memories from the database.

**Usage:**
```bash
vidurai recall [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project` | PATH | `.` | Project path to query |
| `--query` | TEXT | None | Search query (keywords) |
| `--limit` | INT | `20` | Maximum memories to return |
| `--min-salience` | CHOICE | `MEDIUM` | Minimum salience level |
| `--format` | CHOICE | `table` | Output format: `table`, `json`, `text` |

**Salience Levels:**
- `CRITICAL` - Never expires, highest importance
- `HIGH` - 90 days retention
- `MEDIUM` - 30 days retention
- `LOW` - 7 days retention
- `NOISE` - 1 day retention

**Examples:**

```bash
# Search all memories (default: MEDIUM+)
vidurai recall

# Search with keyword
vidurai recall --query "authentication"

# Search with multiple keywords
vidurai recall --query "bug fix login"

# Limit results
vidurai recall --query "API" --limit 5

# Only critical memories
vidurai recall --min-salience CRITICAL

# Only high and critical
vidurai recall --min-salience HIGH

# Output as JSON
vidurai recall --query "database" --format json

# Output as plain text
vidurai recall --format text
```

**Output (table format):**

```
┌────────────────────┬──────────┬─────────────────────────────────────┐
│ Timestamp │ Salience │ Memory │
├────────────────────┼──────────┼─────────────────────────────────────┤
│ 2025-11-17 09:45 │ HIGH │ Fixed authentication bug in login │
│ 2025-11-17 08:30 │ MEDIUM │ Refactored user service │
│ 2025-11-16 15:20 │ CRITICAL │ Database migration to v2.0 │
└────────────────────┴──────────┴─────────────────────────────────────┘
```

**Output (JSON format):**

```json
[
 {
 "id": 1523,
 "timestamp": "2025-11-17T09:45:23",
 "content": "Fixed authentication bug in login",
 "salience": "HIGH",
 "kosha": "Manomaya",
 "project_path": "/home/user/my-project"
 }
]
```

---

### `context`

Get AI-ready formatted context for a query.

**Usage:**
```bash
vidurai context [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project` | PATH | `.` | Project path |
| `--query` | TEXT | None | Context query (optional) |
| `--max-results` | INT | `20` | Maximum memories to include |
| `--output` | PATH | None | Save to file (instead of stdout) |

**Examples:**

```bash
# Get general project context
vidurai context

# Get context for specific query
vidurai context --query "How does authentication work?"

# Get context with more results
vidurai context --query "API endpoints" --max-results 50

# Save to file
vidurai context --query "database schema" --output context.txt

# Pipe to clipboard (macOS)
vidurai context --query "recent bugs" | pbcopy

# Pipe to clipboard (Linux)
vidurai context --query "recent bugs" | xclip -selection clipboard
```

**Output Format:**

```markdown
# Project Context: /home/user/my-project

## Recent Developments (Last 24 hours)
- Fixed authentication bug in login flow
- Refactored user service for better testability
- Added API rate limiting

## Critical Information
- Database migration completed to v2.0 schema
- New authentication system uses JWT tokens
- Rate limit: 100 requests/minute per user

## Related Memories for: "authentication"
1. [2025-11-17] Fixed OAuth callback handling
2. [2025-11-16] Implemented JWT refresh tokens
3. [2025-11-15] Added password strength validation

---
Generated by Vidurai v2.0.0
```

**Use Cases:**

```bash
# Copy context and paste into ChatGPT
vidurai context --query "how does X work" | pbcopy
# Then paste into ChatGPT

# Use with other AI tools
vidurai context --query "refactoring" > context.txt
# Then attach context.txt to your AI chat

# Quick reference
vidurai context --query "API docs"
```

---

### `recent`

Show recent development activity.

**Usage:**
```bash
vidurai recent [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project` | PATH | `.` | Project path |
| `--hours` | INT | `24` | Look back this many hours |
| `--limit` | INT | `50` | Maximum memories to show |

**Examples:**

```bash
# Show last 24 hours (default)
vidurai recent

# Show last 48 hours
vidurai recent --hours 48

# Show last week
vidurai recent --hours 168

# Show last hour
vidurai recent --hours 1

# Limit output
vidurai recent --hours 24 --limit 10
```

**Output:**

```
📅 Recent Activity (Last 24 hours)
Project: /home/user/my-project

2025-11-17 09:45 [HIGH] Fixed authentication bug in login
2025-11-17 08:30 [MEDIUM] Refactored user service
2025-11-17 07:15 [MEDIUM] Updated API documentation
2025-11-16 18:20 [CRITICAL] Database migration to v2.0
2025-11-16 16:45 [HIGH] Implemented rate limiting

Total: 23 memories
```

---

### `export`

Export memories to a file.

**Usage:**
```bash
vidurai export [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project` | PATH | `.` | Project path |
| `--format` | CHOICE | `json` | Format: `json`, `text`, `sql` |
| `--output` | PATH | stdout | Output file path |
| `--min-salience` | CHOICE | `LOW` | Minimum salience level |

**Examples:**

```bash
# Export as JSON
vidurai export --format json --output memories.json

# Export as text
vidurai export --format text --output memories.txt

# Export as SQL INSERT statements
vidurai export --format sql --output memories.sql

# Export only important memories
vidurai export --min-salience HIGH --output important.json

# Export to stdout and pipe
vidurai export --format json | jq '.[] | select(.salience == "CRITICAL")'
```

**JSON Format:**

```json
[
 {
 "id": 1523,
 "timestamp": "2025-11-17T09:45:23",
 "content": "Fixed authentication bug",
 "salience": "HIGH",
 "kosha": "Manomaya",
 "project_path": "/home/user/my-project",
 "metadata": {}
 }
]
```

**Text Format:**

```
================================================================================
Vidurai Memory Export
Project: /home/user/my-project
Exported: 2025-11-17 10:30:00
================================================================================

[2025-11-17 09:45:23] HIGH - Manomaya
Fixed authentication bug in login
---

[2025-11-17 08:30:15] MEDIUM - Manomaya
Refactored user service
---
```

**SQL Format:**

```sql
-- Vidurai Memory Export
-- Project: /home/user/my-project
-- Exported: 2025-11-17 10:30:00

INSERT INTO memories (timestamp, content, salience, kosha, project_path)
VALUES ('2025-11-17 09:45:23', 'Fixed authentication bug', 'HIGH', 'Manomaya', '/home/user/my-project');

INSERT INTO memories (timestamp, content, salience, kosha, project_path)
VALUES ('2025-11-17 08:30:15', 'Refactored user service', 'MEDIUM', 'Manomaya', '/home/user/my-project');
```

---

### `server`

Start the MCP server.

**Usage:**
```bash
vidurai server [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--port` | INT | `8765` | Port to listen on |
| `--host` | TEXT | `localhost` | Host to bind to |
| `--allow-all-origins` | FLAG | False | Allow all CORS origins (dev mode) |

**Examples:**

```bash
# Start with defaults (port 8765, localhost)
vidurai server

# Custom port
vidurai server --port 9000

# Development mode (allow all origins)
vidurai server --allow-all-origins

# Bind to all interfaces (⚠️ security risk)
vidurai server --host 0.0.0.0
```

**Aliases:**

```bash
# These are equivalent
vidurai server
vidurai-mcp
python -m vidurai.mcp_server
```

**Output:**

```
============================================================
 Vidurai MCP Server
============================================================
Listening on: http://localhost:8765
Health check: http://localhost:8765/health
Capabilities: http://localhost:8765/capabilities
============================================================
Tools available:
 • get_project_context - Get AI-ready context
 • search_memories - Search project memories
 • get_recent_activity - Get recent dev activity
 • get_active_project - Get current VS Code project
============================================================
Press Ctrl+C to stop
```

**Testing:**

```bash
# Health check
curl http://localhost:8765/health

# Get capabilities
curl http://localhost:8765/capabilities

# Query a tool
curl -X POST http://localhost:8765 \
 -H "Content-Type: application/json" \
 -d '{"tool": "get_active_project", "params": {}}'
```

**See also:** [MCP Server Documentation](MCP_SERVER.md)

---

### `clear`

Clear project memories (with confirmation).

**Usage:**
```bash
vidurai clear [OPTIONS]
```

**Options:**

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--project` | PATH | `.` | Project path to clear |
| `--yes` | FLAG | False | Skip confirmation prompt |

**Examples:**

```bash
# Clear current project (with confirmation)
vidurai clear

# Clear specific project
vidurai clear --project /path/to/project

# Skip confirmation (dangerous!)
vidurai clear --yes
```

**Interactive Prompt:**

```
⚠️ WARNING: This will permanently delete ALL memories for:
 Project: /home/user/my-project

Are you sure you want to continue? [y/N]: y

 Cleared 342 memories from /home/user/my-project
```

**⚠️ Warning:** This action is **irreversible**. Consider exporting first:

```bash
# Backup before clearing
vidurai export --output backup.json
vidurai clear
```

---

### `info`

Show Vidurai installation information.

**Usage:**
```bash
vidurai info
```

**No options.**

**Example:**

```bash
vidurai info
```

**Output:**

```
 Vidurai Installation Info
============================

Version: 2.0.0
Python: 3.10.12
Database: /home/user/.vidurai/memory.db
Database Size: 2.3 MB
MCP Server: Installed ✓
CLI Tool: Installed ✓

Installation Path: /home/user/.local/lib/python3.10/site-packages/vidurai
Config Directory: /home/user/.vidurai

Files:
 • memory.db (2.3 MB) - Main database
 • active-project.txt - Current project
 • experiences.jsonl (145 KB) - RL experiences
 • q_table.json (89 KB) - RL Q-table

Total Storage: 2.5 MB
```

---

## Environment Variables

The CLI respects these environment variables:

```bash
# Override database location
export VIDURAI_DB_PATH="$HOME/custom-path/memory.db"

# MCP server default port
export VIDURAI_MCP_PORT=9000

# Default project path
export VIDURAI_PROJECT_PATH="$HOME/code/my-project"
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success |
| `1` | General error |
| `2` | Command-line syntax error |
| `3` | Database error |
| `4` | MCP server error |

---

## Shell Integration

### Bash Completion

```bash
# Add to ~/.bashrc
eval "$(_VIDURAI_COMPLETE=bash_source vidurai)"
```

### Zsh Completion

```bash
# Add to ~/.zshrc
eval "$(_VIDURAI_COMPLETE=zsh_source vidurai)"
```

### Fish Completion

```bash
# Add to ~/.config/fish/config.fish
eval (env _VIDURAI_COMPLETE=fish_source vidurai)
```

---

## Common Workflows

### Daily Development Workflow

```bash
# Morning: Check what you worked on yesterday
vidurai recent --hours 24

# During work: Quick context lookup
vidurai context --query "authentication flow"

# End of day: Review statistics
vidurai stats
```

### AI Integration Workflow

```bash
# Start MCP server (once)
vidurai server &

# Get context for ChatGPT
vidurai context --query "current bug" | pbcopy
# Paste into ChatGPT

# Or use ChatGPT extension (automatic injection)
```

### Maintenance Workflow

```bash
# Check installation
vidurai info

# Backup memories
vidurai export --format json --output backup-$(date +%Y%m%d).json

# Review old memories
vidurai recall --min-salience LOW --limit 100

# Clear old project
vidurai clear --project /old/project
```

---

## Troubleshooting

### Command not found

```bash
# Ensure CLI is installed
pip install vidurai[cli]

# Check installation
which vidurai

# If not found, check PATH
echo $PATH
```

### Database locked error

```bash
# Another process is using the database
# Check for running MCP server
pkill -f vidurai-mcp

# Or check processes
ps aux | grep vidurai
```

### No memories found

```bash
# Check if database exists
vidurai info

# Check project path
vidurai stats --project /correct/path

# Verify VS Code extension is running
```

---

## See Also

- [MCP Server Documentation](MCP_SERVER.md)
- [ChatGPT Extension Guide](../vidurai-chatgpt-extension/README.md)
- [Main Documentation](../README.md)
- [Troubleshooting Guide](TROUBLESHOOTING.md)

---

**विस्मृति भी विद्या है** — *"Forgetting too is knowledge"*
**जय विदुराई! 🕉️**
