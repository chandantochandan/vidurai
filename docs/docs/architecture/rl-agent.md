---
sidebar_position: 3
---

# Vismriti RL Agent

The self-learning brain of Vidurai (v1.5.1+).

## What Makes It Unique

Unlike traditional memory systems with hardcoded rules, the Vismriti RL Agent learns optimal compression strategies through **Reinforcement Learning (Q-learning)**.

## How It Works

1. **Observes** system state (memory counts, tokens, importance)
2. **Decides** which action to take (compress now, wait, aggressive, conservative)
3. **Acts** on the decision
4. **Learns** from the outcome (rewards/penalties)
5. **Persists** learning to `~/.vidurai/q_table.json`

## Configuration

```python
from vidurai import Vidurai
from vidurai.core.data_structures_v2 import RewardProfile

# Cost-focused: Prioritize token savings
memory = Vidurai(reward_profile=RewardProfile.COST_FOCUSED)

# Quality-focused: Prioritize information preservation
memory = Vidurai(reward_profile=RewardProfile.QUALITY_FOCUSED)

# Balanced (default)
memory = Vidurai(reward_profile=RewardProfile.BALANCED)
```

## Learning Curve

- **Episodes 1-10:** 30% exploration (learning phase)
- **Episodes 10-50:** 15% exploration (adaptation phase)
- **Episodes 50+:** 5% exploration (mature phase)

The agent needs 50-100 episodes to show clear profile differentiation.

## Monitoring

```python
stats = memory.get_rl_agent_stats()
print(f"Episodes: {stats['episodes']}")
print(f"Epsilon: {stats['epsilon']:.3f}")
print(f"Q-table: {stats['q_table_size']} states")
```

See [Best Practices](../best-practices.md) for optimization tips.
