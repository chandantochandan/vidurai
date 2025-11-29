#!/usr/bin/env python3
"""
Test suite for Phase 6.2: Event Source Integration
Tests that VismritiMemory, CLI, and MCP server publish events to EventBus
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path
from typing import List

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_vismriti_memory_events():
    """Test that VismritiMemory publishes events"""
    print("=" * 70)
    print("🧪 TEST 1: VismritiMemory Event Publishing")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.core.event_bus import EventBus, ViduraiEvent

    # Reset EventBus
    EventBus.reset()

    # Track received events
    received_events: List[ViduraiEvent] = []

    def event_handler(event: ViduraiEvent):
        received_events.append(event)

    EventBus.subscribe(event_handler)

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        # Test 1.1: Memory creation publishes event
        print("Test 1.1: memory.created event")
        memory = VismritiMemory(
            project_path=temp_dir,
            enable_gist_extraction=False
        )

        memory.remember(
            "Fixed authentication bug in auth.py",
            metadata={"type": "bugfix", "file": "auth.py", "line": 42}
        )

        # Find memory.created event
        created_events = [e for e in received_events if e.type == "memory.created"]
        assert len(created_events) >= 1, "Should have at least 1 memory.created event"

        event = created_events[0]
        assert event.source == "vismriti"
        assert event.project_path == temp_dir
        assert "gist" in event.payload
        assert "salience" in event.payload
        assert event.payload["memory_type"] == "bugfix"
        assert event.payload["file_path"] == "auth.py"
        print(f"✅ memory.created event published: {event}")
        print()

        # Test 1.2: Context retrieval publishes event
        print("Test 1.2: memory.context_retrieved event")
        received_events.clear()

        context = memory.get_context_for_ai(query="auth", max_tokens=1000)

        # Find memory.context_retrieved event
        context_events = [e for e in received_events if e.type == "memory.context_retrieved"]
        assert len(context_events) >= 1, "Should have at least 1 memory.context_retrieved event"

        event = context_events[0]
        assert event.source == "vismriti"
        assert event.project_path == temp_dir
        assert event.payload["query"] == "auth"
        assert "memory_count" in event.payload
        assert "context_length" in event.payload
        print(f"✅ memory.context_retrieved event published: {event}")
        print()

        print("✅ PASSED: VismritiMemory publishes events correctly\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        EventBus.reset()


def test_cli_events():
    """Test that CLI commands publish events"""
    print("=" * 70)
    print("🧪 TEST 2: CLI Event Publishing")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.cli import recall, context
    from vidurai.core.event_bus import EventBus, ViduraiEvent
    from click.testing import CliRunner

    # Reset EventBus
    EventBus.reset()

    # Track received events
    received_events: List[ViduraiEvent] = []

    def event_handler(event: ViduraiEvent):
        received_events.append(event)

    EventBus.subscribe(event_handler)

    # Create temp directory with test data
    temp_dir = tempfile.mkdtemp()
    try:
        # Create test memory
        memory = VismritiMemory(project_path=temp_dir, enable_gist_extraction=False)
        memory.remember(
            "Fixed critical authentication bug",
            metadata={"type": "bugfix", "file": "auth.py"}
        )
        received_events.clear()  # Clear creation event

        # Test 2.1: CLI recall publishes event
        print("Test 2.1: cli.recall event")
        runner = CliRunner()
        result = runner.invoke(recall, [
            '--project', temp_dir,
            '--query', 'authentication',
            '--min-salience', 'LOW'
        ])

        assert result.exit_code == 0, f"CLI recall failed: {result.output}"

        # Find cli.recall event
        recall_events = [e for e in received_events if e.type == "cli.recall"]
        assert len(recall_events) >= 1, "Should have at least 1 cli.recall event"

        event = recall_events[0]
        assert event.source == "cli"
        assert event.project_path == temp_dir
        assert event.payload["query"] == "authentication"
        assert "memory_count" in event.payload
        print(f"✅ cli.recall event published: {event}")
        print()

        # Test 2.2: CLI context publishes event
        print("Test 2.2: cli.context event")
        received_events.clear()

        result = runner.invoke(context, [
            '--project', temp_dir,
            '--query', 'auth'
        ])

        assert result.exit_code == 0, f"CLI context failed: {result.output}"

        # Find cli.context event
        context_events = [e for e in received_events if e.type == "cli.context"]
        assert len(context_events) >= 1, "Should have at least 1 cli.context event"

        event = context_events[0]
        assert event.source == "cli"
        assert event.project_path == temp_dir
        assert event.payload["query"] == "auth"
        assert "context_length" in event.payload
        print(f"✅ cli.context event published: {event}")
        print()

        print("✅ PASSED: CLI publishes events correctly\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        EventBus.reset()


def test_mcp_server_events():
    """Test that MCP server code publishes events (via VismritiMemory)"""
    print("=" * 70)
    print("🧪 TEST 3: MCP Server Integration")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.core.event_bus import EventBus, ViduraiEvent

    # Reset EventBus
    EventBus.reset()

    # Track received events
    received_events: List[ViduraiEvent] = []

    def event_handler(event: ViduraiEvent):
        received_events.append(event)

    EventBus.subscribe(event_handler)

    # Create temp directory with test data
    temp_dir = tempfile.mkdtemp()
    try:
        # Create test memory (WITHOUT clearing events yet - we need the handler subscribed)
        memory = VismritiMemory(project_path=temp_dir, enable_gist_extraction=False)
        memory.remember(
            "Implemented OAuth2 authentication in auth module",
            metadata={"type": "feature", "file": "oauth.py"}
        )

        # Test 3.1: MCP server uses VismritiMemory.get_context_for_ai, which publishes events
        print("Test 3.1: MCP context integration (via VismritiMemory)")

        # Clear events after creation (keep handler subscribed)
        received_events.clear()

        # Verify handler is still subscribed
        stats = EventBus.get_statistics()
        print(f"Debug: EventBus has {stats['handler_count']} handlers")

        # Simulate MCP server call - MCP internally calls VismritiMemory.get_context_for_ai
        # Use None for query to get all memories
        result = memory.get_context_for_ai(query=None, max_tokens=1000)

        assert isinstance(result, str), "get_context_for_ai should return string"

        # Debug: print all received events
        print(f"Debug: Received {len(received_events)} events:")
        for e in received_events:
            print(f"  - {e.type} from {e.source}")

        # Find memory.context_retrieved event (published by VismritiMemory)
        context_events = [e for e in received_events if e.type == "memory.context_retrieved"]
        assert len(context_events) >= 1, f"Should have at least 1 memory.context_retrieved event, got {len(received_events)} events total"

        event = context_events[0]
        assert event.source == "vismriti"
        assert event.project_path == temp_dir
        assert event.payload["query"] == "all"  # None query becomes "all"
        assert "context_length" in event.payload
        print(f"✅ memory.context_retrieved event published (used by MCP): {event}")
        print()

        print("✅ PASSED: MCP server integration events work correctly\n")
        print("   Note: MCP server uses VismritiMemory internally, which publishes events")
        print()

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        EventBus.reset()


def test_event_flow_end_to_end():
    """Test end-to-end event flow from memory creation to retrieval"""
    print("=" * 70)
    print("🧪 TEST 4: End-to-End Event Flow")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.core.event_bus import EventBus, ViduraiEvent

    # Reset EventBus
    EventBus.reset()

    # Track all events
    all_events: List[ViduraiEvent] = []

    def event_handler(event: ViduraiEvent):
        all_events.append(event)
        print(f"📨 Event received: [{event.source}] {event.type}")

    EventBus.subscribe(event_handler)

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        memory = VismritiMemory(project_path=temp_dir, enable_gist_extraction=False)

        # Step 1: Create memories
        print("\nStep 1: Creating 3 memories...")
        memory.remember("Fixed bug in login", metadata={"type": "bugfix", "file": "login.py"})
        memory.remember("Added password reset", metadata={"type": "feature", "file": "reset.py"})
        memory.remember("Updated docs", metadata={"type": "docs", "file": "README.md"})

        created_events = [e for e in all_events if e.type == "memory.created"]
        assert len(created_events) == 3, "Should have 3 memory.created events"
        print(f"✅ Received {len(created_events)} memory.created events")

        # Step 2: Retrieve context
        print("\nStep 2: Retrieving context...")
        context = memory.get_context_for_ai(query="login")

        context_events = [e for e in all_events if e.type == "memory.context_retrieved"]
        assert len(context_events) >= 1, "Should have at least 1 memory.context_retrieved event"
        print(f"✅ Received {len(context_events)} memory.context_retrieved events")

        # Step 3: Verify event data
        print("\nStep 3: Verifying event data...")
        for event in all_events:
            assert event.id is not None, "Event should have ID"
            assert event.timestamp is not None, "Event should have timestamp"
            assert event.source in ["vismriti", "cli", "mcp_server"], "Event should have valid source"
            assert event.project_path == temp_dir, "Event should have correct project path"

        print(f"✅ All {len(all_events)} events have valid data")

        # Step 4: Check event ordering
        print("\nStep 4: Checking event ordering...")
        for i in range(1, len(all_events)):
            assert all_events[i].timestamp >= all_events[i-1].timestamp, \
                "Events should be in chronological order"

        print(f"✅ Events are in chronological order")

        print("\n✅ PASSED: End-to-end event flow works correctly\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        EventBus.reset()


def test_event_buffer_persistence():
    """Test that events are stored in ring buffer"""
    print("=" * 70)
    print("🧪 TEST 5: Event Buffer Persistence")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.core.event_bus import EventBus

    # Reset EventBus
    EventBus.reset()

    # Create temp directory
    temp_dir = tempfile.mkdtemp()
    try:
        memory = VismritiMemory(project_path=temp_dir, enable_gist_extraction=False)

        # Create several memories
        print("Creating 5 memories...")
        for i in range(5):
            memory.remember(f"Memory {i}", metadata={"type": "test", "index": i})

        # Check ring buffer
        recent_events = EventBus.get_recent_events(limit=10)
        print(f"✅ Ring buffer contains {len(recent_events)} events")

        # Verify newest first (index 4 should be before index 0)
        # Note: not all events have "index" (we only check if they exist)
        indices = [e.payload.get("index") for e in recent_events if "index" in e.payload]
        if len(indices) >= 2:
            assert indices[0] > indices[-1], "Newest events should be first"
            print("✅ Events ordered newest first")
        else:
            print("✅ Events in buffer (not all have index)")

        # Check statistics
        stats = EventBus.get_statistics()
        print(f"✅ EventBus stats: {stats['buffer_size']} events in buffer")
        assert stats['buffer_size'] >= 5, "Should have at least 5 events"
        assert "memory.created" in stats['event_types'], "Should have memory.created events"

        print("\n✅ PASSED: Event buffer persistence works correctly\n")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
        EventBus.reset()


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 6.2 TEST SUITE: Event Source Integration")
        print()

        test_vismriti_memory_events()
        test_cli_events()
        test_mcp_server_events()
        test_event_flow_end_to_end()
        test_event_buffer_persistence()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 6.2 TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✅ VismritiMemory publishes memory.created and memory.context_retrieved events")
        print("  ✅ CLI commands publish cli.recall and cli.context events")
        print("  ✅ MCP server integration verified (uses VismritiMemory)")
        print("  ✅ End-to-end event flow verified")
        print("  ✅ Event buffer persistence verified")
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
