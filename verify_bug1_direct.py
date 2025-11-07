"""
Direct verification that Bug #1 is fixed:
Force compression and verify tokens decrease
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

    return total


def test_compression_reduces_tokens():
    """Verify compression actually reduces total token count"""
    print("=" * 70)
    print("BUG #1 DIRECT VERIFICATION: Force Compression & Check Tokens")
    print("=" * 70)

    # Create memory system WITHOUT RL agent to have full control
    memory = ViduraiMemory(enable_compression=True, enable_rl_agent=False)

    # Add messages that will be compressed (need 8+ for threshold of 5 with keep_recent=2)
    messages = [
        "Hello, I'm working on a Python project.",
        "I need help with memory management.",
        "The system should compress old messages.",
        "Compression saves tokens and reduces costs.",
        "I want to implement this feature today.",
        "The code is in the vidurai package.",
        "Can you help me test the compression?",
        "Let me know if you have questions.",
        "I think this should be enough messages now.",
    ]

    print(f"\nAdding {len(messages)} messages to memory system...\n")

    for msg in messages:
        memory.remember(msg, importance=0.6)  # High enough for episodic

    tokens_before = count_total_tokens(memory)
    print(f"✅ Tokens BEFORE compression: {tokens_before}")

    # Count memories before
    working_before = len(memory.working.memories)
    episodic_before = len(memory.episodic.memories)
    print(f"  Working memories: {working_before}")
    print(f"  Episodic memories: {episodic_before}")

    # Force compression by calling _try_compress directly
    print(f"\n🔧 Forcing compression with keep_recent=2...")
    result = memory._try_compress(keep_recent=2, importance=0.6)

    if result and result.get('success'):
        print(f"✅ Compression succeeded!")
        print(f"  Tokens saved: {result.get('tokens_saved', 0)}")
        print(f"  Compression ratio: {result.get('compression_ratio', 0):.1%}")

        # Count tokens after
        tokens_after = count_total_tokens(memory)
        print(f"\n✅ Tokens AFTER compression: {tokens_after}")

        # Count memories after
        working_after = len(memory.working.memories)
        episodic_after = len(memory.episodic.memories)
        print(f"  Working memories: {working_after}")
        print(f"  Episodic memories: {episodic_after}")

        # Verify reduction
        print(f"\n📊 Results:")
        print(f"  Token reduction: {tokens_before - tokens_after} tokens")
        print(f"  Percentage saved: {((tokens_before - tokens_after) / tokens_before * 100):.1f}%")

        # The critical check: Did tokens actually decrease?
        if tokens_after < tokens_before:
            print(f"\n✅ BUG #1 FIXED: Tokens DECREASED after compression!")
            print(f"  Original messages were properly deleted from BOTH layers")
            return True
        else:
            print(f"\n❌ BUG #1 NOT FIXED: Tokens stayed the same or increased!")
            print(f"  This indicates original messages weren't deleted properly")
            return False
    else:
        print(f"\n❌ Compression failed or didn't occur")
        print(f"  Result: {result}")
        return False


if __name__ == "__main__":
    result = test_compression_reduces_tokens()
    print("\n" + "=" * 70)
    if result:
        print("✅ VERIFICATION PASSED - BUG #1 IS FIXED")
    else:
        print("❌ VERIFICATION FAILED - BUG #1 NOT FIXED")
    print("=" * 70)
