---
sidebar_position: 4
---

# Viveka Layer

The intelligent decision-making layer that determines what to remember and what to forget.

## Overview

Viveka (Sanskrit: विवेक, "discriminative wisdom") is the layer that applies intelligent filtering and importance scoring to memories.

## Importance Scoring

Each memory receives an importance score (0.0 to 1.0) based on:
- **Recency:** More recent memories score higher
- **Frequency:** Often-accessed memories score higher
- **Semantic significance:** Content-based importance
- **User signals:** Explicit importance markers

## Decay Mechanism

```python
from vidurai import Vidurai

# Enable decay (default)
memory = Vidurai(enable_decay=True)

# Disable decay for critical applications
memory = Vidurai(enable_decay=False)
```

Decay formula:
```
importance(t) = importance(0) * exp(-decay_rate * time_elapsed)
```

## Filtering Strategies

### Threshold-based
```python
# Recall only high-importance memories
results = memory.recall(min_importance=0.7)
```

### Count-based
```python
# Get top N most important
results = memory.recall(limit=10)
```

### Time-based
```python
# Memories from last hour
from datetime import datetime, timedelta
cutoff = datetime.now() - timedelta(hours=1)
results = memory.recall(since=cutoff)
```

See [Memory Management](../guides/memory-management.md) for advanced techniques.
