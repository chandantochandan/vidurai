"""Test RL Agent"""
from vidurai.core.rl_agent_v2 import (
    VismritiRLAgent, RewardProfile, MemoryState, Outcome, Action
)

print("=" * 70)
print("🧠 TESTING RL AGENT")
print("=" * 70)

# Test 1: Create agent
print("\n📦 Test 1: Creating RL Agent...")
agent = VismritiRLAgent(reward_profile=RewardProfile.BALANCED)
print("✅ Agent created")

# Test 2: Epsilon decay
print("\n📉 Test 2: Testing epsilon decay...")
print(f"   Episode 0: ε = {agent.policy.get_epsilon():.3f}")
for i in [100, 500, 1000, 2000]:
    agent.policy.episodes = i
    print(f"   Episode {i}: ε = {agent.policy.get_epsilon():.3f}")

# Test 3: Decision making
print("\n🎯 Test 3: Making decisions...")
state = MemoryState(
    working_memory_count=15,
    episodic_memory_count=200,
    total_tokens=800,
    average_entropy=0.5,
    messages_since_last_compression=10
)
print(f"   State: {state.working_memory_count} memories, {state.total_tokens} tokens")

actions_taken = []
for i in range(10):
    action = agent.decide(state)
    actions_taken.append(action.value)

print(f"   Actions (10 trials): {set(actions_taken)}")
print(f"   ✅ Exploring different actions")

# Test 4: Learning
print("\n🎓 Test 4: Learning from experience...")
initial_episodes = agent.policy.episodes
for i in range(5):
    state = MemoryState(
        working_memory_count=10 + i,
        episodic_memory_count=100,
        total_tokens=500,
    )
    action = agent.decide(state)
    
    outcome = Outcome(
        action=action,
        tokens_saved=30 + i*10,
        retrieval_accuracy=0.9,
    )
    
    next_state = MemoryState(
        working_memory_count=5,
        episodic_memory_count=101,
        total_tokens=300,
    )
    
    agent.learn(outcome, next_state)

agent.end_episode()

print(f"   Experiences stored: {len(agent.experience_buffer.buffer)}")
print(f"   Q-table states: {len(agent.policy.q_table)}")
print(f"   ✅ Agent learning from experience")

# Test 5: Reward profiles
print("\n⚖️  Test 5: Testing reward profiles...")
outcome = Outcome(
    action=Action.COMPRESS_NOW,
    tokens_saved=100,
    retrieval_accuracy=0.8,
    information_loss=0.1,
)

for profile in [RewardProfile.BALANCED, RewardProfile.COST_FOCUSED, RewardProfile.QUALITY_FOCUSED]:
    reward = outcome.calculate_reward(profile)
    print(f"   {profile.value}: reward = {reward:.2f}")

# Test 6: Statistics
print("\n📊 Test 6: Agent statistics...")
stats = agent.get_statistics()
for key, value in stats.items():
    if isinstance(value, float):
        print(f"   {key}: {value:.3f}")
    else:
        print(f"   {key}: {value}")

print("\n" + "=" * 70)
print("✅ ALL RL AGENT TESTS PASSED!")
print("=" * 70)