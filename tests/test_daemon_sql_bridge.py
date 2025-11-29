#!/usr/bin/env python3
"""
Test script for Daemon ↔ SQL Bridge integration
Tests that daemon can pull long-term memory hints from SQL
"""

import sys
import os
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "vidurai-daemon"))

def setup_test_memories():
    """
    Create test memories in SQL that daemon can query
    """
    print("=" * 60)
    print("📝 Setting Up Test Memories in SQL")
    print("=" * 60)
    print()

    from vidurai.storage.database import MemoryDatabase, SalienceLevel

    db = MemoryDatabase()
    project_path = "/home/user/vidurai/test-daemon-bridge"

    # Create HIGH salience memories that should appear in hints
    print("Creating HIGH salience memories...")

    test_memories = [
        {
            'verbatim': 'Fixed AuthenticationError in auth.py by regenerating JWT secret key',
            'gist': 'Fixed AuthenticationError in auth.py with new JWT secret',
            'salience': SalienceLevel.HIGH,
            'event_type': 'bugfix',
            'file_path': '/home/user/vidurai/test-daemon-bridge/auth.py',
            'tags': ['bug_fix', 'auth'],
        },
        {
            'verbatim': 'Database migration failed with IntegrityError - foreign key constraint',
            'gist': 'Database migration failed with IntegrityError',
            'salience': SalienceLevel.HIGH,
            'event_type': 'error',
            'file_path': '/home/user/vidurai/test-daemon-bridge/migrations/001.py',
            'tags': ['database', 'migration'],
        },
        {
            'verbatim': 'Successfully implemented user authentication with OAuth2',
            'gist': 'Implemented OAuth2 authentication',
            'salience': SalienceLevel.CRITICAL,
            'event_type': 'feature',
            'file_path': '/home/user/vidurai/test-daemon-bridge/auth.py',
            'tags': ['feature', 'auth', 'oauth'],
        },
    ]

    for mem in test_memories:
        db.store_memory(
            project_path=project_path,
            verbatim=mem['verbatim'],
            gist=mem['gist'],
            salience=mem['salience'],
            event_type=mem['event_type'],
            file_path=mem.get('file_path'),
            line_number=mem.get('line_number'),
            tags=mem.get('tags'),
            retention_days=90
        )

    print(f"✅ Created {len(test_memories)} HIGH/CRITICAL salience memories")
    print()

    # Also create some LOW salience memories (should NOT appear in hints)
    print("Creating LOW salience memories (should be filtered out)...")

    low_memories = [
        {
            'verbatim': 'Updated comment in utils.py',
            'gist': 'Updated comment',
            'salience': SalienceLevel.LOW,
            'event_type': 'refactor',
        },
        {
            'verbatim': 'Debug log output',
            'gist': 'Debug log',
            'salience': SalienceLevel.NOISE,
            'event_type': 'system_log',
        },
    ]

    for mem in low_memories:
        db.store_memory(
            project_path=project_path,
            verbatim=mem['verbatim'],
            gist=mem['gist'],
            salience=mem['salience'],
            event_type=mem['event_type'],
            file_path=mem.get('file_path'),
            tags=mem.get('tags'),
            retention_days=7
        )

    print(f"✅ Created {len(low_memories)} LOW/NOISE salience memories")
    print()


def test_memory_bridge_direct():
    """
    Test MemoryBridge directly (without full daemon)
    """
    print("=" * 60)
    print("🧪 TEST: Memory Bridge Direct Access")
    print("=" * 60)
    print()

    from vidurai.storage.database import MemoryDatabase
    from intelligence.memory_bridge import MemoryBridge

    # Initialize
    db = MemoryDatabase()
    bridge = MemoryBridge(
        db=db,
        max_memories=3,
        min_salience="HIGH"
    )

    project_path = "/home/user/vidurai/test-daemon-bridge"

    # Test 1: Get hints for debugging (similar error)
    print("Test 1: Get hints for debugging AuthenticationError...")
    hints = bridge.get_relevant_hints(
        current_project=project_path,
        current_error="AuthenticationError: JWT token invalid",
        user_state='debugging'
    )

    print(f"  Found {len(hints)} hints:")
    for i, hint in enumerate(hints, 1):
        print(f"    {i}. [{hint['salience']}] {hint['gist'][:60]}...")
    print()

    # Test 2: Get hints for file work
    print("Test 2: Get hints when working on auth.py...")
    hints = bridge.get_relevant_hints(
        current_project=project_path,
        current_file="/home/user/vidurai/test-daemon-bridge/auth.py",
        user_state='building'
    )

    print(f"  Found {len(hints)} hints:")
    for i, hint in enumerate(hints, 1):
        print(f"    {i}. [{hint['salience']}] {hint['gist'][:60]}...")
    print()

    # Test 3: General high-salience hints
    print("Test 3: Get general high-salience hints...")
    hints = bridge.get_relevant_hints(
        current_project=project_path,
        user_state='building'
    )

    print(f"  Found {len(hints)} hints:")
    for i, hint in enumerate(hints, 1):
        print(f"    {i}. [{hint['salience']}] {hint['gist'][:60]}...")
    print()

    # Test 4: Format hints for context
    print("Test 4: Format hints for natural language context...")
    if hints:
        formatted = bridge.format_hints_for_context(hints)
        print(f"  Formatted: {formatted}")
    print()


def test_context_mediator_with_sql():
    """
    Test ContextMediator with SQL bridge integration
    """
    print("=" * 60)
    print("🧪 TEST: ContextMediator with SQL Hints")
    print("=" * 60)
    print()

    from intelligence.context_mediator import ContextMediator

    # Initialize context mediator (should auto-init memory bridge)
    mediator = ContextMediator()

    # Check if memory bridge initialized
    if mediator.memory_bridge:
        print("✅ Memory bridge initialized successfully")
        print()

        # Simulate daemon state
        mediator.recent_errors.append({
            'output': 'AuthenticationError: Invalid JWT token',
            'time': datetime.now().timestamp()
        })

        mediator.recent_files_changed.append({
            'file': '/home/user/vidurai/test-daemon-bridge/auth.py',
            'time': datetime.now().timestamp()
        })

        mediator.user_state = 'debugging'

        # Prepare context
        print("Preparing context for AI with SQL hints...")
        context = mediator.prepare_context_for_ai(
            user_prompt="How do I fix this AuthenticationError?",
            ai_platform="Claude"
        )

        print()
        print("Generated Context:")
        print("-" * 60)
        print(context)
        print("-" * 60)
        print()

        # Check if SQL hints are included
        if "From past experience" in context or "📜" in context:
            print("✅ SQL hints successfully included in context!")
        else:
            print("⚠️  SQL hints not found in context (may be expected if no relevant hints)")

    else:
        print("❌ Memory bridge NOT initialized")
        print("   This is OK - daemon will work without SQL")

    print()


def test_fail_safe_without_sql():
    """
    Test that daemon works without SQL database
    """
    print("=" * 60)
    print("🧪 TEST: Fail-Safe Operation Without SQL")
    print("=" * 60)
    print()

    # Temporarily break SQL access
    import vidurai.storage.database as db_module
    original_db = db_module.MemoryDatabase

    # Mock broken database
    class BrokenDatabase:
        def __init__(self):
            raise Exception("Database unavailable!")

    db_module.MemoryDatabase = BrokenDatabase

    try:
        from intelligence.context_mediator import ContextMediator

        # This should NOT crash even with broken database
        mediator = ContextMediator()

        if mediator.memory_bridge is None:
            print("✅ Context mediator initialized without SQL (fail-safe working)")
        else:
            print("❌ Memory bridge somehow initialized despite broken DB")

        # Test that context preparation still works
        context = mediator.prepare_context_for_ai(
            user_prompt="Test prompt",
            ai_platform="Claude"
        )

        if context:
            print("✅ Context preparation works without SQL")
        else:
            print("❌ Context preparation failed")

    finally:
        # Restore original database
        db_module.MemoryDatabase = original_db

    print()


if __name__ == "__main__":
    try:
        print()
        print("🚀 DAEMON ↔ SQL BRIDGE TEST SUITE")
        print()

        # Setup
        setup_test_memories()

        # Run tests
        test_memory_bridge_direct()
        test_context_mediator_with_sql()
        test_fail_safe_without_sql()

        print()
        print("=" * 60)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 60)
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
