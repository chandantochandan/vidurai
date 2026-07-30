"""
SQLite-backed persistent memory storage with Queue-Based Actor Pattern
Vidurai v2.5 - Thread-Safe Database Layer

Architecture:
- Single Background Thread owns all WRITE operations (prevents lock contention)
- WAL mode enables concurrent READS while writing
- SimpleFuture pattern for async-safe result passing

Ironclad Rules Followed:
I.   Schema Preservation - All CREATE TABLE statements preserved from v2.0
II.  Write Isolation - Only _writer_loop writes to DB, all methods use _enqueue
III. Reader Segregation - All reads use get_connection_for_reading() (parallel WAL reads)
IV.  Future Safety - SimpleFuture handles errors, never leaves threads hanging
"""
import sqlite3
import threading
import queue
import json
import shutil
import pickle
import logging
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple, Set
from enum import Enum

from vidurai.storage.migrations import run_migrations

logger = logging.getLogger("vidurai.storage")


class SalienceLevel(Enum):
    """Memory importance levels aligned with Three-Kosha architecture"""
    CRITICAL = 5
    HIGH = 4
    MEDIUM = 3
    LOW = 2
    NOISE = 1


class SimpleFuture:
    """
    Thread-safe future for passing results from writer thread to callers.

    Ironclad Rule IV: Future Safety - Never leave a thread hanging.
    """
    def __init__(self):
        self._result = None
        self._error: Optional[Exception] = None
        self._done = threading.Event()

    def set(self, result):
        """Set successful result"""
        self._result = result
        self._done.set()

    def error(self, err: Exception):
        """Set error result"""
        self._error = err
        self._done.set()

    def result(self, timeout: float = 10.0):
        """
        Wait for result with timeout.

        Args:
            timeout: Max seconds to wait (default: 10s)

        Returns:
            The result value

        Raises:
            TimeoutError: If writer doesn't respond in time
            Exception: The original error if write failed
        """
        if not self._done.wait(timeout):
            raise TimeoutError(f"DB Write Timeout after {timeout}s")
        if self._error:
            raise self._error
        return self._result


class MemoryDatabase:
    """
    SQLite-backed persistent memory storage with Queue-Based Actor Pattern.

    Thread Safety:
    - All writes go through a single background thread (zero lock contention)
    - All reads get their own connection (WAL allows parallel reads)

    Usage:
    Robust Queue-based SQLite database for persistent memory and file state.
    """

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the database (or resume from pickle)."""
        if db_path is None:
            db_path = Path.home() / ".vidurai" / "memory.db"
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_path)

        # Setup schema using the deterministic migration lifecycle
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            run_migrations(conn)
        finally:
            conn.close()

        # 1. The Queue: Buffers high-speed write events
        self.write_queue = queue.Queue()
        self.running = True

        # 2. The Actor Thread: Strictly single-threaded writes
        self.writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="vidurai-db-writer"
        )
        self.writer_thread.start()

        logger.info(f"Database initialized at {db_path} (Queue-Based Actor)")

    def __getstate__(self):
        """
        Handle pickle serialization by excluding unpickleable objects.
        
        Returns:
            dict: State dictionary without locks, queues, and threads
        """
        state = self.__dict__.copy()
        # Remove unpickleable entries
        if 'write_queue' in state:
            del state['write_queue']
        if 'writer_thread' in state:
            del state['writer_thread']
        if 'running' in state:
            del state['running']
        # Remove any connection objects that might exist
        if 'conn' in state:
            del state['conn']
        return state

    def __setstate__(self, state):
        """
        Handle pickle deserialization by re-initializing unpickleable objects.
        
        Args:
            state: State dictionary from pickle
        """
        self.__dict__.update(state)
        # Re-initialize locks, queues, and threads
        import threading
        import queue
        
        self.write_queue = queue.Queue()
        self.running = True
        self.writer_thread = threading.Thread(
            target=self._writer_loop,
            daemon=True,
            name="vidurai-db-writer"
        )
        self.writer_thread.start()
        
        # Note: Connection will be re-established when needed
        logger.debug("MemoryDatabase restored from pickle (thread restarted)")

    # =========================================================================
    # WRITER THREAD (Ironclad Rule II: Only function allowed to write)
    # =========================================================================

    def _writer_loop(self):
        """
        The ONLY function allowed to write to the DB.

        Ironclad Rule II: Write Isolation
        - All writes are serialized through this single thread
        - WAL mode allows readers to proceed in parallel
        """
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        # WAL Mode: Critical for allowing Readers while we write
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")

        logger.debug("Writer thread started (WAL mode enabled)")

        while self.running:
            try:
                # Block until we get a task (or timeout for graceful shutdown)
                try:
                    task = self.write_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if task is None:
                    # Shutdown signal
                    break

                query_data, params_data, future = task

                try:
                    # Execute write within transaction
                    with conn:
                        if isinstance(query_data, list):
                            # It's a transaction block: list of (query, params)
                            for q, p in query_data:
                                cursor = conn.execute(q, p)
                            result = True # Batch transaction success
                        elif isinstance(query_data, tuple) and query_data[0] == "MEMORY_TX":
                            _, mem_query, mem_params, receipt_id, processed_at = query_data
                            # 1. Insert memory
                            cursor = conn.execute(mem_query, mem_params)
                            memory_id = cursor.lastrowid
                            
                            # 2. Insert FTS
                            fts_params = params_data + (memory_id,)
                            conn.execute("""
                                INSERT INTO memories_fts (gist, verbatim, tags, memory_id)
                                VALUES (?, ?, ?, ?)
                            """, fts_params)
                            
                            # 3. Update Receipt
                            conn.execute("""
                                UPDATE event_receipts 
                                SET status = 'processed', memory_id = ?, processed_at = ?
                                WHERE receipt_id = ?
                            """, (memory_id, processed_at, receipt_id))
                            
                            result = memory_id
                        elif isinstance(query_data, tuple) and query_data[0] == "CLAIM_RECEIPTS":
                            _, limit = query_data
                            now = int(time.time() * 1000)
                            # Find recorded receipts
                            cursor = conn.execute("""
                                SELECT receipt_id, attempt_count FROM event_receipts
                                WHERE status = 'recorded'
                                ORDER BY received_at ASC
                                LIMIT ?
                            """, (limit,))
                            rows = cursor.fetchall()
                            claimed = []
                            for row in rows:
                                receipt_id = row['receipt_id']
                                attempt = row['attempt_count'] + 1
                                conn.execute("""
                                    UPDATE event_receipts
                                    SET status = 'processing', attempt_count = ?, last_attempt_at = ?
                                    WHERE receipt_id = ?
                                """, (attempt, now, receipt_id))
                                
                                # fetch the full row to return
                                cur = conn.execute("SELECT * FROM event_receipts WHERE receipt_id = ?", (receipt_id,))
                                claimed.append(dict(cur.fetchone()))
                            result = claimed
                        else:
                            cursor = conn.execute(query_data, params_data)
                            # Determine result type based on query
                            if 'INSERT' in query_data.upper():
                                result = cursor.lastrowid
                            elif 'DELETE' in query_data.upper() or 'UPDATE' in query_data.upper():
                                result = cursor.rowcount
                            else:
                                result = True

                    # Pass result back to the caller
                    if future:
                        future.set(result)

                except Exception as e:
                    # Ironclad Rule IV: Never leave a thread hanging
                    logger.error(f"DB Actor Write Error: {e}")
                    if future:
                        future.error(e)
                finally:
                    self.write_queue.task_done()

            except Exception as e:
                # Broad exception handler for loop stability
                logger.error(f"Writer Loop Error (non-fatal): {e}")
                time.sleep(0.1)  # Anti-spin on repeated errors

        conn.close()
        logger.debug("Writer thread stopped")

    def _enqueue(self, query: str, params: tuple) -> SimpleFuture:
        """
        Helper to push write operation to the actor queue.

        Ironclad Rule II: All writes MUST use this method.

        Args:
            query: SQL query string
            params: Query parameters tuple

        Returns:
            SimpleFuture that will contain the result
        """
        future = SimpleFuture()
        self.write_queue.put((query, params, future))
        return future

    def _enqueue_transaction(self, queries: List[Tuple[str, tuple]]) -> SimpleFuture:
        """
        Helper to push a batch of queries to run in a single transaction.

        Args:
            queries: List of (query, params) tuples.

        Returns:
            SimpleFuture that will resolve to True if successful.
        """
        future = SimpleFuture()
        self.write_queue.put((queries, None, future))
        return future

    # =========================================================================
    # READER CONNECTION (Ironclad Rule III: Readers don't wait in queue)
    # =========================================================================

    def get_connection_for_reading(self) -> sqlite3.Connection:
        """
        Get a fresh connection for read operations.

        Ironclad Rule III: Reader Segregation
        - Readers get their own thread-local connection
        - WAL mode allows concurrent reads while writer is active
        - Caller MUST close this connection when done

        Returns:
            sqlite3.Connection configured for reading
        """
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    # =========================================================================
    # SCHEMA INITIALIZATION (Ironclad Rule I: Preserve all tables)
    # =========================================================================



    # =========================================================================
    # PROJECT MANAGEMENT
    # =========================================================================

    def get_or_create_project(self, project_path: str, identity: Optional[Dict] = None) -> int:
        """
        Get project ID, creating if needed.

        Args:
            project_path: Workspace path alias
            identity: Optional resolved identity dict (from vidurai.identity). 
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            
            # If identity provided, lookup by UUID first
            if identity and not identity.get('ambiguous'):
                uuid_str = identity.get('project_uuid')
                if uuid_str:
                    cursor.execute(
                        "SELECT id FROM projects WHERE project_uuid = ?",
                        (uuid_str,)
                    )
                    result = cursor.fetchone()
                    if result:
                        project_id = result['id']
                        # Update last_active on project and ensure alias exists
                        future = self._enqueue("""
                            UPDATE projects SET last_active = CURRENT_TIMESTAMP WHERE id = ?;
                        """, (project_id,))
                        future.result()
                        future = self._enqueue("""
                            INSERT INTO project_aliases (project_id, path, last_active)
                            VALUES (?, ?, CURRENT_TIMESTAMP)
                            ON CONFLICT(path) DO UPDATE SET project_id=excluded.project_id, last_active=CURRENT_TIMESTAMP;
                        """, (project_id, project_path))
                        future.result()
                        return project_id
                        
            # Fallback to path lookup via aliases
            cursor.execute(
                "SELECT project_id FROM project_aliases WHERE path = ?",
                (project_path,)
            )
            result = cursor.fetchone()
            if not result:
                # Legacy fallback just in case alias not migrated
                cursor.execute(
                    "SELECT id FROM projects WHERE path = ?",
                    (project_path,)
                )
                result = cursor.fetchone()
                if result:
                    result = {'project_id': result['id']}

            if result:
                project_id = result['project_id']
                # If we found it by path but we have a UUID, backfill it
                if identity and not identity.get('ambiguous'):
                    uuid_str = identity.get('project_uuid')
                    fp_str = identity.get('remote_fingerprint')
                    if uuid_str:
                        future = self._enqueue(
                            "UPDATE projects SET last_active = CURRENT_TIMESTAMP, project_uuid = ?, remote_fingerprint = ? WHERE id = ?",
                            (uuid_str, fp_str, project_id)
                        )
                        future.result()
                        return project_id

                future = self._enqueue(
                    "UPDATE projects SET last_active = CURRENT_TIMESTAMP WHERE id = ?",
                    (project_id,)
                )
                future.result()
                return project_id
        finally:
            conn.close()

        # Create new project via writer queue
        project_name = Path(project_path).name
        if identity and not identity.get('ambiguous'):
            uuid_str = identity.get('project_uuid')
            fp_str = identity.get('remote_fingerprint')
            if uuid_str:
                future = self._enqueue(
                    "INSERT INTO projects (path, name, project_uuid, remote_fingerprint) VALUES (?, ?, ?, ?)",
                    (project_path, project_name, uuid_str, fp_str)
                )
                project_id = future.result()
                future = self._enqueue(
                    "INSERT INTO project_aliases (project_id, path, last_active) VALUES (?, ?, CURRENT_TIMESTAMP)",
                    (project_id, project_path)
                )
                future.result()
                logger.info(f"Created new project: {project_name} (ID: {project_id}, UUID: {uuid_str})")
                return project_id

        future = self._enqueue(
            "INSERT INTO projects (path, name) VALUES (?, ?)",
            (project_path, project_name)
        )
        project_id = future.result()
        future = self._enqueue(
            "INSERT INTO project_aliases (project_id, path, last_active) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (project_id, project_path)
        )
        future.result()
        logger.info(f"Created new project: {project_name} (ID: {project_id})")
        return project_id

    # =========================================================================
    # MEMORY STORAGE (All writes via _enqueue - Rule II)
    # =========================================================================

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
        retention_days: Optional[int] = None,
        created_at: Optional[datetime] = None,
        identity: Optional[Dict] = None
    ) -> int:
        """
        Store new memory in database.

        Ironclad Rule II: Uses _enqueue for all writes.

        Args:
            project_path: Path to the project
            verbatim: Full verbatim content
            gist: Compressed gist/summary
            salience: Salience level (CRITICAL, HIGH, MEDIUM, LOW, NOISE)
            event_type: Type of event (edit, save, error, etc.)
            file_path: Optional file path
            line_number: Optional line number
            tags: Optional list of tags
            retention_days: Optional retention period in days
            created_at: Optional historical timestamp (Sprint 1.5)
                       If None, SQLite default (CURRENT_TIMESTAMP) is used.
                       This enables ingestion of historical conversations
                       with their original timestamps preserved.

        Returns:
            The ID of the newly created memory
        """
        try:
            project_id = self.get_or_create_project(project_path, identity=identity)

            # Calculate expiration
            expires_at = None
            if retention_days:
                base_time = created_at if created_at else datetime.now()
                expires_at = (base_time + timedelta(days=retention_days)).isoformat()

            # Sprint 1.5: Use provided created_at or let SQLite use default
            created_at_str = created_at.isoformat() if created_at else None

            # Insert memory via writer queue
            # Note: created_at column has DEFAULT CURRENT_TIMESTAMP, so NULL works
            if created_at_str:
                # Explicit timestamp provided (historical ingestion)
                future = self._enqueue("""
                    INSERT INTO memories (
                        project_id, verbatim, gist, salience, event_type,
                        file_path, line_number, tags, expires_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    project_id,
                    verbatim,
                    gist,
                    salience.name,
                    event_type,
                    file_path,
                    line_number,
                    json.dumps(tags) if tags else None,
                    expires_at,
                    created_at_str
                ))
            else:
                # No timestamp - let SQLite use CURRENT_TIMESTAMP default
                future = self._enqueue("""
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

            memory_id = future.result()

            # Add to full-text search via writer queue
            future = self._enqueue("""
                INSERT INTO memories_fts (memory_id, gist, verbatim, tags)
                VALUES (?, ?, ?, ?)
            """, (
                memory_id,
                gist,
                verbatim,
                json.dumps(tags) if tags else None
            ))
            future.result()

            logger.debug(f"Stored memory {memory_id} (salience: {salience.name})")
            return memory_id

        except Exception as e:
            logger.error(f"Database error storing memory: {e}")
            raise

    def process_memory_from_receipt(
        self,
        receipt_id: str,
        project_path: str,
        verbatim: str,
        gist: str,
        salience: SalienceLevel,
        event_type: str,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None,
        tags: Optional[List[str]] = None,
        retention_days: Optional[int] = None,
        created_at: Optional[datetime] = None,
        identity: Optional[Dict] = None
    ) -> int:
        """
        WP-02 Atomic Transaction: Process a memory and link it to its receipt.
        """
        try:
            project_id = self.get_or_create_project(project_path, identity=identity)

            expires_at = None
            if retention_days:
                base_time = created_at if created_at else datetime.now()
                expires_at = (base_time + timedelta(days=retention_days)).isoformat()

            created_at_str = created_at.isoformat() if created_at else None

            # First, we need the memory_id, so we can't easily batch this with _enqueue_transaction
            # We use our specialized MEMORY_TX tuple

            mem_query = """
                INSERT INTO memories (
                    project_id, verbatim, gist, salience, event_type,
                    file_path, line_number, tags, expires_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            # The created_at field handles historical vs current, handled identically since created_at_str falls back to None in the schema which defaults to CURRENT_TIMESTAMP, but wait, SQLite doesn't default NULL to CURRENT_TIMESTAMP unless we omit the column. Let's build the query dynamically.
            if created_at_str:
                mem_query = """
                    INSERT INTO memories (
                        project_id, verbatim, gist, salience, event_type,
                        file_path, line_number, tags, expires_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                mem_params = (project_id, verbatim, gist, salience.name, event_type, file_path, line_number, json.dumps(tags) if tags else None, expires_at, created_at_str)
            else:
                mem_query = """
                    INSERT INTO memories (
                        project_id, verbatim, gist, salience, event_type,
                        file_path, line_number, tags, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """
                mem_params = (project_id, verbatim, gist, salience.name, event_type, file_path, line_number, json.dumps(tags) if tags else None, expires_at)
            
            fts_params = (gist, verbatim, json.dumps(tags) if tags else None)
            processed_at = int(time.time() * 1000)
            
            future = SimpleFuture()
            self.write_queue.put((("MEMORY_TX", mem_query, mem_params, receipt_id, processed_at), fts_params, future))
            memory_id = future.result()
            
            logger.debug(f"WP-02 Atomic Transaction: processed receipt {receipt_id} to memory {memory_id}")
            return memory_id
            
        except Exception as e:
            logger.error(f"Database error in process_memory_from_receipt: {e}")
            raise

    def handle_processing_failure(self, receipt_id: str, error_msg: str) -> None:
        """Handle a processing failure by transitioning back to recorded or failed."""
        conn = self.get_connection_for_reading()
        try:
            row = conn.execute("SELECT attempt_count FROM event_receipts WHERE receipt_id = ?", (receipt_id,)).fetchone()
            if not row:
                return
            
            attempt = row['attempt_count']
            new_status = 'failed' if attempt >= 3 else 'recorded'
            
            # Map exception string to bounded error code
            bounded_code = 'internal_processing_failure'
            if 'fts' in error_msg.lower():
                bounded_code = 'fts_transaction_failed'
            elif 'memory' in error_msg.lower():
                bounded_code = 'memory_processing_failed'
                
            if attempt >= 3:
                bounded_code = 'processing_attempts_exhausted'
            
            future = self._enqueue("""
                UPDATE event_receipts
                SET status = ?, error_code = ?
                WHERE receipt_id = ?
            """, (new_status, bounded_code, receipt_id))
            future.result()
        finally:
            conn.close()

    def store_audience_gists(
        self,
        memory_id: int,
        gists: Dict[str, str]
    ) -> None:
        """
        Store multiple audience-specific gists for a memory.

        Ironclad Rule II: Uses _enqueue for all writes.
        """
        try:
            for audience, gist in gists.items():
                future = self._enqueue("""
                    INSERT OR REPLACE INTO audience_gists (memory_id, audience, gist)
                    VALUES (?, ?, ?)
                """, (memory_id, audience, gist))
                future.result()

            logger.debug(f"Stored {len(gists)} audience gists for memory {memory_id}")

        except Exception as e:
            logger.error(f"Database error storing audience gists: {e}")
            raise

    def update_memory_aggregation(
        self,
        memory_id: int,
        new_gist: str,
        new_salience: str,
        occurrence_count: int,
        tags: List[str]
    ) -> bool:
        """
        Update an existing memory with aggregation metadata.

        Ironclad Rule II: Uses _enqueue for all writes.
        """
        try:
            # Update memory
            future = self._enqueue("""
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
            future.result()

            # Update FTS index
            future = self._enqueue("""
                UPDATE memories_fts
                SET gist = ?,
                    tags = ?
                WHERE memory_id = ?
            """, (
                new_gist,
                json.dumps(tags),
                memory_id
            ))
            future.result()

            logger.debug(f"Updated memory {memory_id} with aggregation data")
            return True

        except Exception as e:
            logger.error(f"Error updating memory aggregation: {e}")
            return False

    def cleanup_expired(self) -> int:
        """
        Remove expired memories.

        Ironclad Rule II: Uses _enqueue for writes.
        """
        try:
            future = self._enqueue("""
                DELETE FROM memories
                WHERE expires_at IS NOT NULL
                    AND expires_at < datetime('now')
            """, ())
            deleted = future.result()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} expired memories")

            return deleted

        except Exception as e:
            logger.error(f"Error cleaning up expired memories: {e}")
            return 0

    # =========================================================================
    # PINNING API (Ironclad Rule II: All writes via _enqueue)
    # =========================================================================

    def set_memory_pinned(
        self,
        memory_id: int,
        pinned: bool,
        tags: Optional[str] = None
    ) -> int:
        """
        Set pinned status for a memory.

        Ironclad Rule II: Uses _enqueue for writes.

        Args:
            memory_id: Memory ID to update
            pinned: True to pin, False to unpin
            tags: Optional updated tags JSON string

        Returns:
            Number of rows affected
        """
        try:
            if tags is not None:
                future = self._enqueue(
                    "UPDATE memories SET pinned = ?, tags = ? WHERE id = ?",
                    (1 if pinned else 0, tags, memory_id)
                )
            else:
                future = self._enqueue(
                    "UPDATE memories SET pinned = ? WHERE id = ?",
                    (1 if pinned else 0, memory_id)
                )
            return future.result()
        except Exception as e:
            logger.error(f"Error setting pinned status: {e}")
            return 0

    def create_pinned_placeholder(
        self,
        project_id: int,
        file_path: str,
        verbatim: str,
        gist: str,
        salience: str = 'CRITICAL',
        event_type: str = 'user_pinned'
    ) -> int:
        """
        Create a placeholder memory that is already pinned.

        Ironclad Rule II: Uses _enqueue for writes.

        Returns:
            New memory ID
        """
        try:
            future = self._enqueue("""
                INSERT INTO memories (
                    project_id, verbatim, gist, salience, event_type,
                    file_path, created_at, pinned
                ) VALUES (?, ?, ?, ?, ?, ?, datetime('now'), 1)
            """, (
                project_id,
                verbatim,
                gist,
                salience,
                event_type,
                file_path
            ))
            return future.result()
        except Exception as e:
            logger.error(f"Error creating pinned placeholder: {e}")
            raise

    # =========================================================================
    # EVENT RECEIPTS (WP-02)
    # =========================================================================

    def insert_event_receipt(
        self,
        receipt_id: str,
        event_type: str,
        payload_hash: str,
        payload_json: str,
        status: str,
        received_at: int,
        event_id: Optional[str] = None,
        identity: Optional[Dict] = None
    ) -> bool:
        try:
            # Identity fields
            project_uuid = identity.get("project_uuid") if identity else None
            branch = identity.get("branch") if identity else None
            commit_hash = identity.get("commit") if identity else None
            detached_head = identity.get("detached") if identity else None

            future = self._enqueue("""
                INSERT INTO event_receipts (
                    receipt_id, event_id, event_type, payload_hash, 
                    payload_json, status, received_at, attempt_count,
                    project_uuid, branch, commit_hash, detached_head
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?)
            """, (receipt_id, event_id, event_type, payload_hash, payload_json, status, received_at, project_uuid, branch, commit_hash, detached_head))
            future.result()
            return True
        except Exception as e:
            logger.error(f"Error inserting event receipt: {e}")
            return False

    def get_receipt_by_event_id(self, event_id: str) -> Optional[dict]:
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_receipts WHERE event_id = ?", (event_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
            
    def get_receipt_by_receipt_id(self, receipt_id: str) -> Optional[dict]:
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM event_receipts WHERE receipt_id = ?", (receipt_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
            
    def update_receipt_status(self, receipt_id: str, status: str, error_code: Optional[str] = None) -> bool:
        try:
            future = self._enqueue("""
                UPDATE event_receipts 
                SET status = ?, error_code = ?
                WHERE receipt_id = ?
            """, (status, error_code, receipt_id))
            future.result()
            return True
        except Exception as e:
            logger.error(f"Error updating event receipt status: {e}")
            return False
            
    def run_startup_recovery(self) -> None:
        """
        WP-02: Startup recovery transitions for interrupted processing.
        """
        future = self._enqueue_transaction([
            # Transition attempt_count < 3 back to recorded
            ("UPDATE event_receipts SET status = 'recorded' WHERE status = 'processing' AND attempt_count < 3", ()),
            # Transition attempt_count >= 3 to failed
            ("UPDATE event_receipts SET status = 'failed', error_code = 'startup_recovery_exhausted' WHERE status = 'processing' AND attempt_count >= 3", ())
        ])
        future.result()

    def claim_recoverable_receipts(self, limit: int = 50) -> List[dict]:
        """
        Atomically transition recoverable receipts to 'processing' and return them.
        """
        future = SimpleFuture()
        self.write_queue.put((("CLAIM_RECEIPTS", limit), None, future))
        return future.result()

    def get_pinned_memories(self, project_id: int) -> List[Dict[str, Any]]:
        """
        Get all pinned memories for a project.

        Ironclad Rule III: Uses get_connection_for_reading.

        Args:
            project_id: Project ID

        Returns:
            List of pinned memory dicts
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, verbatim, gist, salience, event_type,
                       file_path, line_number, tags, created_at, last_accessed
                FROM memories
                WHERE project_id = ? AND pinned = 1
                ORDER BY created_at DESC
            """, (project_id,))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting pinned memories: {e}")
            return []
        finally:
            conn.close()

    def get_pin_count(self, project_id: int) -> int:
        """
        Get count of pinned memories for a project.

        Ironclad Rule III: Uses get_connection_for_reading.

        Args:
            project_id: Project ID

        Returns:
            Count of pinned memories
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM memories WHERE project_id = ? AND pinned = 1",
                (project_id,)
            )
            return cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Error getting pin count: {e}")
            return 0
        finally:
            conn.close()

    def get_pinned_memory_by_path(
        self,
        project_id: int,
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a pinned memory by file path.

        Ironclad Rule III: Uses get_connection_for_reading.

        Returns:
            Memory dict or None
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, verbatim, gist, salience, event_type,
                       file_path, line_number, tags, created_at, pinned
                FROM memories
                WHERE project_id = ? AND file_path = ? AND pinned = 1
                ORDER BY created_at DESC
                LIMIT 1
            """, (project_id, file_path))

            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting pinned memory by path: {e}")
            return None
        finally:
            conn.close()

    def get_memory_by_path(
        self,
        project_id: int,
        file_path: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get most recent memory by file path (pinned or not).

        Ironclad Rule III: Uses get_connection_for_reading.

        Returns:
            Memory dict or None
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, verbatim, gist, salience, event_type,
                       file_path, line_number, tags, created_at, pinned
                FROM memories
                WHERE project_id = ? AND file_path = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (project_id, file_path))

            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting memory by path: {e}")
            return None
        finally:
            conn.close()

    def get_pin_statistics(self) -> Dict[str, Any]:
        """
        Get pinning statistics across all projects.

        Ironclad Rule III: Uses get_connection_for_reading.

        Returns:
            Statistics dict
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()

            # Total pins
            cursor.execute("SELECT COUNT(*) FROM memories WHERE pinned = 1")
            total_pins = cursor.fetchone()[0]

            # Pins by salience
            cursor.execute("""
                SELECT salience, COUNT(*) as count
                FROM memories
                WHERE pinned = 1
                GROUP BY salience
            """)
            by_salience = {row[0]: row[1] for row in cursor.fetchall()}

            # Pins by project
            cursor.execute("""
                SELECT p.path, COUNT(*) as count
                FROM memories m
                JOIN projects p ON m.project_id = p.id
                WHERE m.pinned = 1
                GROUP BY p.path
            """)
            by_project = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                'total_pins': total_pins,
                'by_salience': by_salience,
                'by_project': by_project,
            }
        except sqlite3.Error as e:
            logger.error(f"Error getting pin statistics: {e}")
            return {'total_pins': 0, 'by_salience': {}, 'by_project': {}}
        finally:
            conn.close()

    def get_suggested_pins(
        self,
        project_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get unpinned memories that are good candidates for pinning.

        Ironclad Rule III: Uses get_connection_for_reading.

        Returns:
            List of suggested memory dicts
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, verbatim, gist, salience, event_type,
                       access_count, last_accessed, tags
                FROM memories
                WHERE project_id = ?
                  AND pinned = 0
                  AND salience IN ('CRITICAL', 'HIGH')
                ORDER BY access_count DESC, salience DESC
                LIMIT ?
            """, (project_id, limit))

            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Error getting suggested pins: {e}")
            return []
        finally:
            conn.close()

    def check_table_column(self, table: str, column: str) -> bool:
        """
        Check if a column exists in a table.

        Ironclad Rule III: Uses get_connection_for_reading.

        Returns:
            True if column exists
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]
            return column in columns
        except sqlite3.Error as e:
            logger.error(f"Error checking table column: {e}")
            return False
        finally:
            conn.close()

    def add_column_if_missing(
        self,
        table: str,
        column: str,
        column_def: str
    ) -> bool:
        """
        Add a column to a table if it doesn't exist.

        Ironclad Rule II: Uses _enqueue for writes.

        Args:
            table: Table name
            column: Column name
            column_def: Column definition (e.g., "INTEGER DEFAULT 0")

        Returns:
            True if column was added or already exists
        """
        if self.check_table_column(table, column):
            return True

        try:
            future = self._enqueue(
                f"ALTER TABLE {table} ADD COLUMN {column} {column_def}",
                ()
            )
            future.result()
            logger.info(f"Added '{column}' column to {table} table")
            return True
        except Exception as e:
            logger.error(f"Error adding column {column} to {table}: {e}")
            return False

    def create_index_if_missing(self, index_name: str, index_sql: str) -> bool:
        """
        Create an index if it doesn't exist.

        Ironclad Rule II: Uses _enqueue for writes.

        Args:
            index_name: Name of the index
            index_sql: Full CREATE INDEX statement

        Returns:
            True if successful
        """
        try:
            future = self._enqueue(index_sql, ())
            future.result()
            return True
        except Exception as e:
            # Index might already exist
            if "already exists" not in str(e).lower():
                logger.error(f"Error creating index {index_name}: {e}")
            return False

    # =========================================================================
    # MEMORY RETRIEVAL (All reads via get_connection_for_reading - Rule III)
    # =========================================================================

    def get_audience_gists(
        self,
        memory_id: int,
        audiences: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        Retrieve audience-specific gists for a memory.

        Ironclad Rule III: Uses get_connection_for_reading for parallel reads.
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()

            if audiences:
                placeholders = ','.join('?' * len(audiences))
                sql = f"""
                    SELECT audience, gist
                    FROM audience_gists
                    WHERE memory_id = ?
                      AND audience IN ({placeholders})
                """
                params = [memory_id] + audiences
            else:
                sql = """
                    SELECT audience, gist
                    FROM audience_gists
                    WHERE memory_id = ?
                """
                params = [memory_id]

            results = cursor.execute(sql, params).fetchall()
            gists = {row['audience']: row['gist'] for row in results}

            logger.debug(f"Retrieved {len(gists)} audience gists for memory {memory_id}")
            return gists

        except sqlite3.Error as e:
            logger.error(f"Database error retrieving audience gists: {e}")
            return {}
        finally:
            conn.close()

    def recall_memories(
        self,
        project_path: str,
        query: Optional[str] = None,
        min_salience: SalienceLevel = SalienceLevel.MEDIUM,
        limit: int = 10,
        hours_back: Optional[int] = None,
        keywords: Optional[List[str]] = None  # Smart Query: Pre-sanitized keywords
    ) -> List[Dict[str, Any]]:
        """
        Recall relevant memories for a project.

        CTO Mandate: The Intersection Rule
        - If keywords are provided, uses intersection search (AND conditions)
        - Finds memories containing ALL keywords, not exact phrase match
        - Example: ["architecture", "civi"] finds memories with BOTH terms

        Ironclad Rule III: Uses get_connection_for_reading for parallel reads.
        Note: Access count update uses _enqueue (write).

        Args:
            project_path: Path to project
            query: Original query string (used if keywords not provided)
            min_salience: Minimum salience level
            limit: Max results to return
            hours_back: Optional time filter
            keywords: Pre-sanitized keywords for intersection search (new)
        """
        conn = self.get_connection_for_reading()
        try:
            project_id = self.get_or_create_project(project_path)
            cursor = conn.cursor()

            # Filter by salience
            salience_values = [s.name for s in SalienceLevel if s.value >= min_salience.value]

            # CTO Mandate: Intersection Search
            # If keywords provided, use AND-based LIKE search
            if keywords and len(keywords) > 0:
                # Build dynamic AND conditions for each keyword
                # Each keyword must exist in EITHER verbatim OR gist
                keyword_conditions = []
                keyword_params = []
                for kw in keywords:
                    wildcard = f"%{kw}%"
                    keyword_conditions.append("(m.verbatim LIKE ? OR m.gist LIKE ?)")
                    keyword_params.extend([wildcard, wildcard])

                sql = f"""
                    SELECT m.id, m.verbatim, m.gist, m.salience, m.event_type,
                           m.file_path, m.line_number, m.tags,
                           m.created_at, m.access_count, m.pinned
                    FROM memories m
                    WHERE m.project_id = ?
                        AND (m.expires_at IS NULL OR m.expires_at > datetime('now'))
                        AND m.salience IN ({','.join('?' * len(salience_values))})
                        AND {' AND '.join(keyword_conditions)}
                    ORDER BY m.salience DESC, m.created_at DESC
                    LIMIT ?
                """
                params = [project_id] + salience_values + keyword_params + [limit]

                logger.debug(f"Intersection search with keywords: {keywords}")

            elif query and query.strip():
                # Fallback: Try FTS5 search for simple queries
                # Use bm25() for relevance scoring
                sql = f"""
                    SELECT m.id, m.verbatim, m.gist, m.salience, m.event_type,
                           m.file_path, m.line_number, m.tags,
                           m.created_at, m.access_count, m.pinned,
                           bm25(memories_fts) as rank
                    FROM memories m
                    JOIN memories_fts fts ON fts.memory_id = m.id
                    WHERE m.project_id = ?
                        AND (m.expires_at IS NULL OR m.expires_at > datetime('now'))
                        AND m.salience IN ({','.join('?' * len(salience_values))})
                        AND memories_fts MATCH ?
                    ORDER BY rank, m.created_at DESC
                    LIMIT ?
                """
                params = [project_id] + salience_values + [query, limit]

            else:
                # No query - return recent memories
                sql = f"""
                    SELECT
                        m.id, m.verbatim, m.gist, m.salience, m.event_type,
                        m.file_path, m.line_number, m.tags,
                        m.created_at, m.access_count, m.pinned
                    FROM memories m
                    WHERE m.project_id = ?
                        AND (m.expires_at IS NULL OR m.expires_at > datetime('now'))
                        AND m.salience IN ({','.join('?' * len(salience_values))})
                """
                params: List[Any] = [project_id] + salience_values

                # Filter by time
                if hours_back:
                    sql += " AND m.created_at >= datetime('now', ?)"
                    params.append(f'-{hours_back} hours')

                sql += " ORDER BY m.salience DESC, m.created_at DESC"
                sql += " LIMIT ?"
                params.append(limit)

            cursor.execute(sql, params)
            results = cursor.fetchall()

            # Update access counts via writer queue (non-blocking background)
            memory_ids = [r['id'] for r in results]
            if memory_ids:
                placeholders = ','.join('?' * len(memory_ids))
                self._enqueue(f"""
                    UPDATE memories
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                """, tuple(memory_ids))
                # Don't wait for result - fire and forget

            # Convert to dicts
            memories = [dict(row) for row in results]
            logger.debug(f"Recalled {len(memories)} memories for query: {query}, keywords: {keywords}")
            return memories

        except sqlite3.Error as e:
            logger.error(f"Database error recalling memories: {e}")
            return []
        finally:
            conn.close()

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

    def get_statistics(self, project_path: str) -> Dict[str, Any]:
        """
        Get memory statistics for a project.

        Ironclad Rule III: Uses get_connection_for_reading.
        """
        conn = self.get_connection_for_reading()
        try:
            project_id = self.get_or_create_project(project_path)
            cursor = conn.cursor()

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
        finally:
            conn.close()

    def get_memory_by_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single memory by ID.

        Ironclad Rule III: Uses get_connection_for_reading.
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    id, project_id, verbatim, gist, salience, event_type,
                    file_path, line_number, tags, pinned, pin_reason,
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
        finally:
            conn.close()

    def get_recent_similar_memories(
        self,
        project_path: str,
        file_path: Optional[str] = None,
        event_type: Optional[str] = None,
        hours_back: int = 168  # 7 days default
    ) -> List[Dict[str, Any]]:
        """
        Get recent memories that might be duplicates.

        Ironclad Rule III: Uses get_connection_for_reading.
        """
        conn = self.get_connection_for_reading()
        try:
            project_id = self.get_or_create_project(project_path)
            cursor = conn.cursor()

            sql = """
                SELECT
                    id, verbatim, gist, salience, event_type,
                    file_path, line_number, tags,
                    created_at, access_count
                FROM memories
                WHERE project_id = ?
                    AND created_at >= datetime('now', ?)
            """
            params: List[Any] = [project_id, f'-{hours_back} hours']

            if file_path:
                sql += " AND file_path = ?"
                params.append(file_path)

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
        finally:
            conn.close()

    # =========================================================================
    # ACTIVE STATE MANAGEMENT (Zombie Killer)
    # =========================================================================

    def upsert_file_state(
        self,
        file_path: str,
        project_path: str,
        has_errors: bool,
        error_count: int = 0,
        warning_count: int = 0,
        error_summary: Optional[str] = None
    ) -> bool:
        """
        Upsert file state into active_state table.

        Ironclad Rule II: Uses _enqueue for writes.
        """
        try:
            project_id = self.get_or_create_project(project_path)

            future = self._enqueue("""
                INSERT INTO active_state (
                    file_path, project_id, has_errors, error_count,
                    warning_count, last_updated, error_summary
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    has_errors = excluded.has_errors,
                    error_count = excluded.error_count,
                    warning_count = excluded.warning_count,
                    last_updated = CURRENT_TIMESTAMP,
                    error_summary = excluded.error_summary
            """, (
                file_path,
                project_id,
                has_errors,
                error_count,
                warning_count,
                error_summary
            ))
            future.result()

            logger.debug(f"Upserted state for {file_path}: errors={error_count}, warnings={warning_count}")
            return True

        except Exception as e:
            logger.error(f"Error upserting file state: {e}")
            return False

    def clear_file_state(self, file_path: str) -> bool:
        """
        Remove file from active_state table (file is now clean).

        Ironclad Rule II: Uses _enqueue for writes.
        """
        try:
            future = self._enqueue(
                "DELETE FROM active_state WHERE file_path = ?",
                (file_path,)
            )
            deleted = future.result()

            if deleted > 0:
                logger.debug(f"Cleared state for {file_path} (file is now clean)")

            return deleted > 0

        except Exception as e:
            logger.error(f"Error clearing file state: {e}")
            return False

    def touch_file_state(self, file_path: str) -> bool:
        """
        Update last_updated timestamp for a file.

        Ironclad Rule II: Uses _enqueue for writes.
        """
        try:
            future = self._enqueue("""
                UPDATE active_state
                SET last_updated = CURRENT_TIMESTAMP
                WHERE file_path = ?
            """, (file_path,))
            updated = future.result()

            return updated > 0

        except Exception as e:
            logger.error(f"Error touching file state: {e}")
            return False

    def get_file_state(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Get current state for a file.

        Ironclad Rule III: Uses get_connection_for_reading.
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_path, has_errors, error_count, warning_count,
                       last_updated, error_summary
                FROM active_state
                WHERE file_path = ?
            """, (file_path,))

            result = cursor.fetchone()
            return dict(result) if result else None

        except sqlite3.Error as e:
            logger.error(f"Error getting file state: {e}")
            return None
        finally:
            conn.close()

    def get_files_with_errors(
        self,
        project_path: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all files that currently have errors.

        Ironclad Rule III: Uses get_connection_for_reading.
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()

            if project_path:
                project_id = self.get_or_create_project(project_path)
                cursor.execute("""
                    SELECT file_path, has_errors, error_count, warning_count,
                           last_updated, error_summary
                    FROM active_state
                    WHERE project_id = ? AND has_errors = TRUE
                    ORDER BY error_count DESC, last_updated DESC
                """, (project_id,))
            else:
                cursor.execute("""
                    SELECT file_path, has_errors, error_count, warning_count,
                           last_updated, error_summary
                    FROM active_state
                    WHERE has_errors = TRUE
                    ORDER BY error_count DESC, last_updated DESC
                """)

            return [dict(row) for row in cursor.fetchall()]

        except sqlite3.Error as e:
            logger.error(f"Error getting files with errors: {e}")
            return []
        finally:
            conn.close()

    def get_active_state_summary(
        self,
        project_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of active state for a project.

        Ironclad Rule III: Uses get_connection_for_reading.
        """
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()

            if project_path:
                project_id = self.get_or_create_project(project_path)
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_files,
                        SUM(CASE WHEN has_errors THEN 1 ELSE 0 END) as files_with_errors,
                        SUM(error_count) as total_errors,
                        SUM(warning_count) as total_warnings
                    FROM active_state
                    WHERE project_id = ?
                """, (project_id,))
            else:
                cursor.execute("""
                    SELECT
                        COUNT(*) as total_files,
                        SUM(CASE WHEN has_errors THEN 1 ELSE 0 END) as files_with_errors,
                        SUM(error_count) as total_errors,
                        SUM(warning_count) as total_warnings
                    FROM active_state
                """)

            result = cursor.fetchone()
            return {
                'total_files': result['total_files'] or 0,
                'files_with_errors': result['files_with_errors'] or 0,
                'total_errors': result['total_errors'] or 0,
                'total_warnings': result['total_warnings'] or 0,
            }

        except sqlite3.Error as e:
            logger.error(f"Error getting active state summary: {e}")
            return {
                'total_files': 0,
                'files_with_errors': 0,
                'total_errors': 0,
                'total_warnings': 0,
            }
        finally:
            conn.close()

    # =========================================================================
    # PICKLE MIGRATION (Legacy support)
    # =========================================================================

    def _migrate_from_pickle(self):
        """One-time migration from v1.x pickle files"""
        pickle_dir = Path.home() / ".vidurai" / "sessions"

        if not pickle_dir.exists():
            logger.debug("No pickle sessions found, skipping migration")
            return

        # Check if already migrated
        conn = self.get_connection_for_reading()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM memories")
            if cursor.fetchone()['count'] > 0:
                logger.debug("Database already has memories, skipping migration")
                return
        finally:
            conn.close()

        logger.info("🔄 Migrating from v1.x pickle format...")
        migrated_count = 0

        for pickle_file in pickle_dir.glob("*.pkl"):
            try:
                with open(pickle_file, 'rb') as f:
                    old_data = pickle.load(f)

                project_path = old_data.get('workspace_path', str(pickle_file.stem))

                memories_to_migrate = []
                if 'memory_data' in old_data:
                    memories_to_migrate.extend(old_data.get('memory_data', []))
                if 'annamaya' in old_data:
                    memories_to_migrate.extend(old_data.get('annamaya', []))
                if 'manomaya' in old_data:
                    memories_to_migrate.extend(old_data.get('manomaya', []))
                if 'vijnanamaya' in old_data:
                    memories_to_migrate.extend(old_data.get('vijnanamaya', []))

                for mem in memories_to_migrate:
                    try:
                        content = mem.get('content', '') or mem.get('verbatim', '')
                        gist = mem.get('gist', content[:100])
                        salience_str = mem.get('salience', 'MEDIUM')

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

    # =========================================================================
    # SHUTDOWN
    # =========================================================================

    def close(self):
        """
        Close database and stop writer thread.

        Sends shutdown signal and waits for queue to drain.
        """
        logger.debug("Shutting down database...")

        # Signal shutdown
        self.running = False
        self.write_queue.put(None)  # Poison pill

        # Wait for writer thread to finish (max 5 seconds)
        self.writer_thread.join(timeout=5.0)

        logger.debug("Database connection closed")

    def __del__(self):
        """Cleanup on garbage collection"""
        if hasattr(self, 'running') and self.running:
            self.close()
