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

from vidurai.daemon.mcp.permissions import PermissionManager, Permission
from vidurai.storage.database import MemoryDatabase, SalienceLevel
from vidurai.vismriti_memory import VismritiMemory

logger = logging.getLogger("vidurai.mcp.gateway")

class MCPGateway:
    """MCP Gateway for Vidurai"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.server = Server("vidurai-mcp")
        self.permission_manager = PermissionManager()
        self.db_path = db_path
        
        # Setup MCP handlers
        self.server._request_handlers[types.ListToolsRequest] = self.list_tools
        self.server._request_handlers[types.CallToolRequest] = self.call_tool
        
    def _get_db(self) -> MemoryDatabase:
        return MemoryDatabase(self.db_path)

    def _verify_permission(self, client_id: str, permission: Permission, project_scope: str, operation: str) -> bool:
        """Verify permission and record audit."""
        has_perm = self.permission_manager.has_permission(client_id, permission)
        outcome = "granted" if has_perm else "denied"
        self.permission_manager.audit(
            client_id=client_id,
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
                        "client_id": {"type": "string", "description": "Authenticated MCP client ID"},
                        "project_path": {"type": "string", "description": "Absolute path to the project root"}
                    },
                    "required": ["client_id", "project_path"]
                }
            ),
            types.Tool(
                name="search_memories",
                description="Search relevant confirmed memory retrieval.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Authenticated MCP client ID"},
                        "project_path": {"type": "string", "description": "Absolute path to the project root"},
                        "query": {"type": "string", "description": "Search query text"}
                    },
                    "required": ["client_id", "project_path", "query"]
                }
            ),
            types.Tool(
                name="create_evidence",
                description="Produce evidence for a Vidurai project.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "client_id": {"type": "string", "description": "Authenticated MCP client ID"},
                        "project_path": {"type": "string", "description": "Absolute path to the project root"},
                        "content": {"type": "string", "description": "Evidence content string"},
                        "source": {"type": "string", "description": "Source component identifier"}
                    },
                    "required": ["client_id", "project_path", "content", "source"]
                }
            )
        ]
        return types.ListToolsResult(tools=tools)

    async def call_tool(self, request: types.CallToolRequest) -> types.CallToolResult:
        name = request.params.name
        args = request.params.arguments or {}
        
        client_id = args.get("client_id")
        project_path = args.get("project_path")
        
        if not client_id:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: client_id is required.")])
        if not project_path:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: project_path is required.")])

        if project_path == "." or not project_path.startswith("/"):
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Ambiguous project scope. Absolute path required.")])

        try:
            if name == "get_project_context":
                if not self._verify_permission(client_id, Permission.READ_ONLY, project_path, "get_project_context"):
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Permission denied.")])
                
                db = self._get_db()
                project_id = db.get_or_create_project(project_path)
                with db.get_connection_for_reading() as conn:
                    row = conn.execute("SELECT project_uuid, path FROM projects WHERE id = ?", (project_id,)).fetchone()
                
                if not row:
                    return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": "Project not found"}))])
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"uuid": row[0], "path": row[1], "status": "active"}) )])

            elif name == "search_memories":
                if not self._verify_permission(client_id, Permission.READ_ONLY, project_path, "search_memories"):
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
                
                memory = VismritiMemory()
                memory.project_path = project_path
                results = memory.recall(query, limit=5)
                
                # Format with provenance metadata
                formatted = [{"id": str(r.get("id")), "content": r.get("content"), "provenance": r.get("event_id", "unknown")} for r in results]
                metadata = {"disclosure": "Context supplied via Vidurai MCP Gateway", "project": project_path}
                
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"results": formatted, "_metadata": metadata}) )])

            elif name == "create_evidence":
                if not self._verify_permission(client_id, Permission.EVIDENCE_MUTATION, project_path, "create_evidence"):
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
                
                event_id = str(uuid.uuid4())
                memory = VismritiMemory()
                memory.project_path = project_path
                memory_id = memory.remember(
                    content=content,
                    salience=SalienceLevel.MEDIUM,
                    
                    
                    metadata={"mcp_client": client_id, "source": source, "event_id": event_id}
                )
                
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": "success", "memory_id": str(memory_id), "event_id": event_id}) )])

            else:
                return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text=f"Error: Unknown tool '{name}'.")])
                
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="An internal error occurred during tool execution.")])

    async def run(self):
        """Run the MCP stdio server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())

def main():
    gateway = MCPGateway()
    try:
        anyio.run(gateway.run)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
