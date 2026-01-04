#!/usr/bin/env python3
"""
Stabilizer Tests

Tests the daemon-side event stabilization functionality.

Usage:
    python -m stabilizer.test_stabilizer
"""

import asyncio
import sys
from typing import List

from stabilizer import (
    Stabilizer,
    StabilizerOptions,
    StabilizedEvent,
    should_ignore_file,
)


class TestResults:
    passed = 0
    failed = 0

    @classmethod
    def assert_true(cls, condition: bool, message: str):
        if condition:
            cls.passed += 1
            print(f"  PASS: {message}")
        else:
            cls.failed += 1
            print(f"  FAIL: {message}")

    @classmethod
    def assert_equals(cls, actual, expected, message: str):
        if actual == expected:
            cls.passed += 1
            print(f"  PASS: {message}")
        else:
            cls.failed += 1
            print(f"  FAIL: {message} (expected {expected}, got {actual})")


async def test_smart_filtering():
    """Test smart file filtering"""
    print("TEST 1: Smart File Filtering")

    emitted: List[StabilizedEvent] = []

    async def handler(event: StabilizedEvent):
        emitted.append(event)

    stabilizer = Stabilizer(StabilizerOptions(debug=False, enable_batching=False))
    stabilizer.on_event(handler)
    await stabilizer.start()

    # Submit ignored files
    await stabilizer.submit({'type': 'file_edit', 'file': '/project/node_modules/lodash/index.js'})
    await stabilizer.submit({'type': 'file_edit', 'file': '/project/.git/HEAD'})
    await stabilizer.submit({'type': 'file_edit', 'file': '/project/dist/bundle.js'})
    await stabilizer.submit({'type': 'file_edit', 'file': '/project/file.tmp'})

    await stabilizer.flush()

    TestResults.assert_equals(len(emitted), 0, "All ignored files should be filtered")
    TestResults.assert_equals(stabilizer.stats.filtered, 4, "Should have filtered 4 files")

    await stabilizer.stop()
    print()


async def test_pass_normal_files():
    """Test that normal files pass through"""
    print("TEST 2: Pass Normal Source Files")

    emitted: List[StabilizedEvent] = []

    async def handler(event: StabilizedEvent):
        emitted.append(event)

    stabilizer = Stabilizer(StabilizerOptions(debug=False, enable_batching=False))
    stabilizer.on_event(handler)
    await stabilizer.start()

    await stabilizer.submit({'type': 'file_edit', 'file': '/project/src/index.ts'})
    await stabilizer.flush()

    TestResults.assert_equals(len(emitted), 1, "Normal files should pass")
    TestResults.assert_equals(stabilizer.stats.processed, 1, "Should have processed 1 file")

    await stabilizer.stop()
    print()


async def test_debouncing():
    """Test debouncing of rapid events"""
    print("TEST 3: Debouncing Rapid Edits")

    emitted: List[StabilizedEvent] = []

    async def handler(event: StabilizedEvent):
        emitted.append(event)

    stabilizer = Stabilizer(StabilizerOptions(
        debug=False,
        debounce_delay=0.1,
        enable_batching=False
    ))
    stabilizer.on_event(handler)
    await stabilizer.start()

    # Submit 5 rapid edits
    for i in range(5):
        await stabilizer.submit({
            'type': 'file_edit',
            'file': '/project/src/app.ts',
            'data': {'gist': f'Edit {i}'}
        })

    TestResults.assert_equals(len(emitted), 0, "Events should be debounced initially")

    # Wait for debounce
    await asyncio.sleep(0.15)

    TestResults.assert_equals(len(emitted), 1, "Should emit single event after debounce")
    TestResults.assert_equals(stabilizer.stats.debounced, 4, "Should have debounced 4 events")

    if emitted:
        TestResults.assert_equals(emitted[0].debounce_count, 5, "Debounce count should be 5")

    await stabilizer.stop()
    print()


async def test_deduplication():
    """Test deduplication of identical events"""
    print("TEST 4: Deduplication")

    emitted: List[StabilizedEvent] = []

    async def handler(event: StabilizedEvent):
        emitted.append(event)

    stabilizer = Stabilizer(StabilizerOptions(
        debug=False,
        enable_batching=False,
        debounce_delay=0
    ))
    stabilizer.on_event(handler)
    await stabilizer.start()

    # Submit same focus event twice
    await stabilizer.submit({'type': 'focus', 'file': '/project/src/app.ts'})
    await stabilizer.submit({'type': 'focus', 'file': '/project/src/app.ts'})

    TestResults.assert_equals(len(emitted), 1, "Duplicate events should be deduplicated")
    TestResults.assert_equals(stabilizer.stats.deduplicated, 1, "Should have deduplicated 1 event")

    await stabilizer.stop()
    print()


async def test_rate_limiting():
    """Test rate limiting"""
    print("TEST 5: Rate Limiting")

    emitted: List[StabilizedEvent] = []

    async def handler(event: StabilizedEvent):
        emitted.append(event)

    stabilizer = Stabilizer(StabilizerOptions(
        debug=False,
        max_events_per_second=5,
        enable_batching=False,
        enable_smart_filter=False,
        debounce_delay=0
    ))
    stabilizer.on_event(handler)
    await stabilizer.start()

    # Submit 10 events rapidly
    for i in range(10):
        await stabilizer.submit({'type': 'terminal', 'data': {'command': f'cmd{i}'}})

    TestResults.assert_equals(stabilizer.stats.rate_limited, 5, "Should have rate limited 5 events")

    await stabilizer.stop()
    print()


async def test_batching():
    """Test event batching"""
    print("TEST 6: Batching")

    batches: List[List[StabilizedEvent]] = []

    async def batch_handler(events: List[StabilizedEvent]):
        batches.append(events)

    stabilizer = Stabilizer(StabilizerOptions(
        debug=False,
        enable_batching=True,
        batch_window=0.05,
        max_batch_size=10,
        enable_smart_filter=False,
        debounce_delay=0
    ))
    stabilizer.on_batch(batch_handler)
    await stabilizer.start()

    # Submit several events
    await stabilizer.submit({'type': 'terminal', 'data': {'command': 'cmd1'}})
    await stabilizer.submit({'type': 'terminal', 'data': {'command': 'cmd2'}})
    await stabilizer.submit({'type': 'terminal', 'data': {'command': 'cmd3'}})

    await asyncio.sleep(0.1)

    TestResults.assert_equals(len(batches), 1, "Should emit one batch")
    if batches:
        TestResults.assert_equals(len(batches[0]), 3, "Batch should contain 3 events")

    await stabilizer.stop()
    print()


async def test_flush():
    """Test flush functionality"""
    print("TEST 7: Flush Pending Events")

    emitted: List[StabilizedEvent] = []

    async def handler(event: StabilizedEvent):
        emitted.append(event)

    stabilizer = Stabilizer(StabilizerOptions(
        debug=False,
        debounce_delay=10,  # Long delay
        enable_batching=False
    ))
    stabilizer.on_event(handler)
    await stabilizer.start()

    # Submit debounced events
    await stabilizer.submit({'type': 'file_edit', 'file': '/project/src/a.ts'})
    await stabilizer.submit({'type': 'file_edit', 'file': '/project/src/b.ts'})

    TestResults.assert_equals(len(emitted), 0, "Events should be pending")

    await stabilizer.flush()

    TestResults.assert_equals(len(emitted), 2, "Flush should emit all pending events")

    await stabilizer.stop()
    print()


def test_should_ignore_file():
    """Test should_ignore_file utility"""
    print("TEST 8: should_ignore_file Utility")

    TestResults.assert_true(
        should_ignore_file('/project/node_modules/lodash/index.js'),
        "node_modules should be ignored"
    )
    TestResults.assert_true(
        should_ignore_file('C:\\project\\node_modules\\lodash\\index.js'),
        "Windows node_modules should be ignored"
    )
    TestResults.assert_true(
        should_ignore_file('/project/.git/HEAD'),
        ".git should be ignored"
    )
    TestResults.assert_true(
        should_ignore_file('/project/package-lock.json'),
        "package-lock.json should be ignored"
    )
    TestResults.assert_true(
        should_ignore_file('/project/file.tmp'),
        ".tmp files should be ignored"
    )
    TestResults.assert_true(
        not should_ignore_file('/project/src/app.ts'),
        "Source files should NOT be ignored"
    )
    TestResults.assert_true(
        not should_ignore_file('/project/README.md'),
        "README should NOT be ignored"
    )
    print()


async def test_statistics():
    """Test statistics tracking"""
    print("TEST 9: Statistics")

    stabilizer = Stabilizer(StabilizerOptions(debug=False))

    stats = stabilizer.get_stats()
    TestResults.assert_true('received' in dir(stats), "Stats should have received")
    TestResults.assert_true('processed' in dir(stats), "Stats should have processed")
    TestResults.assert_true('debounced' in dir(stats), "Stats should have debounced")
    TestResults.assert_true('deduplicated' in dir(stats), "Stats should have deduplicated")

    await stabilizer.start()
    await stabilizer.submit({'type': 'file_edit', 'file': '/project/node_modules/x'})
    TestResults.assert_equals(stabilizer.stats.received, 1, "Should track received")

    stabilizer.reset_stats()
    TestResults.assert_equals(stabilizer.stats.received, 0, "Reset should clear stats")

    await stabilizer.stop()
    print()


async def main():
    print("=" * 60)
    print("STABILIZER TESTS")
    print("=" * 60)
    print()

    await test_smart_filtering()
    await test_pass_normal_files()
    await test_debouncing()
    await test_deduplication()
    await test_rate_limiting()
    await test_batching()
    await test_flush()
    test_should_ignore_file()
    await test_statistics()

    print("=" * 60)
    print(f"TESTS COMPLETE: {TestResults.passed} passed, {TestResults.failed} failed")
    print("=" * 60)

    sys.exit(1 if TestResults.failed > 0 else 0)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
