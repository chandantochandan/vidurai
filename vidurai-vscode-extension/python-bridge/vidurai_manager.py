"""
Vidurai Manager
Manages VismritiMemory instance with session persistence
v2.0: Now with database integration
"""
import os
import pickle
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from vidurai import VismritiMemory
from vidurai.core.data_structures_v3 import SalienceLevel, Memory

# v2.0: Database backend
try:
    from vidurai.storage.database import MemoryDatabase, SalienceLevel as DBSalienceLevel
    DATABASE_AVAILABLE = True
except Exception:
    DATABASE_AVAILABLE = False
    logger = logging.getLogger('vidurai-bridge')
    logger.warning("Database not available")

logger = logging.getLogger('vidurai-bridge')


class ViduraiManager:
    """Manage Vidurai memory with local persistence"""

    def __init__(self, session_id: str = None):
        # Use global storage (not workspace directory)
        # Why? Don't pollute user's project directory
        self.session_dir = Path.home() / ".vidurai" / "sessions"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        # Session ID (default: "default")
        self.session_id = session_id or "default"
        self.session_file = self.session_dir / f"{self.session_id}.pkl"

        # Initialize Vidurai memory (v2.0: with database backend)
        self.memory = VismritiMemory(
            enable_gist_extraction=False  # Using rule-based gist
        )

        # v2.0: Direct database access for queries
        self.db = None
        if DATABASE_AVAILABLE:
            try:
                self.db = MemoryDatabase()
            except Exception as e:
                logger.error(f"Failed to initialize database: {e}")

        # Load existing session if available
        self._load_session()

        logger.info(f"Vidurai manager initialized (session: {self.session_id}, db: {self.db is not None})")

    def _load_session(self):
        """Load session from disk if exists"""
        if self.session_file.exists():
            try:
                with open(self.session_file, 'rb') as f:
                    data = pickle.load(f)

                # Restore memory state
                if 'memory_data' in data:
                    # TODO: Load memory state into self.memory
                    # For now, we'll rely on Vidurai's internal persistence
                    pass

                logger.info(f"Loaded session from {self.session_file}")
            except Exception as e:
                logger.error(f"Error loading session: {e}")

    def save_session(self):
        """Save session to disk"""
        try:
            data = {
                'session_id': self.session_id,
                'memory_data': {}  # TODO: Extract memory state from self.memory
            }

            with open(self.session_file, 'wb') as f:
                pickle.dump(data, f)

            logger.info(f"Saved session to {self.session_file}")
        except Exception as e:
            logger.error(f"Error saving session: {e}")

    def remember(self, content: str, metadata: Dict[str, Any],
                 salience: SalienceLevel) -> str:
        """Store content in Vidurai memory"""
        try:
            memory = self.memory.remember(
                content=content,
                metadata=metadata,
                salience=salience
            )

            # Return memory ID (engram_id)
            return memory.engram_id
        except Exception as e:
            logger.error(f"Error storing memory: {e}")
            return None

    def recall(self, query: str, top_k: int = 10) -> List[Memory]:
        """Recall relevant memories"""
        try:
            # Use empty query to get all recent memories
            # (semantic search not critical for v1.0)
            memories = self.memory.recall(
                query=query or "",  # Empty query gets recent memories
                min_salience=SalienceLevel.NOISE,  # Get all
                top_k=top_k
            )

            return memories
        except Exception as e:
            logger.error(f"Error recalling memories: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get current session statistics"""
        try:
            # Get memory ledger
            ledger = self.memory.get_ledger()

            return {
                'session_id': self.session_id,
                'total_memories': len(ledger),
                'session_file': str(self.session_file)
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {
                'session_id': self.session_id,
                'total_memories': 0
            }

    # v2.0: New database query methods

    def get_recent_activity(
        self,
        project_path: str,
        hours: int = 24,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent memories from database (v2.0)"""
        if not self.db:
            logger.warning("Database not available")
            return []

        try:
            return self.db.get_recent_activity(project_path, hours, limit)
        except Exception as e:
            logger.error(f"Error getting recent activity: {e}")
            return []

    def recall_from_database(
        self,
        project_path: str,
        query: Optional[str] = None,
        min_salience: str = 'MEDIUM',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Recall memories from database (v2.0)"""
        if not self.db:
            logger.warning("Database not available")
            return []

        try:
            # Convert string to DBSalienceLevel
            db_salience = DBSalienceLevel[min_salience.upper()]

            return self.db.recall_memories(
                project_path=project_path,
                query=query,
                min_salience=db_salience,
                limit=limit
            )
        except Exception as e:
            logger.error(f"Error recalling from database: {e}")
            return []

    def get_database_statistics(self, project_path: str) -> Dict[str, Any]:
        """Get database statistics for a project (v2.0)"""
        if not self.db:
            logger.warning("Database not available")
            return {'total': 0, 'by_salience': {}, 'by_type': {}}

        try:
            return self.db.get_statistics(project_path)
        except Exception as e:
            logger.error(f"Error getting database statistics: {e}")
            return {'total': 0, 'by_salience': {}, 'by_type': {}}

    def get_context_for_ai(
        self,
        project_path: str,
        query: Optional[str] = None,
        max_tokens: int = 2000
    ) -> str:
        """Get formatted context for AI injection (v2.0)"""
        try:
            return self.memory.get_context_for_ai(query=query, max_tokens=max_tokens)
        except Exception as e:
            logger.error(f"Error getting AI context: {e}")
            return f"[Error: {str(e)}]"
