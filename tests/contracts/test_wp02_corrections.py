import sys
import pytest
import uuid
import json
import asyncio
import os
import sqlite3
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Removed broad sys.modules MagicMocks that break Python 3.12 typing evaluation.

from vidurai.daemon.ipc.server import IPCMessage
from vidurai.daemon.ipc.validation import validate_class1_evidence, normalize_aliases
from vidurai.daemon.server import _handle_class1_evidence, handle_ipc_message
import vidurai.daemon.server as server_module
from vidurai.storage.database import MemoryDatabase, SalienceLevel

# -----------------------------------------------------------------------------
# Real Isolated DB Testing
# -----------------------------------------------------------------------------

class TestContext:
    def __init__(self):
        self.db_path = f"/tmp/vidurai_test_wp02_{uuid.uuid4().hex}.db"
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.db = MemoryDatabase(db_path=Path(self.db_path))
        server_module.memory_db = self.db
        server_module.context_mediator = MagicMock()
        server_module.context_mediator.whisperer = MagicMock()
        server_module.error_watcher = MagicMock()
        server_module.memory_store = MagicMock()
        server_module.vismriti_brain = MagicMock()
        server_module.watched_projects = []
        server_module.metrics = {"changes_detected": 0, "contexts_served": 0, "started_at": "2026-01-01T00:00:00"}
        server_module.context_builder = MagicMock()
        # Mock background task to do nothing
        server_module._process_receipt_async = AsyncMock()
        
    def get_counts(self):
        conn = self.db.get_connection_for_reading()
        r = conn.execute("SELECT COUNT(*) FROM event_receipts").fetchone()[0]
        m = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        f = conn.execute("SELECT COUNT(*) FROM memories_fts").fetchone()[0]
        conn.close()
        return r, m, f
        
    def cleanup(self):
        try:
            self.db.close()
        except:
            pass
            
        if os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except:
                pass

def test_non_severe_diagnostic():
    asyncio.run(_check_test_non_severe_diagnostic())

async def _check_test_non_severe_diagnostic():
    ctx = TestContext()
    # Severity 2
    msg = IPCMessage.from_json({"v": 1, "type": "diagnostic", "ts": 123, "id": str(uuid.uuid4()), "data": {"sev": 2, "msg": "test", "file": "a.py"}})
    res = await handle_ipc_message(MagicMock(), msg)
    assert res.ok
    r, m, f = ctx.get_counts()
    assert r == 0
    assert m == 0
    assert f == 0
    
    # Severity 1 (Severe)
    msg = IPCMessage.from_json({"v": 1, "type": "diagnostic", "ts": 123, "id": str(uuid.uuid4()), "data": {"sev": 1, "msg": "test", "file": "a.py"}})
    res = await handle_ipc_message(MagicMock(), msg)
    assert res.ok
    r, m, f = ctx.get_counts()
    assert r == 1
    ctx.cleanup()

def test_class2_class3_exclusion():
    asyncio.run(_check_test_class2_class3_exclusion())

async def _check_test_class2_class3_exclusion():
    ctx = TestContext()
    msgs = [
        IPCMessage.from_json({"v": 1, "type": "recall", "ts": 123, "data": {"query": "test"}}),
        IPCMessage.from_json({"v": 1, "type": "ping", "ts": 123, "data": {}})
    ]
    for msg in msgs:
        await handle_ipc_message(MagicMock(), msg)
    r, m, f = ctx.get_counts()
    assert r == 0
    assert m == 0
    assert f == 0
    ctx.cleanup()

def test_alias_canonical_equivalence():
    asyncio.run(_check_test_alias_canonical_equivalence())

async def _check_test_alias_canonical_equivalence():
    ctx = TestContext()
    event_id = str(uuid.uuid4())
    
    # Alias
    msg1 = IPCMessage.from_json({"v": 1, "type": "terminal_command", "ts": 123, "id": event_id, "data": {"cmd": "pytest", "project_path": "/a", "out": "test"}})
    res1 = await handle_ipc_message(MagicMock(), msg1)
    
    r1, m1, f1 = ctx.get_counts()
    assert r1 == 1
    
    # Canonical equivalent
    msg2 = IPCMessage.from_json({"v": 1, "type": "terminal", "ts": 123, "id": event_id, "data": {"command": "pytest", "project_path": "/a", "output": "test"}})
    res2 = await handle_ipc_message(MagicMock(), msg2)
    
    r2, m2, f2 = ctx.get_counts()
    assert r2 == 1  # Should hit duplicate, no new receipt
    assert res2.data.get('status') == 'duplicate'
    ctx.cleanup()

def test_real_unique_index_behaviour():
    asyncio.run(_check_test_real_unique_index_behaviour())

async def _check_test_real_unique_index_behaviour():
    ctx = TestContext()
    event_id = str(uuid.uuid4())
    
    msg1 = IPCMessage.from_json({"v": 1, "type": "file_edit", "ts": 123, "id": event_id, "data": {"project_path": "/a", "file": "b", "change": "c"}})
    res1 = await _handle_class1_evidence(msg1, msg1.type, msg1.data)
    
    # Attempt same event ID, same payload
    msg2 = IPCMessage.from_json({"v": 1, "type": "file_edit", "ts": 123, "id": event_id, "data": {"project_path": "/a", "file": "b", "change": "c"}})
    res2 = await _handle_class1_evidence(msg2, msg2.type, msg2.data)
    assert res2.data.get('status') == 'duplicate'
    assert ctx.get_counts()[0] == 1
    
    # Attempt same event ID, different payload
    msg3 = IPCMessage.from_json({"v": 1, "type": "file_edit", "ts": 123, "id": event_id, "data": {"project_path": "/a", "file": "b", "change": "d"}})
    res3 = await _handle_class1_evidence(msg3, msg3.type, msg3.data)
    assert res3.error == "event_id_payload_conflict"
    assert res3.data.get('retryable') is False
    assert ctx.get_counts()[0] == 1
    ctx.cleanup()

def test_atomic_rollback():
    ctx = TestContext()
    # Insert a receipt
    conn = ctx.db.get_connection_for_reading()
    conn.execute("INSERT INTO event_receipts (receipt_id, event_id, event_type, payload_hash, payload_json, status, received_at) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                 ('r1', 'e1', 'file_edit', 'hash1', '{}', 'recorded', 0))
    conn.commit()
    conn.close()
    
    # Drop the memories table to force an INSERT error
    ctx.db._enqueue("DROP TABLE memories", []).result()
    
    try:
        ctx.db.process_memory_from_receipt('r1', '/a', 'verbatim', 'gist', SalienceLevel.HIGH, 'file_edit', '/b', None, [], None, None)
    except Exception:
        pass
        
    # Since memories table is dropped, we can't count it. But we can count FTS and receipts.
    conn = ctx.db.get_connection_for_reading()
    f = conn.execute("SELECT COUNT(*) FROM memories_fts").fetchone()[0]
    status = conn.execute("SELECT status FROM event_receipts WHERE receipt_id='r1'").fetchone()[0]
    conn.close()
    
    assert f == 0
    assert status == 'recorded'
    ctx.cleanup()

def test_live_server_route():
    asyncio.run(_check_test_live_server_route())

async def _check_test_live_server_route():
    ctx = TestContext()
    msg = IPCMessage.from_json({"v": 1, "type": "file_edit", "ts": 123, "id": str(uuid.uuid4()), "data": {"project_path": "/a", "file": "b", "change": "c"}})
    res = await handle_ipc_message(MagicMock(), msg)
    assert res.ok
    assert ctx.get_counts()[0] == 1
    ctx.cleanup()
    
def test_durable_failure():
    asyncio.run(_check_test_durable_failure())

async def _check_test_durable_failure():
    ctx = TestContext()
    ctx.db.insert_event_receipt = MagicMock(return_value=False)
    
    msg = IPCMessage.from_json({"v": 1, "type": "file_edit", "ts": 123, "id": str(uuid.uuid4()), "data": {"project_path": "/a", "file": "b", "change": "c"}})
    res = await _handle_class1_evidence(msg, msg.type, msg.data)
    
    assert not res.ok
    assert res.error == "internal_durable_write_failure"
    assert res.data['retryable'] is True
    assert ctx.get_counts()[0] == 0
    ctx.cleanup()

if __name__ == "__main__":
    print("Running WP-02 Permanent Tests...")
    test_non_severe_diagnostic()
    test_class2_class3_exclusion()
    test_alias_canonical_equivalence()
    test_real_unique_index_behaviour()
    test_atomic_rollback()
    test_live_server_route()
    test_durable_failure()
    print("All permanent tests passed!")

def test_framing_compliance():
    asyncio.run(_check_test_framing_compliance())

async def _check_test_framing_compliance():
    from vidurai.daemon.ipc.server import IPCClientConnection, IPCResponse
    import asyncio
    
    reader = MagicMock()
    writer = MagicMock()
    
    # We will capture responses sent via send()
    sent_responses = []
    async def mock_send(self_conn, resp):
        sent_responses.append(resp)
        return True
        
    handler = AsyncMock(return_value=IPCResponse(type="ack", ok=True))
    
    conn = IPCClientConnection(reader, writer, handler)
    # Monkeypatch send to capture output
    conn.send = mock_send.__get__(conn)
    
    # 1. Truncated frame (no newline)
    conn.buffer += '{"v":1,"type":"file_edit"'
    await conn._process_buffer()
    
    assert len(sent_responses) == 0, "Truncated frame should not produce any response"
    assert handler.call_count == 0, "Truncated frame should not reach handler"
    
    # 2. Complete malformed JSON
    conn.buffer += '\ninvalid-json\n'
    await conn._process_buffer()
    
    assert handler.call_count == 0, "No valid JSON was sent"
    
    # Let's check exactly what happened:
    # First line: '{"v":1,"type":"file_edit"\ninvalid-json\n' -> Split by '\n':
    # line 1: '{"v":1,"type":"file_edit"' -> json.JSONDecodeError -> 'malformed_json'
    # line 2: 'invalid-json' -> json.JSONDecodeError -> 'malformed_json'
    # Wait, the first line is valid JSON? No, it's truncated so json.loads fails.
    
    assert len(sent_responses) == 2
    assert sent_responses[0].error == "malformed_json"
    assert sent_responses[1].error == "malformed_json"
