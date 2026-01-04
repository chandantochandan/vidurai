"""
Unit Tests for Vidurai Bridge
"""
import json
import subprocess
import pytest
import time
from pathlib import Path

from event_processor import EventProcessor, SECRET_PATTERNS
from gist_extractor import GistExtractor
from vidurai.core.data_structures_v3 import SalienceLevel


class TestEventProcessor:
    """Test event processing and salience classification"""

    def setup_method(self):
        self.processor = EventProcessor()

    def test_salience_error_diagnostic(self):
        """Test CRITICAL salience for error diagnostics"""
        result = self.processor.process_diagnostic(
            'main.py', 'error', 'Syntax error'
        )
        assert result['salience'] == SalienceLevel.CRITICAL

    def test_salience_test_file(self):
        """Test HIGH salience for test files"""
        result = self.processor.process_file_edit(
            'test_main.py', 'def test_foo(): pass'
        )
        assert result['salience'] == SalienceLevel.HIGH

    def test_salience_config_file(self):
        """Test HIGH salience for config files"""
        result = self.processor.process_file_edit(
            'package.json', '{"name": "test"}'
        )
        assert result['salience'] == SalienceLevel.HIGH

    def test_salience_normal_edit(self):
        """Test MEDIUM salience for normal edits"""
        result = self.processor.process_file_edit(
            'main.py', 'def hello(): print("hi")'
        )
        assert result['salience'] == SalienceLevel.MEDIUM

    def test_salience_readme(self):
        """Test LOW salience for documentation"""
        result = self.processor.process_file_edit(
            'README.md', '# My Project'
        )
        assert result['salience'] == SalienceLevel.LOW

    def test_salience_terminal_failure(self):
        """Test HIGH salience for failed commands"""
        result = self.processor.process_terminal_output(
            'pytest', 'FAILED', exit_code=1
        )
        assert result['salience'] == SalienceLevel.HIGH

    def test_secrets_detection_openai(self):
        """Test OpenAI key detection"""
        content = 'OPENAI_API_KEY="sk-abcd1234567890abcd1234567890abcd1234567890abcd12"'
        assert self.processor._contains_secrets(content)

    def test_secrets_detection_anthropic(self):
        """Test Anthropic key detection"""
        content = 'api_key = "sk-ant-api03-abcdefg"'
        assert self.processor._contains_secrets(content)

    def test_secrets_sanitization(self):
        """Test secrets are redacted"""
        content = 'API_KEY="sk-test1234567890123456789012345678901234567890ab"'
        sanitized = self.processor._sanitize_content(content)
        assert '[REDACTED]' in sanitized
        assert 'sk-test' not in sanitized

    def test_ignored_files(self):
        """Test .env files are ignored"""
        assert self.processor._should_ignore_file('.env')
        assert self.processor._should_ignore_file('.env.local')
        assert self.processor._should_ignore_file('secrets.json')


class TestGistExtractor:
    """Test gist extraction"""

    def setup_method(self):
        self.extractor = GistExtractor()

    def test_test_file_gist(self):
        """Test gist for test files"""
        gist = self.extractor.extract_file_edit_gist(
            'test_main.py',
            'def test_one(): pass\ndef test_two(): pass'
        )
        assert 'test' in gist.lower()
        assert '2' in gist

    def test_function_gist(self):
        """Test gist for function definitions"""
        gist = self.extractor.extract_file_edit_gist(
            'utils.py',
            'def helper(): return True'
        )
        assert 'function' in gist.lower()

    def test_config_gist(self):
        """Test gist for config files"""
        gist = self.extractor.extract_file_edit_gist(
            'config.yaml',
            'key: value'
        )
        assert 'configuration' in gist.lower()

    def test_terminal_success_gist(self):
        """Test gist for successful command"""
        gist = self.extractor.extract_terminal_gist('npm test', 0)
        assert 'ran command' in gist.lower()

    def test_terminal_failure_gist(self):
        """Test gist for failed command"""
        gist = self.extractor.extract_terminal_gist('pytest', 1)
        assert 'failed' in gist.lower()


class TestBridgeCommunication:
    """Test stdin/stdout communication"""

    def test_bridge_starts(self):
        """Test bridge starts without errors"""
        proc = subprocess.Popen(
            ['python', 'bridge.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Bridge should be running
        assert proc.poll() is None

        # Cleanup
        proc.terminate()
        proc.wait(timeout=2)

    def test_ping_pong(self):
        """Test ping/pong communication"""
        proc = subprocess.Popen(
            ['python', 'bridge.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Send ping
        event = json.dumps({'type': 'ping'}) + '\n'
        proc.stdin.write(event)
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        response = json.loads(response_line)

        assert response['status'] == 'ok'
        assert response['message'] == 'pong'

        # Cleanup
        proc.terminate()
        proc.wait(timeout=2)

    def test_file_edit_event(self):
        """Test file edit event processing"""
        proc = subprocess.Popen(
            ['python', 'bridge.py'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        # Send file edit event
        event = json.dumps({
            'type': 'file_edit',
            'file': 'test.py',
            'content': 'print("hello")'
        }) + '\n'
        proc.stdin.write(event)
        proc.stdin.flush()

        # Read response
        response_line = proc.stdout.readline()
        response = json.loads(response_line)

        assert response['status'] == 'ok'
        assert 'memory_id' in response
        assert 'salience' in response
        assert 'gist' in response

        # Cleanup
        proc.terminate()
        proc.wait(timeout=2)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
