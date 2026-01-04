---
sidebar_position: 5
---

# API Reference

Complete reference for the Vidurai API.

## Core Classes

### Vidurai

The main class for interacting with Vidurai's memory system.
```python
from vidurai import Vidurai

memory = Vidurai(
    api_key: str = None,
    user_id: str = None,
    **config
)
```

**Parameters:**
- `api_key` (str, optional): API key for cloud storage
- `user_id` (str, optional): Unique user identifier
- `**config`: Additional configuration options

---

## Methods

### remember()

Store a new memory.
```python
memory.remember(
    session_id: str,
    content: str,
    category: str = "general",
    metadata: dict = None,
    importance: float = None
) -> Memory
```

**Parameters:**
- `session_id` (str): User/session identifier
- `content` (str): Content to remember
- `category` (str, optional): Memory category (default: "general")
- `metadata` (dict, optional): Additional metadata
- `importance` (float, optional): Manual importance score (0-1)

**Returns:**
- `Memory`: The stored memory object

**Example:**
```python
memory.remember(
    session_id="user-123",
    content="User prefers dark mode",
    category="preference",
    metadata={"source": "settings_page"},
    importance=0.9
)
```

---

### recall()

Retrieve relevant memories based on a query.
```python
memory.recall(
    session_id: str,
    query: str,
    limit: int = 5,
    category: str = None,
    min_score: float = 0.0
) -> List[Memory]
```

**Parameters:**
- `session_id` (str): User/session identifier
- `query` (str): Search query
- `limit` (int, optional): Maximum memories to return (default: 5)
- `category` (str, optional): Filter by category
- `min_score` (float, optional): Minimum relevance score (default: 0.0)

**Returns:**
- `List[Memory]`: List of relevant memories, sorted by relevance

**Example:**
```python
memories = memory.recall(
    session_id="user-123",
    query="What are user's preferences?",
    limit=10,
    category="preference",
    min_score=0.7
)

for m in memories:
    print(f"{m.content} (score: {m.score})")
```

---

### search()

Search memories with advanced filters.
```python
memory.search(
    session_id: str,
    category: str = None,
    after: datetime = None,
    before: datetime = None,
    limit: int = 100
) -> List[Memory]
```

**Parameters:**
- `session_id` (str): User/session identifier
- `category` (str, optional): Filter by category
- `after` (datetime, optional): Memories after this date
- `before` (datetime, optional): Memories before this date
- `limit` (int, optional): Maximum results (default: 100)

**Returns:**
- `List[Memory]`: List of matching memories

**Example:**
```python
from datetime import datetime, timedelta

# Get last week's conversations
recent = memory.search(
    session_id="user-123",
    category="conversation",
    after=datetime.now() - timedelta(days=7),
    limit=50
)
```

---

### update()

Update an existing memory.
```python
memory.update(
    memory_id: str,
    content: str = None,
    category: str = None,
    metadata: dict = None,
    importance: float = None
) -> Memory
```

**Parameters:**
- `memory_id` (str): ID of memory to update
- `content` (str, optional): New content
- `category` (str, optional): New category
- `metadata` (dict, optional): New metadata
- `importance` (float, optional): New importance score

**Returns:**
- `Memory`: Updated memory object

**Example:**
```python
memory.update(
    memory_id="mem_abc123",
    content="User now prefers light mode",
    importance=0.95
)
```

---

### forget()

Delete a specific memory.
```python
memory.forget(
    memory_id: str
) -> bool
```

**Parameters:**
- `memory_id` (str): ID of memory to delete

**Returns:**
- `bool`: True if successful

**Example:**
```python
memory.forget(memory_id="mem_abc123")
```

---

### forget_all()

Delete all memories for a user.
```python
memory.forget_all(
    session_id: str,
    category: str = None
) -> int
```

**Parameters:**
- `session_id` (str): User/session identifier
- `category` (str, optional): Only delete from this category

**Returns:**
- `int`: Number of memories deleted

**Example:**
```python
# Delete all memories
count = memory.forget_all(session_id="user-123")
print(f"Deleted {count} memories")

# Delete only conversations
count = memory.forget_all(
    session_id="user-123",
    category="conversation"
)
```

---

## Data Models

### Memory

The Memory object returned by Vidurai methods.

**Attributes:**
```python
class Memory:
    id: str                    # Unique memory ID
    session_id: str           # User/session identifier
    content: str              # Memory content
    category: str             # Memory category
    importance: float         # Importance score (0-1)
    score: float              # Relevance score (for recall)
    created_at: datetime      # Creation timestamp
    updated_at: datetime      # Last update timestamp
    metadata: dict            # Additional metadata
    kosha: str                # Memory layer (annamaya/manomaya/vijnanamaya)
```

**Methods:**
```python
# Convert to dictionary
memory.to_dict() -> dict

# Convert to JSON
memory.to_json() -> str
```

---

## Categories

Built-in memory categories:

- `preference`: User preferences and settings
- `conversation`: Chat history and interactions
- `fact`: Factual information about the user
- `goal`: User goals and objectives
- `context`: Contextual information
- `general`: Uncategorized memories

**Custom categories:**
```python
memory.remember(
    session_id="user-123",
    content="User completed Python course",
    category="education"  # Custom category
)
```

---

## Error Handling

### Exceptions
```python
# from vidurai.exceptions (removed) import (
    ViduraiError,           # Base exception
    AuthenticationError,    # Invalid API key
    MemoryNotFoundError,    # Memory doesn't exist
    QuotaExceededError,     # Usage limit reached
    ValidationError         # Invalid parameters
)
```

**Example:**
```python
from vidurai import Vidurai
# from vidurai.exceptions (removed) import AuthenticationError, MemoryNotFoundError

try:
    memory = Vidurai(api_key="invalid-key")
    memory.remember(
        session_id="user-123",
        content="Test memory"
    )
except AuthenticationError:
    print("Invalid API key")
except MemoryNotFoundError:
    print("Memory not found")
except ViduraiError as e:
    print(f"Error: {e}")
```

---

## Async API

Asynchronous version of the API:
```python
from vidurai import AsyncVidurai

async def main():
    memory = AsyncVidurai(user_id="user-123")
    
    # Store memory
    await memory.remember(
        session_id="user-123",
        content="Async memory"
    )
    
    # Retrieve memories
    memories = await memory.recall(
        session_id="user-123",
        query="test"
    )
    
    await memory.close()

# Run
import asyncio
asyncio.run(main())
```

---

## Batch Operations

Process multiple memories efficiently:
```python
# Batch remember
memories = memory.batch_remember(
    session_id="user-123",
    contents=[
        "Memory 1",
        "Memory 2",
        "Memory 3"
    ],
    category="conversation"
)

# Batch recall
results = memory.batch_recall(
    session_id="user-123",
    queries=["query1", "query2", "query3"],
    limit=5
)
```

---

## Utilities

### Export/Import
```python
# Export memories
data = memory.export(
    session_id="user-123",
    format="json"  # or "csv"
)

# Import memories
memory.import_data(
    session_id="user-123",
    data=data,
    format="json"
)
```

### Statistics
```python
# Get memory statistics
stats = memory.get_stats(session_id="user-123")

print(stats)
# {
#   "total_memories": 150,
#   "by_category": {"preference": 20, "conversation": 130},
#   "by_kosha": {"annamaya": 10, "manomaya": 100, "vijnanamaya": 40},
#   "avg_importance": 0.65,
#   "storage_size": "2.5 MB"
# }
```

---

## Next Steps

- [Best Practices](./best-practices) - Production deployment guide
- [Configuration](./configuration) - Customize Vidurai

---

Questions? Join our [Discord community](https://discord.gg/DHdgS8eA)!