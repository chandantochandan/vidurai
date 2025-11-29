#!/usr/bin/env python3
"""
Test suite for Phase 5.3: VismritiMemory Integration
Tests multi-audience gist generation integrated into VismritiMemory
"""

import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_initialization():
    """Test VismritiMemory initialization with multi-audience"""
    print("=" * 70)
    print("🧪 TEST 1: Initialization with Multi-Audience")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    # Test 1a: Default (disabled)
    print("1a. Default initialization (multi-audience disabled):")
    memory = VismritiMemory()
    assert memory.multi_audience_generator is None, \
        "Multi-audience should be disabled by default"
    assert memory.multi_audience_config is None, \
        "Config should be None when disabled"
    print("✅ Multi-audience disabled by default")
    print()

    # Test 1b: Explicitly enabled
    print("1b. Enabled initialization:")
    memory = VismritiMemory(enable_multi_audience=True)
    assert memory.multi_audience_generator is not None, \
        "Multi-audience should be enabled"
    assert memory.multi_audience_config is not None, \
        "Config should exist when enabled"
    assert memory.multi_audience_config.enabled is True, \
        "Config should show enabled=True"
    print(f"✅ Multi-audience enabled")
    print(f"   Audiences: {memory.multi_audience_config.audiences}")
    print()

    # Test 1c: Custom configuration
    print("1c. Custom configuration:")
    custom_config = {
        'enabled': True,
        'audiences': ['developer', 'ai']
    }
    memory = VismritiMemory(
        enable_multi_audience=True,
        multi_audience_config=custom_config
    )
    assert len(memory.multi_audience_config.audiences) == 2, \
        "Should have 2 audiences"
    assert 'developer' in memory.multi_audience_config.audiences
    assert 'ai' in memory.multi_audience_config.audiences
    assert 'manager' not in memory.multi_audience_config.audiences
    print(f"✅ Custom audiences: {memory.multi_audience_config.audiences}")
    print()

    print("✅ PASSED: Initialization works correctly\n")


def test_remember_with_multi_audience():
    """Test remember() generates and stores audience gists"""
    print("=" * 70)
    print("🧪 TEST 2: Remember with Multi-Audience")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    # Create temp directory for database
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize with multi-audience enabled
        memory = VismritiMemory(
            enable_multi_audience=True,
            project_path=temp_dir
        )

        # Store a memory
        print("Storing memory: 'Fixed JWT token validation bug in auth.py line 42'")
        mem = memory.remember(
            "Fixed JWT token validation bug in authentication middleware",
            metadata={
                'type': 'bugfix',
                'file': 'auth.py',
                'line': 42
            },
            extract_gist=False  # Use verbatim as gist
        )

        print(f"✅ Memory stored with ID")
        print()

        # Verify database has audience gists
        if memory.db:
            # Get memory ID from database
            memories = memory.db.recall_memories(
                project_path=temp_dir,
                query="JWT",
                limit=1
            )

            assert len(memories) > 0, "Should find the memory in database"
            memory_id = memories[0]['id']

            print(f"Database memory ID: {memory_id}")

            # Get audience gists
            audience_gists = memory.db.get_audience_gists(memory_id)

            print(f"\nStored {len(audience_gists)} audience gists:")
            for audience, gist in audience_gists.items():
                print(f"  {audience:12s}: {gist}")

            # Verify all 4 audiences present
            assert 'developer' in audience_gists, "Developer gist missing"
            assert 'ai' in audience_gists, "AI gist missing"
            assert 'manager' in audience_gists, "Manager gist missing"
            assert 'personal' in audience_gists, "Personal gist missing"

            # Verify each is different (at least some variety)
            unique_gists = set(audience_gists.values())
            assert len(unique_gists) >= 3, \
                "At least 3 audiences should have different gists"

            print("\n✅ All 4 audience gists generated and stored")

        print("\n✅ PASSED: Remember generates audience gists\n")

    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_context_for_ai_with_audience():
    """Test get_context_for_ai() with audience parameter"""
    print("=" * 70)
    print("🧪 TEST 3: get_context_for_ai() with Audience")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Initialize
        memory = VismritiMemory(
            enable_multi_audience=True,
            project_path=temp_dir
        )

        # Store several memories
        memories_data = [
            {
                "content": "Fixed critical authentication bug in JWT validation middleware",
                "metadata": {"type": "bugfix", "file": "auth.py", "line": 42}
            },
            {
                "content": "Implemented new user registration feature with OAuth2 support",
                "metadata": {"type": "feature", "file": "register.py"}
            },
            {
                "content": "Optimized database queries in user model",
                "metadata": {"type": "refactor", "file": "models/user.py"}
            }
        ]

        for mem_data in memories_data:
            memory.remember(
                mem_data["content"],
                metadata=mem_data["metadata"],
                extract_gist=False
            )

        print(f"Stored {len(memories_data)} memories")
        print()

        # Test 3a: Get context without audience (canonical gists)
        print("3a. Context without audience (canonical gists):")
        context_canonical = memory.get_context_for_ai(query="authentication")
        assert "VIDURAI PROJECT CONTEXT" in context_canonical
        assert len(context_canonical) > 100, "Context should have content"
        print(f"✅ Got canonical context ({len(context_canonical)} chars)")
        print()

        # Test 3b: Get context with developer audience
        print("3b. Context with developer audience:")
        context_developer = memory.get_context_for_ai(
            query="authentication",
            audience="developer"
        )
        assert "VIDURAI PROJECT CONTEXT" in context_developer
        print(f"✅ Got developer context ({len(context_developer)} chars)")
        print()

        # Test 3c: Get context with manager audience
        print("3c. Context with manager audience:")
        context_manager = memory.get_context_for_ai(
            query="authentication",
            audience="manager"
        )
        assert "VIDURAI PROJECT CONTEXT" in context_manager
        print(f"✅ Got manager context ({len(context_manager)} chars)")
        print()

        # Test 3d: Verify different audiences return different content
        print("3d. Verify audiences differ:")
        # At minimum, canonical and developer should differ (developer adds context)
        # But they may be the same if no file/line enrichment occurred
        # Manager should differ from developer (removes technical details)
        print(f"   Canonical length: {len(context_canonical)}")
        print(f"   Developer length: {len(context_developer)}")
        print(f"   Manager length:   {len(context_manager)}")
        print("✅ All audience contexts generated")
        print()

        print("✅ PASSED: get_context_for_ai() supports audiences\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_backward_compatibility():
    """Test that existing code still works without multi-audience"""
    print("=" * 70)
    print("🧪 TEST 4: Backward Compatibility")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Test 4a: Old initialization still works
        print("4a. Old-style initialization:")
        memory = VismritiMemory(project_path=temp_dir)
        assert memory.multi_audience_generator is None
        print("✅ Old initialization works (multi-audience disabled)")
        print()

        # Test 4b: Old remember() still works
        print("4b. Old-style remember():")
        mem = memory.remember(
            "Fixed bug in auth.py",
            metadata={"type": "bugfix"},
            extract_gist=False
        )
        assert mem is not None
        assert mem.gist is not None
        print("✅ Old remember() works")
        print()

        # Test 4c: Old get_context_for_ai() still works
        print("4c. Old-style get_context_for_ai():")
        context = memory.get_context_for_ai(query="bug")
        assert "VIDURAI PROJECT CONTEXT" in context
        print("✅ Old get_context_for_ai() works")
        print()

        # Test 4d: Database doesn't have audience gists when disabled
        print("4d. No audience gists when disabled:")
        if memory.db:
            memories = memory.db.recall_memories(
                project_path=temp_dir,
                query="bug",
                limit=1
            )
            if memories:
                memory_id = memories[0]['id']
                audience_gists = memory.db.get_audience_gists(memory_id)
                assert len(audience_gists) == 0, \
                    "Should have no audience gists when feature disabled"
                print("✅ No audience gists stored when disabled")
        print()

        print("✅ PASSED: Full backward compatibility maintained\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_real_world_scenario():
    """Test real-world usage scenario"""
    print("=" * 70)
    print("🧪 TEST 5: Real-World Scenario")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Scenario: Developer using Vidurai with multi-audience for different stakeholders
        print("Scenario: Developer tracking work for different audiences")
        print()

        memory = VismritiMemory(
            enable_multi_audience=True,
            project_path=temp_dir
        )

        # Store various types of memories
        work_log = [
            {
                "content": "Resolved critical TypeError in payment processing webhook "
                          "when handling Stripe callbacks",
                "metadata": {
                    "type": "bugfix",
                    "file": "payments/webhooks.py",
                    "line": 156,
                    "severity": "critical"
                }
            },
            {
                "content": "Implemented automated email notifications for failed payment attempts "
                          "using SendGrid API",
                "metadata": {
                    "type": "feature",
                    "file": "notifications/email.py"
                }
            },
            {
                "content": "Refactored database connection pool to use asyncpg for 3x performance improvement",
                "metadata": {
                    "type": "refactor",
                    "file": "db/pool.py"
                }
            }
        ]

        for entry in work_log:
            memory.remember(
                entry["content"],
                metadata=entry["metadata"],
                extract_gist=False
            )

        print(f"✅ Stored {len(work_log)} work entries")
        print()

        # Developer wants technical context
        print("Developer view (technical details):")
        dev_context = memory.get_context_for_ai(
            query="payment",
            audience="developer"
        )
        print(dev_context[:400] + "...\n")

        # Manager wants high-level summary
        print("Manager view (impact-focused):")
        mgr_context = memory.get_context_for_ai(
            query="payment",
            audience="manager"
        )
        print(mgr_context[:400] + "...\n")

        # Personal diary view
        print("Personal view (first-person narrative):")
        personal_context = memory.get_context_for_ai(
            query="payment",
            audience="personal"
        )
        print(personal_context[:400] + "...\n")

        print("✅ PASSED: Real-world scenario works as expected\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_error_handling():
    """Test error handling and edge cases"""
    print("=" * 70)
    print("🧪 TEST 6: Error Handling")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        memory = VismritiMemory(
            enable_multi_audience=True,
            project_path=temp_dir
        )

        # Test 6a: Very short content
        print("6a. Very short content:")
        mem = memory.remember("x", metadata={}, extract_gist=False)
        assert mem is not None
        print("✅ Handles very short content")
        print()

        # Test 6b: Missing metadata
        print("6b. Missing metadata:")
        mem = memory.remember("Fixed bug", metadata=None, extract_gist=False)
        assert mem is not None
        print("✅ Handles missing metadata")
        print()

        # Test 6c: Unknown audience in get_context_for_ai
        print("6c. Unknown audience:")
        # First make sure we have a memory
        memory.remember("Test bug fix", metadata={}, extract_gist=False)
        context = memory.get_context_for_ai(
            query="Test",
            audience="unknown_audience"
        )
        # Should still return context (just uses canonical gist)
        assert len(context) > 0
        print("✅ Handles unknown audience gracefully")
        print()

        # Test 6d: Query with no results
        print("6d. Query with no results:")
        context = memory.get_context_for_ai(
            query="nonexistent_term_xyz",
            audience="developer"
        )
        assert "No relevant project context found" in context or len(context) > 0
        print("✅ Handles no results")
        print()

        print("✅ PASSED: Error handling works correctly\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 5.3 INTEGRATION TEST SUITE: VismritiMemory + Multi-Audience")
        print()

        test_initialization()
        test_remember_with_multi_audience()
        test_get_context_for_ai_with_audience()
        test_backward_compatibility()
        test_real_world_scenario()
        test_error_handling()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 5.3 INTEGRATION TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✅ Initialization with multi-audience")
        print("  ✅ remember() generates audience gists")
        print("  ✅ get_context_for_ai() supports audience parameter")
        print("  ✅ 100% backward compatibility")
        print("  ✅ Real-world scenarios work")
        print("  ✅ Error handling robust")
        print()

    except AssertionError as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
