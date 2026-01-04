---
sidebar_position: 4
---

# Troubleshooting

Common issues and solutions.

## Token count not decreasing

**Problem:** Tokens increase instead of decrease
**Cause:** Using v1.5.0 (had accumulation bug)
**Solution:** Upgrade to v1.5.1+

```bash
pip install --upgrade vidurai
python -c "import vidurai; print(vidurai.__version__)"  # Should show 1.5.1+
```

## High-threshold recall returns few results

**Problem:** `recall(min_importance=0.7)` returns 1/5 items
**Cause:** Importance decay drops memories below threshold
**Solution:** Disable decay or use lower threshold

```python
# Option 1: Disable decay
memory = Vidurai(enable_decay=False)

# Option 2: Use lower threshold
results = memory.recall(min_importance=0.5)

# Option 3: Use count-based recall
results = memory.recall(limit=10)  # Get top 10 regardless of threshold
```

## RL agent not learning

**Problem:** Q-table not growing, epsilon not decaying
**Cause:** Not enough episodes
**Solution:** Give it 50-100 episodes

```python
stats = memory.get_rl_agent_stats()
if stats['episodes'] < 50:
    print("Agent still learning, needs more episodes")
    print(f"Current episode: {stats['episodes']}")
    print(f"Exploration rate: {stats['epsilon']:.2%}")
```

## Memory not being compressed

**Problem:** Token count keeps growing, no compression triggered
**Cause:** Threshold not reached or compression disabled
**Solution:** Check configuration

```python
# Check current stats
stats = memory.get_memory_stats()
print(f"Tokens: {stats['tokens']}")
print(f"Threshold: {memory.compression_threshold}")

# Manual trigger
memory.trigger_compression()

# Or lower threshold
memory.compression_threshold = 0.7
```

## Import errors

**Problem:** `ModuleNotFoundError: No module named 'vidurai'`
**Cause:** Not installed or wrong environment
**Solution:** Install in correct environment

```bash
# Check current environment
which python

# Install
pip install vidurai

# Verify
python -c "import vidurai; print(vidurai.__version__)"
```

## Performance issues

**Problem:** Slow recall or compression
**Cause:** Large memory store, inefficient queries
**Solution:** Optimize queries and storage

```python
# Use semantic search instead of scanning all memories
results = memory.recall(query="specific topic", limit=5)

# Periodic cleanup
memory.clear_below_threshold(0.2)

# Enable indexing (if available)
memory = Vidurai(enable_indexing=True)
```

## Compression quality issues

**Problem:** Compressed memories lose critical information
**Cause:** Too aggressive compression settings
**Solution:** Use quality-focused profile

```python
from vidurai.core.data_structures_v2 import RewardProfile

memory = Vidurai(
    reward_profile=RewardProfile.QUALITY_FOCUSED,
    compression_threshold=0.85
)
```

## API key errors

**Problem:** `OpenAI API key not found`
**Cause:** Environment variable not set
**Solution:** Set API key

```bash
# Option 1: Environment variable
export OPENAI_API_KEY="sk-..."

# Option 2: In code
import os
os.environ["OPENAI_API_KEY"] = "sk-..."

# Option 3: Pass to constructor
memory = Vidurai(api_key="sk-...")
```

## Getting Help

Still stuck? Get help from:

- **GitHub Issues:** [github.com/chandantochandan/vidurai/issues](https://github.com/chandantochandan/vidurai/issues)
- **Discord:** [discord.gg/DHdgS8eA](https://discord.gg/DHdgS8eA)
- **Documentation:** [Full docs](/docs/intro)

When reporting issues, include:
1. Vidurai version (`vidurai.__version__`)
2. Python version
3. Minimal reproducible code
4. Error messages and stack traces
