# Baseline MCP Contract

## Transport

The current Vidurai server exposes project-specific HTTP/REST endpoints, including capability discovery and direct tool invocation. The WP-00 test verifies retrieval through that existing interface. It does not verify standard MCP JSON-RPC or a standards-compliant MCP transport.

This REST server is what the codebase currently calls "MCP". A future MCP-hardening package will be required to implement actual standard MCP JSON-RPC over stdio or SSE.

- HTTP server via `fastapi` and `uvicorn`.
- Listens on `localhost:8765` by default (overridable via CLI).

## Binding
- Direct integration with `MemoryDatabase` via global references.

## Runtime Tool Inventory
1. `get_project_context`
   - Inputs: `query` (string, optional), `project` (string, required), `min_salience` (string, default: 'MEDIUM')
   - Outputs: Markdown formatted context capsule.
2. `search_memories`
   - Inputs: `query` (string, required), `project` (string, required), `limit` (int, default: 10)
   - Outputs: JSON list of matching memories.
3. `get_recent_activity`
   - Inputs: `project` (string, required), `hours` (int, default: 24)
   - Outputs: JSON list of recent memory events.
4. `get_active_project`
   - Inputs: None
   - Outputs: JSON string path of the active project.
5. `get_proactive_hints`
   - Inputs: `project` (string, required), `max_hints` (int, default: 5), `min_confidence` (number, default: 0.5), `hint_types` (array, optional)
   - Outputs: JSON list of proactive hints.

## Current Security Behavior
- `allow_all_origins` flag overrides origin validation.
- CORS Origin Hardcodes:
  - `http://localhost:*`
  - `http://127.0.0.1:*`
  - `https://chat.openai.com`
  - `https://chatgpt.com`
  - `https://claude.ai`

## Current Database Access Path
- Direct instantiation of `MemoryDatabase()` inside tool endpoints. Tools execute synchronous SQLite queries against `~/.vidurai/memory.db`.
