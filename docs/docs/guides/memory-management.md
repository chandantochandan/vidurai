---
sidebar_position: 2
---

# Memory Management

Advanced techniques for managing memories in Vidurai.

## Memory Lifecycle

```
Store → Assign Importance → Decay Over Time → Compress/Evict
```

## Importance Scores

### Automatic Scoring
Vidurai automatically assigns importance based on:
- Content semantic value
- Position in conversation
- Frequency of access

### Manual Scoring
```python
# Critical information (never forgotten)
memory.store("Production API key: xyz...", importance=1.0)

# Important context
memory.store("User is debugging login flow", importance=0.8)

# Casual mention
memory.store("Weather is nice today", importance=0.3)
```

## Decay Management

### When to Enable Decay
✅ Chatbots with evolving conversations
✅ Long-running sessions
✅ Dynamic user preferences

### When to Disable Decay
❌ Knowledge bases with static facts
❌ Compliance/audit logs
❌ Critical business data

```python
# Disable decay for permanent storage
memory = Vidurai(enable_decay=False)
```

## Memory Inspection

```python
# Get all memories
all_memories = memory.get_all_memories()

# Check memory stats
stats = memory.get_memory_stats()
print(f"Total memories: {stats['total']}")
print(f"Token count: {stats['tokens']}")
print(f"Compression ratio: {stats['compression_ratio']}")
```

## Memory Cleanup

```python
# Clear low-importance memories
memory.clear_below_threshold(importance=0.3)

# Clear by age
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(days=30)
memory.clear_before_date(cutoff)

# Clear specific Kosha
memory.clear_kosha('annamaya')  # Clear working memory
```

## Best Practices

1. **Use appropriate importance scores**
   - 0.9-1.0: Critical, permanent information
   - 0.7-0.8: Important context
   - 0.5-0.6: Normal conversation
   - 0.3-0.4: Casual mentions

2. **Monitor token usage**
   ```python
   if memory.get_token_count() > 50000:
       memory.trigger_compression()
   ```

3. **Periodic maintenance**
   ```python
   # Daily cleanup job
   memory.clear_below_threshold(0.2)
   memory.optimize_storage()
   ```

See [Best Practices](../best-practices.md) for production deployment tips.
