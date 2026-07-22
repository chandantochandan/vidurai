# Baseline SQLite Contract

## Current Schema Version
- Unknown strict numbered versioning; relies on `IF NOT EXISTS` block execution on init.

## Tables & Columns

### 1. `projects`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `path`: TEXT UNIQUE NOT NULL
- `name`: TEXT NOT NULL
- `created_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- `last_active`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 2. `memories`
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `project_id`: INTEGER NOT NULL (FK to projects.id implicitly, though no explicit FOREIGN KEY constraint is enforced)
- `verbatim`: TEXT NOT NULL
- `event_type`: TEXT NOT NULL
- `file_path`: TEXT
- `line_number`: INTEGER
- `salience`: TEXT NOT NULL
- `access_count`: INTEGER DEFAULT 0
- `last_accessed`: TIMESTAMP
- `gist`: TEXT NOT NULL
- `tags`: TEXT

### 3. `metadata`
- `key`: TEXT PRIMARY KEY
- `value`: TEXT
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 4. `active_state`
- `project_id`: INTEGER PRIMARY KEY
- `active_file`: TEXT
- `context_window`: TEXT
- `updated_at`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP

### 5. `audience_gists`
- `memory_id`: INTEGER NOT NULL
- `audience`: TEXT NOT NULL
- `gist`: TEXT NOT NULL
- `last_updated`: TIMESTAMP DEFAULT CURRENT_TIMESTAMP
- Primary Key: `(memory_id, audience)`

## Indexes
- `idx_memories_project_salience` ON `memories(project_id, salience)`
- `idx_memories_last_accessed` ON `memories(last_accessed)`
- `idx_audience_gists_memory` ON `audience_gists(memory_id)`

## FTS Objects
- `memories_fts` (Virtual Table using fts5)
  - Columns: `verbatim`, `gist`, `tags`, `content='memories'`, `content_rowid='id'`

## Migration Sequence
- Executed on `MemoryDatabase.__init__()`.
- Executes `CREATE TABLE IF NOT EXISTS` for all tables.
- Creates indexes `IF NOT EXISTS`.
- Rebuilds FTS virtual table triggers (`memories_ai`, `memories_ad`, `memories_au`).

## Current Persistence Behavior
- Written synchronously in daemon.
- Single global database file located at `~/.vidurai/memory.db`.
