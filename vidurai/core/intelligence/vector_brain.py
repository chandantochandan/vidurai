"""
Vector Brain - Semantic Embedding Engine

Glass Box Protocol: Heavy ML Rule (CRITICAL)
- sentence-transformers and torch are ~500MB+ RAM
- NEVER import at module level
- ONLY import inside generate_embedding() method
- Daemon must start instantly; vector engine warms up in background

Model: all-MiniLM-L6-v2 (384 dimensions, fast, accurate)

@version 2.1.0-Guardian
"""

import sqlite3
from pathlib import Path
from typing import List, Optional, TYPE_CHECKING
from threading import Lock
from loguru import logger

# Glass Box: TYPE_CHECKING for hints only, no runtime import
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer


# =============================================================================
# CONSTANTS
# =============================================================================

MODEL_NAME = "all-MiniLM-L6-v2"
VECTOR_DIMENSIONS = 384
BATCH_SIZE = 10
DB_PATH = Path.home() / '.vidurai' / 'vidurai.db'


# =============================================================================
# VECTOR ENGINE
# =============================================================================

class VectorEngine:
    """
    Semantic embedding engine for Vidurai memories.

    Glass Box Protocol:
    - Lazy loads sentence-transformers (Heavy ML Rule)
    - Thread-safe model access
    - Batch processing for efficiency
    - Integrates with vec_memories SQLite table

    Usage:
        engine = VectorEngine()

        # Generate single embedding
        vec = engine.generate_embedding("Fix authentication bug")

        # Backfill missing vectors
        engine.backfill_vectors()
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize VectorEngine.

        Args:
            db_path: Path to SQLite database (default: ~/.vidurai/vidurai.db)
        """
        self.db_path = db_path or DB_PATH
        self._model: Optional['SentenceTransformer'] = None
        self._model_lock = Lock()
        self._initialized = False

        logger.debug(f"VectorEngine created (model will lazy-load on first use)")

    @property
    def model(self) -> 'SentenceTransformer':
        """
        Lazy-load the sentence transformer model.

        Glass Box Protocol: Heavy ML Rule
        - Import happens HERE, not at module level
        - Thread-safe via lock
        - First call takes ~2-5 seconds (model loading)
        - Subsequent calls are instant
        """
        if self._model is None:
            with self._model_lock:
                # Double-check after acquiring lock
                if self._model is None:
                    logger.info(f"Loading embedding model: {MODEL_NAME}...")

                    # Glass Box: LAZY IMPORT - Critical for startup time
                    from sentence_transformers import SentenceTransformer

                    self._model = SentenceTransformer(MODEL_NAME)
                    self._initialized = True
                    logger.info(f"   Embedding model loaded (dims={VECTOR_DIMENSIONS})")

        return self._model

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed (gist or verbatim)

        Returns:
            List of 384 floats (MiniLM dimensions)

        Glass Box Protocol:
        - Model lazy-loaded on first call
        - Returns Python list (not numpy array) for SQLite compatibility
        """
        if not text or not text.strip():
            # Return zero vector for empty text
            return [0.0] * VECTOR_DIMENSIONS

        # Model access triggers lazy load if needed
        embedding = self.model.encode(text, convert_to_numpy=True)

        # Convert to Python list for SQLite storage
        return embedding.tolist()

    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (more efficient than one-by-one).

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Filter empty texts, track indices
        valid_texts = []
        valid_indices = []
        results = [[0.0] * VECTOR_DIMENSIONS] * len(texts)

        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return results

        # Batch encode
        embeddings = self.model.encode(valid_texts, convert_to_numpy=True)

        # Map back to original indices
        for idx, embedding in zip(valid_indices, embeddings):
            results[idx] = embedding.tolist()

        return results

    def backfill_vectors(self, batch_size: int = BATCH_SIZE) -> int:
        """
        Backfill missing vectors in vec_memories table.

        Finds memories without embeddings and computes them.

        Args:
            batch_size: Number of memories to process per batch

        Returns:
            Total number of memories vectorized
        """
        logger.info("Starting vector backfill...")

        # Glass Box: Lazy import sqlite_vec only when needed
        try:
            import sqlite_vec
        except ImportError:
            logger.error("sqlite-vec not installed. Run: pip install sqlite-vec")
            return 0

        conn = sqlite3.connect(str(self.db_path))

        # Enable sqlite-vec extension
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        cursor = conn.cursor()

        # Find memories without vectors
        cursor.execute("""
            SELECT m.id, m.gist, m.verbatim
            FROM memories m
            WHERE m.id NOT IN (SELECT memory_id FROM vec_memories)
            ORDER BY m.id
        """)

        missing = cursor.fetchall()
        total_missing = len(missing)

        if total_missing == 0:
            logger.info("   No missing vectors found")
            conn.close()
            return 0

        logger.info(f"   Found {total_missing} memories without vectors")

        vectorized = 0

        # Process in batches
        for i in range(0, total_missing, batch_size):
            batch = missing[i:i + batch_size]

            # Prepare texts (prefer gist over verbatim)
            texts = [
                row[1] if row[1] else row[2]  # gist or verbatim
                for row in batch
            ]

            # Generate embeddings
            embeddings = self.generate_embeddings_batch(texts)

            # Insert into vec_memories
            for (memory_id, _, _), embedding in zip(batch, embeddings):
                try:
                    # sqlite-vec uses special serialization for vectors
                    cursor.execute(
                        "INSERT INTO vec_memories (memory_id, embedding) VALUES (?, ?)",
                        (memory_id, sqlite_vec.serialize_float32(embedding))
                    )
                    vectorized += 1
                except Exception as e:
                    logger.warning(f"Failed to vectorize memory {memory_id}: {e}")

            conn.commit()
            logger.info(f"   Vectorized {min(i + batch_size, total_missing)}/{total_missing} memories")

        conn.close()
        logger.info(f"   Vector backfill complete: {vectorized} memories processed")

        return vectorized

    def search_similar(
        self,
        query: str,
        limit: int = 10,
        project_id: Optional[int] = None
    ) -> List[tuple]:
        """
        Search for semantically similar memories.

        Args:
            query: Search query text
            limit: Max results to return
            project_id: Filter by project (optional)

        Returns:
            List of (memory_id, distance) tuples, sorted by similarity
        """
        # Glass Box: Lazy import
        try:
            import sqlite_vec
        except ImportError:
            logger.error("sqlite-vec not installed")
            return []

        # Generate query embedding
        query_vec = self.generate_embedding(query)

        conn = sqlite3.connect(str(self.db_path))
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)

        cursor = conn.cursor()

        # Vector similarity search
        if project_id:
            cursor.execute("""
                SELECT v.memory_id, v.distance
                FROM vec_memories v
                JOIN memories m ON v.memory_id = m.id
                WHERE m.project_id = ?
                  AND v.embedding MATCH ?
                  AND k = ?
                ORDER BY v.distance
            """, (project_id, sqlite_vec.serialize_float32(query_vec), limit))
        else:
            cursor.execute("""
                SELECT memory_id, distance
                FROM vec_memories
                WHERE embedding MATCH ?
                  AND k = ?
                ORDER BY distance
            """, (sqlite_vec.serialize_float32(query_vec), limit))

        results = cursor.fetchall()
        conn.close()

        return results

    def get_stats(self) -> dict:
        """Get vector engine statistics."""
        # Glass Box: Lazy import for sqlite-vec
        try:
            import sqlite_vec
            vec_available = True
        except ImportError:
            vec_available = False

        conn = sqlite3.connect(str(self.db_path))

        # Load extension if available
        if vec_available:
            try:
                conn.enable_load_extension(True)
                sqlite_vec.load(conn)
                conn.enable_load_extension(False)
            except Exception:
                vec_available = False

        cursor = conn.cursor()

        # Count total memories
        cursor.execute("SELECT COUNT(*) FROM memories")
        total_memories = cursor.fetchone()[0]

        # Count vectorized memories (only if vec extension loaded)
        vectorized = 0
        if vec_available:
            try:
                cursor.execute("SELECT COUNT(*) FROM vec_memories")
                vectorized = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                pass  # Table might not exist

        conn.close()

        return {
            'model': MODEL_NAME,
            'dimensions': VECTOR_DIMENSIONS,
            'model_loaded': self._initialized,
            'vec_extension_available': vec_available,
            'total_memories': total_memories,
            'vectorized_memories': vectorized,
            'missing_vectors': total_memories - vectorized,
            'coverage_percent': round(
                (vectorized / total_memories * 100) if total_memories > 0 else 0, 2
            )
        }


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_engine: Optional[VectorEngine] = None


def get_vector_engine(db_path: Optional[Path] = None) -> VectorEngine:
    """
    Get or create the default VectorEngine instance.

    Args:
        db_path: Optional database path

    Returns:
        VectorEngine singleton
    """
    global _default_engine
    if _default_engine is None:
        _default_engine = VectorEngine(db_path=db_path)
    return _default_engine


def reset_vector_engine() -> None:
    """Reset the default engine instance."""
    global _default_engine
    _default_engine = None
