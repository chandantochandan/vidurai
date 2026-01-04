"""
Event Processor
Handles salience classification, secrets detection, and gist extraction
"""
import re
import logging
from typing import Dict, Any
from pathlib import Path

from vidurai.core.data_structures_v3 import SalienceLevel
from gist_extractor import GistExtractor

logger = logging.getLogger('vidurai-bridge')


# Secrets detection patterns
SECRET_PATTERNS = [
    # API Keys
    r'api[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})',
    r'secret[_-]?key\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})',

    # OpenAI
    r'sk-[a-zA-Z0-9]{48}',
    r'sk-proj-[a-zA-Z0-9]{48,}',

    # Anthropic
    r'sk-ant-api[0-9]{2}-[a-zA-Z0-9\-_]{95,}',

    # GitHub
    r'ghp_[a-zA-Z0-9]{36}',
    r'gho_[a-zA-Z0-9]{36}',

    # AWS
    r'AKIA[0-9A-Z]{16}',
    r'aws[_-]?secret[_-]?access[_-]?key',

    # Generic passwords
    r'password\s*[:=]\s*["\']?([^"\'\s]{8,})',

    # Database URLs
    r'postgres://[^@]+:[^@]+@',
    r'mysql://[^@]+:[^@]+@',

    # Private keys
    r'-----BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',

    # JWTs
    r'eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+',
]

# Files to always ignore (contain secrets)
IGNORED_FILES = [
    '.env',
    '.env.local',
    '.env.production',
    '.env.development',
    'secrets.yaml',
    'secrets.json',
    'credentials.json',
    '.aws/credentials',
]


class EventProcessor:
    """Process VS Code events with salience classification and secrets detection"""

    def __init__(self):
        self.gist_extractor = GistExtractor()

    def _contains_secrets(self, content: str) -> bool:
        """Check if content contains secrets"""
        for pattern in SECRET_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                return True
        return False

    def _sanitize_content(self, content: str) -> str:
        """Remove secrets from content"""
        sanitized = content
        for pattern in SECRET_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        return sanitized

    def _should_ignore_file(self, file_path: str) -> bool:
        """Check if file should be ignored"""
        file_name = Path(file_path).name

        # Check exact matches
        if file_name in IGNORED_FILES:
            return True

        # Check patterns
        for pattern in IGNORED_FILES:
            if '*' in pattern:
                # Simple glob matching
                pattern_re = pattern.replace('.', r'\.').replace('*', '.*')
                if re.match(pattern_re, file_name):
                    return True

        return False

    def _classify_file_edit(self, file_path: str, content: str) -> SalienceLevel:
        """Classify salience of file edit"""
        file_lower = file_path.lower()
        file_name = Path(file_path).name.lower()

        # CRITICAL: Contains secrets (should be ignored, but if not caught)
        if self._contains_secrets(content):
            logger.warning(f"Secrets detected in {file_path}")
            return SalienceLevel.CRITICAL

        # HIGH: Test files (important for debugging)
        if 'test' in file_lower:
            return SalienceLevel.HIGH

        # HIGH: Config files (affect entire project)
        if file_name.endswith(('.json', '.yaml', '.yml', '.toml', '.env')):
            return SalienceLevel.HIGH

        # HIGH: Package management files
        if file_name in ['package.json', 'requirements.txt', 'pyproject.toml',
                          'cargo.toml', 'go.mod', 'pom.xml']:
            return SalienceLevel.HIGH

        # LOW: Documentation
        if file_name.endswith(('.md', '.txt', '.rst')):
            return SalienceLevel.LOW

        # MEDIUM: Normal code edits
        return SalienceLevel.MEDIUM

    def _classify_terminal(self, exit_code: int, output: str) -> SalienceLevel:
        """Classify salience of terminal output"""
        # HIGH: Failed commands (important to remember)
        if exit_code != 0:
            return SalienceLevel.HIGH

        # NOISE: Progress bars, ANSI codes
        if '\r' in output or '\x1b[' in output:
            return SalienceLevel.NOISE

        # NOISE: Too long (spam)
        if len(output) > 10000:
            return SalienceLevel.NOISE

        # MEDIUM: Successful commands
        return SalienceLevel.MEDIUM

    def _classify_diagnostic(self, severity: str) -> SalienceLevel:
        """Classify salience of diagnostic"""
        # CRITICAL: Errors
        if severity == 'error':
            return SalienceLevel.CRITICAL

        # HIGH: Warnings
        if severity == 'warning':
            return SalienceLevel.HIGH

        # MEDIUM: Info
        return SalienceLevel.MEDIUM

    def process_file_edit(self, file_path: str, content: str) -> Dict[str, Any]:
        """Process file edit event"""
        # Check if file should be ignored
        if self._should_ignore_file(file_path):
            logger.info(f"Ignoring file: {file_path}")
            return {
                'salience': SalienceLevel.NOISE,
                'gist': f"Ignored file: {file_path}",
                'contains_secrets': True
            }

        # Check for secrets
        contains_secrets = self._contains_secrets(content)
        if contains_secrets:
            content = self._sanitize_content(content)

        # Classify salience
        salience = self._classify_file_edit(file_path, content)

        # Extract gist
        gist = self.gist_extractor.extract_file_edit_gist(file_path, content)

        return {
            'salience': salience,
            'gist': gist,
            'contains_secrets': contains_secrets
        }

    def process_terminal_output(self, command: str, output: str,
                                 exit_code: int) -> Dict[str, Any]:
        """Process terminal output event"""
        # Classify salience
        salience = self._classify_terminal(exit_code, output)

        # Extract gist
        gist = self.gist_extractor.extract_terminal_gist(command, exit_code)

        return {
            'salience': salience,
            'gist': gist
        }

    def process_diagnostic(self, file_path: str, severity: str,
                          message: str) -> Dict[str, Any]:
        """Process diagnostic event"""
        # Classify salience
        salience = self._classify_diagnostic(severity)

        # Extract gist
        gist = self.gist_extractor.extract_diagnostic_gist(
            file_path, severity, message
        )

        return {
            'salience': salience,
            'gist': gist
        }
