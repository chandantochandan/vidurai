"""
Test Script - Vismriti Phase 3-4 Components
Validates passive decay, active unlearning, and memory ledger

Run: python test_vismriti_phase3_4.py
"""

from datetime import datetime, timedelta

print("="*70)
print("VISMRITI v1.6.0 - PHASE 3-4 VALIDATION")
print("="*70)
print()

# Test 1: Import Phase 3-4 modules
print("Test 1: Importing Phase 3-4 modules...")
try:
    from vidurai.core.data_structures_v3 import Memory, SalienceLevel, MemoryStatus
    from vidurai.core.passive_decay import PassiveDecayEngine
    from vidurai.core.active_unlearning import ActiveUnlearningEngine
    from vidurai.core.memory_ledger import MemoryLedger
    print("✅ Successfully imported all Phase 3-4 modules")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 2: Create PassiveDecayEngine
print("\nTest 2: Creating PassiveDecayEngine...")
try:
    decay_engine = PassiveDecayEngine(enable_decay=True)
    print("✅ PassiveDecayEngine created")
    print(f"   Decay periods configured: {len(decay_engine.decay_periods)} salience levels")
    print(f"   Verbatim decay multiplier: {decay_engine.verbatim_decay_multiplier}")
    print(f"   Unused memory multiplier: {decay_engine.unused_multiplier}")
except Exception as e:
    print(f"❌ Creation failed: {e}")
    exit(1)

# Test 3: Test decay logic with different salience levels
print("\nTest 3: Testing decay logic...")
try:
    # Create test memories with different salience levels
    mem_critical = Memory(
        verbatim="API Key: abc123",
        gist="Store critical credential",
        salience=SalienceLevel.CRITICAL
    )

    mem_noise = Memory(
        verbatim="log: system startup",
        gist="System log",
        salience=SalienceLevel.NOISE
    )
    # Make it old enough to prune
    mem_noise.created_at = datetime.now() - timedelta(days=2)

    mem_low = Memory(
        verbatim="Hi there",
        gist="Greeting",
        salience=SalienceLevel.LOW
    )
    # Make it old enough to prune (7+ days)
    mem_low.created_at = datetime.now() - timedelta(days=8)

    mem_medium = Memory(
        verbatim="Working on dashboard",
        gist="Building dashboard component",
        salience=SalienceLevel.MEDIUM
    )
    # Not old enough to prune (< 90 days)
    mem_medium.created_at = datetime.now() - timedelta(days=10)

    # Test should_prune logic
    should_prune_critical = decay_engine.should_prune(mem_critical)
    should_prune_noise = decay_engine.should_prune(mem_noise)
    should_prune_low = decay_engine.should_prune(mem_low)
    should_prune_medium = decay_engine.should_prune(mem_medium)

    assert not should_prune_critical, "CRITICAL should never prune"
    assert should_prune_noise, "OLD NOISE should prune"
    assert should_prune_low, "OLD LOW should prune"
    assert not should_prune_medium, "YOUNG MEDIUM should not prune"

    print("✅ CRITICAL: Never prunes (protected)")
    print("✅ NOISE (2 days old): Prunes (threshold: 1 day)")
    print("✅ LOW (8 days old): Prunes (threshold: 7 days)")
    print("✅ MEDIUM (10 days old): Doesn't prune (threshold: 90 days)")

except Exception as e:
    print(f"❌ Decay logic test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 4: Test verbatim-only accelerated decay
print("\nTest 4: Testing verbatim-only accelerated decay...")
try:
    mem_verbatim_only = Memory(
        verbatim="Some raw verbatim text without gist extraction",
        gist="",
        salience=SalienceLevel.LOW
    )
    # Make it 5 days old (normally wouldn't prune, but verbatim-only should)
    mem_verbatim_only.created_at = datetime.now() - timedelta(days=5)

    decay_info = decay_engine.get_decay_info(mem_verbatim_only)
    print(f"   Verbatim-only memory info:")
    print(f"   - Age: {decay_info['age_days']} days")
    print(f"   - Decay threshold: {decay_info['decay_threshold_days']} days")
    print(f"   - Accelerated: {decay_info['modifiers']['verbatim_only']}")

    # Low salience = 7 days, but verbatim-only = 7 * 0.3 = 2.1 days
    # So 5 days old should prune
    should_prune = decay_engine.should_prune(mem_verbatim_only)
    assert should_prune, "Verbatim-only should prune faster"

    print("✅ Verbatim-only accelerated decay works (70% faster)")

except Exception as e:
    print(f"❌ Verbatim-only test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 5: Test batch pruning
print("\nTest 5: Testing batch pruning...")
try:
    memories = [
        Memory(
            verbatim="Critical data",
            gist="Critical",
            salience=SalienceLevel.CRITICAL
        ),
        Memory(
            verbatim="log: event",
            gist="Log",
            salience=SalienceLevel.NOISE
        ),
        Memory(
            verbatim="log: event2",
            gist="Log2",
            salience=SalienceLevel.NOISE
        ),
    ]

    # Make noise memories old enough to prune
    memories[1].created_at = datetime.now() - timedelta(days=2)
    memories[2].created_at = datetime.now() - timedelta(days=2)

    stats = decay_engine.prune_batch(memories)

    print(f"   Total evaluated: {stats['total_evaluated']}")
    print(f"   Pruned: {stats['pruned']}")
    print(f"   By salience: {stats['by_salience']}")

    assert stats['total_evaluated'] == 3, "Should evaluate 3 memories"
    assert stats['pruned'] == 2, "Should prune 2 NOISE memories"
    assert memories[0].status == MemoryStatus.ACTIVE, "Critical should remain active"
    assert memories[1].status == MemoryStatus.PRUNED, "Noise should be pruned"
    assert memories[2].status == MemoryStatus.PRUNED, "Noise should be pruned"

    print("✅ Batch pruning works correctly")

except Exception as e:
    print(f"❌ Batch pruning test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 6: Create ActiveUnlearningEngine
print("\nTest 6: Creating ActiveUnlearningEngine...")
try:
    unlearn_engine = ActiveUnlearningEngine(rl_agent=None)
    print("✅ ActiveUnlearningEngine created")
except Exception as e:
    print(f"❌ Creation failed: {e}")
    exit(1)

# Test 7: Test active unlearning
print("\nTest 7: Testing active unlearning...")
try:
    memories_to_unlearn = [
        Memory(
            verbatim="Unwanted memory 1",
            gist="Unwanted 1",
            salience=SalienceLevel.MEDIUM
        ),
        Memory(
            verbatim="Unwanted memory 2",
            gist="Unwanted 2",
            salience=SalienceLevel.LOW
        )
    ]

    # Test simple_suppress method (doesn't need RL agent)
    stats = unlearn_engine.forget(
        memories_to_unlearn,
        method="simple_suppress",
        explanation="User requested to forget unwanted memories"
    )

    print(f"   Memories processed: {stats['memories_processed']}")
    print(f"   Unlearned: {stats['unlearned']}")
    print(f"   Failed: {stats['failed']}")
    print(f"   Method: {stats['method']}")

    assert stats['unlearned'] == 2, "Should unlearn 2 memories"
    assert memories_to_unlearn[0].status == MemoryStatus.UNLEARNED, "Should be unlearned"
    assert memories_to_unlearn[1].status == MemoryStatus.UNLEARNED, "Should be unlearned"
    assert memories_to_unlearn[0].salience == SalienceLevel.NOISE, "Should downgrade to NOISE"

    print("✅ Active unlearning (simple_suppress) works")

except Exception as e:
    print(f"❌ Active unlearning test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 8: Test unlearning explanation
print("\nTest 8: Testing unlearning explanations...")
try:
    mem_unlearned = memories_to_unlearn[0]
    explanation = unlearn_engine.explain_unlearning(mem_unlearned)

    print(f"   Memory: '{mem_unlearned.gist}'")
    print(f"   Status: {mem_unlearned.status}")
    print(f"   Explanation: {explanation}")

    assert "suppressed" in explanation.lower() or "unlearned" in explanation.lower()

    print("✅ Unlearning explanation generation works")

except Exception as e:
    print(f"❌ Explanation test failed: {e}")
    exit(1)

# Test 9: Create MemoryLedger
print("\nTest 9: Creating MemoryLedger...")
try:
    # Create diverse set of memories
    test_memories = [
        Memory(
            verbatim="Remember API key abc123",
            gist="Store API key",
            salience=SalienceLevel.CRITICAL
        ),
        Memory(
            verbatim="Fixed authentication bug",
            gist="Fixed auth bug",
            salience=SalienceLevel.HIGH
        ),
        Memory(
            verbatim="Working on dashboard",
            gist="Building dashboard",
            salience=SalienceLevel.MEDIUM
        ),
        Memory(
            verbatim="Hi there",
            gist="Greeting",
            salience=SalienceLevel.LOW
        )
    ]

    # Mark one as pruned
    test_memories[3].status = MemoryStatus.PRUNED
    test_memories[3].created_at = datetime.now() - timedelta(days=10)

    ledger = MemoryLedger(test_memories, decay_engine=decay_engine)
    print("✅ MemoryLedger created with 4 memories")

except Exception as e:
    print(f"❌ MemoryLedger creation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 10: Test ledger DataFrame generation
print("\nTest 10: Testing ledger DataFrame generation...")
try:
    # Get ledger (should exclude pruned by default)
    df = ledger.get_ledger(include_pruned=False)

    print(f"   Active memories in ledger: {len(df)}")
    assert len(df) == 3, "Should have 3 active memories"

    # Get ledger with pruned
    df_all = ledger.get_ledger(include_pruned=True)

    print(f"   All memories in ledger: {len(df_all)}")
    assert len(df_all) == 4, "Should have 4 total memories"

    # Check columns
    expected_columns = [
        "Gist", "Verbatim Preview", "Status", "Salience Score",
        "Salience Level", "Forgetting Mechanism", "Age (days)",
        "Last Accessed", "Access Count", "Engram ID"
    ]

    for col in expected_columns:
        assert col in df.columns, f"Missing column: {col}"

    print("✅ DataFrame generation works with correct columns")

    # Show sample
    print("\n   Sample ledger row:")
    if not df.empty:
        first_row = df.iloc[0]
        print(f"   - Gist: {first_row['Gist']}")
        print(f"   - Salience: {first_row['Salience Level']}")
        print(f"   - Status: {first_row['Status']}")
        print(f"   - Forgetting Mechanism: {first_row['Forgetting Mechanism']}")

except Exception as e:
    print(f"❌ DataFrame test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 11: Test ledger statistics
print("\nTest 11: Testing ledger statistics...")
try:
    stats = ledger.get_statistics()

    print(f"   Total memories: {stats['total_memories']}")
    print(f"   Active: {stats['active_memories']}")
    print(f"   Forgotten: {stats['forgotten_memories']}")
    print(f"   By status: {stats['by_status']}")
    print(f"   By salience: {stats['by_salience']}")

    assert stats['total_memories'] == 4
    assert stats['active_memories'] == 3
    assert stats['forgotten_memories'] == 1

    print("✅ Statistics generation works")

except Exception as e:
    print(f"❌ Statistics test failed: {e}")
    exit(1)

# Test 12: Test CSV export
print("\nTest 12: Testing CSV export...")
try:
    import os
    import tempfile

    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv') as f:
        temp_path = f.name

    # Export
    exported_path = ledger.export_csv(temp_path, include_pruned=True)

    # Verify file exists
    assert os.path.exists(exported_path), "CSV file should exist"

    # Read back
    import pandas as pd
    df_read = pd.read_csv(exported_path)
    assert len(df_read) == 4, "Should have 4 rows in CSV"

    print(f"✅ CSV export works: {exported_path}")
    print(f"   Rows exported: {len(df_read)}")

    # Cleanup
    os.unlink(exported_path)

except Exception as e:
    print(f"❌ CSV export test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 13: Test ledger summary printing
print("\nTest 13: Testing ledger summary...")
try:
    print("\n   --- Ledger Summary Output ---")
    ledger.print_summary()
    print("   --- End of Summary ---")

    print("✅ Summary printing works")

except Exception as e:
    print(f"❌ Summary test failed: {e}")
    exit(1)

# Summary
print("\n" + "="*70)
print("PHASE 3-4 VALIDATION COMPLETE")
print("="*70)
print("✅ All imports successful")
print("✅ PassiveDecayEngine functional")
print("   - Differential decay rates working")
print("   - Verbatim-only acceleration working")
print("   - Batch pruning working")
print("✅ ActiveUnlearningEngine functional")
print("   - Simple suppress working")
print("   - Explanation generation working")
print("✅ MemoryLedger functional")
print("   - DataFrame generation working")
print("   - Statistics working")
print("   - CSV export working")
print()
print("Ready for Part 3 (VismritiMemory Integration)")
print("="*70)
