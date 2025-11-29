#!/usr/bin/env python3
"""
Test script for memory aggregation system
Simulates repeated TypeScript errors to verify aggregation works
"""

import sys
import time
from pathlib import Path

# Add vidurai to path
sys.path.insert(0, str(Path(__file__).parent))

from vidurai import VismritiMemory
from vidurai.core.data_structures_v3 import SalienceLevel


def test_typescript_error_aggregation():
    """
    Simulate repeated TypeScript errors from pythonBridge.ts
    Verify they get aggregated instead of creating 100+ CRITICAL memories
    """
    print("=" * 60)
    print("🧪 TEST: TypeScript Error Aggregation")
    print("=" * 60)
    print()

    # Initialize memory with aggregation enabled
    memory = VismritiMemory(
        enable_aggregation=True,
        enable_decay=True,
        project_path="/home/user/vidurai/vidurai-vscode-extension"
    )

    print("✅ VismritiMemory initialized with aggregation enabled")
    print()

    # Simulate 50 identical TypeScript errors
    print("📝 Simulating 50 identical TypeScript errors...")
    error_message = "Error in pythonBridge.ts: Line 9: Cannot find name 'optional'."
    file_path = "/home/user/vidurai/vidurai-vscode-extension/src/pythonBridge.ts"

    for i in range(50):
        memory.remember(
            content=error_message,
            metadata={
                'type': 'typescript_error',
                'file': file_path,
                'line': 9
            }
        )

        if (i + 1) % 10 == 0:
            print(f"  Stored {i + 1} errors...")

    print("✅ All errors processed")
    print()

    # Check aggregation metrics
    print("📊 Aggregation Metrics:")
    metrics = memory.get_aggregation_metrics()

    if metrics.get('enabled'):
        print(f"  ✅ Aggregation: ENABLED")
        print(f"  📦 Memories aggregated: {metrics['memories_aggregated']}")
        print(f"  🗜️  Occurrences consolidated: {metrics['occurrences_consolidated']}")
        print(f"  🚫 Duplicates prevented: {metrics['duplicates_prevented']}")
        print(f"  💾 Cache size: {metrics['cache_size']}")
        print(f"  📉 Compression ratio: {metrics['compression_ratio']:.2f}x")
    else:
        print(f"  ❌ Aggregation: {metrics.get('message', 'DISABLED')}")

    print()

    # Check database stats
    if memory.db:
        print("🗄️  Database Statistics:")
        stats = memory.db.get_statistics("/home/user/vidurai/vidurai-vscode-extension")

        print(f"  📊 Total memories: {stats['total']}")
        print(f"  📈 By salience:")
        for salience, count in stats['by_salience'].items():
            print(f"     {salience}: {count}")

    print()

    # Test with different error (should create new entry)
    print("📝 Testing with different error (should create new aggregation)...")
    different_error = "Error in pythonBridge.ts: Line 15: TypeError: Cannot read property 'x' of undefined."

    for i in range(20):
        memory.remember(
            content=different_error,
            metadata={
                'type': 'typescript_error',
                'file': file_path,
                'line': 15
            }
        )

    print("✅ Different error processed 20 times")
    print()

    # Final metrics
    print("📊 Final Aggregation Metrics:")
    metrics = memory.get_aggregation_metrics()

    if metrics.get('enabled'):
        print(f"  📦 Memories aggregated: {metrics['memories_aggregated']}")
        print(f"  🗜️  Occurrences consolidated: {metrics['occurrences_consolidated']}")
        print(f"  📉 Compression ratio: {metrics['compression_ratio']:.2f}x")

    print()

    # Query for pythonBridge errors
    if memory.db:
        print("🔍 Querying for pythonBridge.ts errors...")
        results = memory.db.recall_memories(
            project_path="/home/user/vidurai/vidurai-vscode-extension",
            query="pythonBridge",
            limit=10
        )

        print(f"  Found {len(results)} unique memory entries")
        print()

        if results:
            print("  📄 Sample results:")
            for i, mem in enumerate(results[:5], 1):
                gist = mem['gist']
                salience = mem['salience']
                tags = mem.get('tags', '[]')

                print(f"    {i}. [{salience}] {gist[:80]}...")
                if 'occurrences' in tags:
                    print(f"       Tags: {tags}")

    print()
    print("=" * 60)
    print("✅ TEST COMPLETE")
    print("=" * 60)


def test_salience_downgrade():
    """
    Test that repeated errors get downgraded from CRITICAL → MEDIUM → LOW → NOISE
    """
    print()
    print("=" * 60)
    print("🧪 TEST: Salience Downgrade on Repetition")
    print("=" * 60)
    print()

    memory = VismritiMemory(
        enable_aggregation=True,
        project_path="/home/user/vidurai/test"
    )

    error = "SyntaxError: Unexpected token"
    file_path = "/home/user/vidurai/test/test.py"

    # Store error multiple times and check salience
    test_points = [1, 3, 7, 15, 25]

    for i in range(1, 26):
        mem = memory.remember(
            content=error,
            metadata={
                'type': 'syntax_error',
                'file': file_path,
                'line': 42
            }
        )

        if i in test_points:
            print(f"  After {i:2d} occurrences: Salience = {mem.salience.name}")

    print()
    print("✅ Salience downgrade test complete")
    print()


if __name__ == "__main__":
    try:
        # Run tests
        test_typescript_error_aggregation()
        test_salience_downgrade()

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
