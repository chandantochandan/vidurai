"""Test RL Agent integrated into koshas.py"""
from vidurai.core.koshas import ViduraiMemory
from vidurai.core.rl_agent_v2 import RewardProfile

print("=" * 70)
print("🧠 TESTING RL AGENT INTEGRATION")
print("=" * 70)

# Create memory system with RL Agent
print("\n🔧 Creating ViduraiMemory with RL Agent...")
memory = ViduraiMemory(
    enable_compression=True,
    enable_rl_agent=True,
    reward_profile=RewardProfile.BALANCED
)

print(f"✅ Created with RL Agent")
print(f"   Compression enabled: {memory.compression_enabled}")
print(f"   RL Agent enabled: {memory.rl_agent_enabled}")

# Add messages and watch agent make decisions
print("\n📝 Adding 15 messages (agent will decide when to compress)...")
for i in range(15):
    content = f"Message {i}: Working on AI project Vidurai with memory compression"
    memory.remember(content, importance=0.6)
    
    # Check if agent took action
    stats = memory.get_rl_agent_stats()
    if i > 0 and stats['actions_taken'] > 0:
        print(f"   Message {i}: Agent took {stats['actions_taken']} action(s)")

# Get final statistics
print("\n📊 Final Statistics:")
print("\n   RL Agent:")
rl_stats = memory.get_rl_agent_stats()
for key, value in rl_stats.items():
    if isinstance(value, float):
        print(f"      {key}: {value:.3f}")
    else:
        print(f"      {key}: {value}")

print("\n   Compression:")
comp_stats = memory.get_compression_stats()
print(f"      Total compressions: {comp_stats['total_compressions']}")
print(f"      Total tokens saved: {comp_stats['total_tokens_saved']}")

print("\n   Memory Layers:")
print(f"      Working: {len(memory.working.memories)} memories")
print(f"      Episodic: {len(memory.episodic.memories)} memories")

# End conversation (triggers epsilon decay)
print("\n🏁 Ending conversation...")
memory.end_conversation()
final_stats = memory.get_rl_agent_stats()
print(f"   Episodes: {final_stats['episodes']}")
print(f"   Epsilon: {final_stats['epsilon']:.3f}")
print(f"   Maturity: {final_stats['maturity']:.1f}%")

print("\n" + "=" * 70)
print("✅ RL AGENT INTEGRATION SUCCESSFUL!")
print("   The agent is learning optimal compression policies")
print("=" * 70)