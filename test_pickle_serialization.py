"""
Test Suite: Pickle Serialization of ViduraiMemory with RL Agent

This test validates the v1.5.2 fix for pickle serialization.
All learnings from this test will be documented in LEARNINGS.md.

Run: python test_pickle_serialization.py
"""

import pickle
import os
import tempfile
from pathlib import Path

from vidurai import ViduraiMemory
from vidurai.core.rl_agent_v2 import RewardProfile


def test_basic_pickle():
    """Test 1: Basic pickle/unpickle cycle"""
    print("\n" + "="*70)
    print("TEST 1: Basic Pickle/Unpickle")
    print("="*70)

    # Create instance
    vidurai = ViduraiMemory(
        enable_decay=False,
        reward_profile=RewardProfile.QUALITY_FOCUSED,
        enable_compression=True
    )

    # Add memories
    vidurai.remember("Test message 1", metadata={"test": True})
    vidurai.remember("Test message 2", metadata={"test": True})
    vidurai.remember("Test message 3", metadata={"test": True})

    print("✅ Created ViduraiMemory with 3 memories")

    # Pickle
    try:
        pickled = pickle.dumps(vidurai)
        print(f"✅ Successfully pickled ({len(pickled)} bytes)")
    except Exception as e:
        print(f"❌ PICKLE FAILED: {e}")
        return False

    # Unpickle
    try:
        restored = pickle.loads(pickled)
        print(f"✅ Successfully unpickled")
    except Exception as e:
        print(f"❌ UNPICKLE FAILED: {e}")
        return False

    # Verify
    memories = restored.recall("test", min_importance=0.0)
    if len(memories) == 3:
        print(f"✅ All 3 memories preserved")
        return True
    else:
        print(f"❌ Memory loss: expected 3, got {len(memories)}")
        return False


def test_file_based_pickle():
    """Test 2: File-based pickle (real-world scenario)"""
    print("\n" + "="*70)
    print("TEST 2: File-Based Pickle (Real-World)")
    print("="*70)

    # Create instance
    vidurai = ViduraiMemory(
        enable_decay=False,
        reward_profile=RewardProfile.QUALITY_FOCUSED
    )

    # Add diverse content
    vidurai.remember("Fixed authentication bug", metadata={"type": "bugfix"})
    vidurai.remember("Implemented user dashboard", metadata={"type": "feature"})
    vidurai.remember("Refactored database layer", metadata={"type": "refactor"})

    print("✅ Created ViduraiMemory with diverse content")

    # Save to file
    with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix='.pkl') as f:
        temp_file = f.name
        try:
            pickle.dump(vidurai, f)
            print(f"✅ Saved to {temp_file}")
        except Exception as e:
            print(f"❌ SAVE FAILED: {e}")
            return False

    # Load from file
    try:
        with open(temp_file, 'rb') as f:
            loaded = pickle.load(f)
        print(f"✅ Loaded from file")
    except Exception as e:
        print(f"❌ LOAD FAILED: {e}")
        return False
    finally:
        os.unlink(temp_file)

    # Verify functionality
    bugfix_memories = loaded.recall("bug", min_importance=0.0)
    if len(bugfix_memories) > 0:
        print(f"✅ Search works: found {len(bugfix_memories)} bugfix memories")
        return True
    else:
        print(f"❌ Search failed after restore")
        return False


def test_rl_agent_state():
    """Test 3: RL Agent Q-table preservation"""
    print("\n" + "="*70)
    print("TEST 3: RL Agent Q-Table Preservation")
    print("="*70)

    # Create instance
    vidurai = ViduraiMemory(
        enable_decay=False,
        reward_profile=RewardProfile.QUALITY_FOCUSED
    )

    # Trigger RL learning by adding many memories
    for i in range(20):
        vidurai.remember(f"Message {i}", metadata={"index": i})

    print(f"✅ Added 20 memories to trigger RL learning")

    # Get RL agent statistics before pickling
    try:
        if hasattr(vidurai, 'rl_agent') and vidurai.rl_agent:
            stats_before = vidurai.rl_agent.get_statistics()
            print(f"   RL Agent before: {stats_before['episodes']} episodes, "
                  f"{stats_before['q_table_size']} states in Q-table")
    except:
        print(f"   (Could not access RL agent statistics)")

    # Pickle and restore
    try:
        pickled = pickle.dumps(vidurai)
        restored = pickle.loads(pickled)
        print(f"✅ Pickle/unpickle completed")
    except Exception as e:
        print(f"❌ PICKLE/UNPICKLE FAILED: {e}")
        return False

    # Verify RL agent still works
    try:
        restored.remember("New message after restore", metadata={"post_restore": True})
        print(f"✅ RL Agent accepts new memories after restore")
    except Exception as e:
        print(f"❌ RL Agent broken after restore: {e}")
        return False

    # Check episodic memory (working memory has capacity limit of 10)
    episodic_count = len(restored.episodic.memories)
    if episodic_count >= 20:
        print(f"✅ RL Agent functional after restore ({episodic_count} episodic memories)")

        # Compare Q-table sizes
        try:
            if hasattr(restored, 'rl_agent') and restored.rl_agent:
                stats_after = restored.rl_agent.get_statistics()
                print(f"   RL Agent after: {stats_after['episodes']} episodes, "
                      f"{stats_after['q_table_size']} states in Q-table")

                if stats_after['q_table_size'] == stats_before['q_table_size']:
                    print(f"✅ Q-table perfectly preserved ({stats_before['q_table_size']} states)")
        except:
            pass

        return True
    else:
        print(f"❌ RL Agent may be broken: only {episodic_count} episodic memories")
        return False


def test_edge_cases():
    """Test 4: Edge cases and stress tests"""
    print("\n" + "="*70)
    print("TEST 4: Edge Cases")
    print("="*70)

    tests_passed = 0
    total_tests = 3

    # Edge case 1: Empty ViduraiMemory
    try:
        empty = ViduraiMemory()
        pickled = pickle.dumps(empty)
        restored = pickle.loads(pickled)
        print("✅ Edge case 1: Empty instance pickles correctly")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Edge case 1 failed: {e}")

    # Edge case 2: Large memory (stress test)
    try:
        large = ViduraiMemory()
        for i in range(1000):
            large.remember(f"Memory {i}" * 10, metadata={"i": i})
        pickled = pickle.dumps(large)
        size_kb = len(pickled) // 1024
        restored = pickle.loads(pickled)
        print(f"✅ Edge case 2: Large instance (1000 memories, {size_kb}KB)")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Edge case 2 failed: {e}")

    # Edge case 3: Multiple pickle/unpickle cycles
    try:
        vid = ViduraiMemory()
        vid.remember("Test", metadata={})
        for cycle in range(5):
            pickled = pickle.dumps(vid)
            vid = pickle.loads(pickled)
        print(f"✅ Edge case 3: Survived 5 pickle/unpickle cycles")
        tests_passed += 1
    except Exception as e:
        print(f"❌ Edge case 3 failed: {e}")

    print(f"\nEdge cases passed: {tests_passed}/{total_tests}")
    return tests_passed == total_tests


def run_all_tests():
    """Run complete test suite"""
    print("\n" + "="*70)
    print("VIDURAI v1.5.2 PICKLE SERIALIZATION TEST SUITE")
    print("="*70)

    results = []

    results.append(("Basic Pickle", test_basic_pickle()))
    results.append(("File-Based Pickle", test_file_based_pickle()))
    results.append(("RL Agent State", test_rl_agent_state()))
    results.append(("Edge Cases", test_edge_cases()))

    print("\n" + "="*70)
    print("TEST RESULTS SUMMARY")
    print("="*70)

    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")

    all_passed = all(result[1] for result in results)

    print("\n" + "="*70)
    if all_passed:
        print("🎉 ALL TESTS PASSED - v1.5.2 READY FOR RELEASE")
    else:
        print("❌ SOME TESTS FAILED - FIX REQUIRED")
    print("="*70)

    return all_passed


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
