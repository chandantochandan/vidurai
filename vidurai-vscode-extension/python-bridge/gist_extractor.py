"""
Gist Extractor
Rule-based semantic gist extraction (no LLM needed for v1.0)
"""
from pathlib import Path


class GistExtractor:
    """Extract semantic gist from code events using rule-based patterns"""

    def extract_file_edit_gist(self, file_path: str, content: str) -> str:
        """Extract gist from file edit"""
        file_name = Path(file_path).name
        file_lower = file_name.lower()

        # Pattern 1: Test files
        if 'test' in file_lower:
            if 'def test_' in content:
                test_count = content.count('def test_')
                return f"Modified {test_count} test(s) in {file_name}"
            return f"Updated test file: {file_name}"

        # Pattern 2: Function definitions
        if 'def ' in content or 'function ' in content:
            return f"Added/modified functions in {file_name}"

        # Pattern 3: Class definitions
        if 'class ' in content:
            return f"Modified class definitions in {file_name}"

        # Pattern 4: Imports
        if 'import ' in content or 'from ' in content or 'require(' in content:
            return f"Updated imports in {file_name}"

        # Pattern 5: Config files
        if file_name.endswith(('.json', '.yaml', '.yml', '.toml')):
            return f"Updated configuration: {file_name}"

        # Pattern 6: Documentation
        if file_name.endswith('.md'):
            return f"Updated documentation: {file_name}"

        # Default: Just file edit
        return f"Edited {file_name}"

    def extract_terminal_gist(self, command: str, exit_code: int) -> str:
        """Extract gist from terminal output"""
        if exit_code != 0:
            return f"Command failed: {command}"
        else:
            return f"Ran command: {command}"

    def extract_diagnostic_gist(self, file_path: str, severity: str,
                                 message: str) -> str:
        """Extract gist from diagnostic"""
        file_name = Path(file_path).name

        # Truncate long messages
        if len(message) > 100:
            message = message[:97] + "..."

        return f"{severity.capitalize()} in {file_name}: {message}"
