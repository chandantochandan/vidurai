"""
Verify Bug #2 Fix: High-Threshold Recall with Configurable Decay
"""

from vidurai.core.koshas import ViduraiMemory


def test_high_threshold_recall():
    """Test that high-importance memories can be recalled with high thresholds"""
    print("=" * 70)
    print("BUG #2 VERIFICATION: High-Threshold Recall with No Decay")
    print("=" * 70)

    # Create memory system with decay DISABLED
    print("\n🔧 Creating memory system with enable_decay=False...")
    memory = ViduraiMemory(
        enable_compression=False,  # Disable compression for simpler testing
        enable_rl_agent=False,     # Disable RL agent for simpler testing
        enable_decay=False         # BUGFIX: Disable decay for high-threshold recall
    )

    # Add high-importance messages
    high_importance_messages = [
        "Critical user information: username is john_doe",
        "Important API key: sk-1234567890",
        "User preference: dark mode enabled",
        "Critical setting: notifications are on",
    ]

    print(f"\n✅ Adding {len(high_importance_messages)} HIGH importance messages (0.9)...")
    for msg in high_importance_messages:
        memory.remember(msg, importance=0.9)

    # Add many low-importance messages to trigger decay in episodic layer
    print(f"\n✅ Adding 20 LOW importance messages to trigger episodic decay...")
    for i in range(20):
        memory.remember(f"Low importance message number {i}", importance=0.4)

    # Now try to recall with high threshold
    print(f"\n🔍 Attempting recall with min_importance=0.7...")
    recalled = memory.recall(min_importance=0.7, limit=10)

    print(f"\n📊 Results:")
    print(f"  Recalled {len(recalled)} memories")

    # Check if we got the high-importance messages
    high_imp_count = sum(1 for m in recalled if m.importance >= 0.7)
    print(f"  High importance memories (>=0.7): {high_imp_count}")

    # Print details
    print(f"\n📝 Recalled memories:")
    for i, mem in enumerate(recalled, 1):
        content_preview = mem.content[:50] + "..." if len(mem.content) > 50 else mem.content
        print(f"  {i}. [{mem.importance:.3f}] {content_preview}")

    # Verify success
    expected_count = len(high_importance_messages)
    if high_imp_count >= expected_count:
        print(f"\n✅ BUG #2 FIXED: All {expected_count} high-importance memories recalled!")
        print(f"  Decay was properly disabled, importance stayed at 0.9")
        return True
    else:
        print(f"\n❌ BUG #2 NOT FIXED: Only {high_imp_count}/{expected_count} high-importance memories recalled")
        print(f"  Importance likely decayed despite enable_decay=False")
        return False


def test_custom_decay_rate():
    """Test that custom decay rates work correctly"""
    print("\n" + "=" * 70)
    print("BUG #2 BONUS: Custom Decay Rate")
    print("=" * 70)

    # Create memory system with slower decay
    print("\n🔧 Creating memory system with decay_rate=0.99 (slower decay)...")
    memory = ViduraiMemory(
        enable_compression=False,
        enable_rl_agent=False,
        decay_rate=0.99,  # Much slower decay
        enable_decay=True
    )

    # Add high-importance message
    print(f"\n✅ Adding 1 HIGH importance message (0.85)...")
    memory.remember("Critical information", importance=0.85)

    # Add 10 messages to trigger some decay
    print(f"\n✅ Adding 10 more messages to trigger decay...")
    for i in range(10):
        memory.remember(f"Message {i}", importance=0.5)

    # Check importance after decay
    recalled = memory.recall(min_importance=0.0, limit=20)
    critical_mem = [m for m in recalled if "Critical information" in m.content]

    if critical_mem:
        final_importance = critical_mem[0].importance
        print(f"\n📊 Results:")
        print(f"  Original importance: 0.85")
        print(f"  Final importance: {final_importance:.4f}")
        print(f"  Expected with 0.99 decay over 10 steps: {0.85 * (0.99 ** 10):.4f}")

        # With decay_rate=0.99 over 10 steps: 0.85 * 0.99^10 ≈ 0.769
        # Should still be above 0.7 threshold
        if final_importance >= 0.7:
            print(f"\n✅ Custom decay rate working: importance stayed above 0.7")
            return True
        else:
            print(f"\n⚠️  Decay too aggressive, dropped below 0.7")
            return False
    else:
        print(f"\n❌ Critical memory not found!")
        return False


if __name__ == "__main__":
    print("\n")
    result1 = test_high_threshold_recall()
    result2 = test_custom_decay_rate()

    print("\n" + "=" * 70)
    if result1 and result2:
        print("✅ ALL BUG #2 VERIFICATIONS PASSED")
    elif result1:
        print("✅ BUG #2 MAIN FIX VERIFIED (custom decay needs tuning)")
    else:
        print("❌ BUG #2 VERIFICATION FAILED")
    print("=" * 70)
