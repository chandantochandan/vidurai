import sys
import json
import logging
import anyio
from typing import Optional, Dict, Any, List
from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server
import uuid
import os
import asyncio

from vidurai.daemon.mcp.permissions import PermissionManager, Permission, ClientAuthenticator
from vidurai.storage.database import MemoryDatabase, SalienceLevel
from vidurai.vismriti_memory import VismritiMemory

logger = logging.getLogger("vidurai.mcp.gateway")

class MCPGateway:
    """MCP Gateway for Vidurai"""
    
    def __init__(self, client_id: str, token: str, db_path: Optional[str] = None, config_dir: Optional[str] = None):
        self.server = Server("vidurai-mcp")
        self.permission_manager = PermissionManager(config_dir)
        self.authenticator = ClientAuthenticator(config_dir)
        self.db_path = db_path
        self.client_id = client_id
        
        # Immediate authentication check
        if not self.authenticator.verify(client_id, token):
            logger.critical(f"MCP Gateway failed authentication for client '{client_id}'")
            raise ValueError("Authentication failed")
            
        # Setup MCP handlers
        self.server._request_handlers[types.ListToolsRequest] = self.list_tools
        self.server._request_handlers[types.CallToolRequest] = self.call_tool
        
    def _get_db(self) -> MemoryDatabase:
        return MemoryDatabase(self.db_path)

    def _verify_permission(self, permission: Permission, project_scope: str, operation: str) -> bool:
        """Verify permission for the authenticated client and record audit."""
        has_perm = self.permission_manager.has_permission(self.client_id, permission)
        outcome = "granted" if has_perm else "denied"
        self.permission_manager.audit(
            client_id=self.client_id,
            operation=operation,
            project_scope=project_scope,
            permission=permission.value,
            outcome=outcome,
            reason="Verified via PermissionManager" if has_perm else "Lacks permission"
        )
        return has_perm

    async def list_tools(self, request: types.ListToolsRequest) -> types.ListToolsResult:
        tools = [
            types.Tool(
                name="get_project_context",
                description="Get identity and active status for a Vidurai project.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Absolute path to the project root"}
                    },
                    "required": ["project_path"]
                }
            ),
            types.Tool(
                name="search_memories",
                description="Search relevant confirmed memory retrieval.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Absolute path to the project root"},
                        "query": {"type": "string", "description": "Search query text"}
                    },
                    "required": ["project_path", "query"]
                }
            ),
            types.Tool(
                name="create_evidence",
                description="Produce evidence for a Vidurai project.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string", "description": "Absolute path to the project root"},
                        "content": {"type": "string", "description": "Evidence content string"},
                        "source": {"type": "string", "description": "Source component identifier"}
                    },
                    "required": ["project_path", "content", "source"]
                }
            )
        ]
        return types.ListToolsResult(tools=tools)

    async def call_tool(self, request: types.CallToolRequest) -> types.CallToolResult:
        name = request.params.name
        args = request.params.arguments or {}
        
        project_path = args.get("project_path")
        
        if not project_path:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: project_path is required.")])

        if project_path == "." or not project_path.startswith("/"):
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Ambiguous project scope. Absolute path required.")])

        try:
            if name == "get_project_context":
                if not self._verify_permission(Permission.READ_ONLY, project_path, "get_project_context"):
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Permission denied.")])
                
                db = self._get_db()
                project_id = db.get_or_create_project(project_path)
                with db.get_connection_for_reading() as conn:
                    row = conn.execute("SELECT project_uuid, path FROM projects WHERE id = ?", (project_id,)).fetchone()
                
                if not row:
                    return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": "Project not found"}))])
                
                metadata = {
                    "disclosure": "Context supplied via Vidurai MCP Gateway", 
                    "client": self.client_id,
                    "permission": "read-only"
                }
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"uuid": row[0], "path": row[1], "status": "active", "_metadata": metadata}) )])

            elif name == "search_memories":
                if not self._verify_permission(Permission.READ_ONLY, project_path, "search_memories"):
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Permission denied.")])
                
                query = args.get("query")
                if not query:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: query is required.")])
                
                db = self._get_db()
                project_id = db.get_or_create_project(project_path)
                with db.get_connection_for_reading() as conn:
                    row = conn.execute("SELECT project_uuid, path FROM projects WHERE id = ?", (project_id,)).fetchone()
                
                if not row:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Project not found.")])
                
                memory = VismritiMemory(project_path=project_path)
                results = memory.recall(query, limit=5)
                
                # Format with provenance metadata
                formatted = [{"id": str(r.get("id")), "content": r.get("content"), "provenance": r.get("event_id", "unknown")} for r in results]
                metadata = {
                    "disclosure": "Context supplied via Vidurai MCP Gateway", 
                    "project": project_path,
                    "client": self.client_id,
                    "permission_used": "read-only",
                    "categories_released": ["memory"]
                }
                
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"results": formatted, "_metadata": metadata}) )])

            elif name == "create_evidence":
                if not self._verify_permission(Permission.EVIDENCE_MUTATION, project_path, "create_evidence"):
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Permission denied.")])
                
                content = args.get("content")
                source = args.get("source")
                if not content or not source:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: content and source are required.")])
                
                db = self._get_db()
                project_id = db.get_or_create_project(project_path)
                with db.get_connection_for_reading() as conn:
                    row = conn.execute("SELECT project_uuid, path FROM projects WHERE id = ?", (project_id,)).fetchone()
                
                if not row:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Project not found.")])
                
                import time
                from datetime import datetime
                import hashlib
                
                event_id = str(uuid.uuid4())
                receipt_id = f"mcp-{int(time.time()*1000)}-{event_id[:8]}"
                event_type = "mcp_evidence"
                
                # Create WP-02 pipeline receipt
                payload = {"content": content, "source": source, "mcp_client": self.client_id}
                payload_json = json.dumps(payload)
                payload_hash = hashlib.sha256(payload_json.encode('utf-8')).hexdigest()
                
                # We need project context for the receipt
                identity = {
                    "project_uuid": row[0],
                    "branch": "main",  # In standard cases, you'd resolve the branch
                    "commit": None,
                    "detached": False
                }
                
                try:
                    # Enqueue receipt
                    db.insert_event_receipt(
                        receipt_id=receipt_id,
                        event_type=event_type,
                        payload_hash=payload_hash,
                        payload_json=payload_json,
                        status="accepted",
                        received_at=int(time.time() * 1000),
                        event_id=event_id,
                        identity=identity
                    )
                except Exception as e:
                    if "UNIQUE constraint failed" in str(e):
                        return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Duplicate event ID conflict.")])
                    raise

                # Process memory
                try:
                    memory_id = db.process_memory_from_receipt(
                        receipt_id=receipt_id,
                        project_path=project_path,
                        verbatim=content,
                        gist=content,
                        salience=SalienceLevel.MEDIUM,
                        event_type=event_type,
                        created_at=datetime.now(),
                        identity=identity
                    )
                except Exception as e:
                    db.update_receipt_status(receipt_id, "failed", str(e))
                    raise
                
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": "success", "receipt_id": receipt_id, "memory_id": str(memory_id), "event_id": event_id}) )])

            else:
                return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text=f"Error: Unknown tool '{name}'.")])
                
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="An internal error occurred during tool execution.")])

    async def run(self):
        """Run the MCP stdio server"""
        async with stdio_server() as (read_stream, write_stream):
            # 6. Transport and request safety
            # stdio_server inherently handles framing, validation, and JSON-RPC
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Vidurai MCP Gateway")
    parser.add_argument("--client-id", required=True, help="Authenticated Client ID")
    parser.add_argument("--token", required=True, help="Authentication token")
    args = parser.parse_args()
    
    gateway = MCPGateway(client_id=args.client_id, token=args.token)
    try:
        anyio.run(gateway.run)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Gateway failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
