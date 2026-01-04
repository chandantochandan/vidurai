# Vidurai SDK - Complete Feature Guide & Infrastructure Integration

> **The Core Product**: Everything else (daemon, VS Code extension, proxy) are smart gateways.
> **The Brain**: Vidurai SDK is where intelligence lives.

---

## Executive Summary

Vidurai implements a **three-layer memory system** inspired by Vedantic philosophy:

| Layer | Sanskrit | Purpose | Retention | Capacity |
|-------|----------|---------|-----------|----------|
| **Working Memory** | Annamaya Kosha | Immediate context | 5 minutes | 10 items |
| **Episodic Memory** | Manomaya Kosha | Recent interactions | Days/weeks | 1000 items |
| **Wisdom Memory** | Vijnanamaya Kosha | Permanent knowledge | Forever | Unlimited |

The **Vismriti RL Agent** learns optimal compression strategies through reinforcement learning, automatically balancing token costs with information quality.

---

## 1. Three-Layer Memory Architecture

### 1.1 AnnamayaKosha (Working Memory)

**Location:** `vidurai/core/koshas.py` - `AnnamayaKosha` class

**Philosophy:** Physical layer - holds immediate, transient information

**Configuration:**
```python
# Default
capacity = 10      # Max items in working memory
ttl_seconds = 300  # 5 minutes TTL

# Customize
from vidurai.core.koshas import AnnamayaKosha
working = AnnamayaKosha(capacity=20, ttl_seconds=600)  # 20 items, 10 min TTL
```

**Key Methods:**
```python
working.add(memory)           # Add memory
working.get_active()          # Get non-expired memories
working.clear_expired()       # Remove expired
working.remove(memory)        # Remove specific memory
```

**Behavior:**
- Sliding window approach (deque with maxlen)
- Auto-expires based on TTL
- First memories to be compressed

---

### 1.2 ManomayaKosha (Episodic Memory)

**Location:** `vidurai/core/koshas.py` - `ManomayaKosha` class

**Philosophy:** Mental layer - recent interactions with importance decay

**Configuration:**
```python
# Default
capacity = 1000     # Max items
decay_rate = 0.95   # Importance decay per new memory

# Customize
from vidurai.core.koshas import ManomayaKosha
episodic = ManomayaKosha(capacity=2000, decay_rate=0.90)  # Faster decay
```

**Key Methods:**
```python
episodic.add(memory)          # Add with importance scoring
episodic.get(memory_id)       # Retrieve (boosts importance by 1.1x)
episodic.remove(memory)       # Remove specific
```

**Behavior:**
- LRU with importance-based eviction
- Each new memory decays ALL existing memories by `decay_rate`
- Accessing a memory boosts its importance by 10%
- Least important memory evicted when capacity exceeded

---

### 1.3 VijnanamayaKosha (Wisdom Memory)

**Location:** `vidurai/core/koshas.py` - `VijnanamayaKosha` class

**Philosophy:** Wisdom layer - permanent, compressed knowledge

**Configuration:**
```python
# Default
compression_enabled = True

# Customize
from vidurai.core.koshas import VijnanamayaKosha
wisdom = VijnanamayaKosha(compression_enabled=True)
```

**Key Methods:**
```python
wisdom.add(memory, connections=['related_id1', 'related_id2'])
```

**Behavior:**
- Never forgets (only updates)
- Merges similar memories
- Builds knowledge graph connections
- Stores compressed summaries

---

## 2. Vismriti RL Agent

### 2.1 Overview

**Location:** `vidurai/core/rl_agent_v2.py`

The RL Agent learns **when to compress, decay, or wait** through experience. It uses **Q-learning** with epsilon-greedy exploration.

**Philosophy:** "Intelligence emerges from experience, not from rules"

### 2.2 Actions

```python
class Action(Enum):
    COMPRESS_NOW = "compress_now"           # Standard compression
    COMPRESS_AGGRESSIVE = "compress_aggressive"  # More aggressive (keep_recent=2)
    COMPRESS_CONSERVATIVE = "compress_conservative"  # Conservative (keep_recent=5)
    DECAY_LOW_VALUE = "decay_low_value"     # Trigger decay
    DECAY_THRESHOLD_HIGH = "decay_high"     # High threshold decay
    DECAY_THRESHOLD_LOW = "decay_low"       # Low threshold decay
    CONSOLIDATE = "consolidate"             # Future: semantic consolidation
    DO_NOTHING = "do_nothing"               # Wait
```

### 2.3 Reward Profiles

```python
class RewardProfile(Enum):
    BALANCED = "balanced"           # Equal weight to cost & quality
    COST_FOCUSED = "cost_focused"   # Prioritize token savings
    QUALITY_FOCUSED = "quality_focused"  # Prioritize information quality
```

**Reward Weights:**

| Profile | token_weight | quality_weight | loss_penalty |
|---------|--------------|----------------|--------------|
| BALANCED | 1.0 | 1.0 | 2.0 |
| COST_FOCUSED | 3.0 | 0.5 | 0.5 |
| QUALITY_FOCUSED | 0.3 | 2.0 | 5.0 |

### 2.4 Q-Learning Configuration

```python
# Default parameters
epsilon_max = 0.3      # Initial exploration rate (youth)
epsilon_min = 0.05     # Final exploration rate (maturity)
epsilon_decay = 0.003  # How fast to mature
alpha = 0.1           # Learning rate
gamma = 0.9           # Discount factor (future rewards)
```

### 2.5 State Observation

The agent observes:
- `working_memory_count`: Items in working memory
- `episodic_memory_count`: Items in episodic memory
- `total_tokens`: Estimated token count
- `average_entropy`: Information density (0-1)
- `average_importance`: Mean importance score
- `messages_since_last_compression`: Compression trigger hint

### 2.6 Persistence

The RL Agent persists its learning:
- **Q-table:** `~/.vidurai/q_table.json`
- **Experiences:** `~/.vidurai/experiences.jsonl`

---

## 3. VismritiMemory (Main SDK Class)

### 3.1 Initialization

```python
from vidurai import VismritiMemory, SalienceLevel

# Minimal
memory = VismritiMemory()

# Full configuration
memory = VismritiMemory(
    enable_decay=True,              # Passive decay (synaptic pruning)
    enable_gist_extraction=False,   # LLM gist extraction (requires OpenAI key)
    enable_rl_agent=True,           # RL agent for intelligent decisions
    enable_aggregation=True,        # Memory aggregation (deduplication)
    retention_policy="rule_based",  # "rule_based" or "rl_based"
    retention_policy_config=None,   # Custom policy config
    enable_multi_audience=True,     # Phase 5: Multi-audience gists
    multi_audience_config=None,     # Custom audience config
    project_path="/path/to/project" # Persistent storage location
)
```

### 3.2 Core Operations

```python
# REMEMBER - Store with intelligent processing
mem = memory.remember(
    "Fixed authentication bug in JWT validation",
    metadata={
        'type': 'bugfix',
        'file': 'auth.py',
        'line': 42,
        'tags': ['security', 'critical']
    },
    salience=SalienceLevel.HIGH  # Optional override
)

# RECALL - Retrieve relevant memories
results = memory.recall(
    query="auth bug",
    min_salience=SalienceLevel.MEDIUM,
    top_k=10,
    include_forgotten=False,
    audience="developer"  # Phase 5: audience-specific
)

# FORGET - Active unlearning
stats = memory.forget(
    query="temporary test data",
    method="simple_suppress",  # or "gradient_ascent"
    confirmation=False  # Safety off
)

# RUN DECAY CYCLE - Simulates sleep cleanup
stats = memory.run_decay_cycle()
```

### 3.3 Advanced Operations

```python
# Semantic Consolidation (batch compression)
metrics = memory.run_semantic_consolidation(
    dry_run=True,  # Preview without modifying
    config={
        'target_ratio': 0.5,
        'min_salience': 'LOW',
        'max_age_days': 30
    }
)

# Retention Policy Evaluation
result = memory.evaluate_and_execute_retention()
# Returns: {policy, context, action, outcome}

# Get Context for AI
context = memory.get_context_for_ai(
    query="authentication",
    max_tokens=2000,
    audience="developer"
)
```

### 3.4 Inspection & Transparency

```python
# Memory Ledger (Phase 4: Transparency)
ledger = memory.get_ledger(include_pruned=False, format="dataframe")
memory.export_ledger("memory_audit.csv")

# Statistics
stats = memory.get_statistics()
agg_metrics = memory.get_aggregation_metrics()

# Human-readable summary
memory.print_summary()
```

---

## 4. Salience Levels (Dopamine-Mediated Tagging)

**Location:** `vidurai/core/data_structures_v3.py`

```python
class SalienceLevel(int, Enum):
    CRITICAL = 100   # Strong dopamine - credentials, explicit commands
    HIGH = 75        # Medium dopamine - bug fixes, breakthroughs
    MEDIUM = 50      # Baseline - normal work
    LOW = 25         # Weak dopamine - casual interactions
    NOISE = 5        # No dopamine - raw logs, system events
```

**Retention by Salience:**

| Level | Retention | Description |
|-------|-----------|-------------|
| CRITICAL | Never expires | Protected forever |
| HIGH | 90-180 days | Important events |
| MEDIUM | 30-90 days | Standard work |
| LOW | 7 days | Casual data |
| NOISE | 1 day | Logs, debug output |

---

## 5. Four Gates of Forgetting

**Location:** `vidurai/core/vismriti.py` - `VismritiEngine`

### 5.1 Gates

| Gate | Sanskrit | Mechanism |
|------|----------|-----------|
| **Temporal** | kala_dvara | Time-based: forget old memories |
| **Relevance** | artha_dvara | Importance-based: forget unimportant |
| **Redundancy** | punarukti_dvara | Duplication: forget duplicates |
| **Contradiction** | virodha_dvara | Conflict: forget outdated info |

### 5.2 Time Thresholds

**Standard Mode:**
```python
time_thresholds = {
    "very_low": 30,    # importance < 0.3: forget in 30 seconds
    "low": 120,        # importance < 0.5: forget in 2 minutes
    "medium": 300,     # importance < 0.7: forget in 5 minutes
    "high": 3600       # importance >= 0.7: keep for 1 hour
}
```

**Aggressive Mode:**
```python
time_thresholds = {
    "very_low": 5,     # 5 seconds
    "low": 10,         # 10 seconds
    "medium": 30,      # 30 seconds
    "high": 300        # 5 minutes
}
```

---

## 6. Integrations

### 6.1 LangChain

**Location:** `vidurai/integrations/langchain.py`

```python
from vidurai.integrations.langchain import ViduraiMemory, ViduraiConversationChain
from langchain.llms import OpenAI

llm = OpenAI(temperature=0.7)

# Standard mode
chain = ViduraiConversationChain.create(llm)

# Aggressive forgetting
chain = ViduraiConversationChain.create(llm, aggressive=True)

# Use like any LangChain conversation
response = chain.predict(input="Hello, my name is Alice")
```

**Features:**
- Drop-in replacement for `ConversationBufferMemory`
- Auto-filters to top 10 important memories
- Importance scoring: Human input=0.7, AI output=0.6
- Automatic cleanup of forgotten items

### 6.2 LlamaIndex

**Not yet implemented** - but SDK provides all building blocks.

---

## 7. Infrastructure Integration (Maximum Output)

### 7.1 Current Architecture Gap

```
VS Code Extension → IPC → Daemon → [MISSING LINK] → VismritiMemory SDK
                                   ↓
                         Events stored in active_state
                         BUT NOT flowing to VismritiMemory
```

### 7.2 Recommended Integration

**Option A: Direct SDK Integration in Daemon**

```python
# In daemon.py - Add VismritiMemory integration

from vidurai import VismritiMemory, SalienceLevel

# Global SDK instance
sdk_memory = VismritiMemory(
    enable_decay=True,
    enable_rl_agent=True,
    enable_aggregation=True,
    retention_policy="rl_based",
    project_path=None  # Set per-project
)

# In handle_ipc_message() for file_edit:
async def handle_file_edit(data: dict, project_path: str):
    # Store in SDK with intelligent processing
    sdk_memory.project_path = project_path
    sdk_memory.remember(
        content=f"Edited {data['file']}: {data.get('gist', 'code changes')}",
        metadata={
            'type': 'file_edit',
            'file': data['file'],
            'lang': data.get('lang'),
            'lines': data.get('lines')
        },
        salience=SalienceLevel.MEDIUM
    )

# In handle_ipc_message() for diagnostic:
async def handle_diagnostic(data: dict, project_path: str):
    severity = data['sev']
    salience = {
        0: SalienceLevel.HIGH,      # Error
        1: SalienceLevel.MEDIUM,    # Warning
        2: SalienceLevel.LOW,       # Info
        3: SalienceLevel.NOISE      # Hint
    }.get(severity, SalienceLevel.LOW)

    sdk_memory.remember(
        content=f"{data['file']}:{data.get('ln', '?')}: {data['msg']}",
        metadata={
            'type': 'diagnostic',
            'file': data['file'],
            'severity': severity,
            'source': data.get('src')
        },
        salience=salience
    )
```

**Option B: Periodic Sync from active_state to SDK**

```python
# Background task to sync active_state → VismritiMemory

async def sync_active_state_to_sdk():
    """Periodically sync database state to SDK for intelligent processing"""
    while True:
        try:
            # Get recent file states
            files = memory_db.get_files_with_errors()

            for f in files:
                sdk_memory.remember(
                    content=f"File {f['file_path']} has {f['error_count']} errors",
                    metadata={
                        'type': 'error_state',
                        'file': f['file_path'],
                        'error_count': f['error_count'],
                        'warning_count': f['warning_count']
                    },
                    salience=SalienceLevel.HIGH if f['error_count'] > 0 else SalienceLevel.MEDIUM
                )

            # Run decay cycle (simulate sleep cleanup)
            sdk_memory.run_decay_cycle()

            # Evaluate retention policy
            sdk_memory.evaluate_and_execute_retention()

        except Exception as e:
            logger.error(f"SDK sync failed: {e}")

        await asyncio.sleep(3600)  # Every hour
```

### 7.3 Optimal Configuration for Maximum Output

```python
# Daemon initialization with optimal SDK settings

from vidurai import VismritiMemory
from vidurai.core.rl_agent_v2 import RewardProfile

sdk_memory = VismritiMemory(
    # Enable intelligent decay
    enable_decay=True,

    # Enable RL agent for adaptive compression
    enable_rl_agent=True,

    # Enable memory aggregation (prevents duplicates)
    enable_aggregation=True,

    # Use RL-based retention for adaptive decisions
    retention_policy="rl_based",

    # Multi-audience gists for VS Code dashboard
    enable_multi_audience=True,
    multi_audience_config={
        'enabled': True,
        'audiences': ['developer', 'ai', 'manager'],
        'default_audience': 'developer'
    }
)

# Configure RL Agent profile based on user preference
# BALANCED: Default for most users
# COST_FOCUSED: For token-constrained environments
# QUALITY_FOCUSED: For mission-critical applications
```

### 7.4 Event Flow (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│                        VS CODE EXTENSION                         │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                          │
│  │FileWatch│  │DiagWatch│  │TermWatch│                          │
│  └────┬────┘  └────┬────┘  └────┬────┘                          │
│       └───────────┬┴───────────┘                                │
│                   ▼                                              │
│             IPC Client → Named Pipe                              │
└───────────────────┼──────────────────────────────────────────────┘
                    │
                    ▼
┌───────────────────────────────────────────────────────────────────┐
│                        PYTHON DAEMON                              │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │               handle_ipc_message()                          │  │
│  │                                                             │  │
│  │   file_edit → sdk_memory.remember()   ← NEW                │  │
│  │   diagnostic → sdk_memory.remember()  ← NEW                │  │
│  │               + active_state UPSERT                        │  │
│  │   terminal → sdk_memory.remember()    ← NEW                │  │
│  │   request:get_context → sdk_memory.get_context_for_ai()    │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              VismritiMemory SDK                             │  │
│  │                                                             │  │
│  │   ┌───────────┐  ┌───────────┐  ┌───────────┐             │  │
│  │   │ Annamaya  │  │ Manomaya  │  │Vijnanamaya│             │  │
│  │   │ (Working) │→ │(Episodic) │→ │ (Wisdom)  │             │  │
│  │   └───────────┘  └───────────┘  └───────────┘             │  │
│  │                       │                                    │  │
│  │                       ▼                                    │  │
│  │              ┌─────────────────┐                          │  │
│  │              │ Vismriti RL Agent│                         │  │
│  │              │ (Q-Learning)    │                          │  │
│  │              └────────┬────────┘                          │  │
│  │                       │                                    │  │
│  │        ┌──────────────┼──────────────┐                    │  │
│  │        ▼              ▼              ▼                    │  │
│  │   COMPRESS      DO_NOTHING      DECAY                     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│                         ┌─────────────┐                          │
│                         │   SQLite    │                          │
│                         │ memory.db   │                          │
│                         └─────────────┘                          │
└───────────────────────────────────────────────────────────────────┘
```

---

## 8. Configuration Tweaks for Maximum Performance

### 8.1 For Token-Constrained Environments

```python
memory = VismritiMemory(
    enable_decay=True,
    enable_rl_agent=True,
    enable_aggregation=True,  # Critical: prevents duplicates
    retention_policy="rl_based",
    retention_policy_config={
        'reward_profile': 'cost_focused'  # Prioritize token savings
    }
)

# Use aggressive VismritiEngine
from vidurai import create_memory_system
system = create_memory_system(
    working_capacity=5,      # Smaller working memory
    episodic_capacity=500,   # Smaller episodic
    aggressive_forgetting=True  # Fast cleanup
)
```

### 8.2 For Quality-Critical Applications

```python
memory = VismritiMemory(
    enable_decay=True,
    enable_gist_extraction=True,  # LLM-based gist (requires OpenAI)
    enable_rl_agent=True,
    enable_aggregation=True,
    retention_policy="rl_based",
    retention_policy_config={
        'reward_profile': 'quality_focused'  # Prioritize information
    },
    enable_multi_audience=True  # Rich perspectives
)
```

### 8.3 For Real-Time Applications

```python
# Minimize latency by disabling heavy features
memory = VismritiMemory(
    enable_decay=False,          # Skip decay checks
    enable_gist_extraction=False, # Skip LLM calls
    enable_rl_agent=False,        # Skip RL decisions
    enable_aggregation=False      # Skip aggregation checks
)
```

---

## 9. SDK API Reference Summary

### Core Classes

| Class | Purpose | Location |
|-------|---------|----------|
| `VismritiMemory` | Main SDK class | `vidurai/vismriti_memory.py` |
| `ViduraiMemory` | Legacy Three-Kosha | `vidurai/core/koshas.py` |
| `VismritiRLAgent` | RL decision maker | `vidurai/core/rl_agent_v2.py` |
| `VismritiEngine` | Four Gates forgetting | `vidurai/core/vismriti.py` |
| `MemoryDatabase` | SQLite persistence | `vidurai/storage/database.py` |
| `Oracle` | Query interface | `vidurai/core/oracle.py` |

### Enums

| Enum | Values | Purpose |
|------|--------|---------|
| `SalienceLevel` | CRITICAL, HIGH, MEDIUM, LOW, NOISE | Dopamine tagging |
| `MemoryStatus` | ACTIVE, CONSOLIDATED, PRUNED, UNLEARNED, SILENCED | Memory state |
| `RewardProfile` | BALANCED, COST_FOCUSED, QUALITY_FOCUSED | RL priorities |
| `ForgettingPolicy` | TEMPORAL, RELEVANCE, REDUNDANCY, CONTRADICTION | Four Gates |
| `Action` | COMPRESS_*, DECAY_*, DO_NOTHING | RL actions |

### Key Methods

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `remember()` | content, metadata, salience | Memory | Store with processing |
| `recall()` | query, min_salience, top_k | List[Memory] | Retrieve memories |
| `forget()` | query, method | Dict | Active unlearning |
| `run_decay_cycle()` | - | Dict | Passive cleanup |
| `get_context_for_ai()` | query, max_tokens, audience | str | AI context |
| `get_ledger()` | include_pruned, format | DataFrame/Dict | Transparency |
| `evaluate_and_execute_retention()` | - | Dict | RL retention |
| `run_semantic_consolidation()` | dry_run, config | Metrics | Batch compression |

---

## 10. Quick Start Examples

### Basic Usage

```python
from vidurai import VismritiMemory, SalienceLevel

# Initialize
memory = VismritiMemory()

# Remember
memory.remember("Debugged auth flow", metadata={'file': 'auth.py'})

# Recall
bugs = memory.recall("auth bug", top_k=5)

# Get AI context
context = memory.get_context_for_ai(query="authentication")
print(context)
```

### With RL Agent

```python
from vidurai import VismritiMemory

memory = VismritiMemory(
    enable_rl_agent=True,
    enable_aggregation=True
)

# Store many memories - RL agent learns optimal compression
for i in range(100):
    memory.remember(f"Event {i}", metadata={'index': i})

# Check RL stats
print(memory.get_statistics())
```

### LangChain Integration

```python
from langchain.llms import OpenAI
from vidurai.integrations.langchain import ViduraiConversationChain

llm = OpenAI()
chain = ViduraiConversationChain.create(llm, aggressive=True)

# Intelligent conversation with automatic memory management
chain.predict(input="Hello, I'm working on auth bugs")
chain.predict(input="Found the issue in JWT validation")
chain.predict(input="Fixed it by adding expiry check")

# Memory automatically compresses/forgets unimportant data
```

---

## 11. Conclusion

**Vidurai SDK is the brain. Everything else is plumbing.**

Key takeaways:
1. **Three-Kosha Architecture** provides biologically-inspired memory hierarchy
2. **RL Agent** learns optimal compression through experience
3. **Four Gates** implement intelligent forgetting
4. **Multi-Audience Gists** enable perspective-aware recall
5. **Infrastructure integration** is the missing link - events should flow to SDK

**Recommended Next Step:** Wire daemon's `handle_ipc_message()` to call `sdk_memory.remember()` for all events. This connects the smart gateway to the brain.
