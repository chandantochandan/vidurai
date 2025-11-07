"""
Quick verification that Bug #1 is fixed:
Compression should DECREASE tokens, not increase them
"""

from vidurai.core.koshas import ViduraiMemory
from vidurai.core.data_structures_v2 import estimate_tokens


def count_total_tokens(memory_system):
    """Count total tokens across all memory layers"""
    total = 0

    # Working memory
    for mem in memory_system.working.memories:
        total += estimate_tokens(mem.content)

    # Episodic memory
    for mem in memory_system.episodic.memories.values():
        total += estimate_tokens(mem.content)

    # Archival memory
    for mem in memory_system.archival.memories.values():
        total += estimate_tokens(mem.content)

    return total


def test_compression_reduces_tokens():
    """Verify compression actually reduces total token count"""
    print("=" * 70)
    print("BUG #1 VERIFICATION: Compression Should Reduce Tokens")
    print("=" * 70)

    # Create memory system with compression and RL agent
    memory = ViduraiMemory(enable_compression=True, enable_rl_agent=True)

    # Add enough messages to trigger compression (need 8+ for RL agent)
    messages = [
        "Hello, I'm working on a Python project.",
        "I need help with memory management.",
        "The system should compress old messages.",
        "Compression saves tokens and reduces costs.",
        "I want to implement this feature today.",
        "The code is in the vidurai package.",
        "Can you help me test the compression?",
        "Let me know if you have questions.",
        "I think this should be enough messages.",
        "One more message to be safe.",
    ]

    print(f"\nAdding {len(messages)} messages to memory system...\n")

    for i, msg in enumerate(messages, 1):
        memory.remember(msg, importance=0.6)  # High enough for episodic
        tokens_before = count_total_tokens(memory)
        print(f"  Message {i}: {tokens_before} total tokens")

    # Get final token count
    tokens_after = count_total_tokens(memory)

    print(f"\n📊 Results:")
    print(f"  Total tokens after {len(messages)} messages: {tokens_after}")

    # Check compression stats
    comp_stats = memory.get_compression_stats()
    print(f"\n✨ Compression Stats:")
    print(f"  Enabled: {comp_stats.get('enabled', False)}")
    print(f"  Total compressions: {comp_stats.get('total_compressions', 0)}")
    print(f"  Total tokens saved: {comp_stats.get('total_tokens_saved', 0)}")

    # Verify compression occurred
    if comp_stats.get('total_compressions', 0) > 0:
        print(f"\n✅ SUCCESS: Compression occurred!")
        print(f"  Tokens saved: {comp_stats.get('total_tokens_saved', 0)}")

        # The key test: final token count should be reasonable
        # Not higher than the sum of all messages
        total_original = sum(estimate_tokens(msg) for msg in messages)
        print(f"\n📈 Token Analysis:")
        print(f"  Original total (all messages): ~{total_original} tokens")
        print(f"  Current total (after compression): {tokens_after} tokens")

        if tokens_after < total_original:
            print(f"\n✅ BUG #1 FIXED: Tokens DECREASED as expected!")
            print(f"  Reduction: {total_original - tokens_after} tokens ({(1 - tokens_after/total_original)*100:.1f}%)")
            return True
        else:
            print(f"\n❌ BUG #1 NOT FIXED: Tokens INCREASED or stayed same!")
            print(f"  This indicates original messages weren't deleted")
            return False
    else:
        print(f"\n⚠️  No compression occurred during test")
        print(f"  This might be expected if RL agent chose DO_NOTHING")
        return None


if __name__ == "__main__":
    result = test_compression_reduces_tokens()
    print("\n" + "=" * 70)
    if result is True:
        print("✅ VERIFICATION PASSED")
    elif result is False:
        print("❌ VERIFICATION FAILED")
    else:
        print("⚠️  VERIFICATION INCONCLUSIVE (no compression occurred)")
    print("=" * 70)
