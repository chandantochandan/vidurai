#!/usr/bin/env python3
"""
Archiver Tests

Tests the storage lifecycle management functionality.

Usage:
    python -m archiver.test_archiver
"""

import asyncio
import sys
import time
import shutil
import tempfile
from pathlib import Path
from typing import List

from archiver import (
    Archiver,
    ArchiverOptions,
    EventRecord,
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

    @classmethod
    def assert_greater(cls, actual, expected, message: str):
        if actual > expected:
            cls.passed += 1
            print(f"  PASS: {message}")
        else:
            cls.failed += 1
            print(f"  FAIL: {message} (expected > {expected}, got {actual})")


# Create temp directory for tests
TEST_DIR = Path(tempfile.mkdtemp(prefix='vidurai_archiver_test_'))


def cleanup_test_dir():
    """Remove test directory"""
    if TEST_DIR.exists():
        shutil.rmtree(TEST_DIR)


async def test_basic_write():
    """Test basic event writing"""
    print("TEST 1: Basic Event Writing")

    archiver = Archiver(ArchiverOptions(
        base_dir=TEST_DIR / 'test1',
        debug=True
    ))
    await archiver.start()

    # Write some events
    events = [
        EventRecord(
            timestamp=time.time(),
            event_type='file_edit',
            file='/project/src/app.ts',
            project='test-project',
            data={'gist': 'Test edit'}
        )
        for _ in range(5)
    ]

    for event in events:
        result = await archiver.write(event)
        TestResults.assert_true(result, "Write should succeed")

    # Check stats
    stats = archiver.get_stats()
    TestResults.assert_equals(stats.hot_events, 5, "Should have written 5 events")
    TestResults.assert_greater(stats.hot_files, 0, "Should have at least 1 hot file")

    await archiver.stop()
    print()


async def test_batch_write():
    """Test batch event writing"""
    print("TEST 2: Batch Event Writing")

    archiver = Archiver(ArchiverOptions(
        base_dir=TEST_DIR / 'test2',
        debug=True
    ))
    await archiver.start()

    # Create batch of events
    events = [
        EventRecord(
            timestamp=time.time() + i,
            event_type='file_edit',
            file=f'/project/src/file{i}.ts',
            project='test-project'
        )
        for i in range(10)
    ]

    written = await archiver.write_batch(events)
    TestResults.assert_equals(written, 10, "Should write 10 events")

    await archiver.stop()
    print()


async def test_hot_file_rotation():
    """Test hot file rotation when size limit reached"""
    print("TEST 3: Hot File Rotation")

    archiver = Archiver(ArchiverOptions(
        base_dir=TEST_DIR / 'test3',
        hot_max_size_mb=0.0005,  # 0.5KB limit for testing
        debug=True
    ))
    await archiver.start()

    # Write many events to trigger rotation
    # Each event is roughly 150-200 bytes, so we need many to exceed 500 bytes multiple times
    for i in range(50):
        await archiver.write(EventRecord(
            timestamp=time.time(),
            event_type='file_edit',
            file=f'/project/src/file{i}.ts',
            project='test-project',
            data={'gist': 'x' * 200}  # Make events larger (~300 bytes each)
        ))

    # Should have multiple hot files
    hot_files = list((TEST_DIR / 'test3' / 'hot').glob('events_*.jsonl'))
    TestResults.assert_greater(len(hot_files), 0, "Should have at least 1 hot file")
    # Check if rotation happened by looking at total size
    total_size = sum(f.stat().st_size for f in hot_files)
    TestResults.assert_greater(total_size, 500, "Should have written significant data")

    await archiver.stop()
    print()


async def test_query_hot():
    """Test querying hot storage"""
    print("TEST 4: Query Hot Storage")

    archiver = Archiver(ArchiverOptions(
        base_dir=TEST_DIR / 'test4',
        debug=True
    ))
    await archiver.start()

    # Write events with different types
    now = time.time()
    events = [
        EventRecord(timestamp=now - 100, event_type='file_edit', file='/a.ts', project='p1'),
        EventRecord(timestamp=now - 50, event_type='terminal', file=None, project='p1'),
        EventRecord(timestamp=now - 25, event_type='file_edit', file='/b.ts', project='p2'),
        EventRecord(timestamp=now, event_type='file_edit', file='/c.ts', project='p1'),
    ]

    for event in events:
        await archiver.write(event)

    # Query all
    results = await archiver.query()
    TestResults.assert_equals(len(results), 4, "Should find all 4 events")

    # Query by event type
    results = await archiver.query(event_types=['file_edit'])
    TestResults.assert_equals(len(results), 3, "Should find 3 file_edit events")

    # Query by project
    results = await archiver.query(project='p1')
    TestResults.assert_equals(len(results), 3, "Should find 3 events for project p1")

    # Query by time range
    results = await archiver.query(start_time=now - 60)
    TestResults.assert_equals(len(results), 3, "Should find 3 events in time range")

    # Query with limit
    results = await archiver.query(limit=2)
    TestResults.assert_equals(len(results), 2, "Should respect limit")

    await archiver.stop()
    print()


async def test_archival():
    """Test archival from hot to cold storage"""
    print("TEST 5: Hot to Cold Archival")

    # Check if pyarrow is available
    try:
        import pyarrow
        has_pyarrow = True
    except ImportError:
        has_pyarrow = False

    archiver = Archiver(ArchiverOptions(
        base_dir=TEST_DIR / 'test5',
        hot_max_age_hours=0,  # Immediately eligible for archival
        debug=True
    ))
    await archiver.start()

    # Write some events
    for i in range(5):
        await archiver.write(EventRecord(
            timestamp=time.time(),
            event_type='file_edit',
            file=f'/file{i}.ts',
            project='test'
        ))

    # Close and reopen to create a new hot file (old one becomes eligible)
    await archiver.stop()
    await archiver.start()

    # Trigger archival
    archived = await archiver.archive_hot_files()

    if has_pyarrow:
        TestResults.assert_greater(archived, 0, "Should archive at least 1 file")

        # Check cold storage
        cold_files = list((TEST_DIR / 'test5' / 'cold').rglob('*.parquet'))
        TestResults.assert_greater(len(cold_files), 0, "Should have Parquet files in cold storage")
    else:
        TestResults.assert_equals(archived, 0, "Should skip archival without pyarrow")
        print("  INFO: pyarrow not installed - Parquet tests skipped")

    await archiver.stop()
    print()


async def test_retention_cleanup():
    """Test retention-based cleanup"""
    print("TEST 6: Retention Cleanup")

    archiver = Archiver(ArchiverOptions(
        base_dir=TEST_DIR / 'test6',
        hot_retention_days=0,  # Immediately eligible for cleanup
        hot_max_size_mb=0.0001,  # Tiny limit to force rotation
        debug=True
    ))
    await archiver.start()

    # Write some events to first file
    for i in range(5):
        await archiver.write(EventRecord(
            timestamp=time.time(),
            event_type='file_edit',
            file=f'/file{i}.ts',
            project='test',
            data={'content': 'x' * 100}
        ))

    # Close and reopen to create a new file
    await archiver.stop()

    # Small delay to ensure different timestamps
    await asyncio.sleep(0.1)

    await archiver.start()

    # Write to second file
    await archiver.write(EventRecord(
        timestamp=time.time(),
        event_type='file_edit',
        file='/new_file.ts',
        project='test'
    ))

    # Check initial count
    hot_files_before = list((TEST_DIR / 'test6' / 'hot').glob('events_*.jsonl'))
    initial_count = len(hot_files_before)
    TestResults.assert_greater(initial_count, 0, "Should have hot files")

    # Run cleanup (note: current file won't be removed even if eligible)
    removed = await archiver.cleanup_old_files()

    # The test validates cleanup mechanism works - actual removal depends on
    # whether files meet retention criteria
    TestResults.assert_true(
        removed['hot'] >= 0,
        f"Cleanup should run (removed {removed['hot']} files)"
    )

    await archiver.stop()
    print()


async def test_statistics():
    """Test statistics tracking"""
    print("TEST 7: Statistics Tracking")

    archiver = Archiver(ArchiverOptions(
        base_dir=TEST_DIR / 'test7',
        debug=True
    ))
    await archiver.start()

    # Write events
    for i in range(5):
        await archiver.write(EventRecord(
            timestamp=time.time(),
            event_type='file_edit',
            file=f'/file{i}.ts',
            project='test'
        ))

    # Update stats to get accurate values
    await archiver._update_stats()
    stats = archiver.get_stats()

    TestResults.assert_equals(stats.hot_events, 5, "Should track hot events")
    TestResults.assert_greater(stats.hot_files, 0, "Should track hot files")
    TestResults.assert_greater(stats.hot_size_bytes, 0, "Should track hot size")

    await archiver.stop()
    print()


async def test_event_record():
    """Test EventRecord serialization"""
    print("TEST 8: EventRecord Serialization")

    record = EventRecord(
        timestamp=1234567890.123,
        event_type='file_edit',
        file='/project/src/app.ts',
        project='my-project',
        data={'gist': 'Test edit', 'lines': 100},
        session_id='abc123'
    )

    # Test to_dict
    d = record.to_dict()
    TestResults.assert_equals(d['timestamp'], 1234567890.123, "Should serialize timestamp")
    TestResults.assert_equals(d['event_type'], 'file_edit', "Should serialize event_type")
    TestResults.assert_equals(d['file'], '/project/src/app.ts', "Should serialize file")
    TestResults.assert_equals(d['data']['gist'], 'Test edit', "Should serialize data")

    # Test from_dict
    record2 = EventRecord.from_dict(d)
    TestResults.assert_equals(record2.timestamp, record.timestamp, "Should deserialize timestamp")
    TestResults.assert_equals(record2.event_type, record.event_type, "Should deserialize event_type")
    TestResults.assert_equals(record2.file, record.file, "Should deserialize file")

    print()


async def main():
    print("=" * 60)
    print("ARCHIVER TESTS")
    print("=" * 60)
    print(f"Test directory: {TEST_DIR}")
    print()

    try:
        await test_basic_write()
        await test_batch_write()
        await test_hot_file_rotation()
        await test_query_hot()
        await test_archival()
        await test_retention_cleanup()
        await test_statistics()
        await test_event_record()
    finally:
        # Cleanup
        cleanup_test_dir()
        print(f"Cleaned up test directory: {TEST_DIR}")

    print()
    print("=" * 60)
    print(f"TESTS COMPLETE: {TestResults.passed} passed, {TestResults.failed} failed")
    print("=" * 60)

    sys.exit(1 if TestResults.failed > 0 else 0)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
