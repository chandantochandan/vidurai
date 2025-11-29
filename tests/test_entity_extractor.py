"""
Test Suite for Entity Extractor (SF-2.2)

Tests entity extraction from memory text with 100% preservation guarantee.
"""

import pytest
from vidurai.core.entity_extractor import (
    EntityExtractor,
    ExtractedEntities,
    extract_entities
)


class TestEntityExtractor:
    """Test entity extraction from memory text"""

    def setup_method(self):
        """Setup extractor for each test"""
        self.extractor = EntityExtractor()

    def test_error_type_extraction(self):
        """Test extraction of error types"""
        text = "TypeError: Cannot read property 'x' of undefined. ValueError in validation."

        entities = self.extractor.extract(text)

        assert 'TypeError' in entities.error_types
        assert 'ValueError' in entities.error_types
        assert len(entities.error_types) == 2

    def test_error_message_extraction(self):
        """Test extraction of complete error messages"""
        text = "Error: JWT validation failed due to timestamp mismatch in auth module"

        entities = self.extractor.extract(text)

        assert len(entities.error_messages) > 0
        assert 'JWT validation failed' in entities.error_messages[0]

    def test_stack_trace_extraction_python(self):
        """Test extraction of Python stack traces"""
        text = '''
        File "/app/auth.py", line 42, in validateToken
        File "/app/main.py", line 100, in handle_request
        '''

        entities = self.extractor.extract(text)

        assert len(entities.stack_traces) >= 2
        # Check first trace
        trace = entities.stack_traces[0]
        assert '/app/auth.py' in trace['file']
        assert trace['line'] == 42
        assert trace['function'] == 'validateToken'

    def test_stack_trace_extraction_javascript(self):
        """Test extraction of JavaScript stack traces"""
        text = "at validateToken (auth.js:42:10)\nat handleRequest (main.js:100:5)"

        entities = self.extractor.extract(text)

        assert len(entities.stack_traces) >= 1
        trace = entities.stack_traces[0]
        assert trace['function'] == 'validateToken'
        assert 'auth.js' in trace['file']
        assert trace['line'] == 42

    def test_function_name_extraction(self):
        """Test extraction of function names"""
        text = "Called validateToken() and authenticateUser() functions"

        entities = self.extractor.extract(text)

        assert 'validateToken' in entities.function_names
        assert 'authenticateUser' in entities.function_names

    def test_class_name_extraction(self):
        """Test extraction of class names (CamelCase)"""
        text = "UserAuthenticator and TokenValidator classes"

        entities = self.extractor.extract(text)

        assert 'UserAuthenticator' in entities.class_names
        assert 'TokenValidator' in entities.class_names

    def test_variable_name_extraction(self):
        """Test extraction of variable names (snake_case)"""
        text = "The jwt_timestamp and auth_token variables"

        entities = self.extractor.extract(text)

        assert 'jwt_timestamp' in entities.variable_names
        assert 'auth_token' in entities.variable_names

    def test_file_path_extraction(self):
        """Test extraction of file paths"""
        text = "Error in src/auth.py and config/settings.json"

        entities = self.extractor.extract(text)

        assert any('auth.py' in fp for fp in entities.file_paths)
        assert any('settings.json' in fp for fp in entities.file_paths)

    def test_config_key_extraction(self):
        """Test extraction of config keys (SCREAMING_SNAKE_CASE)"""
        text = "Set DATABASE_URL and API_KEY in environment"

        entities = self.extractor.extract(text)

        assert 'DATABASE_URL' in entities.config_keys
        assert 'API_KEY' in entities.config_keys

    def test_environment_variable_extraction(self):
        """Test extraction of environment variables with values"""
        text = "NODE_ENV=production and DEBUG=true"

        entities = self.extractor.extract(text)

        assert 'NODE_ENV' in entities.environment_vars
        assert entities.environment_vars['NODE_ENV'] == 'production'
        assert 'DEBUG' in entities.environment_vars

    def test_database_field_extraction(self):
        """Test extraction of database fields (table.column)"""
        text = "Query user.email and session.expires_at fields"

        entities = self.extractor.extract(text)

        assert 'user.email' in entities.database_fields
        assert 'session.expires_at' in entities.database_fields

    def test_timestamp_extraction(self):
        """Test extraction of ISO 8601 timestamps"""
        text = "Event at 2025-11-24T15:30:00Z and 2025-11-24 10:00:00"

        entities = self.extractor.extract(text)

        assert len(entities.timestamps) >= 1
        assert any('2025-11-24' in ts for ts in entities.timestamps)

    def test_url_extraction(self):
        """Test extraction of URLs"""
        text = "API at https://api.example.com/auth and http://localhost:3000"

        entities = self.extractor.extract(text)

        assert 'https://api.example.com/auth' in entities.urls
        assert 'http://localhost:3000' in entities.urls

    def test_ip_address_extraction(self):
        """Test extraction of IP addresses"""
        text = "Server at 192.168.1.100 and 10.0.0.1"

        entities = self.extractor.extract(text)

        assert '192.168.1.100' in entities.ip_addresses
        assert '10.0.0.1' in entities.ip_addresses

    def test_version_extraction(self):
        """Test extraction of version numbers"""
        text = "Upgraded to v1.2.3 and 2.0.0-beta"

        entities = self.extractor.extract(text)

        assert any('1.2.3' in v for v in entities.version_numbers)
        assert any('2.0.0' in v for v in entities.version_numbers)

    def test_hash_extraction(self):
        """Test extraction of git commit hashes"""
        text = "Commit abc123def456 and full hash 1234567890abcdef1234567890abcdef12345678"

        entities = self.extractor.extract(text)

        assert len(entities.hash_values) >= 1
        assert any(len(h) >= 7 for h in entities.hash_values)

    def test_entity_merging(self):
        """Test merging of multiple ExtractedEntities"""
        entities1 = ExtractedEntities(
            error_types=['TypeError'],
            function_names=['validateToken'],
            file_paths=['auth.py']
        )

        entities2 = ExtractedEntities(
            error_types=['ValueError'],  # Different error
            function_names=['validateToken'],  # Duplicate (should deduplicate)
            file_paths=['auth.py', 'main.py']  # One duplicate, one new
        )

        merged = entities1.merge(entities2)

        assert set(merged.error_types) == {'TypeError', 'ValueError'}
        assert set(merged.function_names) == {'validateToken'}
        assert set(merged.file_paths) == {'auth.py', 'main.py'}

    def test_entity_count(self):
        """Test counting total entities"""
        entities = ExtractedEntities(
            error_types=['TypeError', 'ValueError'],
            function_names=['func1', 'func2'],
            file_paths=['file1.py', 'file2.py']
        )

        assert entities.count() == 6  # 2 + 2 + 2

    def test_compact_string_representation(self):
        """Test compact string format for display"""
        entities = ExtractedEntities(
            error_types=['TypeError'],
            file_paths=['auth.py'],
            line_numbers=[42],
            function_names=['validateToken'],
            variable_names=['jwt_timestamp']
        )

        compact = entities.to_compact_string()

        assert 'TypeError' in compact
        assert 'auth.py:42' in compact
        assert 'validateToken()' in compact
        assert 'jwt_timestamp' in compact

    def test_to_dict_serialization(self):
        """Test dictionary serialization"""
        entities = ExtractedEntities(
            error_types=['TypeError'],
            function_names=['validateToken']
        )

        data = entities.to_dict()

        assert isinstance(data, dict)
        assert 'error_types' in data
        assert 'function_names' in data
        assert data['error_types'] == ['TypeError']

    def test_batch_extraction(self):
        """Test extraction from multiple texts"""
        texts = [
            "TypeError in auth.py",
            "ValueError in validateToken()",
            "Error at 192.168.1.100"
        ]

        results = self.extractor.extract_batch(texts)

        assert len(results) == 3
        assert 'TypeError' in results[0].error_types
        assert 'validateToken' in results[1].function_names
        assert '192.168.1.100' in results[2].ip_addresses

    def test_convenience_function(self):
        """Test convenience function"""
        entities = extract_entities("TypeError in auth.py line 42: Cannot find validateToken()")

        assert 'TypeError' in entities.error_types
        assert any('auth.py' in fp for fp in entities.file_paths)
        assert 'validateToken' in entities.function_names


class TestEntityExtractionEdgeCases:
    """Test edge cases for entity extraction"""

    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_empty_text(self):
        """Test extraction from empty text"""
        entities = self.extractor.extract("")

        assert entities.count() == 0

    def test_no_entities(self):
        """Test text with no recognizable entities"""
        entities = self.extractor.extract("This is just plain text with no technical content")

        # May have some variables, but should be minimal
        assert entities.count() <= 5  # Mostly empty (some words might match variable pattern)

    def test_overlapping_entities(self):
        """Test text with overlapping entity patterns"""
        # This could match as both function and variable
        text = "get_user_info is a function"

        entities = self.extractor.extract(text)

        # Should appear in at least one category
        assert len(entities.function_names) + len(entities.variable_names) > 0

    def test_false_positive_filtering(self):
        """Test that common false positives are filtered out"""
        text = "The function is called and will return the value"

        entities = self.extractor.extract(text)

        # Common words like 'is', 'the', 'and', 'will' should be filtered
        assert 'is' not in entities.function_names
        assert 'the' not in entities.variable_names
        assert 'and' not in entities.variable_names

    def test_very_long_text(self):
        """Test extraction from very long text"""
        long_text = "TypeError in auth.py. " * 1000  # Repeated content

        entities = self.extractor.extract(long_text)

        # Should still extract and deduplicate
        assert 'TypeError' in entities.error_types
        assert len(entities.error_types) == 1  # Deduplicated

    def test_special_characters(self):
        """Test extraction with special characters"""
        text = "Error: @user/package#method() failed with $ERROR_CODE"

        entities = self.extractor.extract(text)

        # Should handle gracefully
        assert entities.count() >= 0  # No crash

    def test_unicode_text(self):
        """Test extraction from Unicode text"""
        text = "TypeError in 文件.py: 错误消息"

        entities = self.extractor.extract(text)

        # Should extract the error type at minimum
        assert 'TypeError' in entities.error_types


class TestEntityPreservationGuarantee:
    """Test that entities are NEVER lost"""

    def setup_method(self):
        self.extractor = EntityExtractor()

    def test_100_percent_preservation(self):
        """Test that all extracted entities are preserved through merge"""
        # Extract from multiple memories
        memories = [
            "TypeError in auth.py line 42 with validateToken()",
            "ValueError in main.py with authenticateUser()",
            "Error at https://api.example.com/auth"
        ]

        all_entities = ExtractedEntities()
        for text in memories:
            entities = self.extractor.extract(text)
            all_entities = all_entities.merge(entities)

        # Verify all unique entities present
        assert 'TypeError' in all_entities.error_types
        assert 'ValueError' in all_entities.error_types
        assert 'validateToken' in all_entities.function_names
        assert 'authenticateUser' in all_entities.function_names
        assert any('auth.py' in fp for fp in all_entities.file_paths)
        assert any('main.py' in fp for fp in all_entities.file_paths)
        assert 'https://api.example.com/auth' in all_entities.urls

        # Total count should be >= sum of individual counts (allowing for deduplication)
        assert all_entities.count() >= 7  # At least the unique ones


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
