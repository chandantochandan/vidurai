---
sidebar_position: 1
---

# Getting Started

A practical guide to using Vidurai in your projects.

## Basic Setup

```python
from vidurai import Vidurai

# Initialize with defaults
memory = Vidurai()

# Store a memory
memory.store("User prefers dark mode interface")

# Recall memories
results = memory.recall("interface preferences")
print(results)
```

## Understanding Memory Flow

1. **Store:** Add new information
2. **Compress:** Automatic when tokens exceed limits
3. **Recall:** Retrieve relevant information
4. **Decay:** Gradual importance reduction over time

## Common Patterns

### Pattern 1: User Preferences
```python
# Store user preferences
memory.store("User works as a Python developer", importance=0.9)
memory.store("User prefers type hints in code", importance=0.8)

# Recall when generating code
prefs = memory.recall("coding preferences")
```

### Pattern 2: Conversation Context
```python
# Store conversation turns
for msg in conversation:
    memory.store(f"{msg['role']}: {msg['content']}")

# Get relevant context
context = memory.recall(query="project requirements", limit=5)
```

### Pattern 3: Knowledge Base
```python
# Store permanent knowledge in Vijnanamaya Kosha
memory.store(
    "Company coding standards: Use black formatter, pytest for tests",
    importance=1.0  # Never forgotten
)
```

## Next Steps

- Learn about [Memory Management](./memory-management.md)
- Explore [Compression Strategies](./compression-strategies.md)
- Check [Troubleshooting](./troubleshooting.md) for common issues
