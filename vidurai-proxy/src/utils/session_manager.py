"""
Session Manager
Manages Vidurai memory instances per session with persistence
Each session maintains its own conversation context and learning
"""

import os
import pickle
import hashlib
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

from vidurai import VismritiMemory
from vidurai.core.rl_agent_v2 import RewardProfile

class SessionManager:
    """
    Manages multiple Vidurai sessions with persistence and timeout

    Features:
    - One Vidurai instance per session (isolated memory)
    - Session ID generated from API key hash (automatic)
    - Sessions persist to disk (survive restarts)
    - Automatic cleanup of expired sessions
    - Thread-safe session access
    """

    def __init__(self, config):
        """
        Initialize session manager

        Args:
            config: Config object from config_loader
        """
        self.config = config
        self.sessions: Dict[str, VismritiMemory] = {}
        self.last_activity: Dict[str, datetime] = {}

        # Create session directory
        self.session_dir = Path(config.session.memory_dir)
        self.session_dir.mkdir(exist_ok=True, parents=True)

        logger.info(f"SessionManager initialized with dir: {self.session_dir}")

        # Load persisted sessions if enabled
        if config.session.persist_memory:
            self._load_persisted_sessions()

    def get_session(self, session_id: str) -> VismritiMemory:
        """
        Get or create Vismriti instance for session

        Args:
            session_id: Unique session identifier

        Returns:
            VismritiMemory instance for this session
        """

        # Update activity timestamp
        self.last_activity[session_id] = datetime.now()

        # Return existing session if available
        if session_id in self.sessions:
            logger.debug(f"Retrieved existing session: {session_id[:8]}...")
            return self.sessions[session_id]

        # Try to load persisted session
        if self.config.session.persist_memory:
            vidurai = self._load_session_from_disk(session_id)
            if vidurai:
                self.sessions[session_id] = vidurai
                logger.info(f"Loaded persisted session: {session_id[:8]}...")
                return vidurai

        # Create new session
        vidurai = self._create_vidurai_instance()
        self.sessions[session_id] = vidurai
        logger.info(f"Created new session: {session_id[:8]}...")

        return vidurai

    def _create_vidurai_instance(self) -> VismritiMemory:
        """
        Create new Vismriti instance from config settings

        Returns:
            Configured VismritiMemory instance
        """

        # Map config profile string to RewardProfile enum
        profile_map = {
            'QUALITY': RewardProfile.QUALITY_FOCUSED,
            'QUALITY_FOCUSED': RewardProfile.QUALITY_FOCUSED,
            'BALANCED': RewardProfile.BALANCED,
            'COST': RewardProfile.COST_FOCUSED,
            'COST_FOCUSED': RewardProfile.COST_FOCUSED
        }

        reward_profile = profile_map.get(
            self.config.vidurai.reward_profile.upper(),
            RewardProfile.QUALITY_FOCUSED
        )

        # Create VismritiMemory with config settings
        # Note: Gist extraction is optional (requires OPENAI_API_KEY), disable for now
        # RL agent provides compression via learned policies
        memory = VismritiMemory(
            enable_gist_extraction=False,  # Optional feature, requires OpenAI API key
            enable_decay=self.config.vidurai.enable_decay,
            enable_rl_agent=True  # Enable RL agent to use reward profile
        )

        # Configure RL agent with reward profile if enabled
        if memory.rl_agent:
            memory.rl_agent.reward_profile = reward_profile

        logger.debug(
            f"Created VismritiMemory instance: "
            f"profile={self.config.vidurai.reward_profile}, "
            f"decay={self.config.vidurai.enable_decay}, "
            f"gist_extraction=False (optional), "
            f"rl_agent=True"
        )

        return memory

    def generate_session_id(self, api_key: str) -> str:
        """
        Generate consistent session ID from API key

        Args:
            api_key: User's API key

        Returns:
            Hashed session ID (first 16 chars of SHA256)
        """
        # Hash the API key for privacy
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        session_id = key_hash[:16]

        logger.debug(f"Generated session ID: {session_id}")
        return session_id

    def cleanup_expired_sessions(self) -> int:
        """
        Remove expired sessions based on timeout

        Returns:
            Number of sessions cleaned up
        """
        timeout = timedelta(minutes=self.config.session.timeout_minutes)
        now = datetime.now()

        expired = [
            sid for sid, last_active in self.last_activity.items()
            if now - last_active > timeout
        ]

        for session_id in expired:
            # Persist before removing
            if self.config.session.persist_memory:
                self._persist_session(session_id)

            # Remove from memory
            del self.sessions[session_id]
            del self.last_activity[session_id]

            logger.info(f"Cleaned up expired session: {session_id[:8]}...")

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired sessions")

        return len(expired)

    def _persist_session(self, session_id: str) -> bool:
        """
        Save session to disk

        Args:
            session_id: Session to persist

        Returns:
            True if successful, False otherwise
        """
        if session_id not in self.sessions:
            return False

        try:
            session_file = self.session_dir / f"{session_id}.pkl"

            with open(session_file, 'wb') as f:
                pickle.dump(self.sessions[session_id], f)

            logger.debug(f"Persisted session: {session_id[:8]}...")
            return True

        except Exception as e:
            logger.error(f"Failed to persist session {session_id[:8]}...: {e}")
            return False

    def _load_session_from_disk(self, session_id: str) -> Optional[VismritiMemory]:
        """
        Load session from disk

        Args:
            session_id: Session to load

        Returns:
            VismritiMemory instance or None if not found/error
        """
        session_file = self.session_dir / f"{session_id}.pkl"

        if not session_file.exists():
            return None

        try:
            with open(session_file, 'rb') as f:
                vidurai = pickle.load(f)

            logger.debug(f"Loaded session from disk: {session_id[:8]}...")
            return vidurai

        except Exception as e:
            logger.error(f"Failed to load session {session_id[:8]}...: {e}")
            return None

    def _load_persisted_sessions(self):
        """Load all persisted sessions from disk at startup"""

        session_files = list(self.session_dir.glob("*.pkl"))

        if not session_files:
            logger.info("No persisted sessions found")
            return

        loaded = 0
        for session_file in session_files:
            try:
                session_id = session_file.stem

                with open(session_file, 'rb') as f:
                    vidurai = pickle.load(f)

                self.sessions[session_id] = vidurai
                self.last_activity[session_id] = datetime.now()
                loaded += 1

            except Exception as e:
                logger.error(f"Failed to load {session_file.name}: {e}")

        logger.info(f"Loaded {loaded} persisted sessions")

    def persist_all_sessions(self):
        """Persist all active sessions to disk"""

        if not self.config.session.persist_memory:
            return

        persisted = 0
        for session_id in self.sessions.keys():
            if self._persist_session(session_id):
                persisted += 1

        logger.info(f"Persisted {persisted} sessions to disk")

    def get_session_count(self) -> int:
        """Get number of active sessions"""
        return len(self.sessions)

    def get_session_stats(self) -> dict:
        """
        Get statistics about all sessions

        Returns:
            Dictionary with session statistics
        """
        return {
            'active_sessions': len(self.sessions),
            'total_sessions_seen': len(self.last_activity),
            'persisted_sessions': len(list(self.session_dir.glob("*.pkl")))
        }
