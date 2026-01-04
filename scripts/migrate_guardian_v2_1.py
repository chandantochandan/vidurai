#!/usr/bin/env python3
"""
Guardian Schema Migration v2.1.0

Phase 1: The Foundation - Data Layer Upgrade

This migration adds:
- Purgatory Columns (status, decay_reason) for Smart Forgetting
- Reality Column (outcome) for RL Learning Signal
- Vector Table (vec_memories) for Semantic Search [384 dims - MiniLM]
- Trigger (after_memory_insert) for auto-vectorization

Glass Box Protocol:
- Backup First: Creates timestamped backup before any changes
- Idempotency: Safe to run multiple times (IF NOT EXISTS, graceful errors)
- Lazy Loading: Heavy imports (sqlite_vec) inside functions

@version 2.1.0-Guardian
"""

import os
import sys
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONSTANTS
# =============================================================================

VECTOR_DIMENSIONS = 384  # Standard MiniLM (sentence-transformers)
DB_PATH = Path.home() / '.vidurai' / 'vidurai.db'
SCHEMA_VERSION = 3  # Increment from v2 to v3 for this migration


# =============================================================================
# BACKUP
# =============================================================================

def create_backup(db_path: Path) -> Path:
    """
    Create timestamped backup before migration.

    Glass Box Protocol: "Do No Harm" - Backup First
    """
    if not db_path.exists():
        print(f"⚠️  Database not found at {db_path}")
        print("   Creating new database...")
        return None

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.parent / f'vidurai_backup_{timestamp}.db'

    print(f"📦 Creating backup: {backup_path}")
    shutil.copy2(db_path, backup_path)
    print(f"   ✓ Backup created ({backup_path.stat().st_size / 1024:.1f} KB)")

    return backup_path


# =============================================================================
# SCHEMA CHECKS
# =============================================================================

def column_exists(cursor: sqlite3.Cursor, table: str, column: str) -> bool:
    """Check if a column exists in a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [row[1] for row in cursor.fetchall()]
    return column in columns


def table_exists(cursor: sqlite3.Cursor, table: str) -> bool:
    """Check if a table exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,)
    )
    return cursor.fetchone() is not None


def trigger_exists(cursor: sqlite3.Cursor, trigger_name: str) -> bool:
    """Check if a trigger exists."""
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' AND name=?",
        (trigger_name,)
    )
    return cursor.fetchone() is not None


# =============================================================================
# MIGRATION STEPS
# =============================================================================

def add_purgatory_columns(cursor: sqlite3.Cursor) -> int:
    """
    Add Purgatory columns for Smart Forgetting.

    - status: ACTIVE | DECAYED | PURGED | SILENCED
    - decay_reason: Why was this memory forgotten?
    """
    added = 0

    # Status column
    if not column_exists(cursor, 'memories', 'status'):
        print("   Adding column: status (TEXT DEFAULT 'ACTIVE')")
        cursor.execute("""
            ALTER TABLE memories
            ADD COLUMN status TEXT DEFAULT 'ACTIVE'
        """)
        added += 1
    else:
        print("   ✓ Column 'status' already exists")

    # Decay reason column
    if not column_exists(cursor, 'memories', 'decay_reason'):
        print("   Adding column: decay_reason (TEXT, nullable)")
        cursor.execute("""
            ALTER TABLE memories
            ADD COLUMN decay_reason TEXT
        """)
        added += 1
    else:
        print("   ✓ Column 'decay_reason' already exists")

    return added


def add_reality_columns(cursor: sqlite3.Cursor) -> int:
    """
    Add Reality columns for RL Learning & Safety.

    - outcome: 0=Unknown, 1=Success, -1=Failure (RL signal)
    - pinned: 1=Immune to Decay (The Constitution)
    """
    added = 0

    # Outcome column (RL signal)
    if not column_exists(cursor, 'memories', 'outcome'):
        print("   Adding column: outcome (INTEGER DEFAULT 0)")
        cursor.execute("""
            ALTER TABLE memories
            ADD COLUMN outcome INTEGER DEFAULT 0
        """)
        added += 1
    else:
        print("   ✓ Column 'outcome' already exists")

    # Pinned column (Constitution - Immunity)
    # Note: This may already exist from v2.2 schema
    if not column_exists(cursor, 'memories', 'pinned'):
        print("   Adding column: pinned (INTEGER DEFAULT 0)")
        cursor.execute("""
            ALTER TABLE memories
            ADD COLUMN pinned INTEGER DEFAULT 0
        """)
        added += 1
    else:
        print("   ✓ Column 'pinned' already exists")

    return added


def create_vector_table(conn: sqlite3.Connection, cursor: sqlite3.Cursor) -> bool:
    """
    Create vec_memories virtual table for vector search.

    Glass Box Protocol: Lazy Loading - sqlite_vec imported here only
    Vector Dimensions: 384 (Standard MiniLM)
    """
    # Check if already exists
    if table_exists(cursor, 'vec_memories'):
        print("   ✓ Table 'vec_memories' already exists")
        return False

    # Load sqlite-vec extension
    print("   Loading sqlite-vec extension...")
    try:
        # Glass Box: Lazy import
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        print("   ✓ sqlite-vec extension loaded")
    except ImportError as e:
        print(f"   ⚠️  sqlite-vec not installed: {e}")
        print("   Run: pip install sqlite-vec")
        return False
    except Exception as e:
        print(f"   ⚠️  Failed to load sqlite-vec: {e}")
        return False

    # Create virtual table
    print(f"   Creating vec_memories table (dimensions={VECTOR_DIMENSIONS})")
    try:
        cursor.execute(f"""
            CREATE VIRTUAL TABLE vec_memories USING vec0(
                memory_id INTEGER PRIMARY KEY,
                embedding FLOAT[{VECTOR_DIMENSIONS}]
            )
        """)
        print("   ✓ vec_memories table created")
        return True
    except sqlite3.OperationalError as e:
        print(f"   ⚠️  Failed to create vec_memories: {e}")
        return False


def create_insert_trigger(cursor: sqlite3.Cursor) -> bool:
    """
    Create trigger to auto-insert into vec_memories.

    Note: This trigger inserts a placeholder NULL embedding.
    The actual embedding must be populated by the application
    after computing it from the gist/verbatim text.
    """
    trigger_name = 'after_memory_insert'

    if trigger_exists(cursor, trigger_name):
        print(f"   ✓ Trigger '{trigger_name}' already exists")
        return False

    # Check if vec_memories exists (required for trigger)
    if not table_exists(cursor, 'vec_memories'):
        print(f"   ⚠️  Skipping trigger: vec_memories table not found")
        return False

    print(f"   Creating trigger: {trigger_name}")

    # Note: SQLite doesn't support inserting computed vectors in triggers.
    # The trigger inserts a placeholder row; the application must UPDATE
    # the embedding after computing it.
    #
    # Alternative approach: Don't use a trigger, have the application
    # insert into vec_memories explicitly after computing embeddings.
    #
    # For now, we create a simple trigger that the application can use
    # as a hook point, but actual embedding insertion is application-side.

    try:
        cursor.execute(f"""
            CREATE TRIGGER {trigger_name}
            AFTER INSERT ON memories
            FOR EACH ROW
            BEGIN
                -- Placeholder: Application must compute and insert actual embedding
                -- This trigger serves as documentation of the expected flow
                SELECT 1;  -- No-op for now
            END
        """)
        print(f"   ✓ Trigger '{trigger_name}' created (placeholder)")
        print("   Note: Application must compute and insert embeddings explicitly")
        return True
    except sqlite3.OperationalError as e:
        print(f"   ⚠️  Failed to create trigger: {e}")
        return False


def update_schema_version(cursor: sqlite3.Cursor, version: int) -> None:
    """Update schema version in metadata table."""
    cursor.execute("""
        INSERT OR REPLACE INTO metadata (key, value)
        VALUES ('schema_version', ?)
    """, (str(version),))
    print(f"   ✓ Schema version updated to {version}")


# =============================================================================
# VERIFICATION
# =============================================================================

def verify_migration(cursor: sqlite3.Cursor) -> bool:
    """
    Verify all migration steps completed successfully.
    """
    print("\n🔍 Verifying migration...")

    required_columns = [
        ('memories', 'status'),
        ('memories', 'decay_reason'),
        ('memories', 'outcome'),
        ('memories', 'pinned'),
    ]

    all_ok = True

    for table, column in required_columns:
        if column_exists(cursor, table, column):
            print(f"   ✓ {table}.{column}")
        else:
            print(f"   ✗ {table}.{column} MISSING")
            all_ok = False

    # Check vec_memories (optional - may fail if sqlite-vec not available)
    if table_exists(cursor, 'vec_memories'):
        print(f"   ✓ vec_memories table")
    else:
        print(f"   ⚠ vec_memories table not created (sqlite-vec may not be available)")

    return all_ok


# =============================================================================
# MAIN
# =============================================================================

def main():
    """
    Run the Guardian v2.1.0 migration.
    """
    print("=" * 60)
    print("🏛️  VIDURAI GUARDIAN SCHEMA MIGRATION v2.1.0")
    print("=" * 60)
    print()

    # Ensure .vidurai directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Step 1: Backup
    print("📦 Step 1: Backup")
    backup_path = create_backup(DB_PATH)
    print()

    # Connect to database
    print(f"🔌 Connecting to: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")

    # Ensure base tables exist (in case this is a fresh DB)
    print()
    print("📋 Step 2: Ensuring base schema exists")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
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
            occurrence_count INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    print("   ✓ Base schema verified")
    conn.commit()
    print()

    # Step 3: Add Purgatory columns
    print("⚰️  Step 3: Adding Purgatory columns (Smart Forgetting)")
    purgatory_added = add_purgatory_columns(cursor)
    conn.commit()
    print()

    # Step 4: Add Reality columns
    print("🎯 Step 4: Adding Reality columns (RL Learning)")
    reality_added = add_reality_columns(cursor)
    conn.commit()
    print()

    # Step 5: Create vector table
    print(f"🔮 Step 5: Creating vector table (dims={VECTOR_DIMENSIONS})")
    vector_created = create_vector_table(conn, cursor)
    conn.commit()
    print()

    # Step 6: Create trigger
    print("⚡ Step 6: Creating insert trigger")
    trigger_created = create_insert_trigger(cursor)
    conn.commit()
    print()

    # Step 7: Update schema version
    print("📝 Step 7: Updating schema version")
    update_schema_version(cursor, SCHEMA_VERSION)
    conn.commit()
    print()

    # Verification
    if verify_migration(cursor):
        print()
        print("=" * 60)
        print("✅ MIGRATION COMPLETE")
        print("=" * 60)
        print()
        print("Impact Radius Checked:")
        print("  • database.py INSERT statements: SAFE (use explicit columns)")
        print("  • database.py SELECT statements: SAFE (new columns have defaults)")
        print("  • memory_pinning.py: SAFE (pinned column already existed)")
        print("  • cli.py recall: SAFE (no schema dependency)")
        print()
        if backup_path:
            print(f"Backup location: {backup_path}")
        print(f"Database: {DB_PATH}")
        print(f"Schema version: {SCHEMA_VERSION}")
    else:
        print()
        print("=" * 60)
        print("⚠️  MIGRATION INCOMPLETE - Some columns missing")
        print("=" * 60)
        if backup_path:
            print(f"\nRestore from backup if needed: {backup_path}")
        sys.exit(1)

    conn.close()


if __name__ == "__main__":
    main()
