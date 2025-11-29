# 🌐 Vidurai MCP Server API Documentation

Complete API reference for the Vidurai Model Context Protocol (MCP) Server.

**Version:** 2.0.0
**Protocol:** HTTP-based REST API
**Default Port:** 8765
**Last Updated:** November 17, 2025

---

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [API Endpoints](#api-endpoints)
4. [Tools Reference](#tools-reference)
5. [Security & CORS](#security--cors)
6. [Error Handling](#error-handling)
7. [Client Examples](#client-examples)
8. [Integration Guides](#integration-guides)

---

## Overview

The Vidurai MCP Server provides a standardized HTTP API for AI tools and applications to access project memory and context. It implements a simplified version of the Model Context Protocol optimized for local development.

### Key Features

- **HTTP-based** - Simple REST API, no complex protocols
- **4 powerful tools** - Context retrieval, search, activity tracking, project detection
- **CORS security** - Restricted to localhost and trusted domains
- **Auto-discovery** - Integrates with VS Code for project detection
- **Lightweight** - Single-threaded, perfect for personal use
- **Zero config** - Works out of the box

### Architecture

```
┌──────────────┐
│ AI Tool │ (ChatGPT, Custom App, etc.)
└──────┬───────┘
 │ HTTP POST
 ↓
┌──────────────┐
│ MCP Server │ :8765
│ (Vidurai) │
└──────┬───────┘
 │
 ↓
┌──────────────┐
│ SQLite DB │ ~/.vidurai/memory.db
└──────────────┘
```

---

## Getting Started

### Installation

```bash
# Install Vidurai with CLI support
pip install vidurai[cli]

# Verify installation
vidurai-mcp --help
```

### Starting the Server

```bash
# Method 1: Using CLI command
vidurai server

# Method 2: Direct command
vidurai-mcp

# Method 3: Python module
python -m vidurai.mcp_server

# Method 4: With custom options
vidurai server --port 9000 --allow-all-origins
```

### Server Output

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

### Quick Test

```bash
# Health check
curl http://localhost:8765/health

# Expected: {"status": "ok", "version": "2.0.0"}
```

---

## API Endpoints

### `GET /health`

Health check endpoint.

**Response:**
```json
{
 "status": "ok",
 "version": "2.0.0"
}
```

**Status Codes:**
- `200 OK` - Server is healthy

---

### `GET /capabilities`

Get server capabilities and available tools.

**Response:**
```json
{
 "capabilities": {
 "tools": {
 "get_project_context": {
 "description": "Get AI-ready formatted context for a project and optional query",
 "parameters": {
 "project": {
 "type": "string",
 "description": "Project path (default: current directory)",
 "required": false
 },
 "query": {
 "type": "string",
 "description": "Optional search query to focus context",
 "required": false
 },
 "max_results": {
 "type": "integer",
 "description": "Maximum memories to include",
 "default": 20,
 "required": false
 }
 }
 },
 "search_memories": {
 "description": "Search project memories with optional filters",
 "parameters": {
 "project": {
 "type": "string",
 "description": "Project path",
 "required": false
 },
 "query": {
 "type": "string",
 "description": "Search query",
 "required": false
 },
 "min_salience": {
 "type": "string",
 "description": "Minimum salience level",
 "enum": ["CRITICAL", "HIGH", "MEDIUM", "LOW", "NOISE"],
 "default": "MEDIUM",
 "required": false
 },
 "limit": {
 "type": "integer",
 "description": "Maximum results",
 "default": 20,
 "required": false
 }
 }
 },
 "get_recent_activity": {
 "description": "Get recent development activity for a project",
 "parameters": {
 "project": {
 "type": "string",
 "description": "Project path",
 "required": false
 },
 "hours": {
 "type": "integer",
 "description": "Look back this many hours",
 "default": 24,
 "required": false
 }
 }
 },
 "get_active_project": {
 "description": "Get the current active project from VS Code",
 "parameters": {}
 }
 }
 }
}
```

**Status Codes:**
- `200 OK` - Capabilities returned

---

### `POST /`

Execute a tool.

**Request Format:**
```json
{
 "tool": "tool_name",
 "params": {
 "param1": "value1",
 "param2": "value2"
 }
}
```

**Response Format (Success):**
```json
{
 "result": "... tool result ..."
}
```

**Response Format (Error):**
```json
{
 "error": "Error message"
}
```

**Status Codes:**
- `200 OK` - Tool executed successfully
- `400 Bad Request` - Invalid request format or missing tool
- `500 Internal Server Error` - Tool execution failed

---

## Tools Reference

### 1. `get_project_context`

Get AI-ready formatted context for a project.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | No | `.` | Project path |
| `query` | string | No | `null` | Search query to focus context |
| `max_results` | integer | No | `20` | Maximum memories to include |

**Request Example:**
```json
{
 "tool": "get_project_context",
 "params": {
 "project": "/home/user/my-project",
 "query": "authentication flow",
 "max_results": 30
 }
}
```

**Response Example:**
```json
{
 "result": "# Project Context: /home/user/my-project\n\n## Recent Developments (Last 24 hours)\n- Fixed OAuth callback handling\n- Implemented JWT refresh tokens\n\n## Critical Information\n- Database uses PostgreSQL 14\n- Authentication via JWT tokens\n\n## Related Memories for: \"authentication flow\"\n1. [2025-11-17] Added password strength validation\n2. [2025-11-16] Implemented rate limiting\n\n---\nGenerated by Vidurai v2.0.0"
}
```

**Use Cases:**
- Inject project context into AI chat
- Generate documentation from project memory
- Provide background for code reviews

---

### 2. `search_memories`

Search project memories with filters.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | No | `.` | Project path |
| `query` | string | No | `null` | Search keywords |
| `min_salience` | string | No | `MEDIUM` | Minimum importance level |
| `limit` | integer | No | `20` | Maximum results |

**Salience Levels:**
- `CRITICAL` - Never expires
- `HIGH` - 90 days retention
- `MEDIUM` - 30 days retention
- `LOW` - 7 days retention
- `NOISE` - 1 day retention

**Request Example:**
```json
{
 "tool": "search_memories",
 "params": {
 "project": "/home/user/my-project",
 "query": "bug fix",
 "min_salience": "HIGH",
 "limit": 10
 }
}
```

**Response Example:**
```json
{
 "result": [
 {
 "id": 1523,
 "timestamp": "2025-11-17T09:45:23",
 "content": "Fixed authentication bug in login flow",
 "salience": "HIGH",
 "kosha": "Manomaya",
 "project_path": "/home/user/my-project",
 "metadata": {}
 },
 {
 "id": 1501,
 "timestamp": "2025-11-16T14:32:10",
 "content": "Resolved race condition in session handling",
 "salience": "CRITICAL",
 "kosha": "Vijnanamaya",
 "project_path": "/home/user/my-project",
 "metadata": {}
 }
 ]
}
```

**Use Cases:**
- Find specific memories by keyword
- Filter by importance level
- Build custom memory views

---

### 3. `get_recent_activity`

Get recent development activity.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `project` | string | No | `.` | Project path |
| `hours` | integer | No | `24` | Look back this many hours |

**Request Example:**
```json
{
 "tool": "get_recent_activity",
 "params": {
 "project": "/home/user/my-project",
 "hours": 48
 }
}
```

**Response Example:**
```json
{
 "result": [
 {
 "timestamp": "2025-11-17T09:45:23",
 "content": "Fixed authentication bug",
 "salience": "HIGH"
 },
 {
 "timestamp": "2025-11-17T08:30:15",
 "content": "Refactored user service",
 "salience": "MEDIUM"
 }
 ]
}
```

**Use Cases:**
- Daily standup summaries
- Progress tracking
- Activity reports

---

### 4. `get_active_project`

Get the current active project from VS Code.

**Parameters:** None

**Request Example:**
```json
{
 "tool": "get_active_project",
 "params": {}
}
```

**Response Example (VS Code detected):**
```json
{
 "result": "/home/user/my-project",
 "source": "vscode"
}
```

**Response Example (No VS Code):**
```json
{
 "result": "/home/user/current-directory",
 "source": "default"
}
```

**How It Works:**
1. Checks `~/.vidurai/active-project.txt` (written by VS Code extension)
2. If found, returns that path with `source: "vscode"`
3. If not found, returns current directory with `source: "default"`

**Use Cases:**
- Auto-detect project in browser extensions
- Context-aware CLI tools
- Multi-project workflows

---

## Security & CORS

### CORS Policy

By default, MCP server **restricts CORS** to trusted origins:

**Allowed Origins:**
- `http://localhost:*`
- `http://127.0.0.1:*`
- `https://chat.openai.com`
- `https://chatgpt.com`

**Development Mode:**

```bash
# Allow all origins (⚠️ use only for development)
vidurai server --allow-all-origins
```

**Warning:** Development mode disables CORS protection. Only use on trusted networks.

### Security Best Practices

1. **Run on localhost only**
 ```bash
 vidurai server --host localhost
 ```

2. **Don't expose to internet**
 - Never bind to `0.0.0.0` on public networks
 - Use firewall rules to block external access

3. **Audit allowed origins**
 - Only add trusted domains to CORS whitelist
 - Review `vidurai/mcp_server.py:_is_origin_allowed()`

4. **Monitor access logs**
 - Server logs all requests with IP addresses
 - Check for unexpected access patterns

### Authentication

**Current:** No authentication (localhost-only deployment)

**Future (v2.5+):**
- API key authentication
- JWT tokens
- OAuth integration

---

## Error Handling

### Error Response Format

```json
{
 "error": "Error message describing what went wrong"
}
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `"Invalid request format"` | Malformed JSON | Check request body syntax |
| `"Missing 'tool' in request"` | No tool specified | Add `"tool": "tool_name"` |
| `"Unknown tool: xyz"` | Invalid tool name | Use `/capabilities` to see valid tools |
| `"Database error: ..."` | SQLite failure | Check database file permissions |
| `"Project not found: /path"` | Invalid project path | Verify path exists |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Bad request (client error) |
| `403` | Forbidden (CORS rejection) |
| `500` | Internal server error |

---

## Client Examples

### cURL

```bash
# Get active project
curl -X POST http://localhost:8765 \
 -H "Content-Type: application/json" \
 -d '{"tool": "get_active_project", "params": {}}'

# Get context with query
curl -X POST http://localhost:8765 \
 -H "Content-Type: application/json" \
 -d '{
 "tool": "get_project_context",
 "params": {
 "project": "/home/user/my-project",
 "query": "authentication"
 }
 }'

# Search memories
curl -X POST http://localhost:8765 \
 -H "Content-Type: application/json" \
 -d '{
 "tool": "search_memories",
 "params": {
 "query": "bug",
 "min_salience": "HIGH",
 "limit": 5
 }
 }'
```

### Python

```python
import requests

MCP_URL = "http://localhost:8765"

def get_project_context(project: str, query: str = None):
 response = requests.post(MCP_URL, json={
 "tool": "get_project_context",
 "params": {
 "project": project,
 "query": query
 }
 })
 return response.json()["result"]

# Usage
context = get_project_context(
 project="/home/user/my-project",
 query="how does authentication work"
)
print(context)
```

### JavaScript (Node.js)

```javascript
const fetch = require('node-fetch');

const MCP_URL = 'http://localhost:8765';

async function getProjectContext(project, query) {
 const response = await fetch(MCP_URL, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 tool: 'get_project_context',
 params: { project, query }
 })
 });

 const data = await response.json();
 return data.result;
}

// Usage
getProjectContext('/home/user/my-project', 'authentication')
 .then(context => console.log(context));
```

### JavaScript (Browser)

```javascript
const MCP_URL = 'http://localhost:8765';

async function getActiveProject() {
 try {
 const response = await fetch(MCP_URL, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 tool: 'get_active_project',
 params: {}
 })
 });

 const data = await response.json();
 return data.result;
 } catch (error) {
 console.error('MCP server not running:', error);
 return null;
 }
}

// Usage in ChatGPT extension
getActiveProject().then(project => {
 console.log('Active project:', project);
});
```

---

## Integration Guides

### ChatGPT Browser Extension

See [ChatGPT Extension Guide](../vidurai-chatgpt-extension/README.md)

**Quick Integration:**

```javascript
// 1. Query active project
const project = await fetch('http://localhost:8765', {
 method: 'POST',
 body: JSON.stringify({
 tool: 'get_active_project',
 params: {}
 })
}).then(r => r.json()).then(d => d.result);

// 2. Get context for user message
const context = await fetch('http://localhost:8765', {
 method: 'POST',
 body: JSON.stringify({
 tool: 'get_project_context',
 params: { project, query: userMessage }
 })
}).then(r => r.json()).then(d => d.result);

// 3. Inject into ChatGPT
const enhancedMessage = `<!--\nVIDURAI CONTEXT:\n${context}\n-->\n\n${userMessage}`;
```

### Custom CLI Tool

```bash
#!/bin/bash
# my-ai-assistant.sh

PROJECT=$(curl -s -X POST http://localhost:8765 \
 -H "Content-Type: application/json" \
 -d '{"tool": "get_active_project", "params": {}}' \
 | jq -r '.result')

CONTEXT=$(curl -s -X POST http://localhost:8765 \
 -H "Content-Type: application/json" \
 -d "{\"tool\": \"get_project_context\", \"params\": {\"project\": \"$PROJECT\", \"query\": \"$1\"}}" \
 | jq -r '.result')

echo "PROJECT: $PROJECT"
echo ""
echo "$CONTEXT"
```

### Custom IDE Extension

**Pseudocode:**

```typescript
// Get project from workspace
const projectPath = workspace.workspaceFolders[0].uri.fsPath;

// Query MCP server
const response = await fetch('http://localhost:8765', {
 method: 'POST',
 body: JSON.stringify({
 tool: 'get_project_context',
 params: {
 project: projectPath,
 query: 'current file context'
 }
 })
});

const context = (await response.json()).result;

// Use context in AI assistant
aiAssistant.setContext(context);
```

---

## Configuration

### Environment Variables

```bash
# Override database location
export VIDURAI_DB_PATH="$HOME/custom-path/memory.db"

# Default MCP port
export VIDURAI_MCP_PORT=9000
```

### Command-Line Options

```bash
vidurai server --help

Options:
 --port INTEGER Port to listen on [default: 8765]
 --host TEXT Host to bind to [default: localhost]
 --allow-all-origins Allow all CORS origins (dev mode)
 --help Show this message and exit
```

---

## Troubleshooting

### Server won't start

**Error:** `Address already in use`

```bash
# Check if port is in use
lsof -i :8765

# Kill existing server
pkill -f vidurai-mcp

# Or use different port
vidurai server --port 9000
```

### CORS errors in browser

**Error:** `Access-Control-Allow-Origin`

```bash
# Development mode (allows all origins)
vidurai server --allow-all-origins

# Or add your domain to allowed origins in vidurai/mcp_server.py
```

### No active project detected

**Issue:** `get_active_project` returns current directory, not VS Code project

**Solutions:**
1. Ensure VS Code extension is installed and running
2. Check `~/.vidurai/active-project.txt` exists
3. Open a workspace folder in VS Code
4. Reload VS Code window

### Database errors

**Error:** `Database locked`

```bash
# Check for multiple processes
ps aux | grep vidurai

# Kill all Vidurai processes
pkill -f vidurai

# Restart server
vidurai server
```

---

## Roadmap

### v2.0.0 (Current)
- HTTP-based protocol
- 4 core tools
- CORS security
- Project auto-detection

### v2.5.0 (Planned - Q1 2025)
- [ ] stdio-based MCP for official clients
- [ ] JSON-RPC 2.0 support
- [ ] WebSocket for real-time updates
- [ ] API key authentication

### v3.0.0 (Planned - Q2 2025)
- [ ] Multi-project workspaces
- [ ] Streaming responses
- [ ] GraphQL API
- [ ] Advanced analytics endpoints

---

## API Changelog

### v2.0.0 (2025-11-17)
- Initial HTTP-based MCP server
- 4 tools: get_project_context, search_memories, get_recent_activity, get_active_project
- CORS security with whitelist
- Health and capabilities endpoints

---

## See Also

- [CLI Reference](CLI_REFERENCE.md)
- [ChatGPT Extension](../vidurai-chatgpt-extension/README.md)
- [Main Documentation](../README.md)
- [Phase 2 Implementation Summary](../PHASE2_IMPLEMENTATION_SUMMARY.md)

---

**विस्मृति भी विद्या है** — *"Forgetting too is knowledge"*
**जय विदुराई! 🕉️**
