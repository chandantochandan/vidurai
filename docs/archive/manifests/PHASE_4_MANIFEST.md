# Phase 4 Manifest: The Awakening (Archival, Analytics & Learning)

**Version:** 2.1.0-Guardian
**Date:** 2024-12-15
**Status:** IMPLEMENTED

---

## 1. Overview

Phase 4 implements "The Awakening" - the tiered storage lifecycle and offline learning:
- **MemoryArchiver:** Moves ARCHIVED memories from SQLite (Hot) to Parquet (Cold)
- **RepoAnalyst:** Queries archived data using DuckDB
- **DreamCycle:** Offline RL training on archived memories with outcomes
- **Maintenance Loop:** Daemon scheduling for periodic archival and training

---

## 2. The Archiver (SQLite → Parquet)

### File Location
`vidurai/core/archival/archiver.py`

### Glass Box Protocol: Atomic Archiver

```python
def flush_archived_memories(self) -> int:
    # Step 1: SELECT rows WHERE status = 'ARCHIVED'
    cursor.execute("SELECT * FROM memories WHERE status = 'ARCHIVED'")

    # Step 2: Convert to DataFrame (LAZY LOAD pandas)
    import pandas as pd
    df = pd.DataFrame(memories)

    # Step 3: Write to Parquet (partitioned)
    df.to_parquet(parquet_file, engine='pyarrow', compression='snappy')

    # Step 4: VERIFY file exists (CRITICAL)
    if not parquet_file.exists():
        return 0  # Abort - don't delete from SQLite

    # Step 5: DELETE from SQLite (ONLY if verified)
    cursor.execute("DELETE FROM memories WHERE id IN (...)")
```

**CRITICAL:** Never delete from SQLite before Parquet write is confirmed.

### Partition Structure

```
~/.vidurai/archive/
├── year=2024/
│   ├── month=01/
│   │   └── memories_20240115_143022.parquet
│   ├── month=02/
│   │   └── memories_20240228_091544.parquet
│   └── month=12/
│       └── memories_20241215_005523.parquet
└── year=2025/
    └── month=01/
        └── memories_20250102_120000.parquet
```

### Parquet Schema

| Column | Type | Description |
|--------|------|-------------|
| `id` | int64 | Memory ID |
| `verbatim` | string | Raw memory content |
| `gist` | string | Compressed summary |
| `salience` | string | Importance level |
| `created_at` | string | ISO timestamp |
| `expires_at` | string | Expiry timestamp |
| `access_count` | int64 | Access count |
| `outcome` | int64 | RL signal (-1, 0, 1) |
| `file_path` | string | Associated file |
| `decay_reason` | string | Why archived |
| `event_type` | string | Event type |
| `tags` | string | Tags (JSON) |
| `project_id` | int64 | Project ID |
| `archived_at` | string | Archive timestamp |

---

## 3. The Analyst (DuckDB Reader)

### File Location
`vidurai/core/analytics/engine.py`

### Glass Box Protocol: Empty Archive Rule

```python
def query_archive(self, sql_query: str) -> List[Dict]:
    # CRITICAL: Check if archive has files BEFORE querying
    if not self._has_archive_files():
        return []  # Don't crash on empty archive

    # Create VIEW for archive
    con.execute("""
        CREATE OR REPLACE VIEW history AS
        SELECT * FROM read_parquet('~/.vidurai/archive/**/*.parquet')
    """)

    # Execute query
    return con.execute(sql_query).fetchall()
```

**WHY:** `duckdb.read_parquet()` crashes if directory is empty or doesn't exist.

### DuckDB VIEW Definition

```sql
CREATE OR REPLACE VIEW history AS
SELECT * FROM read_parquet('~/.vidurai/archive/**/*.parquet')
```

### Example Queries

```python
# Get training data for RL
analyst.query_archive("""
    SELECT id, content, salience, outcome, access_count
    FROM history
    WHERE outcome IS NOT NULL AND outcome != 0
    ORDER BY archived_at DESC
    LIMIT 1000
""")

# Get aggregate stats
analyst.query_archive("""
    SELECT
        COUNT(*) as total_memories,
        SUM(CASE WHEN outcome = 1 THEN 1 ELSE 0 END) as positive,
        SUM(CASE WHEN outcome = -1 THEN 1 ELSE 0 END) as negative,
        AVG(salience) as avg_salience
    FROM history
""")

# Search by keyword
analyst.query_archive("""
    SELECT * FROM history
    WHERE LOWER(content) LIKE LOWER('%authentication%')
    LIMIT 50
""")
```

---

## 4. The Dreamer (Offline RL Training)

### File Location
`vidurai/core/rl/dreamer.py`

### Glass Box Protocol: Dream Cycle Safety

```python
def run(self) -> Dict[str, Any]:
    stats = {'success': False, 'error': None, ...}

    try:
        # All training logic here
        ...
        stats['success'] = True

    except Exception as e:
        # CRITICAL: Capture ALL exceptions
        # Never raise - daemon must not crash
        stats['error'] = str(e)
        logger.error(f"[DreamCycle] Error (daemon safe): {e}")

    return stats
```

**WHY:** DreamCycle runs in background thread. Unhandled exceptions would kill the daemon.

### RL Agent Type

**Implementation:** Q-Learning (existing `VismritiRLAgent`)

```python
from vidurai.core.rl_agent_v2 import VismritiRLAgent, MemoryState, Outcome, Action

agent = VismritiRLAgent(reward_profile=RewardProfile.BALANCED)

# For each archived memory with outcome
state = create_state_from_memory(memory)
agent.current_state = state
agent.current_action = infer_action(memory)
agent.learn(outcome, next_state)

# Save updated Q-table
agent.policy.save_q_table()
```

### Training Data Selection

Memories are selected for training if:
- `outcome != 0` (has RL signal)
- `outcome = 1` → Positive reward (memory was useful)
- `outcome = -1` → Negative reward (memory caused issues)

---

## 5. The Maintenance Loop (Daemon Scheduling)

### File Location
`vidurai-daemon/daemon.py` → `_maintenance_loop()`

### Schedule

| Interval | Action |
|----------|--------|
| 24 hours | Run full maintenance cycle |

### Sequence

```
1. MemoryArchiver.flush_archived_memories()
   └── SQLite ARCHIVED → Parquet

2. DreamCycle.run()
   └── Train RL agent on Parquet data with outcomes
```

### Exception Safety

```python
async def _maintenance_loop():
    while True:
        try:
            await asyncio.sleep(24 * 3600)

            # Step 1: Archive (wrapped in try/except)
            try:
                archiver.flush_archived_memories()
            except Exception as e:
                logger.error(f"Archiver error (daemon safe): {e}")

            # Step 2: Dream (wrapped in try/except)
            try:
                dreamer.run()
            except Exception as e:
                logger.error(f"Dream error (daemon safe): {e}")

        except asyncio.CancelledError:
            break
        except Exception as e:
            # Outer catch - NEVER crash daemon
            logger.error(f"Maintenance error (daemon safe): {e}")
```

---

## 6. Verification Commands

### Test MemoryArchiver
```bash
# Run test cases
python -m vidurai.core.archival.archiver --test

# Show archive stats
python -m vidurai.core.archival.archiver --stats

# Manually flush archived memories
python -m vidurai.core.archival.archiver --flush
```

### Test RepoAnalyst
```bash
# Run test cases
python -m vidurai.core.analytics.engine --test

# Show archive statistics
python -m vidurai.core.analytics.engine --stats

# Execute SQL query
python -m vidurai.core.analytics.engine --query "SELECT COUNT(*) FROM history"

# Search archive
python -m vidurai.core.analytics.engine --search "error"
```

### Test DreamCycle
```bash
# Run test cases
python -m vidurai.core.rl.dreamer --test

# Manually run dream cycle
python -m vidurai.core.rl.dreamer --run
```

---

## 7. Architecture

### File Structure
```
vidurai/
├── core/
│   ├── archival/
│   │   ├── __init__.py
│   │   └── archiver.py         # MemoryArchiver (SQLite→Parquet)
│   │
│   ├── analytics/
│   │   ├── __init__.py
│   │   └── engine.py           # RepoAnalyst (DuckDB)
│   │
│   ├── rl/
│   │   ├── __init__.py
│   │   └── dreamer.py          # DreamCycle (Offline Training)
│   │
│   └── rl_agent_v2.py          # VismritiRLAgent (Q-Learning)
│
vidurai-daemon/
└── daemon.py                   # _maintenance_loop()
```

### Dependencies

| Module | Dependency | Loading |
|--------|------------|---------|
| MemoryArchiver | pandas, pyarrow | Lazy (inside method) |
| RepoAnalyst | duckdb | Lazy (inside method) |
| DreamCycle | vidurai.core.rl_agent_v2 | Lazy (inside method) |

---

## 8. Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                        MEMORY LIFECYCLE                          │
└─────────────────────────────────────────────────────────────────┘

    CREATE → ACTIVE → [low utility] → PENDING_DECAY → ARCHIVED
                                                         │
                                                         ▼
                                            ┌────────────────────┐
                                            │  SQLite (Hot)      │
                                            │  status='ARCHIVED' │
                                            └─────────┬──────────┘
                                                      │
                                                      │ MemoryArchiver
                                                      │ (24h interval)
                                                      ▼
                                            ┌────────────────────┐
                                            │  Parquet (Cold)    │
                                            │  year=YYYY/month=MM│
                                            └─────────┬──────────┘
                                                      │
                                                      │ DreamCycle
                                                      │ (queries via DuckDB)
                                                      ▼
                                            ┌────────────────────┐
                                            │  RL Agent Training │
                                            │  Q-table update    │
                                            └────────────────────┘
```

---

## 9. Caveats & Limitations

### MemoryArchiver
1. **Requires pandas/pyarrow:** Fails gracefully if not installed
2. **Atomic but not transactional:** If purge fails after write, data is in Parquet (safe)
3. **No deduplication:** Same memory can be archived multiple times if re-archived

### RepoAnalyst
1. **Requires duckdb:** Fails gracefully if not installed
2. **Memory usage:** Large archives may consume significant RAM
3. **No indexes:** Full table scans for all queries

### DreamCycle
1. **Synthetic states:** Creates approximated MemoryState from archived data
2. **Inferred actions:** Actions are inferred, not logged with memories
3. **Separate agent instance:** Training updates separate Q-table (daemon agent must reload)

### Maintenance Loop
1. **24h fixed interval:** No adaptive scheduling
2. **Sequential execution:** Archiver runs before DreamCycle
3. **No resume:** If interrupted, restarts from beginning

---

## 10. Next Steps (Phase 5)

1. **Build Runner:** Execute builds in Shadow Sandbox
2. **Beacon Integration:** Full VS Code focus event wiring
3. **Semantic Search:** Use VectorEngine for archive queries
4. **Adaptive Scheduling:** Dynamic maintenance intervals based on load

---

*Generated by Vidurai Guardian v2.1.0*
