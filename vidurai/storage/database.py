"""
SQLite-backed persistent memory storage
Vidurai v2.0 - Phase 1 Database Layer
"""
import sqlite3
import json
import shutil
import pickle
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
from enum import Enum

logger = logging.getLogger("vidurai.database")


class SalienceLevel(Enum):
    """Memory importance levels aligned with Three-Kosha architecture"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    NOISE = 1


class MemoryDatabase:
    """SQLite-backed persistent memory storage with auto-migration"""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path.home() / ".vidurai" / "memory.db"

        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self.conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Enable foreign key constraints (required for CASCADE)
        self.conn.execute("PRAGMA foreign_keys = ON")

        logger.info(f"Initializing database at {db_path}")

        # Initialize schema
        self._init_schema()

        # Auto-migrate from pickle if exists
        self._migrate_from_pickle()

        # Auto-cleanup expired memories
        self.cleanup_expired()

        logger.info("Database initialized successfully")

    def _init_schema(self):
        """Create database schema with Three-Kosha architecture"""
        cursor = self.conn.cursor()

        # Projects table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Memories table (Three-Kosha architecture)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,

                -- Annamaya Kosha (Physical/Verbatim)
                verbatim TEXT NOT NULL,
                event_type TEXT NOT NULL,
                file_path TEXT,
                line_number INTEGER,

                -- Pranamaya Kosha (Active/Salience)
                salience TEXT NOT NULL,
                access_count INTEGER DEFAULT 0,
                last_accessed TIMESTAMP,

                -- Manomaya Kosha (Wisdom/Gist)
                gist TEXT NOT NULL,
                tags TEXT,

                -- Metadata
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,

                FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
            )
        """)

        # Indexes for fast queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_project
            ON memories(project_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_salience
            ON memories(salience)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_created
            ON memories(created_at DESC)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_memories_file
            ON memories(file_path)
        """)

        # Full-text search on gists (FTS5 for Phase 1)
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(memory_id, gist, verbatim, tags)
        """)

        # Metadata table for schema versioning
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        self.conn.commit()
        logger.debug("Database schema initialized")

        # Check and upgrade schema version
        self._check_and_migrate_schema()

    def _check_and_migrate_schema(self):
        """Check current schema version and apply migrations"""
        cursor = self.conn.cursor()

        # Get current schema version
        try:
            result = cursor.execute(
                "SELECT value FROM metadata WHERE key = 'schema_version'"
            ).fetchone()
            current_version = int(result['value']) if result else 1
        except (sqlite3.OperationalError, TypeError):
            # metadata table doesn't exist or no version set
            current_version = 1

        # Schema version 2: Multi-audience gists
        if current_version < 2:
            logger.info("Migrating schema to version 2 (multi-audience gists)")
            self._migrate_to_v2()
            current_version = 2

        # Store current version
        cursor.execute("""
            INSERT OR REPLACE INTO metadata (key, value)
            VALUES ('schema_version', ?)
        """, (str(current_version),))
        self.conn.commit()

        logger.debug(f"Schema version: {current_version}")

    def _migrate_to_v2(self):
        """Migrate to schema version 2: Add audience_gists table"""
        cursor = self.conn.cursor()

        # Create audience_gists table
        cursor.execute("""
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

        # Index for fast lookups by memory_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audience_gists_memory
            ON audience_gists(memory_id)
        """)

        # Index for queries by audience type
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audience_gists_audience
            ON audience_gists(audience)
        """)

        self.conn.commit()
        logger.info("✅ Schema migration to v2 complete (audience_gists table added)")

    def get_or_create_project(self, project_path: str) -> int:
        """Get project ID, creating if needed"""
        cursor = self.conn.cursor()

        # Try to find existing
        cursor.execute(
            "SELECT id FROM projects WHERE path = ?",
            (project_path,)
        )
        result = cursor.fetchone()

        if result:
            # Update last_active
            cursor.execute(
                "UPDATE projects SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
                (result['id'],)
            )
            self.conn.commit()
            return result['id']

        # Create new
        project_name = Path(project_path).name
        cursor.execute(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (project_path, project_name)
        )
        self.conn.commit()
        logger.info(f"Created new project: {project_name} (ID: {cursor.lastrowid})")
        return cursor.lastrowid

    def store_memory(
        self,
        project_path: str,
        verbatim: str,
        gist: str,
        salience: SalienceLevel,
        event_type: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        tags: Optional[List[str]] = None,
        retention_days: Optional[int] = None
    ) -> int:
        """Store new memory in database"""
        try:
            project_id = self.get_or_create_project(project_path)
            cursor = self.conn.cursor()

            # Calculate expiration
            expires_at = None
            if retention_days:
                expires_at = (datetime.now() + timedelta(days=retention_days)).isoformat()

            # Insert memory
            cursor.execute("""
                INSERT INTO memories (
                    project_id, verbatim, gist, salience, event_type,
                    file_path, line_number, tags, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_id,
                verbatim,
                gist,
                salience.name,
                event_type,
                file_path,
                line_number,
                json.dumps(tags) if tags else None,
                expires_at
            ))

            memory_id = cursor.lastrowid

            # Add to full-text search
            cursor.execute("""
                INSERT INTO memories_fts (memory_id, gist, verbatim, tags)
                VALUES (?, ?, ?, ?)
            """, (
                memory_id,
                gist,
                verbatim,
                json.dumps(tags) if tags else None
            ))

            self.conn.commit()
            logger.debug(f"Stored memory {memory_id} (salience: {salience.name})")
            return memory_id

        except sqlite3.Error as e:
            logger.error(f"Database error storing memory: {e}")
            raise

    def store_audience_gists(
        self,
        memory_id: int,
        gists: Dict[str, str]
    ) -> None:
        """
        Store multiple audience-specific gists for a memory.

        Uses UPSERT (INSERT OR REPLACE) to handle both new and updated gists.

        Args:
            memory_id: ID of the memory
            gists: Dictionary mapping audience -> gist text
                   e.g., {"developer": "...", "ai": "...", "manager": "...", "personal": "..."}

        Example:
            >>> db.store_audience_gists(123, {
            ...     "developer": "Fixed auth bug in JWT validation",
            ...     "ai": "Pattern: Authentication error resolution",
            ...     "manager": "Auth system stabilized",
            ...     "personal": "I learned JWT token validation"
            ... })
        """
        try:
            cursor = self.conn.cursor()

            for audience, gist in gists.items():
                cursor.execute("""
                    INSERT OR REPLACE INTO audience_gists (memory_id, audience, gist)
                    VALUES (?, ?, ?)
                """, (memory_id, audience, gist))

            self.conn.commit()
            logger.debug(f"Stored {len(gists)} audience gists for memory {memory_id}")

        except sqlite3.Error as e:
            logger.error(f"Database error storing audience gists: {e}")
            raise

    def get_audience_gists(
        self,
        memory_id: int,
        audiences: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Retrieve audience-specific gists for a memory.

        Args:
            memory_id: ID of the memory
            audiences: Optional list of audience types to retrieve.
                      If None, returns all audiences.
                      e.g., ["developer", "ai"]

        Returns:
            Dictionary mapping audience -> gist text
            Empty dict if no gists found

        Example:
            >>> gists = db.get_audience_gists(123)
            >>> print(gists)
            {"developer": "...", "ai": "...", "manager": "...", "personal": "..."}

            >>> dev_gist = db.get_audience_gists(123, audiences=["developer"])
            >>> print(dev_gist)
            {"developer": "..."}
        """
        try:
            cursor = self.conn.cursor()

            if audiences:
                # Filter by specific audiences
                placeholders = ','.join('?' * len(audiences))
                sql = f"""
                    SELECT audience, gist
                    FROM audience_gists
                    WHERE memory_id = ?
                      AND audience IN ({placeholders})
                """
                params = [memory_id] + audiences
            else:
                # Get all audiences
                sql = """
                    SELECT audience, gist
                    FROM audience_gists
                    WHERE memory_id = ?
                """
                params = [memory_id]

            results = cursor.execute(sql, params).fetchall()

            # Convert to dictionary
            gists = {row['audience']: row['gist'] for row in results}

            logger.debug(f"Retrieved {len(gists)} audience gists for memory {memory_id}")
            return gists

        except sqlite3.Error as e:
            logger.error(f"Database error retrieving audience gists: {e}")
            return {}  # Fail-safe: return empty dict

    def recall_memories(
        self,
        project_path: str,
        query: Optional[str] = None,
        min_salience: SalienceLevel = SalienceLevel.MEDIUM,
        limit: int = 10,
        hours_back: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Recall relevant memories for a project"""
        try:
            project_id = self.get_or_create_project(project_path)
            cursor = self.conn.cursor()

            # Build query
            sql = """
                SELECT
                    m.id, m.verbatim, m.gist, m.salience, m.event_type,
                    m.file_path, m.line_number, m.tags,
                    m.created_at, m.access_count
                FROM memories m
                WHERE m.project_id = ?
                    AND (m.expires_at IS NULL OR m.expires_at > datetime('now'))
            """
            params = [project_id]

            # Filter by salience
            salience_values = [s.name for s in SalienceLevel if s.value >= min_salience.value]
            sql += f" AND m.salience IN ({','.join('?' * len(salience_values))})"
            params.extend(salience_values)

            # Filter by time
            if hours_back:
                sql += " AND m.created_at >= datetime('now', ?)"
                params.append(f'-{hours_back} hours')

            # Full-text search if query provided
            if query and query.strip():
                sql = f"""
                    SELECT m.*, 0 as rank
                    FROM ({sql}) m
                    JOIN memories_fts fts ON fts.memory_id = m.id
                    WHERE memories_fts MATCH ?
                    ORDER BY fts.rank, m.created_at DESC
                """
                params.append(query)
            else:
                sql += " ORDER BY m.salience DESC, m.created_at DESC"

            sql += " LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            results = cursor.fetchall()

            # Update access counts
            memory_ids = [r['id'] for r in results]
            if memory_ids:
                placeholders = ','.join('?' * len(memory_ids))
                cursor.execute(f"""
                    UPDATE memories
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                """, memory_ids)
                self.conn.commit()

            # Convert to dicts
            memories = [dict(row) for row in results]
            logger.debug(f"Recalled {len(memories)} memories for query: {query}")
            return memories

        except sqlite3.Error as e:
            logger.error(f"Database error recalling memories: {e}")
            return []

    def get_recent_activity(
        self,
        project_path: str,
        hours: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent memories for a project"""
        return self.recall_memories(
            project_path=project_path,
            min_salience=SalienceLevel.LOW,
            hours_back=hours,
            limit=limit
        )

    def cleanup_expired(self) -> int:
        """Remove expired memories (auto-run on startup)"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                DELETE FROM memories
                WHERE expires_at IS NOT NULL
                    AND expires_at < datetime('now')
            """)
            deleted = cursor.rowcount
            self.conn.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired memories")

            return deleted

        except sqlite3.Error as e:
            logger.error(f"Error cleaning up expired memories: {e}")
            return 0

    def get_statistics(self, project_path: str) -> Dict[str, Any]:
        """Get memory statistics for a project"""
        try:
            project_id = self.get_or_create_project(project_path)
            cursor = self.conn.cursor()

            # Total memories
            cursor.execute(
                "SELECT COUNT(*) as total FROM memories WHERE project_id = ?",
                (project_id,)
            )
            total = cursor.fetchone()['total']

            # By salience
            cursor.execute("""
                SELECT salience, COUNT(*) as count
                FROM memories
                WHERE project_id = ?
                GROUP BY salience
            """, (project_id,))
            by_salience = {row['salience']: row['count'] for row in cursor.fetchall()}

            # By event type
            cursor.execute("""
                SELECT event_type, COUNT(*) as count
                FROM memories
                WHERE project_id = ?
                GROUP BY event_type
            """, (project_id,))
            by_type = {row['event_type']: row['count'] for row in cursor.fetchall()}

            return {
                'total': total,
                'by_salience': by_salience,
                'by_type': by_type
            }

        except sqlite3.Error as e:
            logger.error(f"Error getting statistics: {e}")
            return {'total': 0, 'by_salience': {}, 'by_type': {}}

    def _migrate_from_pickle(self):
        """One-time migration from v1.x pickle files"""
        pickle_dir = Path.home() / ".vidurai" / "sessions"

        if not pickle_dir.exists():
            logger.debug("No pickle sessions found, skipping migration")
            return

        # Check if already migrated
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM memories")
        if cursor.fetchone()['count'] > 0:
            logger.debug("Database already has memories, skipping migration")
            return

        logger.info("🔄 Migrating from v1.x pickle format...")
        migrated_count = 0

        for pickle_file in pickle_dir.glob("*.pkl"):
            try:
                with open(pickle_file, 'rb') as f:
                    old_data = pickle.load(f)

                # Extract project path from session data or filename
                project_path = old_data.get('workspace_path', str(pickle_file.stem))

                # Migrate memories from different Kosha layers
                # Try to extract from common pickle structures
                memories_to_migrate = []

                # Check for VismritiMemory structure
                if 'memory_data' in old_data:
                    memories_to_migrate.extend(old_data.get('memory_data', []))

                # Check for direct memory lists
                if 'annamaya' in old_data:
                    memories_to_migrate.extend(old_data.get('annamaya', []))
                if 'manomaya' in old_data:
                    memories_to_migrate.extend(old_data.get('manomaya', []))
                if 'vijnanamaya' in old_data:
                    memories_to_migrate.extend(old_data.get('vijnanamaya', []))

                # Migrate each memory
                for mem in memories_to_migrate:
                    try:
                        # Handle different pickle structures
                        content = mem.get('content', '') or mem.get('verbatim', '')
                        gist = mem.get('gist', content[:100])
                        salience_str = mem.get('salience', 'MEDIUM')

                        # Convert string salience to enum
                        try:
                            salience = SalienceLevel[salience_str.upper()]
                        except (KeyError, AttributeError):
                            salience = SalienceLevel.MEDIUM

                        self.store_memory(
                            project_path=project_path,
                            verbatim=content,
                            gist=gist,
                            salience=salience,
                            event_type=mem.get('type', 'generic'),
                            file_path=mem.get('file'),
                            line_number=mem.get('line')
                        )
                        migrated_count += 1

                    except Exception as e:
                        logger.warning(f"Failed to migrate individual memory: {e}")
                        continue

                # Backup old file
                backup_path = pickle_file.with_suffix('.pkl.v1.bak')
                shutil.move(str(pickle_file), str(backup_path))
                logger.info(f"Migrated {pickle_file.name} → backed up to {backup_path.name}")

            except Exception as e:
                logger.error(f"Failed to migrate {pickle_file}: {e}")
                continue

        if migrated_count > 0:
            logger.info(f"✅ Migration complete! Migrated {migrated_count} memories from pickle format")
        else:
            logger.debug("No memories found in pickle files")

    def get_recent_similar_memories(
        self,
        project_path: str,
        file_path: Optional[str] = None,
        event_type: Optional[str] = None,
        hours_back: int = 168  # 7 days default
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories that might be duplicates

        Used by aggregation system to find similar memories

        Args:
            project_path: Project path
            file_path: Optional file path to filter
            event_type: Optional event type to filter
            hours_back: Hours to look back (default: 168 = 7 days)

        Returns:
            List of memory dicts
        """
        try:
            project_id = self.get_or_create_project(project_path)
            cursor = self.conn.cursor()

            sql = """
                SELECT
                    id, verbatim, gist, salience, event_type,
                    file_path, line_number, tags,
                    created_at, access_count
                FROM memories
                WHERE project_id = ?
                    AND created_at >= datetime('now', ?)
            """
            params = [project_id, f'-{hours_back} hours']

            # Filter by file if provided
            if file_path:
                sql += " AND file_path = ?"
                params.append(file_path)

            # Filter by event type if provided
            if event_type:
                sql += " AND event_type = ?"
                params.append(event_type)

            sql += " ORDER BY created_at DESC LIMIT 100"

            cursor.execute(sql, params)
            results = cursor.fetchall()

            memories = [dict(row) for row in results]
            logger.debug(f"Found {len(memories)} recent similar memories")
            return memories

        except sqlite3.Error as e:
            logger.error(f"Error getting recent similar memories: {e}")
            return []

    def update_memory_aggregation(
        self,
        memory_id: int,
        new_gist: str,
        new_salience: str,
        occurrence_count: int,
        tags: List[str]
    ) -> bool:
        """
        Update an existing memory with aggregation metadata

        Used to update memories that have been aggregated

        Args:
            memory_id: ID of memory to update
            new_gist: Updated gist with occurrence count
            new_salience: Adjusted salience level
            occurrence_count: Number of occurrences
            tags: Updated tags list

        Returns:
            True if successful
        """
        try:
            cursor = self.conn.cursor()

            # Update memory
            cursor.execute("""
                UPDATE memories
                SET gist = ?,
                    salience = ?,
                    access_count = ?,
                    tags = ?,
                    last_accessed = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                new_gist,
                new_salience,
                occurrence_count,
                json.dumps(tags),
                memory_id
            ))

            # Update FTS index
            cursor.execute("""
                UPDATE memories_fts
                SET gist = ?,
                    tags = ?
                WHERE memory_id = ?
            """, (
                new_gist,
                json.dumps(tags),
                memory_id
            ))

            self.conn.commit()
            logger.debug(f"Updated memory {memory_id} with aggregation data")
            return True

        except sqlite3.Error as e:
            logger.error(f"Error updating memory aggregation: {e}")
            return False

    def get_memory_by_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single memory by ID

        Args:
            memory_id: Memory ID

        Returns:
            Memory dict or None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute("""
                SELECT
                    id, verbatim, gist, salience, event_type,
                    file_path, line_number, tags,
                    created_at, access_count
                FROM memories
                WHERE id = ?
            """, (memory_id,))

            result = cursor.fetchone()
            if result:
                return dict(result)
            return None

        except sqlite3.Error as e:
            logger.error(f"Error getting memory by ID {memory_id}: {e}")
            return None

    def close(self):
        """Close database connection"""
        self.conn.close()
        logger.debug("Database connection closed")
