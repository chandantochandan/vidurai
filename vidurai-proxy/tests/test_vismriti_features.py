"""
VismritiMemory Feature Tests
Tests for v1.6.1 Vismriti Architecture features in proxy
"""

import pytest
from vidurai import VismritiMemory, SalienceLevel, MemoryStatus
from src.utils.session_manager import SessionManager
from src.utils.config_loader import load_config


class TestVismritiFeatures:
    """Test Vismriti-specific features"""

    @pytest.fixture
    def config(self):
        """Load test config"""
        return load_config()

    @pytest.fixture
    def session_manager(self, config):
        """Create session manager"""
        return SessionManager(config)

    def test_vismriti_memory_creation(self, session_manager):
        """Test that VismritiMemory instance is created"""
        session_id = session_manager.generate_session_id("test_api_key")
        memory = session_manager.get_session(session_id)

        assert isinstance(memory, VismritiMemory)
        assert memory is not None

    def test_salience_classification(self, session_manager):
        """Test salience level classification"""
        session_id = session_manager.generate_session_id("test_salience")
        memory = session_manager.get_session(session_id)

        # Remember different types of memories
        mem_critical = memory.remember("Remember this API key: sk-test-123")
        mem_low = memory.remember("Hello world")

        # Check salience levels were assigned
        assert mem_critical.salience == SalienceLevel.CRITICAL
        assert mem_low.salience == SalienceLevel.LOW

    def test_memory_status(self, session_manager):
        """Test memory status tracking"""
        session_id = session_manager.generate_session_id("test_status")
        memory = session_manager.get_session(session_id)

        # Create memory
        mem = memory.remember("Test memory")

        # Check initial status
        assert mem.status == MemoryStatus.ACTIVE

    def test_memory_recall(self, session_manager):
        """Test memory recall functionality"""
        session_id = session_manager.generate_session_id("test_recall")
        memory = session_manager.get_session(session_id)

        # Store memories
        memory.remember("Python programming tips")
        memory.remember("JavaScript debugging")
        memory.remember("Python data structures")

        # Recall Python-related memories
        results = memory.recall("Python")

        assert len(results) >= 2
        assert all("Python" in r.gist or "Python" in r.verbatim for r in results)

    def test_memory_ledger(self, session_manager):
        """Test memory ledger generation"""
        session_id = session_manager.generate_session_id("test_ledger")
        memory = session_manager.get_session(session_id)

        # Store some memories
        memory.remember("Test 1", salience=SalienceLevel.HIGH)
        memory.remember("Test 2", salience=SalienceLevel.LOW)

        # Get ledger
        ledger = memory.get_ledger(format="dataframe")

        assert len(ledger) == 2
        assert "Gist" in ledger.columns
        assert "Salience Level" in ledger.columns
        assert "Status" in ledger.columns

    def test_memory_statistics(self, session_manager):
        """Test memory statistics"""
        session_id = session_manager.generate_session_id("test_stats")
        memory = session_manager.get_session(session_id)

        # Store memories
        memory.remember("Stat test 1")
        memory.remember("Stat test 2")
        memory.remember("Stat test 3")

        # Get statistics
        stats = memory.get_statistics()

        assert stats["total_memories"] == 3
        assert stats["active_memories"] == 3
        assert stats["forgotten_memories"] == 0

    def test_active_forgetting(self, session_manager):
        """Test active forgetting feature"""
        session_id = session_manager.generate_session_id("test_forget")
        memory = session_manager.get_session(session_id)

        # Store memories
        memory.remember("Keep this")
        mem_forget = memory.remember("Forget this")

        # Forget specific memory
        result = memory.forget("forget this", confirmation=False)

        assert result["unlearned"] >= 1
        assert mem_forget.status == MemoryStatus.UNLEARNED

    def test_session_isolation(self, session_manager):
        """Test that sessions are isolated"""
        # Create two sessions
        session1_id = session_manager.generate_session_id("user1_api_key")
        session2_id = session_manager.generate_session_id("user2_api_key")

        memory1 = session_manager.get_session(session1_id)
        memory2 = session_manager.get_session(session2_id)

        # Store memory in session 1
        memory1.remember("Session 1 data")

        # Check session 2 doesn't have it
        results = memory2.recall("Session 1 data")
        assert len(results) == 0

        # Check session 1 does have it
        results = memory1.recall("Session 1 data")
        assert len(results) >= 1

    def test_memory_persistence_compatibility(self, session_manager):
        """Test that VismritiMemory can be pickled (v1.5.2 fix)"""
        import pickle

        session_id = session_manager.generate_session_id("test_pickle")
        memory = session_manager.get_session(session_id)

        # Store some data
        memory.remember("Pickle test")

        # Try to pickle (should not raise exception)
        try:
            pickled = pickle.dumps(memory)
            restored = pickle.loads(pickled)
            assert isinstance(restored, VismritiMemory)
            assert len(restored.memories) == 1
        except Exception as e:
            pytest.fail(f"Pickling failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
