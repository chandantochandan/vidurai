---
sidebar_position: 4
---

# Configuration

Customize Vidurai's behavior to match your needs.

## Basic Configuration
```python
from vidurai import Vidurai

memory = Vidurai(
    api_key="your-api-key",      # Optional for local use
    user_id="user-123",           # Unique user identifier
    model="gpt-3.5-turbo",        # Embedding model
    persist_directory="./data"    # Data storage location
)
```

## Configuration Options

### Memory Settings
```python
memory = Vidurai(
    # Core settings
    user_id="user-123",
    
    # Memory capacity
    max_memories=10000,           # Maximum memories per user
    
    # Retrieval settings
    default_limit=5,              # Default number of memories to retrieve
    similarity_threshold=0.7,     # Minimum relevance score (0-1)
    
    # Decay settings
    enable_decay=True,            # Enable intelligent forgetting
    decay_rate=0.1,               # How quickly memories fade
)
```

### Storage Backend

#### Local Storage (Default)
```python
memory = Vidurai(
    user_id="user-123",
    storage="local",
    persist_directory="./vidurai_data"
)
```

#### Cloud Storage
```python
memory = Vidurai(
    user_id="user-123",
    storage="cloud",
    api_key="your-vidurai-api-key"
)
```

### Embedding Models

Choose the embedding model for semantic search:
```python
# OpenAI embeddings (requires API key)
memory = Vidurai(
    user_id="user-123",
    embedding_model="openai",
    openai_api_key="your-openai-key"
)

# Local embeddings (free, no API needed)
memory = Vidurai(
    user_id="user-123",
    embedding_model="sentence-transformers",
    model_name="all-MiniLM-L6-v2"  # Fast and efficient
)

# Custom embeddings
memory = Vidurai(
    user_id="user-123",
    embedding_model="custom",
    embedding_function=my_custom_embedder
)
```

## Advanced Configuration

### Three-Kosha Architecture

Configure the memory layers:
```python
memory = Vidurai(
    user_id="user-123",
    
    # Annamaya Kosha (Working Memory)
    working_memory_size=10,       # Recent context window
    
    # Manomaya Kosha (Episodic Memory)
    episodic_decay=True,          # Enable decay
    episodic_retention_days=30,   # Keep for 30 days
    
    # Vijnanamaya Kosha (Wisdom Memory)
    wisdom_consolidation=True,    # Auto-consolidate important memories
    wisdom_threshold=0.9          # Importance threshold for wisdom layer
)
```

### Vismriti Engine (Strategic Forgetting)
```python
memory = Vidurai(
    user_id="user-123",

    # Forgetting strategy
    enable_vismriti=True,
    compression_ratio=0.366,      # 36.6%+ token reduction (production-verified)

    # What to forget
    forget_trivial=True,          # "hmm", "let me think", etc.
    forget_duplicates=True,       # Remove redundant memories
    forget_outdated=True,         # Remove superseded information
)
```

### Vismriti RL Agent (v1.5.1+)

The self-learning brain of Vidurai. Uses Q-learning to optimize compression decisions:

```python
from vidurai import Vidurai
from vidurai.core.data_structures_v2 import RewardProfile

# Cost-focused: Prioritizes token savings
memory = Vidurai(reward_profile=RewardProfile.COST_FOCUSED)

# Quality-focused: Prioritizes information preservation
memory = Vidurai(reward_profile=RewardProfile.QUALITY_FOCUSED)

# Balanced: Middle ground (default)
memory = Vidurai(reward_profile=RewardProfile.BALANCED)
```

**How it learns:**
- Starts with epsilon=0.30 (30% exploration, 70% exploitation)
- Decays to epsilon=0.05 over 1000 episodes (5% exploration, 95% exploitation)
- Learns Q-values for state-action pairs through experience
- Persists learning to `~/.vidurai/q_table.json`

**Key difference from v1.0:** No hardcoded rules. Intelligence emerges through reinforcement learning.

**Monitor learning progress:**
```python
stats = memory.get_rl_agent_stats()
print(f"Episodes: {stats['episodes']}")
print(f"Epsilon: {stats['epsilon']:.3f}")
print(f"Q-table size: {stats['q_table_size']}")
```

The agent needs 50-100 episodes to fully mature and show clear profile differentiation.

### Viveka Layer (Conscience)
```python
memory = Vidurai(
    user_id="user-123",
    
    # Importance scoring
    auto_importance=True,         # Automatic importance detection
    importance_factors=[
        "emotional_significance",
        "goal_relevance",
        "surprise_value",
        "user_engagement"
    ],
    
    # Ethical guardrails
    dharma_alignment=True,
    filter_harmful=True,
    filter_biased=True,
)
```

## Environment Variables

Set configuration via environment variables:
```bash
# .env file
VIDURAI_API_KEY=your-api-key
VIDURAI_USER_ID=default-user
VIDURAI_STORAGE=local
VIDURAI_PERSIST_DIR=./data
VIDURAI_MAX_MEMORIES=10000
```

Load in code:
```python
from dotenv import load_dotenv
load_dotenv()

memory = Vidurai()  # Auto-loads from environment
```

## Production Configuration

Recommended settings for production:
```python
import os
from vidurai import Vidurai

memory = Vidurai(
    # Security
    api_key=os.getenv("VIDURAI_API_KEY"),
    user_id=request.user.id,  # From your auth system
    
    # Performance
    storage="cloud",
    max_memories=50000,
    
    # Quality
    similarity_threshold=0.75,
    enable_vismriti=True,
    compression_ratio=0.9,
    
    # Privacy
    enable_encryption=True,
    auto_delete_after_days=365,
    
    # Monitoring
    enable_logging=True,
    log_level="INFO",
)
```

## Next Steps

- [Best Practices](./best-practices) - Production deployment guide
- [API Reference](./api-reference) - Complete API documentation

---

Need help with configuration? Join our [Discord](https://discord.gg/DHdgS8eA)!