---
sidebar_position: 3
---

# Compression Strategies

Understanding and optimizing Vidurai's compression behavior.

## Compression Modes

### Conservative Mode
**When to use:** Production systems, critical data, compliance requirements

```python
memory = Vidurai(
    compression_threshold=0.9,  # Compress at 90% capacity
    reward_profile=RewardProfile.QUALITY_FOCUSED
)
```

**Characteristics:**
- ✅ Maximum information preservation
- ✅ High-quality semantic compression
- ❌ Higher token costs
- ❌ More frequent LLM calls

### Balanced Mode (Default)
**When to use:** Most applications, general-purpose chatbots

```python
memory = Vidurai()  # Uses balanced defaults
```

**Characteristics:**
- ✅ Good quality preservation
- ✅ Reasonable token costs
- ✅ Adaptive learning

### Aggressive Mode
**When to use:** Cost-sensitive applications, high-volume scenarios

```python
memory = Vidurai(
    compression_threshold=0.6,  # Compress at 60% capacity
    reward_profile=RewardProfile.COST_FOCUSED
)
```

**Characteristics:**
- ✅ Lower token costs
- ✅ Proactive compression
- ❌ Some information loss
- ❌ More frequent compression cycles

## Custom Compression Logic

```python
from vidurai import Vidurai

class CustomVidurai(Vidurai):
    def should_compress(self) -> bool:
        """Override compression trigger logic"""
        stats = self.get_memory_stats()

        # Custom logic: Compress if token count > 30k OR memory count > 500
        return (stats['tokens'] > 30000 or
                stats['total'] > 500)

    def select_compression_candidates(self):
        """Override candidate selection"""
        # Custom logic: Prioritize older, low-importance memories
        return self.get_memories_sorted_by(
            criteria=['age', 'importance'],
            limit=10
        )

memory = CustomVidurai()
```

## Compression Monitoring

```python
# Track compression events
compression_log = []

def on_compression(event):
    compression_log.append({
        'timestamp': event.timestamp,
        'memories_compressed': event.count,
        'tokens_saved': event.tokens_saved,
        'duration': event.duration
    })

memory.on('compression', on_compression)
```

## Optimization Tips

1. **Tune compression threshold based on usage patterns**
   ```python
   # High-frequency updates: Lower threshold
   memory = Vidurai(compression_threshold=0.6)

   # Low-frequency updates: Higher threshold
   memory = Vidurai(compression_threshold=0.85)
   ```

2. **Use RL agent for automatic optimization**
   ```python
   # Let the agent learn optimal strategy
   memory = Vidurai(
       enable_rl_agent=True,
       reward_profile=RewardProfile.BALANCED
   )

   # Check learning progress after 50+ episodes
   stats = memory.get_rl_agent_stats()
   ```

3. **Batch operations for efficiency**
   ```python
   # Store multiple memories at once
   memories = [
       ("Memory 1", 0.7),
       ("Memory 2", 0.8),
       ("Memory 3", 0.6),
   ]
   memory.store_batch(memories)
   ```

## Performance Benchmarks

| Mode | Token Reduction | Quality Score | LLM Calls/Hour |
|------|----------------|---------------|----------------|
| Conservative | 30-40% | 0.92 | 2-3 |
| Balanced | 50-60% | 0.85 | 4-5 |
| Aggressive | 70-80% | 0.75 | 8-10 |

See [RL Agent](../architecture/rl-agent.md) for advanced learning configurations.
