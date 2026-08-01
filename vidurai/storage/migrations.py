import sqlite3
import logging
from typing import Callable, List, Tuple

logger = logging.getLogger("vidurai.storage.migrations")

TARGET_SCHEMA_VERSION = 7

class MigrationError(Exception):
    pass

class FutureVersionError(MigrationError):
    pass

def _migration_v2(conn: sqlite3.Connection):
    # v2: Audience Gists table (multi-audience support)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audience_gists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id INTEGER NOT NULL,
            audience TEXT NOT NULL,
            gist TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(memory_id) REFERENCES memories(id) ON DELETE CASCADE,
            UNIQUE(memory_id, audience)
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_audience_gists_memory
        ON audience_gists(memory_id)
    """)

def _migration_v3(conn: sqlite3.Connection):
    # v3: Add occurrence_count column for deduplication
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN occurrence_count INTEGER DEFAULT 1")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise

def _migration_v4(conn: sqlite3.Connection):
    # v4: v2.1.0 hotfix: ensure occurrence_count exists (may have been missed in v3 migration)
    try:
        conn.execute("ALTER TABLE memories ADD COLUMN occurrence_count INTEGER DEFAULT 1")
    except sqlite3.OperationalError as e:
        if "duplicate column name" not in str(e).lower():
            raise

def _migration_v5(conn: sqlite3.Connection):
    # v5: WP-02 event_receipts table
    conn.execute("""
        CREATE TABLE IF NOT EXISTS event_receipts (
            receipt_id TEXT PRIMARY KEY NOT NULL,
            event_id TEXT,
            event_type TEXT NOT NULL,
            payload_hash TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL
                CHECK (status IN ('recorded', 'processing', 'processed', 'failed')),
            memory_id INTEGER,
            received_at INTEGER NOT NULL,
            processed_at INTEGER,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            last_attempt_at INTEGER,
            error_code TEXT
        )
    """)
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_event_receipts_event_id
        ON event_receipts(event_id)
        WHERE event_id IS NOT NULL
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_event_receipts_recovery
        ON event_receipts(status, received_at)
    """)

def _migration_v6(conn: sqlite3.Connection):
    # v6: WP-03 identity
    cols_to_add = [
        ('projects', 'project_uuid', 'TEXT'),
        ('projects', 'remote_fingerprint', 'TEXT'),
        ('event_receipts', 'project_uuid', 'TEXT'),
        ('event_receipts', 'branch', 'TEXT'),
        ('event_receipts', 'commit_hash', 'TEXT'),
        ('event_receipts', 'detached_head', 'BOOLEAN')
    ]
    for table, col, defn in cols_to_add:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {defn}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise
                
    conn.execute("""
        CREATE TABLE IF NOT EXISTS project_aliases (
            project_id INTEGER NOT NULL,
            path TEXT UNIQUE NOT NULL,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
    """)
    
    conn.execute("""
        INSERT OR IGNORE INTO project_aliases (project_id, path, last_active)
        SELECT id, path, last_active FROM projects
    """)

def _migration_v7(conn: sqlite3.Connection):
    # v7: WP-07 Context Capsule
    conn.execute("""
        CREATE TABLE IF NOT EXISTS context_capsules (
            capsule_id TEXT PRIMARY KEY NOT NULL,
            client_id TEXT NOT NULL,
            project_uuid TEXT NOT NULL,
            branch TEXT,
            task TEXT,
            content_hash TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('preview', 'approved', 'rejected', 'expired')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            delivery_count INTEGER DEFAULT 0
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_context_capsules_lookup ON context_capsules(client_id, project_uuid, status)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS capsule_items (
            capsule_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            category TEXT NOT NULL CHECK (category IN ('evidence', 'decision', 'working', 'unresolved', 'contradiction', 'interpretation', 'recommendation')),
            source_id TEXT,
            content TEXT NOT NULL,
            inclusion_reason TEXT,
            provenance TEXT,
            FOREIGN KEY (capsule_id) REFERENCES context_capsules(capsule_id) ON DELETE CASCADE,
            UNIQUE(capsule_id, item_id)
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_capsule_items_capsule ON capsule_items(capsule_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS capsule_excluded_items (
            capsule_id TEXT NOT NULL,
            item_id TEXT NOT NULL,
            exclusion_reason TEXT,
            FOREIGN KEY (capsule_id) REFERENCES context_capsules(capsule_id) ON DELETE CASCADE,
            UNIQUE(capsule_id, item_id)
        )
    """)

MIGRATIONS: List[Callable[[sqlite3.Connection], None]] = [
    None, # v0 -> v1 is base schema
    _migration_v2, # v1 -> v2
    _migration_v3, # v2 -> v3
    _migration_v4, # v3 -> v4
    _migration_v5, # v4 -> v5
    _migration_v6, # v5 -> v6
    _migration_v7, # v6 -> v7
]

def get_current_version(conn: sqlite3.Connection) -> int:
    try:
        # Check if metadata table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
        if not cursor.fetchone():
            return 0 # Fresh database
            
        result = conn.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
        if result:
            return int(result[0])
        return 1 # Has metadata but no schema_version -> v1
    except sqlite3.OperationalError:
        return 0

def run_migrations(conn: sqlite3.Connection):
    """
    Run migrations safely and atomically.
    """
    current_version = get_current_version(conn)
    
    if current_version > TARGET_SCHEMA_VERSION:
        raise FutureVersionError(f"Database schema version {current_version} is newer than supported version {TARGET_SCHEMA_VERSION}. Please upgrade Vidurai.")
        
    if current_version == TARGET_SCHEMA_VERSION:
        logger.debug(f"Database schema is up to date (v{TARGET_SCHEMA_VERSION})")
        return
        
    logger.info(f"Database schema needs migration: v{current_version} -> v{TARGET_SCHEMA_VERSION}")
    
    # We must use isolation_level=None to control transactions manually,
    # because some schema changes (like PRAGMA) might interfere, but ALTER TABLE
    # can be run inside a transaction in SQLite.
    
    conn.execute("BEGIN EXCLUSIVE")
    try:
        # If fresh db, we still apply all migrations from 1 to latest.
        # But wait, v1 requires the base tables to exist!
        if current_version == 0:
            _create_base_schema(conn)
            current_version = 1
            
        for version in range(current_version + 1, TARGET_SCHEMA_VERSION + 1):
            logger.info(f"Applying migration to v{version}...")
            migration_func = MIGRATIONS[version - 1]
            if migration_func:
                migration_func(conn)
                
        # Update version in metadata
        conn.execute("INSERT OR REPLACE INTO metadata (key, value) VALUES ('schema_version', ?)", (str(TARGET_SCHEMA_VERSION),))
        conn.commit()
        logger.info(f"Successfully migrated schema to v{TARGET_SCHEMA_VERSION}")
    except Exception as e:
        conn.rollback()
        logger.error(f"Migration failed at version {current_version}->{TARGET_SCHEMA_VERSION}: {e}")
        raise MigrationError(f"Database migration failed: {e}")

def _create_base_schema(conn: sqlite3.Connection):
    """Creates the base v1 schema."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            verbatim TEXT NOT NULL,
            event_type TEXT NOT NULL,
            file_path TEXT,
            line_number INTEGER,
            salience TEXT NOT NULL,
            access_count INTEGER DEFAULT 0,
            last_accessed TIMESTAMP,
            gist TEXT NOT NULL,
            tags TEXT,
            pinned INTEGER DEFAULT 0,
            pin_reason TEXT,
            pinned_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_salience ON memories(salience)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_created ON memories(created_at DESC)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_file ON memories(file_path)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_pinned ON memories(pinned) WHERE pinned = 1")
    
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
        USING fts5(memory_id, gist, verbatim, tags)
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS active_state (
            file_path TEXT PRIMARY KEY,
            project_id INTEGER,
            has_errors BOOLEAN DEFAULT FALSE,
            error_count INTEGER DEFAULT 0,
            warning_count INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_summary TEXT,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_active_state_project ON active_state(project_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_active_state_errors ON active_state(has_errors) WHERE has_errors = TRUE")
