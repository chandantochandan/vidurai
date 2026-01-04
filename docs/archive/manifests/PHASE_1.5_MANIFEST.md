# Phase 1.5 Manifest: Vector Intelligence & Reality Sensors

**Version:** 2.1.0-Guardian
**Date:** 2024-12-15
**Status:** IMPLEMENTED

---

## 1. Tech Stack

### Dependencies Added

| Library | Version | Purpose | Size Impact |
|---------|---------|---------|-------------|
| `sentence-transformers` | `>=2.2.0` | Embedding generation | ~500MB+ (includes torch) |
| `sqlite-vec` | `>=0.1.0` | Vector search in SQLite | ~5MB |

### Models Used

| Model | Dimensions | Speed | Use Case |
|-------|------------|-------|----------|
| `all-MiniLM-L6-v2` | 384 | Fast | Semantic similarity search |

---

## 2. Architecture

### File Structure

```
vidurai/
├── core/
│   ├── intelligence/
│   │   ├── __init__.py          # Module exports
│   │   └── vector_brain.py      # VectorEngine class
│   │
│   └── sensors/
│       ├── __init__.py          # Module exports
│       └── reality_check.py     # RealityVerifier class
```

### Component Responsibilities

#### VectorEngine (`core/intelligence/vector_brain.py`)

- **Purpose:** Generates semantic embeddings for memories
- **Model:** `all-MiniLM-L6-v2` (384 dimensions)
- **Storage:** `vec_memories` SQLite virtual table
- **Methods:**
  - `generate_embedding(text)` → `list[float]`
  - `generate_embeddings_batch(texts)` → `list[list[float]]`
  - `backfill_vectors()` → `int` (count vectorized)
  - `search_similar(query, limit)` → `list[(memory_id, distance)]`

#### RealityVerifier (`core/sensors/reality_check.py`)

- **Purpose:** Verifies memory snippets against actual file contents
- **Outcome Values:**
  - `1` = Success (code exists in file)
  - `-1` = Failure (code not found)
  - `0` = Unknown (file missing, error)
- **Methods:**
  - `verify_outcome(memory_id, file_path, snippet)` → `int`
  - `update_db_outcome(memory_id, result)` → `bool`
  - `batch_verify(limit)` → `(success, failure, unknown)`

---

## 3. Glass Box Protocols Applied

### Heavy ML Rule (CRITICAL)

```python
# WRONG - Do NOT do this:
from sentence_transformers import SentenceTransformer  # Top-level import

# CORRECT - Lazy loading inside method:
class VectorEngine:
    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer  # HERE
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model
```

**Why:** Daemon must start in <200ms. sentence-transformers/torch take 2-5 seconds to import.

### Fuzzy Reality Rule

```python
@staticmethod
def normalize(text: str) -> str:
    """Strip all whitespace for comparison."""
    normalized = re.sub(r'\s+', '', text)
    normalized = normalized.lower()
    return normalized
```

**Why:** Code formatting changes (tabs vs spaces, trailing whitespace). Normalized comparison handles this.

---

## 4. Verification Commands

### Test VectorEngine

```bash
# Python interactive test
python3 -c "
from vidurai.core.intelligence import VectorEngine
engine = VectorEngine()

# Generate single embedding
vec = engine.generate_embedding('Fix authentication bug')
print(f'Embedding dims: {len(vec)}')  # Should be 384

# Check stats
print(engine.get_stats())
"
```

### Test Vector Backfill

```bash
# Manually trigger backfill
python3 -c "
from vidurai.core.intelligence import VectorEngine
engine = VectorEngine()
count = engine.backfill_vectors()
print(f'Vectorized: {count} memories')
"
```

### Test RealityVerifier

```bash
# Run batch verification
python3 -m vidurai.core.sensors.reality_check --test --batch 10

# Show statistics
python3 -m vidurai.core.sensors.reality_check --stats
```

### Verify Database Schema

```bash
# Check vec_memories table exists
sqlite3 ~/.vidurai/vidurai.db ".schema vec_memories"

# Check outcome column
sqlite3 ~/.vidurai/vidurai.db "PRAGMA table_info(memories)" | grep outcome
```

---

## 5. Daemon Integration

### Background Initialization

In `vidurai-daemon/daemon.py`, VectorEngine is initialized in `_background_initialization()`:

1. **VectorEngine created** (instant - no model loaded yet)
2. **Backfill triggered** in daemon thread (non-blocking)
3. **Model lazy-loads** on first `generate_embedding()` call

```python
# From daemon.py:_background_initialization()
from vidurai.core.intelligence import VectorEngine

vector_engine = VectorEngine()  # Instant
backfill_thread = threading.Thread(target=vector_engine.backfill_vectors, daemon=True)
backfill_thread.start()  # Non-blocking
```

---

## 6. Caveats & Limitations

### Known Limitations

1. **First embedding is slow:** Model loads on first `generate_embedding()` call (~2-5 seconds)
2. **Memory usage:** sentence-transformers + torch use ~500MB+ RAM when loaded
3. **Trigger is placeholder:** SQLite trigger can't compute embeddings; application must do it
4. **Vector search requires sqlite-vec:** Not available on all platforms

### Workarounds

1. **Warmup on startup:** Daemon triggers backfill which loads model in background
2. **Graceful degradation:** If sqlite-vec unavailable, vector search disabled (FTS5 still works)
3. **Application-side vectorization:** New memories must call `VectorEngine.generate_embedding()` explicitly

---

## 7. Database Schema (Phase 1 + 1.5)

### memories table (new columns)

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `status` | TEXT | 'ACTIVE' | Purgatory state |
| `decay_reason` | TEXT | NULL | Why forgotten |
| `outcome` | INTEGER | 0 | RL signal (1/-1/0) |
| `pinned` | INTEGER | 0 | Immunity flag |

### vec_memories table (virtual)

```sql
CREATE VIRTUAL TABLE vec_memories USING vec0(
    memory_id INTEGER PRIMARY KEY,
    embedding FLOAT[384]
);
```

---

## 8. Next Steps (Phase 2)

1. **Build Runner:** Execute `npm build` / `pytest` in Shadow Sandbox
2. **Auditor (AST):** Static analysis for safety checks
3. **Retention Policy:** Implement UtilityScore and Immunity Clause
4. **Wire Reality Check:** Auto-verify memories on file save events

---

*Generated by Vidurai Guardian v2.1.0*
