"""
Comprehensive Integration Tests for VismritiMemory v1.6.0

Tests all four phases of the Vismriti Architecture:
- Phase 1: Gist/Verbatim Split
- Phase 2: Salience Classification
- Phase 3A: Passive Decay
- Phase 3B: Active Unlearning
- Phase 4: Memory Ledger

जय विदुराई! 🕉️
"""

import sys
import os
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vidurai.vismriti_memory import VismritiMemory
from vidurai.core.data_structures_v3 import SalienceLevel, MemoryStatus


class TestPhase2SalienceClassification:
    """Test Phase 2: Salience Tagging"""

    def test_critical_salience(self):
        """Test CRITICAL salience classification"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        # Explicit "remember this" should be CRITICAL
        mem = memory_sys.remember("Remember this API key: sk-test-123")
        assert mem.salience == SalienceLevel.CRITICAL

        # Credentials metadata should be CRITICAL
        mem2 = memory_sys.remember(
            "My password",
            metadata={"type": "credential"}
        )
        assert mem2.salience == SalienceLevel.CRITICAL

        print("✅ CRITICAL salience classification works")

    def test_high_salience(self):
        """Test HIGH salience classification"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        # Bug fix should be HIGH
        mem = memory_sys.remember(
            "Finally fixed the authentication bug!",
            metadata={"solved_bug": True}
        )
        assert mem.salience == SalienceLevel.HIGH

        print("✅ HIGH salience classification works")

    def test_low_salience(self):
        """Test LOW salience classification"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        # Casual greeting should be LOW
        mem = memory_sys.remember("Hello there")
        assert mem.salience == SalienceLevel.LOW

        print("✅ LOW salience classification works")

    def test_noise_salience(self):
        """Test NOISE salience classification"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        # System log should be NOISE
        mem = memory_sys.remember(
            "Log: 2024-11-07 12:34:56 - INFO",
            metadata={"type": "system_log"}
        )
        assert mem.salience == SalienceLevel.NOISE

        print("✅ NOISE salience classification works")

    def test_manual_salience_override(self):
        """Test manual salience override"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        # Override automatic classification
        mem = memory_sys.remember(
            "Casual text",
            salience=SalienceLevel.CRITICAL
        )
        assert mem.salience == SalienceLevel.CRITICAL

        print("✅ Manual salience override works")


class TestPhase3APassiveDecay:
    """Test Phase 3A: Passive Decay (Synaptic Pruning)"""

    def test_decay_disabled(self):
        """Test that decay doesn't happen when disabled"""
        memory_sys = VismritiMemory(enable_decay=False)

        # Add old, low-salience memory
        mem = memory_sys.remember("Test", salience=SalienceLevel.LOW)

        # Manually set old creation time
        mem.created_at = datetime.now() - timedelta(days=30)

        # Run decay cycle
        stats = memory_sys.run_decay_cycle()

        assert stats["pruned"] == 0
        assert mem.status == MemoryStatus.ACTIVE

        print("✅ Decay disabled works")

    def test_noise_decay_fast(self):
        """Test NOISE memories decay within 1 day"""
        memory_sys = VismritiMemory(enable_decay=True)

        # Add NOISE memory
        mem = memory_sys.remember("Log entry", salience=SalienceLevel.NOISE)

        # Simulate 2 days ago
        mem.created_at = datetime.now() - timedelta(days=2)

        # Run decay
        stats = memory_sys.run_decay_cycle()

        assert stats["pruned"] >= 1
        assert mem.status == MemoryStatus.PRUNED

        print("✅ NOISE memory decay (1 day) works")

    def test_low_decay_medium(self):
        """Test LOW memories decay within 7 days"""
        memory_sys = VismritiMemory(enable_decay=True)

        mem = memory_sys.remember("Casual", salience=SalienceLevel.LOW)
        mem.created_at = datetime.now() - timedelta(days=8)

        stats = memory_sys.run_decay_cycle()

        assert mem.status == MemoryStatus.PRUNED

        print("✅ LOW memory decay (7 days) works")

    def test_critical_never_decays(self):
        """Test CRITICAL memories never decay"""
        memory_sys = VismritiMemory(enable_decay=True)

        mem = memory_sys.remember(
            "Remember this forever",
            salience=SalienceLevel.CRITICAL
        )
        mem.created_at = datetime.now() - timedelta(days=365)  # 1 year old

        stats = memory_sys.run_decay_cycle()

        assert mem.status == MemoryStatus.ACTIVE  # Still active!

        print("✅ CRITICAL memory protection works")

    def test_verbatim_only_decay_faster(self):
        """Test verbatim-only memories decay faster than gist+verbatim"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        # Verbatim-only (no gist extraction)
        mem_verbatim_only = memory_sys.remember(
            "Verbatim only",
            salience=SalienceLevel.MEDIUM,
            extract_gist=False
        )

        # Make verbatim empty to create verbatim-only scenario
        mem_verbatim_only.gist = ""
        mem_verbatim_only.verbatim = "Verbatim only"

        # Should decay faster (30% of normal)
        # MEDIUM normally decays in 90 days
        # Verbatim-only should decay in ~27 days
        mem_verbatim_only.created_at = datetime.now() - timedelta(days=30)

        stats = memory_sys.run_decay_cycle()

        # Should be pruned (30 > 27 days)
        assert mem_verbatim_only.status == MemoryStatus.PRUNED

        print("✅ Verbatim-only faster decay works")


class TestPhase3BActiveUnlearning:
    """Test Phase 3B: Active Unlearning (Motivated Forgetting)"""

    def test_forget_with_confirmation(self):
        """Test forget requires confirmation by default"""
        memory_sys = VismritiMemory()

        memory_sys.remember("Temporary test data 123")
        memory_sys.remember("Temporary test data 456")

        # Without confirmation=False, should not forget
        result = memory_sys.forget("temporary")

        assert result["confirmation_required"] == True
        assert result["unlearned"] == 0

        print("✅ Forget confirmation safety works")

    def test_forget_simple_suppress(self):
        """Test active forgetting with simple suppress"""
        memory_sys = VismritiMemory()

        mem1 = memory_sys.remember("Forget me please")
        mem2 = memory_sys.remember("Keep this one")

        # Forget with confirmation=False
        result = memory_sys.forget(
            "forget me",
            method="simple_suppress",
            confirmation=False
        )

        assert result["unlearned"] >= 1
        assert mem1.status == MemoryStatus.UNLEARNED
        assert mem2.status == MemoryStatus.ACTIVE  # Should not be affected

        print("✅ Active unlearning (simple_suppress) works")

    def test_forget_excludes_from_recall(self):
        """Test forgotten memories don't appear in recall"""
        memory_sys = VismritiMemory()

        memory_sys.remember("Secret data ABC")

        # Verify it's recallable
        results_before = memory_sys.recall("secret")
        assert len(results_before) >= 1

        # Forget it
        memory_sys.forget("secret", confirmation=False)

        # Should not be in recall results
        results_after = memory_sys.recall("secret", include_forgotten=False)
        assert len(results_after) == 0

        # But should appear if we explicitly include forgotten
        results_with_forgotten = memory_sys.recall("secret", include_forgotten=True)
        assert len(results_with_forgotten) >= 1

        print("✅ Forgotten memories excluded from recall")


class TestPhase4MemoryLedger:
    """Test Phase 4: Memory Ledger (Transparency)"""

    def test_get_ledger_dataframe(self):
        """Test ledger returns DataFrame"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        memory_sys.remember("Test 1", salience=SalienceLevel.CRITICAL)
        memory_sys.remember("Test 2", salience=SalienceLevel.LOW)

        ledger = memory_sys.get_ledger(format="dataframe")

        assert len(ledger) == 2
        assert "Gist" in ledger.columns
        assert "Salience Score" in ledger.columns
        assert "Forgetting Mechanism" in ledger.columns

        print("✅ Memory ledger DataFrame works")

    def test_ledger_export_csv(self):
        """Test ledger CSV export"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        memory_sys.remember("Export test")

        filepath = memory_sys.export_ledger("/tmp/test_ledger_v160.csv")

        # Verify file exists
        import os
        assert os.path.exists(filepath)

        # Cleanup
        os.remove(filepath)

        print("✅ Ledger CSV export works")

    def test_get_statistics(self):
        """Test statistics generation"""
        memory_sys = VismritiMemory(enable_gist_extraction=False)

        memory_sys.remember("Test 1", salience=SalienceLevel.CRITICAL)
        memory_sys.remember("Test 2", salience=SalienceLevel.LOW)
        memory_sys.forget("test 2", confirmation=False)

        stats = memory_sys.get_statistics()

        assert stats["total_memories"] == 2
        assert stats["active_memories"] == 1
        assert stats["forgotten_memories"] == 1

        print("✅ Statistics generation works")


class TestEndToEndIntegration:
    """End-to-end integration tests"""

    def test_complete_workflow(self):
        """Test complete workflow: remember → recall → forget → decay"""
        print("\n" + "="*60)
        print("COMPLETE WORKFLOW TEST")
        print("="*60)

        memory_sys = VismritiMemory(
            enable_gist_extraction=False,
            enable_decay=True
        )

        # 1. Remember different types of memories
        print("\n1. Remembering...")
        mem_critical = memory_sys.remember(
            "Remember my API key: sk-test-123",
            salience=SalienceLevel.CRITICAL
        )
        mem_high = memory_sys.remember(
            "Fixed the auth bug in auth.py",
            metadata={"solved_bug": True}
        )
        mem_low = memory_sys.remember("Hello there")
        mem_noise = memory_sys.remember(
            "Log: Debug trace",
            metadata={"type": "system_log"}
        )

        print(f"   Stored 4 memories")
        print(f"   CRITICAL: {mem_critical.gist}")
        print(f"   HIGH: {mem_high.gist}")
        print(f"   LOW: {mem_low.gist}")
        print(f"   NOISE: {mem_noise.gist}")

        # 2. Recall
        print("\n2. Recalling...")
        results = memory_sys.recall("auth")
        print(f"   Found {len(results)} memories about 'auth'")
        assert len(results) >= 1

        # 3. Active forgetting
        print("\n3. Actively forgetting...")
        memory_sys.forget("hello", confirmation=False)
        print(f"   Forgot memories matching 'hello'")
        assert mem_low.status == MemoryStatus.UNLEARNED

        # 4. Passive decay
        print("\n4. Running decay cycle...")
        # Make NOISE memory old
        mem_noise.created_at = datetime.now() - timedelta(days=2)
        stats = memory_sys.run_decay_cycle()
        print(f"   Pruned {stats['pruned']} old memories")
        assert mem_noise.status == MemoryStatus.PRUNED

        # 5. Memory ledger
        print("\n5. Checking memory ledger...")
        ledger = memory_sys.get_ledger(include_pruned=True)
        print(f"   Ledger has {len(ledger)} total entries")
        print("\n   Ledger preview:")
        print(ledger[["Gist", "Status", "Salience Level", "Forgetting Mechanism"]].to_string())

        # 6. Verify protections
        print("\n6. Verifying protections...")
        assert mem_critical.status == MemoryStatus.ACTIVE  # CRITICAL never decays
        assert mem_high.status == MemoryStatus.ACTIVE      # HIGH still active
        print(f"   ✅ CRITICAL memory protected")
        print(f"   ✅ HIGH memory still active")

        print("\n" + "="*60)
        print("✅ COMPLETE WORKFLOW TEST PASSED")
        print("="*60)

    def test_pickle_serialization(self):
        """Test that VismritiMemory can be pickled (v1.5.2 fix)"""
        import pickle

        memory_sys = VismritiMemory(enable_gist_extraction=False)
        memory_sys.remember("Test memory")

        # Pickle
        pickled = pickle.dumps(memory_sys)

        # Unpickle
        restored = pickle.loads(pickled)

        assert len(restored.memories) == 1
        assert restored.memories[0].gist == "Test memory"

        print("✅ Pickle serialization works (v1.5.2 fix validated)")


def run_all_tests():
    """Run all test classes"""
    print("\n" + "="*70)
    print("VIDURAI v1.6.0 - VISMRITI ARCHITECTURE TEST SUITE")
    print("="*70)

    test_classes = [
        TestPhase2SalienceClassification(),
        TestPhase3APassiveDecay(),
        TestPhase3BActiveUnlearning(),
        TestPhase4MemoryLedger(),
        TestEndToEndIntegration()
    ]

    total_tests = 0
    passed_tests = 0

    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n{'='*70}")
        print(f"Running: {class_name}")
        print('='*70)

        # Get all test methods
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]

        for method_name in test_methods:
            total_tests += 1
            print(f"\n{method_name}...")
            try:
                method = getattr(test_class, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                print(f"❌ FAILED: {e}")
                import traceback
                traceback.print_exc()

    # Summary
    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)
    print(f"Total tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")

    if passed_tests == total_tests:
        print("\n🎉 ALL TESTS PASSED - v1.6.0 READY FOR RELEASE")
    else:
        print(f"\n❌ {total_tests - passed_tests} TESTS FAILED")

    print("="*70 + "\n")

    return passed_tests == total_tests


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
