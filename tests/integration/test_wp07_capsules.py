import pytest
import asyncio
import uuid
import os
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from vidurai.storage.database import MemoryDatabase, SalienceLevel
from vidurai.daemon.capsules.models import CapsuleCategory, CapsuleStatus
from vidurai.daemon.capsules.service import CapsuleService

@pytest.fixture
def db_and_dir():
    with TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "vidurai.db")
        db = MemoryDatabase(db_path)
        yield db, tmpdir

def test_capsule_generation_and_consumption(db_and_dir):
    db, tmpdir = db_and_dir
    project_id = db.get_or_create_project(tmpdir, identity={"project_uuid": str(uuid.uuid4())})
    with db.get_connection_for_reading() as conn:
        project_uuid = conn.execute("SELECT project_uuid FROM projects WHERE id = ?", (project_id,)).fetchone()[0]

    # Insert some memories directly
    # high salience -> DECISION
    # low salience -> WORKING
    # tags 'contradict' -> CONTRADICTION
    # tags 'unresolved' -> UNRESOLVED
    
    db.store_memory(tmpdir, "test1", "gist1", SalienceLevel.HIGH, "test_event")
    db.store_memory(tmpdir, "test2", "gist2", SalienceLevel.LOW, "test_event")
    db.store_memory(tmpdir, "test3", "gist3", SalienceLevel.MEDIUM, "test_event", tags=["contradict"])
    db.store_memory(tmpdir, "test4", "gist4", SalienceLevel.MEDIUM, "test_event", tags=["unresolved"])
    db.store_memory(tmpdir, "test5", "gist5", SalienceLevel.MEDIUM, "test_event") # EVIDENCE
    
    service = CapsuleService(db)
    
    # 1. Preview
    capsule = service.generate_preview(
        client_id="client1",
        project_uuid=project_uuid,
        branch="main",
        task="Test task",
        requested_categories=[CapsuleCategory.DECISION, CapsuleCategory.WORKING, CapsuleCategory.CONTRADICTION, CapsuleCategory.UNRESOLVED, CapsuleCategory.EVIDENCE],
        max_items=3,
        project_path=tmpdir
    )
    
    assert capsule.status == CapsuleStatus.PREVIEW
    assert len(capsule.items) == 3
    assert len(capsule.excluded_items) == 2 # 5 total matching, max 3
    
    # 2. Cannot consume without approval
    res = service.consume_capsule("client1", capsule.capsule_id)
    assert res is None
    
    # 3. Reject
    assert service.reject_capsule("client1", capsule.capsule_id)
    capsule = service.get_capsule(capsule.capsule_id)
    assert capsule.status == CapsuleStatus.REJECTED
    
    # 4. Generate another preview and approve
    capsule2 = service.generate_preview(
        client_id="client1",
        project_uuid=project_uuid,
        branch="main",
        task="Test task 2",
        requested_categories=[CapsuleCategory.DECISION],
        max_items=50,
        project_path=tmpdir
    )
    assert service.approve_capsule("client1", capsule2.capsule_id)
    
    # 5. Consume
    consumed = service.consume_capsule("client1", capsule2.capsule_id)
    assert consumed is not None
    assert consumed.delivery_count == 1
    assert len(consumed.items) == 1
    assert consumed.items[0].category == CapsuleCategory.DECISION
    
    # 6. Cannot consume from other client
    assert service.consume_capsule("client2", capsule2.capsule_id) is None
