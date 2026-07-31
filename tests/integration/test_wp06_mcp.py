import pytest
import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from vidurai.daemon.mcp.permissions import PermissionManager, Permission
from vidurai.storage.database import MemoryDatabase
from vidurai.vismriti_memory import VismritiMemory

def test_permissions():
    with TemporaryDirectory() as tmpdir:
        pm = PermissionManager(Path(tmpdir))
        
        # Test default
        assert not pm.has_permission("clientA", Permission.READ_ONLY)
        
        # Test grant
        pm.grant("clientA", Permission.READ_ONLY)
        assert pm.has_permission("clientA", Permission.READ_ONLY)
        assert not pm.has_permission("clientA", Permission.MEMORY_MUTATION)
        
        # Test revoke
        pm.revoke("clientA", Permission.READ_ONLY)
        assert not pm.has_permission("clientA", Permission.READ_ONLY)
        
        # Test admin
        pm.grant("adminClient", Permission.ADMIN)
        assert pm.has_permission("adminClient", Permission.READ_ONLY)
        assert pm.has_permission("adminClient", Permission.MEMORY_MUTATION)
        
        # Test audit
        pm.audit("adminClient", "test_op", "/test/path", "admin", "granted", "test")
        
        audit_file = Path(tmpdir) / "mcp_audit.jsonl"
        assert audit_file.exists()
        with open(audit_file) as f:
            lines = f.readlines()
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["client_id"] == "adminClient"

@pytest.mark.anyio
async def test_mcp_gateway():
    from vidurai.daemon.mcp.gateway import MCPGateway
    import mcp.types as types
    
    with TemporaryDirectory() as tmpdir:
        # Set up a test DB
        db_path = os.path.join(tmpdir, "vidurai.db")
        db = MemoryDatabase(db_path)
        project_uuid = db.get_or_create_project(tmpdir)
        
        # Setup PM
        os.environ["HOME"] = tmpdir  # Hack for PermissionManager default
        gateway = MCPGateway(db_path=db_path)
        gateway.permission_manager = PermissionManager(Path(tmpdir))
        
        # List tools
        req_list = types.ListToolsRequest(method="tools/list")
        res_list = await gateway.list_tools(req_list)
        assert len(res_list.tools) == 3
        
        # Call tool without permission
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="get_project_context",
                arguments={"client_id": "test_client", "project_path": tmpdir}
            )
        )
        res = await gateway.call_tool(req)
        assert res.is_error
        assert "Permission denied" in res.content[0].text
        
        # Grant permission
        gateway.permission_manager.grant("test_client", Permission.READ_ONLY)
        
        # Call tool with permission
        res = await gateway.call_tool(req)
        assert not res.is_error
        data = json.loads(res.content[0].text)
        assert data["status"] == "active"
        
        # Test ambiguous path
        req_ambiguous = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="get_project_context",
                arguments={"client_id": "test_client", "project_path": "."}
            )
        )
        res_ambiguous = await gateway.call_tool(req_ambiguous)
        assert res_ambiguous.is_error
        assert "Ambiguous project scope" in res_ambiguous.content[0].text

        # Test evidence mutation denial
        req_mut = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="create_evidence",
                arguments={"client_id": "test_client", "project_path": tmpdir, "content": "hello", "source": "test"}
            )
        )
        res_mut = await gateway.call_tool(req_mut)
        assert res_mut.is_error
        assert "Permission denied" in res_mut.content[0].text
        
        # Grant mutation
        gateway.permission_manager.grant("test_client", Permission.EVIDENCE_MUTATION)
        res_mut2 = await gateway.call_tool(req_mut)
        assert not res_mut2.is_error
        data2 = json.loads(res_mut2.content[0].text)
        assert data2["status"] == "success"
        assert "memory_id" in data2
