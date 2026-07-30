import pytest
import sqlite3
import tempfile
from pathlib import Path
from vidurai.storage.database import MemoryDatabase
from vidurai.storage.migrations import run_migrations, FutureVersionError, MigrationError, TARGET_SCHEMA_VERSION

def test_fresh_database_creation():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        db = MemoryDatabase(db_path=db_path)
        
        # Verify schema version
        conn = sqlite3.connect(db_path)
        res = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        assert res is not None
        assert int(res[0]) == TARGET_SCHEMA_VERSION
        
        # Verify a table exists
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories'")
        assert cursor.fetchone() is not None
        conn.close()
        db.close()

def _create_v1_database(db_path: Path):
    conn = sqlite3.connect(db_path)
    # v1 schema (no audience_gists, no occurrence_count, no event_receipts, no identity)
    conn.execute("""
        CREATE TABLE projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE memories (
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
    conn.execute("CREATE VIRTUAL TABLE memories_fts USING fts5(memory_id, gist, verbatim, tags)")
    conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute("INSERT INTO metadata (key, value) VALUES ('schema_version', '1')")
    
    # Insert some data to ensure preservation
    conn.execute("INSERT INTO projects (path, name) VALUES ('/test/path', 'test')")
    conn.execute("INSERT INTO memories (project_id, verbatim, event_type, salience, gist) VALUES (1, 'code', 'edit', 'high', 'gist')")
    
    conn.commit()
    conn.close()

def test_v1_to_latest_upgrade():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        _create_v1_database(db_path)
        
        # Open with MemoryDatabase, which runs migrations
        db = MemoryDatabase(db_path=db_path)
        
        conn = sqlite3.connect(db_path)
        # Verify schema version
        res = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        assert int(res[0]) == TARGET_SCHEMA_VERSION
        
        # Verify occurrence_count added
        cursor = conn.execute("PRAGMA table_info(memories)")
        cols = [row[1] for row in cursor.fetchall()]
        assert "occurrence_count" in cols
        
        # Verify WP-03 project aliases added
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_aliases'")
        assert cursor.fetchone() is not None
        
        # Verify old data preserved
        res = conn.execute("SELECT gist FROM memories WHERE id=1").fetchone()
        assert res[0] == 'gist'
        
        # Verify project_aliases got populated from projects
        res = conn.execute("SELECT path FROM project_aliases WHERE project_id=1").fetchone()
        assert res[0] == '/test/path'
        
        conn.close()
        db.close()

def test_future_version_rejection():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        conn.execute("INSERT INTO metadata (key, value) VALUES ('schema_version', '999')")
        conn.commit()
        conn.close()
        
        with pytest.raises(FutureVersionError) as excinfo:
            MemoryDatabase(db_path=db_path)
        assert "newer than supported version" in str(excinfo.value)

def test_migration_failure_rollback():
    # Simulate a failure during migration by introducing a typo in a mock migration
    import vidurai.storage.migrations as migrations
    
    original_v6 = migrations._migration_v6
    
    def _faulty_v6(conn):
        # Do something right
        conn.execute("CREATE TABLE temp_test (id INTEGER)")
        # Then throw an error
        conn.execute("SYNTAX ERROR BAD SQL")
        
    migrations.MIGRATIONS[5] = _faulty_v6
    
    try:
        with tempfile.TemporaryDirectory() as tmp:
            db_path = Path(tmp) / "test.db"
            _create_v1_database(db_path)
            
            # Change version to 5 so only v6 runs
            conn = sqlite3.connect(db_path)
            conn.execute("UPDATE metadata SET value = '5' WHERE key = 'schema_version'")
            conn.commit()
            conn.close()
            
            with pytest.raises(MigrationError):
                MemoryDatabase(db_path=db_path)
                
            # Verify rollback
            conn = sqlite3.connect(db_path)
            res = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
            assert int(res[0]) == 5 # Version not incremented
            
            # Verify temp_test was rolled back
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='temp_test'")
            assert cursor.fetchone() is None
            
    finally:
        migrations.MIGRATIONS[5] = original_v6

    # Now remove the injected failure and prove reopening completes successfully
    db2 = MemoryDatabase(db_path=db_path)
    conn = sqlite3.connect(db_path)
    res = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
    assert int(res[0]) == TARGET_SCHEMA_VERSION
    conn.close()
    db2.close()


def test_repeated_startup_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        # First startup (creates fresh)
        db1 = MemoryDatabase(db_path=db_path)
        
        # Insert some test data to ensure it is not wiped
        conn = sqlite3.connect(db_path)
        conn.execute("INSERT INTO projects (path, name) VALUES ('/test', 'test')")
        conn.commit()
        conn.close()
        
        # Second startup (should do nothing)
        db2 = MemoryDatabase(db_path=db_path)
        
        conn = sqlite3.connect(db_path)
        res = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        assert int(res[0]) == TARGET_SCHEMA_VERSION
        
        res = conn.execute("SELECT count(*) FROM projects").fetchone()
        assert res[0] == 1
        conn.close()
        db1.close()
        db2.close()


def test_v4_to_latest_upgrade():
    # Pre-WP-02 database -> latest
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        
        # Create base
        _create_v1_database(db_path)
        conn = sqlite3.connect(db_path)
        
        # Apply up to v4
        import vidurai.storage.migrations as migrations
        migrations._migration_v2(conn)
        migrations._migration_v3(conn)
        migrations._migration_v4(conn)
        conn.execute("UPDATE metadata SET value = '4' WHERE key = 'schema_version'")
        
        # Verify FTS and memories data exist
        conn.execute("INSERT INTO memories_fts(memory_id, gist, verbatim, tags) VALUES (1, 'gist', 'code', '')")
        conn.commit()
        conn.close()
        
        # Upgrade
        db = MemoryDatabase(db_path=db_path)
        
        conn = sqlite3.connect(db_path)
        # Verify data preserved
        res = conn.execute("SELECT gist FROM memories WHERE id=1").fetchone()
        assert res[0] == 'gist'
        res = conn.execute("SELECT gist FROM memories_fts WHERE memory_id=1").fetchone()
        assert res[0] == 'gist'
        
        # Verify schema version
        res = conn.execute("SELECT value FROM metadata WHERE key='schema_version'").fetchone()
        assert int(res[0]) == TARGET_SCHEMA_VERSION
        
        conn.close()
        db.close()

def test_v5_to_latest_upgrade():
    # WP-02 database (v5) -> latest
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        
        _create_v1_database(db_path)
        conn = sqlite3.connect(db_path)
        
        import vidurai.storage.migrations as migrations
        migrations._migration_v2(conn)
        migrations._migration_v3(conn)
        migrations._migration_v4(conn)
        migrations._migration_v5(conn)
        conn.execute("UPDATE metadata SET value = '5' WHERE key = 'schema_version'")
        
        # Insert event receipt
        conn.execute("INSERT INTO event_receipts (receipt_id, event_id, event_type, payload_hash, payload_json, status, memory_id, received_at, attempt_count) VALUES ('r1', 'e1', 'type1', 'hash1', '{}', 'processed', 1, 12345, 1)")
        conn.commit()
        conn.close()
        
        # Upgrade
        db = MemoryDatabase(db_path=db_path)
        
        conn = sqlite3.connect(db_path)
        # Verify event receipt preserved
        res = conn.execute("SELECT status, event_id, memory_id FROM event_receipts WHERE receipt_id='r1'").fetchone()
        assert res[0] == 'processed'
        assert res[1] == 'e1'
        assert res[2] == 1
        
        conn.close()
        db.close()

def test_v6_reopen_preserves_identity():
    # WP-03 database (v6) reopening
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        
        # Full creation
        db = MemoryDatabase(db_path=db_path)
        conn = sqlite3.connect(db_path)
        
        # Insert WP-03 specific fields
        conn.execute("INSERT INTO projects (id, path, name, project_uuid, remote_fingerprint) VALUES (99, '/wp03', 'wp03', 'uuid-99', 'fingerprint-99')")
        conn.execute("INSERT INTO project_aliases (project_id, path) VALUES (99, '/alias-wp03')")
        conn.execute("INSERT INTO event_receipts (receipt_id, event_type, payload_hash, payload_json, status, received_at, project_uuid, branch, commit_hash, detached_head) VALUES ('r99', 'type', 'hash', '{}', 'recorded', 123, 'uuid-99', 'main', 'abcdef', 0)")
        conn.commit()
        conn.close()
        db.close()
        
        # Reopen
        db2 = MemoryDatabase(db_path=db_path)
        conn = sqlite3.connect(db_path)
        
        res = conn.execute("SELECT project_uuid, remote_fingerprint FROM projects WHERE id=99").fetchone()
        assert res[0] == 'uuid-99'
        assert res[1] == 'fingerprint-99'
        
        res = conn.execute("SELECT path FROM project_aliases WHERE project_id=99").fetchone()
        assert res[0] == '/alias-wp03'
        
        res = conn.execute("SELECT branch, commit_hash, detached_head FROM event_receipts WHERE receipt_id='r99'").fetchone()
        assert res[0] == 'main'
        assert res[1] == 'abcdef'
        assert res[2] == 0
        
        conn.close()
        db2.close()
