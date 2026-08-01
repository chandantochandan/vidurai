import pytest
import asyncio
import os
import sys
import subprocess
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from vidurai.daemon.mcp.gateway import MCPGateway
import mcp.types as types
from vidurai.daemon.mcp.permissions import ClientAuthenticator, PermissionManager, Permission
from vidurai.storage.database import MemoryDatabase, SalienceLevel
from vidurai.daemon.capsules.models import CapsuleCategory, CapsuleStatus

@pytest.mark.anyio
async def test_mcp_capsule_sensitive_flow():
    with TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "memory.db")
        db = MemoryDatabase(db_path)
        import uuid
        project_uuid = str(uuid.uuid4())
        db.get_or_create_project(tmpdir, identity={"project_uuid": project_uuid})

        # Init git
        subprocess.run(["git", "init"], cwd=tmpdir, check=True, capture_output=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", "init"], cwd=tmpdir, check=True, capture_output=True)
        
        # Store memories
        db.store_memory(tmpdir, "decision1", "Make this architecture change", SalienceLevel.HIGH, "test", tags=["decision"])
        db.store_memory(tmpdir, "working1", "doing some work", SalienceLevel.LOW, "test")

        # Setup Auth
        auth = ClientAuthenticator(Path(tmpdir))
        token1 = auth.generate_credential("client1")
        token2 = auth.generate_credential("client2")

        # Setup Permissions
        pm = PermissionManager(Path(tmpdir))
        pm.grant("client1", Permission.READ_ONLY)
        # client1 doesn't have sensitive-read

        gateway = MCPGateway(client_id="client1", token=token1, db_path=db_path, config_dir=Path(tmpdir))

        # 1. client1 tries to request a preview with DECISION (sensitive) -> should fail
        req_preview = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="request_capsule_preview",
                arguments={
                    "task": "architecture",
                    "requested_categories": ["decision", "working"],
                    "project_path": tmpdir
                }
            )
        )
        res1 = await gateway.call_tool(req_preview)
        assert res1.is_error == True
        assert "sensitive-read" in res1.content[0].text

        # 2. Grant sensitive-read and try again -> should succeed
        pm.grant("client1", Permission.SENSITIVE_READ)
        res2 = await gateway.call_tool(req_preview)
        assert res2.is_error == False
        data = json.loads(res2.content[0].text)
        assert data["status"] == "preview_ready"
        capsule_id = data["capsule_id"]

        # 3. Use the CLI commands (like VS Code does) to approve
        # First check list-pending
        res_list = subprocess.run([".venv/bin/vidurai", "capsule", "list-pending"], check=True, capture_output=True, text=True, env={**os.environ, "VIDURAI_HOME": tmpdir})
        assert capsule_id in res_list.stdout

        # Approve via CLI
        res_approve = subprocess.run([".venv/bin/vidurai", "capsule", "approve", capsule_id, "client1"], check=True, capture_output=True, text=True, env={**os.environ, "VIDURAI_HOME": tmpdir})
        assert "Approved." in res_approve.stdout

        # 4. client2 tries to consume -> should fail (not their capsule)
        gateway2 = MCPGateway(client_id="client2", token=token2, db_path=db_path, config_dir=Path(tmpdir))
        req_consume2 = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="consume_capsule",
                arguments={"capsule_id": capsule_id, "project_path": tmpdir}
            )
        )
        res3 = await gateway2.call_tool(req_consume2)
        assert res3.is_error == True
        assert "another client" in res3.content[0].text

        # 5. client1 consumes -> should succeed
        req_consume1 = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="consume_capsule",
                arguments={"capsule_id": capsule_id, "project_path": tmpdir}
            )
        )
        res4 = await gateway.call_tool(req_consume1)
        assert res4.is_error == False
        capsule_data = json.loads(res4.content[0].text)
        assert len(capsule_data["items"]) == 1 # only decision matches task (working1 doesn't have "architecture")
        
        # 6. Test VS Code Reject Flow
        res5 = await gateway.call_tool(req_preview)
        capsule_id2 = json.loads(res5.content[0].text)["capsule_id"]
        
        res_reject = subprocess.run([".venv/bin/vidurai", "capsule", "reject", capsule_id2, "client1"], check=True, capture_output=True, text=True, env={**os.environ, "VIDURAI_HOME": tmpdir})
        assert "Rejected." in res_reject.stdout
        
        req_consume_rejected = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name="consume_capsule",
                arguments={"capsule_id": capsule_id2, "project_path": tmpdir}
            )
        )
        res6 = await gateway.call_tool(req_consume_rejected)
        assert res6.is_error == True
