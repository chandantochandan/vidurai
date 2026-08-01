import sys
import json
import logging
import anyio
import uuid
import os
import asyncio
import time
from typing import Optional, Dict, Any, List

from mcp.server import Server
import mcp.types as types
from mcp.server.stdio import stdio_server

from vidurai.daemon.mcp.permissions import PermissionManager, Permission, ClientAuthenticator
from vidurai.storage.database import MemoryDatabase, SalienceLevel
from vidurai.vismriti_memory import VismritiMemory
from vidurai.daemon.ingestion import ingest_class1_evidence

logger = logging.getLogger("vidurai.mcp.gateway")

class MCPGateway:
    """MCP Gateway for Vidurai"""
    
    def __init__(self, client_id: str, token: str, db_path: Optional[str] = None, config_dir: Optional[Any] = None):
        self.server = Server("vidurai-mcp")
        self.permission_manager = PermissionManager(config_dir)
        self.authenticator = ClientAuthenticator(config_dir)
        self.db_path = db_path
        self.client_id = client_id
        self.token = token
        
        # Immediate authentication check
        if not self.authenticator.verify(self.client_id, self.token):
            logger.critical(f"MCP Gateway failed authentication for client '{self.client_id}'")
            raise ValueError("Authentication failed")
            
        # Setup MCP handlers
        self.server._request_handlers[types.ListToolsRequest] = self.list_tools
        self.server._request_handlers[types.CallToolRequest] = self.call_tool_with_safeguards
        
    def _get_db(self) -> MemoryDatabase:
        return MemoryDatabase(self.db_path)

    def _check_auth_active(self) -> bool:
        """Check if the client's token is still valid (not revoked)."""
        # Force reload to see changes from disk
        self.authenticator._load()
        return self.authenticator.verify(self.client_id, self.token)

    def _verify_permission(self, permission: Permission, project_scope: str, operation: str) -> bool:
        """Verify permission for the authenticated client and record audit."""
        # Force reload permissions
        self.permission_manager._load()
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
        if not self._check_auth_active():
            raise RuntimeError("Authentication revoked during active session")
            
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
                        "source": {"type": "string"},
                        "event_id": {"type": "string"},
                        "timestamp": {"type": "integer"}
                    },
                    "required": ["project_path", "content", "source"]
                }
            ),
            types.Tool(
                name="request_capsule_preview",
                description="Request a Context Capsule preview for a given task and category list.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                        "task": {"type": "string"},
                        "requested_categories": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "max_items": {"type": "integer"}
                    },
                    "required": ["project_path", "task", "requested_categories"]
                }
            ),
            types.Tool(
                name="get_capsule_status",
                description="Get the status of a requested Context Capsule.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "capsule_id": {"type": "string"}
                    },
                    "required": ["capsule_id"]
                }
            ),
            types.Tool(
                name="consume_capsule",
                description="Consume an approved Context Capsule.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "capsule_id": {"type": "string"}
                    },
                    "required": ["capsule_id"]
                }
            ),
            types.Tool(
                name="approve_capsule",
                description="Approve a Context Capsule preview for delivery.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "capsule_id": {"type": "string"}
                    },
                    "required": ["capsule_id"]
                }
            ),
            types.Tool(
                name="reject_capsule",
                description="Reject a Context Capsule preview.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "capsule_id": {"type": "string"}
                    },
                    "required": ["capsule_id"]
                }
            )
        ]
        return types.ListToolsResult(tools=tools)

    async def call_tool_with_safeguards(self, request: types.CallToolRequest) -> types.CallToolResult:
        """Wrapper to enforce session auth, size limits, and timeouts."""
        if not self._check_auth_active():
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Authentication revoked.")])
            
        # Size limit check (simulate by checking args length since we can't easily intercept raw stdio bytes here)
        args_str = json.dumps(request.params.arguments or {})
        if len(args_str) > 1024 * 1024:  # 1MB limit
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Payload exceeds maximum size limit (1MB).")])
            
        try:
            # 30 second timeout for any tool call
            return await asyncio.wait_for(self.call_tool(request), timeout=30.0)
        except asyncio.TimeoutError:
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Request timed out.")])
        except asyncio.CancelledError:
            logger.info("Request cancelled by client disconnect")
            raise

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
                    "categories_released": ["memory"],
                    "note": "Unresolved or ambiguous memories are labeled with null provenance or low salience."
                }
                
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"results": formatted, "_metadata": metadata}) )])

            elif name == "create_evidence":
                if not self._verify_permission(Permission.EVIDENCE_MUTATION, project_path, "create_evidence"):
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Permission denied.")])
                
                content = args.get("content")
                source = args.get("source")
                event_id = args.get("event_id") or str(uuid.uuid4())
                msg_ts = args.get("timestamp") or int(time.time() * 1000)
                
                if not content or not source:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: content and source are required.")])
                
                db = self._get_db()
                
                # WP-06 Shared Evidence Ingestion Pipeline
                msg_data = {
                    "project_path": project_path,
                    "content": content,
                    "metadata": {
                        "source": source,
                        "mcp_client": self.client_id
                    }
                }
                
                success, result = await ingest_class1_evidence(
                    memory_db=db,
                    msg_version=1,
                    msg_id=event_id,
                    msg_ts=msg_ts,
                    msg_type="mcp_evidence",
                    msg_data=msg_data
                )
                
                if not success:
                    error_msg = result.get("error", "unknown_error")
                    if error_msg == "event_id_payload_conflict":
                        error_msg = "Duplicate event ID conflict with different payload."
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text=f"Error: {error_msg}")])
                
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": result.get("status", "success"), "receipt_id": result.get("receipt_id"), "event_id": event_id}) )])


            elif name == "request_capsule_preview":
                from vidurai.daemon.capsules.models import CapsuleCategory
                from vidurai.daemon.capsules.service import CapsuleService
                
                task = args.get("task")
                cats = args.get("requested_categories", [])
                max_items = args.get("max_items", 50)
                
                if not task:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: task is required.")])
                    
                requested = []
                for c in cats:
                    try:
                        requested.append(CapsuleCategory(c))
                    except ValueError:
                        return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text=f"Error: Invalid category {c}.")])
                        
                db = self._get_db()
                project_id = db.get_or_create_project(project_path)
                with db.get_connection_for_reading() as conn:
                    row = conn.execute("SELECT project_uuid FROM projects WHERE id = ?", (project_id,)).fetchone()
                
                if not row:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Project not found.")])
                    
                service = CapsuleService(db)
                capsule = service.generate_preview(
                    client_id=self.client_id,
                    project_uuid=row[0],
                    branch=None,
                    task=task,
                    requested_categories=requested,
                    max_items=max_items,
                    project_path=project_path
                )
                
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": "preview_ready", "capsule_id": capsule.capsule_id}))])
                
            elif name == "get_capsule_status":
                from vidurai.daemon.capsules.service import CapsuleService
                capsule_id = args.get("capsule_id")
                if not capsule_id:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: capsule_id is required.")])
                    
                db = self._get_db()
                service = CapsuleService(db)
                capsule = service.get_capsule(capsule_id)
                
                if not capsule or capsule.client_id != self.client_id:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Capsule not found.")])
                    
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": capsule.status.value, "capsule": capsule.to_dict()}))])
                
            elif name == "approve_capsule":
                from vidurai.daemon.capsules.service import CapsuleService
                capsule_id = args.get("capsule_id")
                if not capsule_id:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: capsule_id is required.")])
                    
                db = self._get_db()
                service = CapsuleService(db)
                ok = service.approve_capsule(self.client_id, capsule_id, project_path=project_path)
                
                if not ok:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Cannot approve capsule.")])
                    
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": "approved"}))])
                
            elif name == "reject_capsule":
                from vidurai.daemon.capsules.service import CapsuleService
                capsule_id = args.get("capsule_id")
                if not capsule_id:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: capsule_id is required.")])
                    
                db = self._get_db()
                service = CapsuleService(db)
                ok = service.reject_capsule(self.client_id, capsule_id)
                
                if not ok:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Cannot reject capsule.")])
                    
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps({"status": "rejected"}))])
                
            elif name == "consume_capsule":
                from vidurai.daemon.capsules.service import CapsuleService
                capsule_id = args.get("capsule_id")
                if not capsule_id:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: capsule_id is required.")])
                    
                db = self._get_db()
                service = CapsuleService(db)
                capsule = service.consume_capsule(self.client_id, capsule_id, project_path=project_path)
                
                if not capsule:
                    return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="Error: Cannot consume capsule. It may not be approved or belongs to another client.")])
                    
                return types.CallToolResult(is_error=False, content=[types.TextContent(type="text", text=json.dumps(capsule.to_dict()))])

            else:
                return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text=f"Error: Unknown tool '{name}'.")])
                
        except Exception as e:
            logger.error(f"Error calling tool {name}: {e}")
            return types.CallToolResult(is_error=True, content=[types.TextContent(type="text", text="An internal error occurred during tool execution.")])

    async def run(self):
        """Run the MCP stdio server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, self.server.create_initialization_options())
