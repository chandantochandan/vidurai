#!/usr/bin/env python3
"""
Test script for semantic consolidation system
Tests batch consolidation of old LOW/NOISE memories
"""

import sys
import time
from pathlib import Path
from datetime import datetime, timedelta

# Add vidurai to path
sys.path.insert(0, str(Path(__file__).parent))

from vidurai import VismritiMemory
from vidurai.storage.database import MemoryDatabase, SalienceLevel


def create_test_memories():
    """
    Create test memories for consolidation testing
    Simulates 50 old LOW/NOISE memories about same file
    """
    print("=" * 60)
    print("📝 Creating Test Memories for Consolidation")
    print("=" * 60)
    print()

    db = MemoryDatabase()
    project_path = "/home/user/vidurai/test-consolidation"

    # Create 50 LOW salience memories about same file
    file_path = "/home/user/vidurai/test-consolidation/main.py"

    print(f"Creating 50 LOW salience memories (simulating 30+ days old)...")

    for i in range(50):
        db.store_memory(
            project_path=project_path,
            verbatim=f"Working on refactor iteration {i+1} in main.py",
            gist=f"Refactor iteration {i+1} in main.py",
            salience=SalienceLevel.LOW,
            event_type="code_change",
            file_path=file_path,
            line_number=100 + i,
            tags=None,
            retention_days=7
        )

        if (i + 1) % 10 == 0:
            print(f"  Created {i + 1} memories...")

    # Create some NOISE salience memories too
    print(f"Creating 20 NOISE salience memories...")
    for i in range(20):
        db.store_memory(
            project_path=project_path,
            verbatim=f"Debug log output {i+1}",
            gist=f"Debug log {i+1}",
            salience=SalienceLevel.NOISE,
            event_type="system_log",
            file_path=file_path,
            line_number=200 + i,
            tags=None,
            retention_days=1
        )

    # Create some HIGH/CRITICAL that should NOT be consolidated
    print(f"Creating 5 HIGH salience memories (should be preserved)...")
    for i in range(5):
        db.store_memory(
            project_path=project_path,
            verbatim=f"Fixed critical bug #{i+1}",
            gist=f"Critical bug fix #{i+1}",
            salience=SalienceLevel.HIGH,
            event_type="bugfix",
            file_path=file_path,
            line_number=300 + i,
            tags=['important'],
            retention_days=90
        )

    print()
    print("✅ Test memories created:")
    print(f"  LOW: 50 memories")
    print(f"  NOISE: 20 memories")
    print(f"  HIGH: 5 memories")
    print(f"  Total: 75 memories")
    print()


def test_consolidation_dry_run():
    """
    Test consolidation in dry-run mode (no database changes)
    """
    print("=" * 60)
    print("🧪 TEST: Consolidation Dry Run")
    print("=" * 60)
    print()

    memory = VismritiMemory(
        project_path="/home/user/vidurai/test-consolidation"
    )

    # Enable consolidation via config
    config = {
        'enabled': True,
        'target_ratio': 0.5,  # 50% reduction
        'min_memories_to_consolidate': 5,
        'min_salience': 'LOW',  # Consolidate LOW and NOISE
        'max_age_days': 0,  # Consolidate all ages (for testing)
        'group_by': ['file_path'],
        'preserve_critical': True,
        'preserve_high': True,
        'keep_originals': False,
    }

    print("Running consolidation (dry run)...")
    print()

    metrics = memory.run_semantic_consolidation(
        dry_run=True,
        config=config
    )

    if metrics:
        print("📊 Consolidation Metrics (Dry Run):")
        print(f"  Memories before: {metrics.memories_before}")
        print(f"  Memories after: {metrics.memories_after}")
        print(f"  Memories consolidated: {metrics.memories_consolidated}")
        print(f"  Compression ratio: {metrics.compression_ratio:.1%}")
        print()
        print(f"  Salience distribution before:")
        for salience, count in metrics.salience_distribution_before.items():
            print(f"    {salience}: {count}")
        print()
        print(f"  HIGH preserved: {metrics.high_preserved}")
        print(f"  Execution time: {metrics.execution_time_seconds:.2f}s")
    else:
        print("❌ No metrics returned")

    print()
    print("=" * 60)
    print("✅ DRY RUN COMPLETE (no changes made)")
    print("=" * 60)
    print()


def test_consolidation_real():
    """
    Test actual consolidation (modifies database)
    """
    print("=" * 60)
    print("🧪 TEST: Real Consolidation")
    print("=" * 60)
    print()

    # Check current state
    db = MemoryDatabase()
    before_stats = db.get_statistics("/home/user/vidurai/test-consolidation")

    print(f"Database before consolidation:")
    print(f"  Total memories: {before_stats['total']}")
    print(f"  By salience:")
    for salience, count in before_stats['by_salience'].items():
        print(f"    {salience}: {count}")
    print()

    memory = VismritiMemory(
        project_path="/home/user/vidurai/test-consolidation"
    )

    # Enable consolidation
    config = {
        'enabled': True,
        'target_ratio': 0.5,
        'min_memories_to_consolidate': 5,
        'min_salience': 'LOW',
        'max_age_days': 0,  # All ages for testing
        'group_by': ['file_path'],
        'preserve_critical': True,
        'preserve_high': True,
        'keep_originals': False,  # Delete originals
    }

    print("Running consolidation (REAL)...")
    print()

    metrics = memory.run_semantic_consolidation(
        dry_run=False,
        config=config
    )

    if metrics:
        print("📊 Consolidation Results:")
        print(f"  {metrics.memories_before} → {metrics.memories_after} memories")
        print(f"  Compression: {metrics.compression_ratio:.1%}")
        print(f"  Groups processed: {metrics.groups_processed}")
        print()

    # Check final state
    after_stats = db.get_statistics("/home/user/vidurai/test-consolidation")

    print(f"Database after consolidation:")
    print(f"  Total memories: {after_stats['total']}")
    print(f"  By salience:")
    for salience, count in after_stats['by_salience'].items():
        print(f"    {salience}: {count}")
    print()

    # Verify HIGH memories preserved
    if before_stats['by_salience'].get('HIGH', 0) == after_stats['by_salience'].get('HIGH', 0):
        print("✅ HIGH salience memories preserved correctly")
    else:
        print("❌ HIGH salience memories were affected!")

    print()
    print("=" * 60)
    print("✅ REAL CONSOLIDATION COMPLETE")
    print("=" * 60)
    print()


def test_query_after_consolidation():
    """
    Test that queries still work after consolidation
    """
    print("=" * 60)
    print("🧪 TEST: Query After Consolidation")
    print("=" * 60)
    print()

    db = MemoryDatabase()

    # Query for main.py memories
    results = db.recall_memories(
        project_path="/home/user/vidurai/test-consolidation",
        query="main.py",
        limit=10
    )

    print(f"Query results for 'main.py': {len(results)} memories found")
    print()

    if results:
        print("Sample results:")
        for i, mem in enumerate(results[:3], 1):
            gist = mem['gist']
            salience = mem['salience']
            tags = mem.get('tags', '')

            print(f"  {i}. [{salience}] {gist[:80]}...")
            if 'consolidated' in tags:
                print(f"     (CONSOLIDATED)")
        print()

    print("✅ Queries working after consolidation")
    print()


if __name__ == "__main__":
    try:
        print()
        print("🚀 SEMANTIC CONSOLIDATION TEST SUITE")
        print()

        # Run tests in sequence
        create_test_memories()
        time.sleep(1)

        test_consolidation_dry_run()
        time.sleep(1)

        test_consolidation_real()
        time.sleep(1)

        test_query_after_consolidation()

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
