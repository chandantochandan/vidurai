---
sidebar_position: 6
---

# Best Practices

Production-ready patterns for building with Vidurai.

## Architecture Patterns

### 1. Session Management

Always use consistent session IDs:
```python
# ✅ Good: Use authenticated user ID
memory = Vidurai()
user_id = request.user.id  # From your auth system
memories = memory.recall(session_id=user_id, query=query)

# ❌ Bad: Random or temporary IDs
session_id = str(uuid.uuid4())  # Lost after session ends
```

### 2. Memory Categorization

Organize memories by type for better retrieval:
```python
# User preferences
memory.remember(
    session_id=user_id,
    content="User prefers email notifications",
    category="preference"
)

# Factual information
memory.remember(
    session_id=user_id,
    content="User lives in New York",
    category="fact"
)

# Conversations
memory.remember(
    session_id=user_id,
    content=f"User: {user_msg}\nAssistant: {bot_reply}",
    category="conversation"
)
```

### 3. Importance Scoring

Guide Vidurai's memory prioritization:
```python
# High importance: Core preferences
memory.remember(
    session_id=user_id,
    content="User is allergic to peanuts",
    category="fact",
    importance=0.95  # Critical information
)

# Medium importance: Preferences
memory.remember(
    session_id=user_id,
    content="User prefers morning meetings",
    category="preference",
    importance=0.7
)

# Low importance: Casual conversation
memory.remember(
    session_id=user_id,
    content="User said 'hmm, interesting'",
    category="conversation",
    importance=0.2  # Will be forgotten faster
)
```

---

## Performance Optimization

### 1. Limit Memory Retrieval

Don't retrieve more than needed:
```python
# ✅ Good: Reasonable limit
memories = memory.recall(
    session_id=user_id,
    query=query,
    limit=5  # Only what you need
)

# ❌ Bad: Too many results
memories = memory.recall(
    session_id=user_id,
    query=query,
    limit=100  # Slows down response
)
```

### 2. Use Similarity Threshold

Filter low-relevance results:
```python
memories = memory.recall(
    session_id=user_id,
    query=query,
    limit=10,
    min_score=0.7  # Only highly relevant memories
)
```

### 3. Batch Operations

Process multiple operations efficiently:
```python
# ✅ Good: Batch insert
memory.batch_remember(
    session_id=user_id,
    contents=[msg1, msg2, msg3],
    category="conversation"
)

# ❌ Bad: Individual inserts in loop
for msg in messages:
    memory.remember(session_id=user_id, content=msg)
```

---

## Privacy & Security

### 1. Data Sanitization

Never store sensitive information:
```python
# ❌ Bad: Storing PII
memory.remember(
    session_id=user_id,
    content=f"User's SSN is {ssn}"
)

# ✅ Good: Store references only
memory.remember(
    session_id=user_id,
    content="User completed identity verification",
    metadata={"verification_id": verification_id}
)
```

### 2. User Consent

Respect user privacy preferences:
```python
class PrivacyAwareBot:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.memory = Vidurai()
        self.can_remember = self.get_user_consent()
    
    def chat(self, message: str) -> str:
        # Only use memory if user consents
        if self.can_remember:
            memories = self.memory.recall(
                session_id=self.user_id,
                query=message
            )
            context = self.build_context(memories)
        else:
            context = ""
        
        return self.generate_response(message, context)
    
    def forget_me(self):
        """GDPR-compliant deletion"""
        self.memory.forget_all(session_id=self.user_id)
```

### 3. Encryption

Enable encryption for sensitive data:
```python
memory = Vidurai(
    user_id=user_id,
    enable_encryption=True,
    encryption_key=os.getenv("ENCRYPTION_KEY")
)
```

---

## Error Handling

### 1. Graceful Degradation

Always handle memory failures:
```python
from vidurai import Vidurai
# from vidurai.exceptions (removed) import ViduraiError

class ResilientBot:
    def __init__(self):
        self.memory = Vidurai()
    
    def chat(self, user_id: str, message: str) -> str:
        try:
            # Try to use memory
            memories = self.memory.recall(
                session_id=user_id,
                query=message
            )
            context = self.build_context(memories)
        except ViduraiError as e:
            # Gracefully degrade - still respond
            print(f"Memory error: {e}")
            context = ""
        
        # Bot still works without memory
        return self.generate_response(message, context)
```

### 2. Retry Logic

Handle transient failures:
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def store_with_retry(memory, session_id, content):
    return memory.remember(
        session_id=session_id,
        content=content
    )
```

---

## Context Building

### 1. Structured Context

Build clean, structured context for LLMs:
```python
def build_context(memories: List[Memory]) -> str:
    """Convert memories into LLM-friendly context"""
    
    # Group by category
    by_category = {}
    for m in memories:
        by_category.setdefault(m.category, []).append(m)
    
    # Build structured context
    context_parts = []
    
    if "preference" in by_category:
        prefs = [m.content for m in by_category["preference"]]
        context_parts.append(
            f"User Preferences:\n" + "\n".join(f"- {p}" for p in prefs)
        )
    
    if "fact" in by_category:
        facts = [m.content for m in by_category["fact"]]
        context_parts.append(
            f"\nKey Facts:\n" + "\n".join(f"- {f}" for f in facts)
        )
    
    return "\n\n".join(context_parts)
```

### 2. Context Window Management

Keep context within LLM limits:
```python
def smart_context_building(memories: List[Memory], max_tokens: int = 2000):
    """Build context within token limit"""
    
    # Sort by importance and recency
    sorted_memories = sorted(
        memories,
        key=lambda m: (m.importance, m.created_at),
        reverse=True
    )
    
    context = []
    token_count = 0
    
    for memory in sorted_memories:
        memory_tokens = estimate_tokens(memory.content)
        
        if token_count + memory_tokens > max_tokens:
            break
        
        context.append(memory.content)
        token_count += memory_tokens
    
    return "\n".join(context)
```

---

## Testing

### 1. Unit Tests

Test memory operations:
```python
import pytest
from vidurai import Vidurai

@pytest.fixture
def memory():
    return Vidurai(user_id="test-user")

def test_remember_and_recall(memory):
    # Store memory
    mem = memory.remember(
        session_id="test-123",
        content="Test content"
    )
    
    assert mem.id is not None
    
    # Retrieve memory
    results = memory.recall(
        session_id="test-123",
        query="Test"
    )
    
    assert len(results) > 0
    assert "Test content" in results[0].content

def test_forget(memory):
    # Store and delete
    mem = memory.remember(
        session_id="test-123",
        content="Temporary"
    )
    
    memory.forget(memory_id=mem.id)
    
    # Verify deletion
    results = memory.search(session_id="test-123")
    assert mem.id not in [m.id for m in results]
```

### 2. Integration Tests

Test with real LLMs:
```python
def test_chatbot_with_memory():
    bot = MemoryBot(user_id="test-user")
    
    # First conversation
    response1 = bot.chat("My name is Alice")
    assert "Alice" in response1
    
    # Later conversation - should remember
    response2 = bot.chat("What's my name?")
    assert "Alice" in response2
```

---

## Monitoring

### 1. Log Memory Operations

Track usage and performance:
```python
import logging

logger = logging.getLogger(__name__)

class MonitoredMemory:
    def __init__(self, user_id: str):
        self.memory = Vidurai(user_id=user_id)
    
    def remember(self, session_id: str, content: str, **kwargs):
        start = time.time()
        result = self.memory.remember(session_id, content, **kwargs)
        duration = time.time() - start
        
        logger.info(
            f"Memory stored",
            extra={
                "session_id": session_id,
                "category": kwargs.get("category"),
                "duration_ms": duration * 1000
            }
        )
        
        return result
```

### 2. Track Metrics

Monitor memory system health:
```python
from prometheus_client import Counter, Histogram

memory_operations = Counter(
    'vidurai_operations_total',
    'Total memory operations',
    ['operation', 'status']
)

memory_latency = Histogram(
    'vidurai_operation_duration_seconds',
    'Memory operation duration'
)

@memory_latency.time()
def recall_with_metrics(memory, session_id, query):
    try:
        result = memory.recall(session_id=session_id, query=query)
        memory_operations.labels(operation='recall', status='success').inc()
        return result
    except Exception as e:
        memory_operations.labels(operation='recall', status='error').inc()
        raise
```

---

## Production Checklist

Before deploying to production:

- ✅ Use environment variables for API keys
- ✅ Enable encryption for sensitive data
- ✅ Implement user consent and GDPR compliance
- ✅ Add error handling and retry logic
- ✅ Set up monitoring and logging
- ✅ Write tests for memory operations
- ✅ Configure memory limits per user
- ✅ Enable strategic forgetting (Vismriti)
- ✅ Set up backup and recovery
- ✅ Document memory categories and usage

---

## Next Steps

- [FAQ](./faq) - Common questions and answers
- [Configuration](./configuration) - Advanced configuration options

---

Need help? Join our [Discord community](https://discord.gg/DHdgS8eA)!