#!/usr/bin/env python3
"""
Test suite for Phase 6.1: Event Bus
Tests the local telemetry core for Vidurai
"""

import sys
import time
import threading
from pathlib import Path
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent))


def test_basic_publish_subscribe():
    """Test basic publish/subscribe functionality"""
    print("=" * 70)
    print("🧪 TEST 1: Basic Publish/Subscribe")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    # Reset EventBus
    EventBus.reset()

    # Track received events
    received_events = []

    def handler(event: ViduraiEvent):
        received_events.append(event)

    # Subscribe
    EventBus.subscribe(handler)
    print("✅ Subscribed handler")

    # Publish event
    event = ViduraiEvent(
        type="terminal.command",
        source="daemon",
        project_path="/test/project",
        payload={"command": "pytest", "exit_code": 0}
    )
    EventBus.publish(event)
    print(f"✅ Published event: {event}")

    # Verify
    assert len(received_events) == 1, "Should receive 1 event"
    assert received_events[0].type == "terminal.command"
    assert received_events[0].payload["command"] == "pytest"
    print("✅ Handler received correct event")

    print("\n✅ PASSED: Basic publish/subscribe works\n")


def test_multiple_handlers():
    """Test multiple handlers receive same event"""
    print("=" * 70)
    print("🧪 TEST 2: Multiple Handlers")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    EventBus.reset()

    # Track events for each handler
    handler1_events = []
    handler2_events = []
    handler3_events = []

    def handler1(event):
        handler1_events.append(event)

    def handler2(event):
        handler2_events.append(event)

    def handler3(event):
        handler3_events.append(event)

    # Subscribe all
    EventBus.subscribe(handler1)
    EventBus.subscribe(handler2)
    EventBus.subscribe(handler3)
    print("✅ Subscribed 3 handlers")

    # Publish event
    event = ViduraiEvent(type="test.event", source="test", payload={"data": "test"})
    EventBus.publish(event)
    print("✅ Published 1 event")

    # Verify all received
    assert len(handler1_events) == 1, "Handler 1 should receive event"
    assert len(handler2_events) == 1, "Handler 2 should receive event"
    assert len(handler3_events) == 1, "Handler 3 should receive event"
    print("✅ All 3 handlers received the event")

    # Verify same event
    assert handler1_events[0].id == handler2_events[0].id == handler3_events[0].id
    print("✅ All handlers received same event instance")

    print("\n✅ PASSED: Multiple handlers work correctly\n")


def test_ring_buffer():
    """Test ring buffer keeps last N events"""
    print("=" * 70)
    print("🧪 TEST 3: Ring Buffer")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    EventBus.reset()

    # Get buffer max size
    stats = EventBus.get_statistics()
    max_size = stats['buffer_max_size']
    print(f"Ring buffer max size: {max_size}")

    # Publish more events than buffer size
    num_events = max_size + 100
    print(f"Publishing {num_events} events...")

    for i in range(num_events):
        EventBus.publish(ViduraiEvent(
            type=f"test.event_{i}",
            source="test",
            payload={"index": i}
        ))

    # Get recent events
    recent = EventBus.get_recent_events()
    print(f"✅ Published {num_events} events")
    print(f"✅ Buffer contains {len(recent)} events")

    # Verify buffer size limit
    assert len(recent) <= max_size, f"Buffer should not exceed {max_size}"
    print(f"✅ Buffer size respected: {len(recent)} <= {max_size}")

    # Verify newest events are kept (newest first in return)
    assert recent[0].payload["index"] == num_events - 1, "Newest event should be first"
    assert recent[-1].payload["index"] >= num_events - max_size, "Oldest kept event"
    print("✅ Newest events kept, oldest discarded")

    print("\n✅ PASSED: Ring buffer works correctly\n")


def test_thread_safety():
    """Test thread-safe concurrent publish/subscribe"""
    print("=" * 70)
    print("🧪 TEST 4: Thread Safety")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    EventBus.reset()

    # Track events
    received_events = []
    lock = threading.Lock()

    def handler(event: ViduraiEvent):
        with lock:
            received_events.append(event)

    EventBus.subscribe(handler)

    # Publish from multiple threads
    num_threads = 10
    events_per_thread = 50
    threads = []

    def publish_events(thread_id):
        for i in range(events_per_thread):
            EventBus.publish(ViduraiEvent(
                type=f"thread.{thread_id}.event",
                source="test",
                payload={"thread_id": thread_id, "index": i}
            ))

    print(f"Starting {num_threads} threads, {events_per_thread} events each...")

    for i in range(num_threads):
        t = threading.Thread(target=publish_events, args=(i,))
        threads.append(t)
        t.start()

    # Wait for all threads
    for t in threads:
        t.join()

    total_expected = num_threads * events_per_thread
    print(f"✅ All threads completed")
    print(f"✅ Expected {total_expected} events, received {len(received_events)}")

    # Verify all events received
    assert len(received_events) == total_expected, \
        f"Should receive all {total_expected} events"
    print("✅ All events received (no race conditions)")

    # Verify no corruption (each event has valid data)
    for event in received_events:
        assert "thread_id" in event.payload
        assert "index" in event.payload
        assert 0 <= event.payload["thread_id"] < num_threads
        assert 0 <= event.payload["index"] < events_per_thread

    print("✅ All events valid (no data corruption)")

    print("\n✅ PASSED: Thread safety verified\n")


def test_unsubscribe():
    """Test unsubscribing handlers"""
    print("=" * 70)
    print("🧪 TEST 5: Unsubscribe")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    EventBus.reset()

    received = []

    def handler(event):
        received.append(event)

    # Subscribe
    EventBus.subscribe(handler)

    # Publish event
    EventBus.publish(ViduraiEvent(type="test1", source="test"))
    assert len(received) == 1
    print("✅ Handler received event while subscribed")

    # Unsubscribe
    EventBus.unsubscribe(handler)

    # Publish another event
    EventBus.publish(ViduraiEvent(type="test2", source="test"))
    assert len(received) == 1, "Should not receive event after unsubscribe"
    print("✅ Handler did not receive event after unsubscribe")

    print("\n✅ PASSED: Unsubscribe works correctly\n")


def test_event_filtering():
    """Test handlers can filter events by type"""
    print("=" * 70)
    print("🧪 TEST 6: Event Filtering")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    EventBus.reset()

    terminal_events = []
    ai_events = []

    def terminal_handler(event):
        if event.type.startswith("terminal."):
            terminal_events.append(event)

    def ai_handler(event):
        if event.type.startswith("ai."):
            ai_events.append(event)

    EventBus.subscribe(terminal_handler)
    EventBus.subscribe(ai_handler)

    # Publish mixed events
    EventBus.publish(ViduraiEvent(type="terminal.command", source="test"))
    EventBus.publish(ViduraiEvent(type="ai.user_message", source="test"))
    EventBus.publish(ViduraiEvent(type="terminal.error", source="test"))
    EventBus.publish(ViduraiEvent(type="ai.assistant_message", source="test"))
    EventBus.publish(ViduraiEvent(type="editor.file_save", source="test"))

    print(f"Published 5 events (2 terminal, 2 ai, 1 editor)")
    print(f"Terminal handler received: {len(terminal_events)}")
    print(f"AI handler received: {len(ai_events)}")

    assert len(terminal_events) == 2, "Terminal handler should see 2 events"
    assert len(ai_events) == 2, "AI handler should see 2 events"
    print("✅ Handlers correctly filtered events")

    print("\n✅ PASSED: Event filtering works\n")


def test_convenience_function():
    """Test publish_event convenience function"""
    print("=" * 70)
    print("🧪 TEST 7: Convenience Function")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, publish_event

    EventBus.reset()

    received = []
    EventBus.subscribe(lambda e: received.append(e))

    # Use convenience function
    event = publish_event(
        "terminal.error",
        source="daemon",
        project_path="/test/project",
        error="TypeError",
        file="auth.py",
        line=42
    )

    print(f"✅ Published event: {event}")

    assert len(received) == 1
    assert received[0].type == "terminal.error"
    assert received[0].source == "daemon"
    assert received[0].project_path == "/test/project"
    assert received[0].payload["error"] == "TypeError"
    assert received[0].payload["file"] == "auth.py"
    assert received[0].payload["line"] == 42
    print("✅ Convenience function works correctly")

    print("\n✅ PASSED: Convenience function works\n")


def test_statistics():
    """Test get_statistics()"""
    print("=" * 70)
    print("🧪 TEST 8: Statistics")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    EventBus.reset()

    # Subscribe handlers
    EventBus.subscribe(lambda e: None)
    EventBus.subscribe(lambda e: None)

    # Publish various events
    EventBus.publish(ViduraiEvent(type="terminal.command", source="daemon"))
    EventBus.publish(ViduraiEvent(type="terminal.command", source="daemon"))
    EventBus.publish(ViduraiEvent(type="terminal.error", source="daemon"))
    EventBus.publish(ViduraiEvent(type="ai.user_message", source="browser"))

    stats = EventBus.get_statistics()

    print(f"Statistics: {stats}")

    assert stats['enabled'] == True
    assert stats['handler_count'] == 2
    assert stats['buffer_size'] == 4
    assert stats['event_types']['terminal.command'] == 2
    assert stats['event_types']['terminal.error'] == 1
    assert stats['event_types']['ai.user_message'] == 1
    assert stats['event_sources']['daemon'] == 3
    assert stats['event_sources']['browser'] == 1

    print("✅ Statistics accurate")

    print("\n✅ PASSED: Statistics work correctly\n")


def test_error_handling():
    """Test that handler errors don't break event bus"""
    print("=" * 70)
    print("🧪 TEST 9: Error Handling")
    print("=" * 70)
    print()

    from vidurai.core.event_bus import EventBus, ViduraiEvent

    EventBus.reset()

    good_received = []
    bad_called = False

    def good_handler(event):
        good_received.append(event)

    def bad_handler(event):
        nonlocal bad_called
        bad_called = True
        raise ValueError("Intentional error")

    EventBus.subscribe(bad_handler)
    EventBus.subscribe(good_handler)

    # Publish event
    EventBus.publish(ViduraiEvent(type="test", source="test"))

    # Verify good handler still received event
    assert bad_called, "Bad handler should have been called"
    assert len(good_received) == 1, "Good handler should still receive event"
    print("✅ Good handler received event despite bad handler error")

    print("\n✅ PASSED: Error handling works\n")


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 6.1 TEST SUITE: Event Bus")
        print()

        test_basic_publish_subscribe()
        test_multiple_handlers()
        test_ring_buffer()
        test_thread_safety()
        test_unsubscribe()
        test_event_filtering()
        test_convenience_function()
        test_statistics()
        test_error_handling()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 6.1 TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("  ✅ Basic publish/subscribe")
        print("  ✅ Multiple handlers")
        print("  ✅ Ring buffer (last N events)")
        print("  ✅ Thread safety (concurrent access)")
        print("  ✅ Unsubscribe")
        print("  ✅ Event filtering")
        print("  ✅ Convenience function")
        print("  ✅ Statistics")
        print("  ✅ Error handling")
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
