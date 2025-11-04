# Vidurai Troubleshooting Guide

**Version:** 1.5.1
**Author:** Chandan
**Last Updated:** 2025-11-03

This guide helps you diagnose and fix common issues with Vidurai memory management.

---

## 🚨 Critical Issues Fixed in v1.5.1

If you're experiencing any of these issues, **upgrade to v1.5.1 immediately**:

```bash
pip install --upgrade vidurai
```

### Issue #1: Token Count Increasing Instead of Decreasing

**Symptoms:**
- Token usage grows over time despite compression
- Memory footprint increases unexpectedly
- Negative ROI on compression costs

**Root Cause (v1.5.0):**
The `_try_compress()` method removed compressed messages from working memory but **not** from episodic memory, resulting in both the compressed summary AND original messages being stored.

**Fix (v1.5.1):**
System now removes original messages from BOTH working AND episodic memory layers after compression.

**Verification:**
```python
from vidurai.core import ViduraiMemory

memory = ViduraiMemory()

# Add multiple messages
for i in range(20):
    memory.remember(f"Message {i}: Some content here", importance=0.8)

# Check token count before and after compression
# Should show reduction, not increase
```

**Expected Result:** Token count should decrease by ~36.6% on average

---

### Issue #2: High-Importance Memories Not Being Recalled

**Symptoms:**
- `recall(min_importance=0.7)` returns no results
- High-importance memories (0.9+) seem to disappear
- Recall rate drops to 20% when it should be 100%

**Root Cause (v1.5.0):**
Fixed importance decay (0.95^n) affected ALL memories without configuration options. A memory with importance=0.95 decays to ~0.36 after just 20 messages.

**Fix (v1.5.1):**
Added configurable decay parameters:
- `enable_decay`: Boolean to disable decay entirely
- `decay_rate`: Float to control decay speed (default: 0.95)

**Solutions:**

**Option 1 - Disable Decay (Recommended for High-Threshold Recall):**
```python
from vidurai.core import ViduraiMemory

# For applications requiring reliable high-threshold recall
memory = ViduraiMemory(enable_decay=False)

# Add high-importance memories
memory.remember("Critical user preference", importance=0.9)
memory.remember("Important context", importance=0.85)

# These will maintain their importance indefinitely
results = memory.recall(min_importance=0.7)
# Should return all memories with original importance >= 0.7
```

**Option 2 - Slower Decay Rate:**
```python
# Use slower decay for longer memory retention
memory = ViduraiMemory(decay_rate=0.98)  # Instead of 0.95

# After 20 messages:
# - Original (0.95): 0.95 × (0.95^19) ≈ 0.34 ❌ (falls below 0.5)
# - Slower (0.98): 0.95 × (0.98^19) ≈ 0.64 ✅ (stays above 0.5)
```

**Option 3 - Lower Thresholds:**
```python
# Use thresholds that work reliably with default decay
memory = ViduraiMemory()  # Default decay_rate=0.95

# Use min_importance between 0.3-0.5 for reliable recall
important_memories = memory.recall(min_importance=0.4)
```

**Verification Test:**
```python
from vidurai.core import ViduraiMemory

# Test with decay disabled
memory = ViduraiMemory(enable_decay=False)
memory.remember("Test memory", importance=0.9)

# Add 20 filler messages
for i in range(20):
    memory.remember(f"Filler {i}", importance=0.3)

# Should still recall the high-importance memory
results = memory.recall(min_importance=0.7)
assert len(results) > 0, "High-importance memory should be recalled"
assert any(m.importance >= 0.9 for m in results), "Importance should be preserved"
```

---

### Issue #3: Reward Profiles Behaving Backwards

**Symptoms:**
- QUALITY_FOCUSED compresses MORE aggressively than COST_FOCUSED
- COST_FOCUSED preserves MORE information than expected
- Reward profiles seem inverted

**Root Cause (v1.5.0):**
1. Token reward calculation used tiny pricing multiplier (0.002), making token savings insignificant
2. Insufficient weight differentiation between profiles

**Fix (v1.5.1):**
1. Removed pricing multiplier, using direct token scaling: `(tokens_saved / 10) * weight`
2. Adjusted profile weights:
   - COST_FOCUSED: `token_weight=3.0`, `loss_penalty=0.5`
   - QUALITY_FOCUSED: `token_weight=0.3`, `loss_penalty=5.0`

**Verification:**
```python
from vidurai.core import ViduraiMemory
from vidurai.core.rl_agent_v2 import RewardProfile

# Test COST_FOCUSED (should prefer aggressive compression)
cost_memory = ViduraiMemory(reward_profile=RewardProfile.COST_FOCUSED)

# Test QUALITY_FOCUSED (should prefer conservative compression)
quality_memory = ViduraiMemory(reward_profile=RewardProfile.QUALITY_FOCUSED)

# Add same content to both
content = "Some content that could be compressed" * 10

cost_memory.remember(content, importance=0.7)
quality_memory.remember(content, importance=0.7)

# Monitor compression behavior
cost_stats = cost_memory.get_rl_agent_stats()
quality_stats = quality_memory.get_rl_agent_stats()

# COST_FOCUSED should compress more aggressively
# QUALITY_FOCUSED should preserve more information
```

---

## 🔧 Common Issues & Solutions

### RL Agent Not Learning

**Symptoms:**
- Compression behavior doesn't improve over time
- Q-table remains empty or small
- Epsilon stays at initial value (0.30)

**Diagnosis:**
```python
stats = memory.get_rl_agent_stats()
print(f"Episodes: {stats['episodes']}")
print(f"Q-table size: {stats['q_table_size']}")
print(f"Epsilon: {stats['epsilon']:.3f}")
```

**Causes & Solutions:**

1. **Not enough episodes**
   - Need: 50-100 episodes for basic learning, 1000+ for maturity
   - Solution: Process more conversations or use synthetic training data

2. **Persistence not working**
   - Check: `~/.vidurai/` directory exists and is writable
   - Solution: Ensure proper file permissions
   ```bash
   ls -la ~/.vidurai/
   # Should show experiences.jsonl and q_table.json
   ```

3. **Experience buffer not persisting**
   - Check file size: `ls -lh ~/.vidurai/experiences.jsonl`
   - Solution: Verify write permissions and disk space

---

### Memory Footprint Growing Too Large

**Symptoms:**
- `~/.vidurai/experiences.jsonl` grows beyond 10MB
- Slow recall performance
- High memory usage

**Solutions:**

1. **Manual cleanup:**
```python
import os
import shutil

vidurai_dir = os.path.expanduser("~/.vidurai/")

# Backup current state
shutil.copy(f"{vidurai_dir}/experiences.jsonl",
            f"{vidurai_dir}/experiences_backup.jsonl")

# Clear experience buffer
os.remove(f"{vidurai_dir}/experiences.jsonl")

# Q-table persists, so learning isn't lost
```

2. **Automated cleanup (add to your code):**
```python
def cleanup_experiences_if_needed(max_size_mb=10):
    import os
    exp_file = os.path.expanduser("~/.vidurai/experiences.jsonl")

    if os.path.exists(exp_file):
        size_mb = os.path.getsize(exp_file) / (1024 * 1024)
        if size_mb > max_size_mb:
            # Keep Q-table, clear experiences
            os.remove(exp_file)
            print(f"Cleared experience buffer ({size_mb:.1f}MB)")

# Call before initializing memory
cleanup_experiences_if_needed()
memory = ViduraiMemory()
```

---

### Compression Not Happening

**Symptoms:**
- Token count never decreases
- No compression messages in logs
- Context window fills up quickly

**Diagnosis:**
```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

memory = ViduraiMemory()
# Watch for compression-related log messages
```

**Possible Causes:**

1. **RL agent in exploration phase**
   - First 10-20 episodes have 30% exploration (epsilon=0.30)
   - Solution: Be patient, agent learns over time

2. **Content too short to compress**
   - Need minimum context size (typically 500+ tokens)
   - Solution: Accumulate more messages before expecting compression

3. **LLM client not configured**
   - Check if compression LLM is available
   - Solution: Configure OpenAI or Anthropic API keys

---

### Semantic Drift After Compression

**Symptoms:**
- Compressed summaries lose important details
- Quality degradation over time
- Context becomes less useful

**Solutions:**

1. **Use QUALITY_FOCUSED profile:**
```python
from vidurai.core.rl_agent_v2 import RewardProfile

memory = ViduraiMemory(reward_profile=RewardProfile.QUALITY_FOCUSED)
```

2. **Mark critical information with high importance:**
```python
# Critical info should have importance >= 0.9
memory.remember("User is allergic to peanuts", importance=0.95)
memory.remember("Project deadline is Friday", importance=0.90)

# Less critical context can be lower
memory.remember("User said 'um' a few times", importance=0.3)
```

3. **Disable compression for critical sessions:**
```python
# For critical conversations, disable RL agent temporarily
memory = ViduraiMemory(enable_rl_agent=False)
```

---

## 🧪 Testing Your Configuration

### Basic Health Check

```python
from vidurai.core import ViduraiMemory

def health_check():
    memory = ViduraiMemory()

    # Test 1: Basic remember/recall
    memory.remember("Test memory", importance=0.8)
    results = memory.recall()
    assert len(results) > 0, "❌ Basic recall failed"
    print("✅ Basic remember/recall working")

    # Test 2: Importance decay (with decay enabled)
    memory_with_decay = ViduraiMemory(enable_decay=True, decay_rate=0.95)
    memory_with_decay.remember("Decay test", importance=0.9)

    for i in range(20):
        memory_with_decay.remember(f"Filler {i}", importance=0.3)

    results = memory_with_decay.recall(min_importance=0.7)
    # Should have decayed below 0.7
    print(f"✅ Decay working (recalled {len(results)} items)")

    # Test 3: Decay disabled
    memory_no_decay = ViduraiMemory(enable_decay=False)
    memory_no_decay.remember("No decay test", importance=0.9)

    for i in range(20):
        memory_no_decay.remember(f"Filler {i}", importance=0.3)

    results = memory_no_decay.recall(min_importance=0.7)
    assert len(results) > 0, "❌ Decay disable failed"
    print(f"✅ Decay disabled working (recalled {len(results)} items)")

    # Test 4: RL agent stats
    stats = memory.get_rl_agent_stats()
    print(f"✅ RL Agent: {stats['episodes']} episodes, epsilon={stats['epsilon']:.3f}")

    print("\n✅ All health checks passed!")

health_check()
```

---

## 📊 Performance Benchmarking

### Token Reduction Test

```python
import tiktoken

def benchmark_token_reduction():
    encoder = tiktoken.encoding_for_model("gpt-3.5-turbo")
    memory = ViduraiMemory()

    # Add substantial content
    conversation = [
        "Let me think about this problem carefully. Hmm, well, you know...",
        "Actually, I think the answer might be related to machine learning.",
        "Yeah, so basically, neural networks learn patterns from data.",
        # ... add more realistic conversation content
    ]

    initial_tokens = 0
    for msg in conversation:
        initial_tokens += len(encoder.encode(msg))
        memory.remember(msg, importance=0.5)

    # Trigger compression (may need more messages)
    # ... add enough content for compression to occur

    # Measure final token count
    final_tokens = 0
    recalled = memory.recall()
    for m in recalled:
        final_tokens += len(encoder.encode(m.content))

    reduction = ((initial_tokens - final_tokens) / initial_tokens) * 100
    print(f"Token reduction: {reduction:.1f}%")
    print(f"Initial: {initial_tokens} → Final: {final_tokens}")

benchmark_token_reduction()
```

---

## 🆘 Getting Help

If you're still experiencing issues:

1. **Check version:** Ensure you're on v1.5.1+
   ```bash
   pip show vidurai
   ```

2. **Enable debug logging:**
   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

3. **Gather diagnostics:**
   ```python
   stats = memory.get_rl_agent_stats()
   print(f"Episodes: {stats['episodes']}")
   print(f"Epsilon: {stats['epsilon']}")
   print(f"Q-table size: {stats['q_table_size']}")
   ```

4. **Report issues:**
   - GitHub Issues: https://github.com/chandantochandan/vidurai/issues
   - Include: Version, error messages, reproduction steps
   - **Do not include:** API keys, sensitive data

---

## 📖 Additional Resources

- **README:** [Main documentation](../README.md)
- **CHANGELOG:** [Version history and fixes](../CHANGELOG.md)
- **Examples:** Check `tests/` directory for usage examples
- **Discord:** [Community support](https://discord.gg/DHdgS8eA)

---

**Author:** Chandan
**Vidurai Team**
*Building the conscience layer for AI, one learned memory at a time.*
