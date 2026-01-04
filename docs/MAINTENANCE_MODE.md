# VIDURAI CODING CONSTITUTION
**Phase:** MAINTENANCE (Post-Launch)
**Version:** 2.2.0-Guardian
**Status:** LOCKED

---

## MAINTENANCE PROTOCOLS

### 1. The "No Regressions" Rule

Any change to `core/` must pass the existing "Impact Radius" check:

```bash
# Before ANY change to core/, run:
python scripts/verify_lifecycle.py
```

**CRITICAL:** Do not break the Atomic Archiver logic:
```
SELECT → WRITE → VERIFY → DELETE
```

If the Parquet file doesn't exist after write, **ABORT** the SQLite delete.

---

### 2. Schema Discipline

If you change the SQLite schema, you **MUST** update the Parquet schema in `MemoryArchiver` to match.

**SQLite Schema (Source of Truth):** `vidurai/storage/database.py`

**Parquet Schema (Must Match):** `vidurai/core/archival/archiver.py`

| SQLite Column | Parquet Column | Type |
|---------------|----------------|------|
| `id` | `id` | int64 |
| `verbatim` | `verbatim` | string |
| `gist` | `gist` | string |
| `salience` | `salience` | string |
| `status` | - | (not archived) |
| `outcome` | `outcome` | int64 |
| `file_path` | `file_path` | string |
| `decay_reason` | `decay_reason` | string |
| `event_type` | `event_type` | string |
| `tags` | `tags` | string (JSON) |
| `project_id` | `project_id` | int64 |
| `created_at` | `created_at` | string (ISO) |
| `expires_at` | `expires_at` | string (ISO) |
| `access_count` | `access_count` | int64 |
| - | `archived_at` | string (ISO) |

**Mismatched columns = Broken Analytics**

If you add a column to SQLite:
1. Add it to the `SELECT` in `archiver.py:flush_archived_memories()`
2. Add it to the dict construction loop
3. Update `docs/PHASE_4_MANIFEST.md` Parquet Schema table

---

### 3. Dependency Freeze

We are locked on these critical dependencies:

| Package | Locked Version | Reason |
|---------|----------------|--------|
| `sqlite-vec` | >=0.1.0 | Vector search |
| `duckdb` | >=0.9.0 | Archive analytics |
| `sentence-transformers` | >=2.2.0 | Embeddings |
| `pyarrow` | >=14.0.0 | Parquet I/O |
| `pandas` | >=2.0.0 | DataFrame ops |

**DO NOT** upgrade major versions without:
1. A migration plan document
2. Full test suite pass
3. Backup of existing archive data

---

## RECURRING CHECKS

### Weekly Maintenance

```bash
# 1. Run lifecycle verification
python scripts/verify_lifecycle.py

# 2. Check archive stats
python -m vidurai.core.archival.archiver --stats

# 3. Run hygiene cycle
vidurai hygiene --dry-run
```

### Flight Recorder Audit

Periodically check for silent failures:

```bash
# Check if crash dump exists
ls -la ~/.vidurai/crash_dump.bin

# If exists, decode and review
python -c "
import pickle
from pathlib import Path
dump = Path.home() / '.vidurai' / 'crash_dump.bin'
if dump.exists():
    with open(dump, 'rb') as f:
        data = pickle.load(f)
        print(data)
"
```

---

## MANIFEST UPDATES

If you modify any core logic, update the corresponding manifest:

| Component | Manifest File |
|-----------|---------------|
| SearchController, ZombieKiller | `docs/PHASE_0_MANIFEST.md` |
| Schema, Status columns | `docs/PHASE_1_MANIFEST.md` |
| CodeAuditor, RetentionJudge | `docs/PHASE_2_MANIFEST.md` |
| StateLinker, ViduraiRetriever | `docs/PHASE_3_MANIFEST.md` |
| Archiver, Analyst, DreamCycle | `docs/PHASE_4_MANIFEST.md` |

---

## PR CHECKLIST

Before merging any PR to `main`:

- [ ] `python scripts/verify_lifecycle.py` passes
- [ ] No new dependencies added without approval
- [ ] Schema changes reflected in both SQLite and Parquet
- [ ] Manifest documentation updated if logic changed
- [ ] TypeScript compiles: `npm run compile` in `vidurai-vscode-extension/`
- [ ] Security audit: All IPC sends use `sanitize()` (see `SECURITY_PROTOCOLS.md`)

---

*Status: Active | Vidurai Guardian v2.2.0*
