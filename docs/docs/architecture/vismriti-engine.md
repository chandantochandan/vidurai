---
sidebar_position: 2
---

# Vismriti Engine

The intelligent compression engine at the heart of Vidurai.

## Overview

Vismriti (Sanskrit: विस्मृति, "strategic forgetting") is Vidurai's compression engine that intelligently manages memory by selectively compressing or discarding less important information.

## How It Works

1. **Monitors** token usage across all Koshas
2. **Identifies** compression candidates based on importance scores
3. **Applies** LLM-based semantic compression
4. **Preserves** high-importance memories

## Compression Strategies

### Conservative
- Compress only when absolutely necessary
- Higher quality preservation
- Higher token costs

### Balanced (Default)
- Smart compression when approaching limits
- Good balance of quality and cost

### Aggressive
- Proactive compression
- Lower token costs
- May lose some detail

## Configuration

```python
from vidurai import Vidurai

# Balanced approach (default)
memory = Vidurai()

# Aggressive compression
memory = Vidurai(compression_threshold=0.7)

# Conservative approach
memory = Vidurai(compression_threshold=0.9)
```

See [Compression Strategies](../guides/compression-strategies.md) for advanced usage.
