#!/usr/bin/env python3
"""
Test suite for Phase 5.1: Audience Gists Storage Layer
Tests schema migration and database API methods
"""

import sys
import os
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

def test_schema_migration():
    """Test that audience_gists table is auto-created"""
    print("=" * 70)
    print("🧪 TEST 1: Schema Migration")
    print("=" * 70)
    print()

    from vidurai.storage.database import MemoryDatabase

    # Create new database (will trigger migration)
    db = MemoryDatabase()

    cursor = db.conn.cursor()

    # Check that audience_gists table exists
    tables = cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='audience_gists'
    """).fetchall()

    print(f"audience_gists table exists: {len(tables) > 0}")
    assert len(tables) > 0, "audience_gists table not created"

    # Check schema version
    version = cursor.execute("""
        SELECT value FROM metadata WHERE key='schema_version'
    """).fetchone()

    print(f"Schema version: {version['value']}")
    assert version['value'] == '2', "Schema not migrated to v2"

    # Check table structure
    schema = cursor.execute("PRAGMA table_info(audience_gists)").fetchall()
    columns = {row[1]: row[2] for row in schema}

    print(f"\naudience_gists columns:")
    for col, typ in columns.items():
        print(f"  {col}: {typ}")

    assert 'memory_id' in columns, "memory_id column missing"
    assert 'audience' in columns, "audience column missing"
    assert 'gist' in columns, "gist column missing"

    # Check indexes
    indexes = cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='index' AND tbl_name='audience_gists'
    """).fetchall()

    print(f"\nIndexes: {[idx[0] for idx in indexes]}")
    assert len(indexes) >= 2, "Expected at least 2 indexes"

    print("\n✅ PASSED: Schema migration successful\n")


def test_store_audience_gists():
    """Test storing audience gists"""
    print("=" * 70)
    print("🧪 TEST 2: Store Audience Gists")
    print("=" * 70)
    print()

    from vidurai.storage.database import MemoryDatabase, SalienceLevel

    db = MemoryDatabase()

    # Create a test memory first
    memory_id = db.store_memory(
        project_path="/test/phase5",
        verbatim="Fixed authentication bug in JWT validation",
        gist="Fixed auth bug",
        salience=SalienceLevel.HIGH,
        event_type="bugfix"
    )

    print(f"Created memory ID: {memory_id}")

    # Store audience gists
    gists = {
        "developer": "Fixed JWT token validation in auth middleware",
        "ai": "Pattern: Authentication error resolution",
        "manager": "Auth system stabilized",
        "personal": "I learned how JWT tokens work"
    }

    db.store_audience_gists(memory_id, gists)
    print(f"✅ Stored {len(gists)} audience gists")

    # Verify they were stored
    cursor = db.conn.cursor()
    stored = cursor.execute("""
        SELECT audience, gist FROM audience_gists WHERE memory_id = ?
    """, (memory_id,)).fetchall()

    print(f"\nStored gists in database:")
    for row in stored:
        print(f"  {row['audience']}: {row['gist'][:50]}...")

    assert len(stored) == 4, f"Expected 4 gists, got {len(stored)}"

    print("\n✅ PASSED: Audience gists stored successfully\n")


def test_upsert_audience_gists():
    """Test UPSERT behavior (update existing gists)"""
    print("=" * 70)
    print("🧪 TEST 3: UPSERT Behavior")
    print("=" * 70)
    print()

    from vidurai.storage.database import MemoryDatabase, SalienceLevel

    db = MemoryDatabase()

    # Create a test memory
    memory_id = db.store_memory(
        project_path="/test/phase5",
        verbatim="Test memory",
        gist="Test",
        salience=SalienceLevel.MEDIUM,
        event_type="test"
    )

    # Store initial gists
    gists_v1 = {
        "developer": "Version 1",
        "ai": "Version 1"
    }
    db.store_audience_gists(memory_id, gists_v1)
    print("Stored version 1 gists")

    # Update with new gists (UPSERT)
    gists_v2 = {
        "developer": "Version 2 - Updated",
        "ai": "Version 2 - Updated",
        "manager": "New audience"
    }
    db.store_audience_gists(memory_id, gists_v2)
    print("Stored version 2 gists (UPSERT)")

    # Verify
    cursor = db.conn.cursor()
    final = cursor.execute("""
        SELECT audience, gist FROM audience_gists WHERE memory_id = ?
    """, (memory_id,)).fetchall()

    print(f"\nFinal gists:")
    for row in final:
        print(f"  {row['audience']}: {row['gist']}")

    assert len(final) == 3, f"Expected 3 gists, got {len(final)}"

    # Check that developer was updated (not duplicated)
    dev_gist = [r['gist'] for r in final if r['audience'] == 'developer'][0]
    assert "Version 2" in dev_gist, "Developer gist not updated"

    print("\n✅ PASSED: UPSERT works correctly\n")


def test_get_audience_gists():
    """Test retrieving audience gists"""
    print("=" * 70)
    print("🧪 TEST 4: Get Audience Gists")
    print("=" * 70)
    print()

    from vidurai.storage.database import MemoryDatabase, SalienceLevel

    db = MemoryDatabase()

    # Create a test memory with gists
    memory_id = db.store_memory(
        project_path="/test/phase5",
        verbatim="Test memory",
        gist="Test",
        salience=SalienceLevel.MEDIUM,
        event_type="test"
    )

    gists = {
        "developer": "Dev version",
        "ai": "AI version",
        "manager": "Manager version",
        "personal": "Personal version"
    }
    db.store_audience_gists(memory_id, gists)

    # Test 1: Get all gists
    all_gists = db.get_audience_gists(memory_id)
    print(f"Get all gists: {len(all_gists)} returned")
    assert len(all_gists) == 4, "Should return all 4 gists"
    assert all_gists['developer'] == "Dev version", "Developer gist mismatch"

    # Test 2: Get specific audiences
    dev_ai = db.get_audience_gists(memory_id, audiences=["developer", "ai"])
    print(f"Get developer+ai: {len(dev_ai)} returned")
    assert len(dev_ai) == 2, "Should return only 2 gists"
    assert "developer" in dev_ai and "ai" in dev_ai, "Wrong audiences returned"

    # Test 3: Get single audience
    manager = db.get_audience_gists(memory_id, audiences=["manager"])
    print(f"Get manager: {len(manager)} returned")
    assert len(manager) == 1, "Should return 1 gist"
    assert manager['manager'] == "Manager version", "Manager gist mismatch"

    # Test 4: Non-existent memory (fail-safe)
    empty = db.get_audience_gists(999999)
    print(f"Get non-existent: {len(empty)} returned")
    assert len(empty) == 0, "Should return empty dict"

    print("\n✅ PASSED: Audience gist retrieval works\n")


def test_cascade_delete():
    """Test that deleting a memory cascades to audience_gists"""
    print("=" * 70)
    print("🧪 TEST 5: CASCADE DELETE")
    print("=" * 70)
    print()

    from vidurai.storage.database import MemoryDatabase, SalienceLevel

    db = MemoryDatabase()

    # Create a test memory with gists
    memory_id = db.store_memory(
        project_path="/test/phase5",
        verbatim="Test memory for deletion",
        gist="Test",
        salience=SalienceLevel.MEDIUM,
        event_type="test"
    )

    gists = {
        "developer": "Dev",
        "ai": "AI",
        "manager": "Manager",
        "personal": "Personal"
    }
    db.store_audience_gists(memory_id, gists)

    # Verify gists exist
    before = db.get_audience_gists(memory_id)
    print(f"Before delete: {len(before)} gists")
    assert len(before) == 4, "Gists should exist"

    # Delete the memory
    cursor = db.conn.cursor()
    cursor.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    db.conn.commit()
    print(f"Deleted memory {memory_id}")

    # Verify gists are deleted (CASCADE)
    after = db.get_audience_gists(memory_id)
    print(f"After delete: {len(after)} gists")
    assert len(after) == 0, "Gists should be deleted via CASCADE"

    print("\n✅ PASSED: CASCADE DELETE works\n")


def test_unique_constraint():
    """Test UNIQUE constraint on (memory_id, audience)"""
    print("=" * 70)
    print("🧪 TEST 6: UNIQUE Constraint")
    print("=" * 70)
    print()

    from vidurai.storage.database import MemoryDatabase, SalienceLevel

    db = MemoryDatabase()

    # Create a test memory
    memory_id = db.store_memory(
        project_path="/test/phase5",
        verbatim="Test",
        gist="Test",
        salience=SalienceLevel.MEDIUM,
        event_type="test"
    )

    cursor = db.conn.cursor()

    # Insert first gist
    cursor.execute("""
        INSERT INTO audience_gists (memory_id, audience, gist)
        VALUES (?, 'developer', 'Version 1')
    """, (memory_id,))
    db.conn.commit()
    print("Inserted developer gist v1")

    # Try to insert duplicate (should fail without OR REPLACE)
    try:
        cursor.execute("""
            INSERT INTO audience_gists (memory_id, audience, gist)
            VALUES (?, 'developer', 'Version 2')
        """, (memory_id,))
        db.conn.commit()
        print("❌ FAILED: Duplicate insert should have raised error")
        assert False, "UNIQUE constraint not enforced"
    except Exception as e:
        print(f"✅ Duplicate rejected: {type(e).__name__}")
        db.conn.rollback()

    # But INSERT OR REPLACE should work (what we use in store_audience_gists)
    cursor.execute("""
        INSERT OR REPLACE INTO audience_gists (memory_id, audience, gist)
        VALUES (?, 'developer', 'Version 2')
    """, (memory_id,))
    db.conn.commit()
    print("INSERT OR REPLACE succeeded")

    # Verify only one row exists
    count = cursor.execute("""
        SELECT COUNT(*) FROM audience_gists
        WHERE memory_id = ? AND audience = 'developer'
    """, (memory_id,)).fetchone()[0]

    assert count == 1, "Should have exactly 1 row (updated, not duplicated)"

    print("\n✅ PASSED: UNIQUE constraint enforced\n")


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 5.1 TEST SUITE: Audience Gists Storage")
        print()

        test_schema_migration()
        test_store_audience_gists()
        test_upsert_audience_gists()
        test_get_audience_gists()
        test_cascade_delete()
        test_unique_constraint()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 5.1 TESTS PASSED")
        print("=" * 70)
        print()

    except AssertionError as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
