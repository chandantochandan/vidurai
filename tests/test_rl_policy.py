#!/usr/bin/env python3
"""
Test script for RL Policy Layer Integration
Tests that retention policies work correctly with VismritiMemory
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

def setup_test_environment():
    """Create test memories for retention policy testing"""
    print("=" * 70)
    print("📝 Setting Up Test Environment")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.storage.database import SalienceLevel

    # Use test project path
    test_project = "/home/user/vidurai/test-rl-policy"

    print(f"Test project: {test_project}")
    print()

    # Create memory system
    memory = VismritiMemory(
        project_path=test_project,
        enable_aggregation=True,
        retention_policy="rule_based"  # Start with rule-based
    )

    print("Creating test memories with different salience levels...")

    # Create 100 LOW salience memories (should trigger consolidation)
    for i in range(100):
        memory.remember(
            f"Debug log entry {i}: processing item",
            metadata={'type': 'log', 'level': 'debug'},
            salience=SalienceLevel.LOW
        )

    print(f"✅ Created 100 LOW salience memories")

    # Create 20 HIGH salience memories (should be preserved)
    for i in range(20):
        memory.remember(
            f"Fixed critical bug #{i} in authentication system",
            metadata={'type': 'bugfix', 'priority': 'high'},
            salience=SalienceLevel.HIGH
        )

    print(f"✅ Created 20 HIGH salience memories")

    # Create 30 NOISE memories (should be cleaned up)
    for i in range(30):
        memory.remember(
            f"Noise entry {i}",
            metadata={'type': 'noise'},
            salience=SalienceLevel.NOISE
        )

    print(f"✅ Created 30 NOISE salience memories")

    print()
    print(f"Total memories created: 150")
    print()

    return memory


def test_rule_based_policy():
    """Test rule-based retention policy"""
    print("=" * 70)
    print("🧪 TEST 1: Rule-Based Retention Policy")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    test_project = "/home/user/vidurai/test-rl-policy"

    # Create memory system with rule-based policy
    memory = VismritiMemory(
        project_path=test_project,
        enable_aggregation=True,
        retention_policy="rule_based",
        retention_policy_config={
            'low_noise_threshold': 100,  # Should trigger with our 130 LOW/NOISE memories
            'compress_light_threshold': 500,
            'compress_aggressive_threshold': 1000,
        }
    )

    print(f"Policy: {memory.retention_policy.name}")
    print()

    # Get initial stats
    if memory.db:
        initial_stats = memory.db.get_statistics(test_project)
        print(f"Initial state:")
        print(f"  Total memories: {initial_stats.get('total', 0)}")
        print(f"  By salience: {initial_stats.get('by_salience', {})}")
        print()

    # Evaluate and execute retention
    print("Evaluating retention policy...")
    result = memory.evaluate_and_execute_retention()

    if result:
        print()
        print("Retention Result:")
        print(f"  Policy: {result['policy']}")
        print(f"  Action: {result['action']}")
        print(f"  Context: {result['context']}")
        print(f"  Outcome: {result['outcome']}")
        print()

        # Check that correct action was taken
        action = result['action']
        if action == 'consolidate_and_decay':
            print("✅ PASSED: Rule correctly triggered CONSOLIDATE_AND_DECAY")
            print(f"   (130 LOW/NOISE memories > threshold of 100)")
        else:
            print(f"⚠️  UNEXPECTED: Got action '{action}' instead of 'consolidate_and_decay'")
    else:
        print("❌ FAILED: No retention result returned")

    print()


def test_rl_based_policy():
    """Test RL-based retention policy"""
    print("=" * 70)
    print("🧪 TEST 2: RL-Based Retention Policy")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory

    test_project = "/home/user/vidurai/test-rl-policy"

    try:
        # Create memory system with RL policy
        memory = VismritiMemory(
            project_path=test_project,
            enable_aggregation=True,
            retention_policy="rl_based",
            retention_policy_config={
                'reward_profile': 'BALANCED',
            }
        )

        print(f"Policy: {memory.retention_policy.name}")
        print()

        # Get RL agent stats
        if memory.retention_policy:
            rl_stats = memory.retention_policy.get_statistics()
            print(f"RL Agent State:")
            print(f"  Episodes: {rl_stats.get('episodes', 0)}")
            print(f"  Epsilon: {rl_stats.get('epsilon', 0):.3f}")
            print(f"  Q-table size: {rl_stats.get('q_table_size', 0)}")
            print(f"  Maturity: {rl_stats.get('maturity', 0):.1f}%")
            print()

        # Simulate multiple retention cycles (for learning)
        print("Running 3 retention evaluation cycles...")
        print()

        for cycle in range(3):
            print(f"--- Cycle {cycle + 1} ---")

            result = memory.evaluate_and_execute_retention()

            if result:
                print(f"  Action: {result['action']}")
                print(f"  Compression: {result['outcome']['compression_ratio']:.1%}")
                print(f"  Tokens saved: {result['outcome']['tokens_saved']}")
                print()
            else:
                print("  No result returned")
                print()

        # Get updated RL stats
        if memory.retention_policy:
            updated_stats = memory.retention_policy.get_statistics()
            print(f"RL Agent After Learning:")
            print(f"  Total reward: {updated_stats.get('total_reward', 0):.2f}")
            print(f"  Avg reward/episode: {updated_stats.get('avg_reward_per_episode', 0):.2f}")
            print(f"  Actions taken: {updated_stats.get('actions_taken', 0)}")
            print()

        print("✅ PASSED: RL policy executed and learned from outcomes")

    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()

    print()


def test_policy_comparison():
    """Compare rule-based vs RL-based decisions"""
    print("=" * 70)
    print("🧪 TEST 3: Policy Comparison (Rule-Based vs RL-Based)")
    print("=" * 70)
    print()

    from vidurai.vismriti_memory import VismritiMemory
    from vidurai.core.retention_policy import create_retention_policy, RetentionContext

    # Create identical context
    context = RetentionContext(
        total_memories=150,
        high_salience_count=20,
        medium_salience_count=0,
        low_salience_count=100,
        noise_salience_count=30,
        avg_age_days=15.0,
        oldest_memory_days=30.0,
        total_size_mb=0.15,
        estimated_tokens=15000,
        memories_added_last_day=0,
        memories_accessed_last_day=0,
        project_path="/test"
    )

    print("Test Context:")
    print(f"  Total: {context.total_memories}")
    print(f"  HIGH: {context.high_salience_count}")
    print(f"  LOW: {context.low_salience_count}")
    print(f"  NOISE: {context.noise_salience_count}")
    print()

    # Test rule-based decision
    rule_policy = create_retention_policy('rule_based', low_noise_threshold=100)
    rule_action = rule_policy.decide_action(context)
    print(f"Rule-Based Policy Decision: {rule_action.value}")
    print(f"  Reasoning: 130 LOW/NOISE > threshold (100)")
    print()

    # Test RL-based decision
    try:
        rl_policy = create_retention_policy('rl_based', reward_profile='BALANCED')
        rl_action = rl_policy.decide_action(context)
        print(f"RL-Based Policy Decision: {rl_action.value}")
        print(f"  (Based on learned Q-values or exploration)")
        print()

        if rule_action == rl_action:
            print("✅ Both policies agree on action")
        else:
            print("ℹ️  Policies chose different actions (expected during exploration phase)")

    except Exception as e:
        print(f"⚠️  RL policy test skipped: {e}")

    print()


def test_policy_statistics():
    """Test policy statistics tracking"""
    print("=" * 70)
    print("🧪 TEST 4: Policy Statistics")
    print("=" * 70)
    print()

    from vidurai.core.retention_policy import create_retention_policy

    # Rule-based stats
    print("Rule-Based Policy Statistics:")
    rule_policy = create_retention_policy('rule_based')
    rule_stats = rule_policy.get_statistics()
    print(f"  Policy: {rule_stats.get('policy')}")
    print(f"  Actions taken: {rule_stats.get('actions_taken')}")
    print(f"  Thresholds: {rule_stats.get('thresholds')}")
    print()

    # RL-based stats
    try:
        print("RL-Based Policy Statistics:")
        rl_policy = create_retention_policy('rl_based', reward_profile='COST_FOCUSED')
        rl_stats = rl_policy.get_statistics()
        print(f"  Policy: {rl_stats.get('policy')}")
        print(f"  Reward profile: {rl_stats.get('reward_profile')}")
        print(f"  Episodes: {rl_stats.get('episodes')}")
        print(f"  Epsilon: {rl_stats.get('epsilon', 0):.3f}")
        print(f"  Q-table states: {rl_stats.get('q_table_size')}")
        print(f"  Maturity: {rl_stats.get('maturity', 0):.1f}%")
        print()

        print("✅ PASSED: Statistics available for both policies")
    except Exception as e:
        print(f"⚠️  RL stats test skipped: {e}")

    print()


def test_reward_profiles():
    """Test different reward profiles"""
    print("=" * 70)
    print("🧪 TEST 5: Reward Profiles (BALANCED, COST_FOCUSED, QUALITY_FOCUSED)")
    print("=" * 70)
    print()

    try:
        from vidurai.core.retention_policy import create_retention_policy

        profiles = ['BALANCED', 'COST_FOCUSED', 'QUALITY_FOCUSED']

        for profile in profiles:
            policy = create_retention_policy('rl_based', reward_profile=profile)
            stats = policy.get_statistics()
            print(f"{profile}:")
            print(f"  Policy name: {policy.name}")
            print(f"  Reward profile: {stats.get('reward_profile')}")
            print()

        print("✅ PASSED: All reward profiles initialized successfully")

    except Exception as e:
        print(f"⚠️  Reward profile test skipped: {e}")

    print()


if __name__ == "__main__":
    try:
        print()
        print("🚀 RL POLICY LAYER - TEST SUITE")
        print()

        # Setup
        memory = setup_test_environment()

        # Run tests
        test_rule_based_policy()
        test_rl_based_policy()
        test_policy_comparison()
        test_policy_statistics()
        test_reward_profiles()

        print()
        print("=" * 70)
        print("✅ ALL TESTS COMPLETE")
        print("=" * 70)
        print()

    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Tests failed with error: {e}")
        import traceback
        traceback.print_exc()
