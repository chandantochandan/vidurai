"""
Test Suite for Memory Role Classifier (SF-2.1)

Tests role classification accuracy and priority scoring.
"""

import pytest
from vidurai.core.memory_role_classifier import (
    MemoryRoleClassifier,
    MemoryRole,
    classify_memory_role
)


class TestMemoryRoleClassifier:
    """Test memory role classification"""

    def setup_method(self):
        """Setup classifier for each test"""
        self.classifier = MemoryRoleClassifier()

    def test_resolution_classification(self):
        """Test detection of RESOLUTION memories"""
        # Test cases with resolution keywords
        test_cases = [
            "Fixed the authentication bug. Tests now pass.",
            "Solved the JWT issue by normalizing timestamps.",
            "Problem resolved - deployed to production.",
            "The fix was to update the config. Working now.",
        ]

        for text in test_cases:
            result = self.classifier.classify(text)
            assert result.role == MemoryRole.RESOLUTION, f"Failed to detect resolution in: {text}"
            assert result.confidence >= 0.7, f"Low confidence for resolution: {result.confidence}"
            assert len(result.keywords_matched) > 0, "No keywords matched"

    def test_cause_classification(self):
        """Test detection of CAUSE memories"""
        test_cases = [
            "Root cause was JWT timestamp mismatch.",
            "The issue is timezone handling in auth module.",
            "Problem caused by incorrect datetime format.",
            "Found the reason - missing timezone conversion.",
        ]

        for text in test_cases:
            result = self.classifier.classify(text)
            assert result.role == MemoryRole.CAUSE, f"Failed to detect cause in: {text}"
            assert result.confidence >= 0.7
            assert len(result.keywords_matched) > 0

    def test_attempted_fix_classification(self):
        """Test detection of ATTEMPTED_FIX memories"""
        test_cases = [
            "Tried adding timezone info but still failing.",
            "Attempted to normalize timestamps - didn't work.",
            "Debugging the auth flow, testing different approaches.",
        ]

        for text in test_cases:
            result = self.classifier.classify(text)
            assert result.role == MemoryRole.ATTEMPTED_FIX, f"Failed to detect attempted fix in: {text}"
            assert result.confidence >= 0.6

        # Edge case: "Maybe the issue is" could be CAUSE or ATTEMPTED_FIX
        # Both are semantically valid - it's hypothesizing about the cause
        edge_case = "Maybe the issue is in the validation logic?"
        result = self.classifier.classify(edge_case)
        assert result.role in [MemoryRole.CAUSE, MemoryRole.ATTEMPTED_FIX], \
            f"Should be CAUSE or ATTEMPTED_FIX, got {result.role}"

    def test_context_classification(self):
        """Test detection of CONTEXT memories"""
        test_cases = [
            "For context: this auth system uses JWT tokens.",
            "Background: the issue started after the deployment.",
            "Note that this affects all API endpoints.",
            "Related to the timezone refactoring from last week.",
        ]

        for text in test_cases:
            result = self.classifier.classify(text)
            assert result.role == MemoryRole.CONTEXT, f"Failed to detect context in: {text}"

    def test_noise_classification(self):
        """Test detection of NOISE memories"""
        test_cases = [
            "ok",
            "hmm",
            "...",
            "yes",
            "short",  # Very short text
        ]

        for text in test_cases:
            result = self.classifier.classify(text)
            assert result.role == MemoryRole.NOISE, f"Failed to detect noise in: {text}"

    def test_priority_scoring(self):
        """Test priority scores for different roles"""
        priorities = {
            MemoryRole.RESOLUTION: 20,
            MemoryRole.CAUSE: 18,
            MemoryRole.ATTEMPTED_FIX: 12,
            MemoryRole.CONTEXT: 8,
            MemoryRole.NOISE: 0,
        }

        for role, expected_priority in priorities.items():
            actual_priority = self.classifier.get_role_priority(role)
            assert actual_priority == expected_priority, \
                f"{role.value} priority mismatch: expected {expected_priority}, got {actual_priority}"

    def test_confidence_levels(self):
        """Test confidence scores are within valid range"""
        test_texts = [
            "Fixed the bug completely.",
            "Root cause identified.",
            "Tried a different approach.",
            "For context, this is important.",
            "noise",
        ]

        for text in test_texts:
            result = self.classifier.classify(text)
            assert 0.0 <= result.confidence <= 1.0, \
                f"Invalid confidence: {result.confidence}"

    def test_batch_classification(self):
        """Test batch processing of multiple memories"""
        memories = [
            {'id': 1, 'verbatim': 'Fixed the auth issue.', 'gist': None, 'metadata': None},
            {'id': 2, 'verbatim': 'Root cause was timezone.', 'gist': None, 'metadata': None},
            {'id': 3, 'verbatim': 'Tried normalizing times.', 'gist': None, 'metadata': None},
            {'id': 4, 'verbatim': 'Background context.', 'gist': None, 'metadata': None},
            {'id': 5, 'verbatim': 'ok', 'gist': None, 'metadata': None},
        ]

        results = self.classifier.classify_batch(memories)

        assert len(results) == 5
        assert results[1].role == MemoryRole.RESOLUTION
        assert results[2].role == MemoryRole.CAUSE
        assert results[3].role == MemoryRole.ATTEMPTED_FIX
        assert results[4].role == MemoryRole.CONTEXT
        assert results[5].role == MemoryRole.NOISE

    def test_gist_metadata_usage(self):
        """Test that gist and metadata are used in classification"""
        # Verbatim is vague, but gist has clear resolution
        result = self.classifier.classify(
            verbatim="Made some changes to the code.",
            gist="Fixed the authentication bug completely.",
            metadata={'event_type': 'code_change'}
        )

        assert result.role == MemoryRole.RESOLUTION

    def test_convenience_function(self):
        """Test the convenience function"""
        result = classify_memory_role(
            "Root cause was missing timezone conversion."
        )

        assert isinstance(result.role, MemoryRole)
        assert result.role == MemoryRole.CAUSE

    def test_statistics(self):
        """Test classifier statistics"""
        stats = self.classifier.get_statistics()

        assert stats['classifier'] == 'pattern_based'
        assert 'pattern_counts' in stats
        assert stats['total_patterns'] > 0
        assert stats['pattern_counts']['resolution'] > 0
        assert stats['pattern_counts']['cause'] > 0


class TestRoleClassificationEdgeCases:
    """Test edge cases and corner scenarios"""

    def setup_method(self):
        self.classifier = MemoryRoleClassifier()

    def test_empty_text(self):
        """Test classification of empty text"""
        result = self.classifier.classify("")
        assert result.role == MemoryRole.NOISE

    def test_very_long_text(self):
        """Test classification of very long text"""
        long_text = "This is a long debugging session. " * 100 + "Fixed the issue finally."
        result = self.classifier.classify(long_text)
        assert result.role == MemoryRole.RESOLUTION  # Should still detect resolution

    def test_mixed_signals(self):
        """Test text with multiple role indicators"""
        # Has both cause and resolution keywords
        mixed = "Root cause was JWT issue. Fixed by normalizing timestamps."
        result = self.classifier.classify(mixed)

        # Resolution should win (higher priority in pattern matching)
        assert result.role == MemoryRole.RESOLUTION

    def test_ambiguous_text(self):
        """Test ambiguous text without clear role indicators"""
        result = self.classifier.classify("Working on the authentication module.")
        # Should default to CONTEXT
        assert result.role == MemoryRole.CONTEXT
        assert result.confidence < 0.6  # Low confidence for ambiguous

    def test_case_insensitivity(self):
        """Test that classification is case-insensitive"""
        results = []
        for text in ["FIXED THE BUG", "fixed the bug", "FiXeD tHe BuG"]:
            result = self.classifier.classify(text)
            results.append(result.role)

        # All should be RESOLUTION
        assert all(role == MemoryRole.RESOLUTION for role in results)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
