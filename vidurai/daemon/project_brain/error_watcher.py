#!/usr/bin/env python3
"""
PHASE 2: ERROR CAPTURE & MONITORING
Watches for errors and captures complete context
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from collections import deque
import subprocess

logger = logging.getLogger("vidurai.project_brain.error_watcher")


class ErrorContext:
    """Complete context of an error"""

    def __init__(self, error_text: str, command: str = None):
        self.error_text = error_text
        self.command = command
        self.directory = str(Path.cwd())
        self.timestamp = datetime.now()
        self.error_type = self._classify_error(error_text)
        self.recent_changes = []
        self.git_branch = None
        self.affected_files = self._extract_file_references(error_text)

    def _classify_error(self, text: str) -> str:
        """Classify the type of error"""
        if 'Traceback' in text or 'File "' in text:
            return 'Python Exception'
        elif 'npm ERR!' in text:
            return 'NPM Error'
        elif 'error:' in text.lower() and 'compiler' in text.lower():
            return 'Compilation Error'
        elif 'FAILED' in text:
            return 'Test Failure'
        elif any(err in text for err in ['TypeError', 'ValueError', 'AttributeError', 'KeyError']):
            return 'Python Runtime Error'
        elif 'SyntaxError' in text:
            return 'Syntax Error'
        elif 'ModuleNotFoundError' in text or 'ImportError' in text:
            return 'Import Error'
        elif 'Cannot find module' in text:
            return 'Module Not Found'
        else:
            return 'Unknown Error'

    def _extract_file_references(self, text: str) -> List[str]:
        """Extract file paths mentioned in error"""
        files = []

        # Python traceback: File "path", line X
        python_files = re.findall(r'File "([^"]+)"', text)
        files.extend(python_files)

        # Generic path patterns
        path_patterns = [
            r'([a-zA-Z0-9_/\-\.]+\.py)',
            r'([a-zA-Z0-9_/\-\.]+\.js)',
            r'([a-zA-Z0-9_/\-\.]+\.ts)',
            r'([a-zA-Z0-9_/\-\.]+\.tsx)',
        ]

        for pattern in path_patterns:
            found = re.findall(pattern, text)
            files.extend(found)

        # Remove duplicates while preserving order
        seen = set()
        unique_files = []
        for f in files:
            if f not in seen:
                seen.add(f)
                unique_files.append(f)

        return unique_files[:10]  # Limit to 10 files

    def to_dict(self) -> dict:
        return {
            "error_text": self.error_text,
            "error_type": self.error_type,
            "command": self.command,
            "directory": self.directory,
            "timestamp": self.timestamp.isoformat(),
            "recent_changes": self.recent_changes,
            "git_branch": self.git_branch,
            "affected_files": self.affected_files
        }


class ErrorWatcher:
    """Monitor and capture errors with context"""

    def __init__(self, max_errors: int = 5):
        self.recent_errors: deque[ErrorContext] = deque(maxlen=max_errors)
        self.terminal_buffer: deque[str] = deque(maxlen=200)  # Keep last 200 lines
        self.last_command: Optional[str] = None
        self.watching_history = False

        # Error patterns to detect
        self.error_patterns = [
            r'Traceback \(most recent call last\)',
            r'Error:',
            r'FAILED',
            r'TypeError:',
            r'ValueError:',
            r'AttributeError:',
            r'KeyError:',
            r'SyntaxError:',
            r'ImportError:',
            r'ModuleNotFoundError:',
            r'npm ERR!',
            r'error TS\d+:',  # TypeScript errors
            r'Compilation failed',
            r'command not found',
            r'Permission denied',
        ]

        self.compiled_patterns = [re.compile(p, re.IGNORECASE) for p in self.error_patterns]

    def start_monitoring_history(self):
        """Start monitoring shell history files for errors"""
        self.watching_history = True
        logger.info("📊 Started monitoring shell history for errors")

        # Detect shell type and history file
        shell_histories = [
            Path.home() / ".bash_history",
            Path.home() / ".zsh_history",
            Path.home() / ".history",
        ]

        for history_file in shell_histories:
            if history_file.exists():
                logger.info(f"   Watching: {history_file}")

        # Note: Actual file watching would be done by the daemon's file watcher

    def add_terminal_output(self, output: str):
        """Add terminal output to buffer for error detection"""
        lines = output.split('\n')
        for line in lines:
            self.terminal_buffer.append(line)

            # Check if this line contains an error pattern
            if self.is_error_line(line):
                self.capture_error_from_buffer()

    def is_error_line(self, line: str) -> bool:
        """Check if a line contains an error pattern"""
        return any(pattern.search(line) for pattern in self.compiled_patterns)

    def capture_error_from_buffer(self):
        """Capture error context from terminal buffer"""
        # Get recent buffer content
        buffer_text = '\n'.join(self.terminal_buffer)

        # Find error start
        error_start_idx = 0
        for i, line in enumerate(self.terminal_buffer):
            if self.is_error_line(line):
                # Go back 10 lines for context
                error_start_idx = max(0, i - 10)
                break

        # Extract error text (from start to end of buffer)
        error_lines = list(self.terminal_buffer)[error_start_idx:]
        error_text = '\n'.join(error_lines)

        # Create error context
        error_ctx = ErrorContext(error_text, self.last_command)

        # Get recent file changes
        error_ctx.recent_changes = self.get_recent_file_changes(minutes=5)

        # Get git branch
        error_ctx.git_branch = self.get_current_git_branch()

        # Store error
        self.recent_errors.append(error_ctx)

        logger.warning(f"🚨 Captured error: {error_ctx.error_type}")
        logger.debug(f"   Command: {error_ctx.command}")
        logger.debug(f"   Files: {', '.join(error_ctx.affected_files[:3])}")

    def capture_error_context(self, error_text: str, command: str = None) -> ErrorContext:
        """Manually capture an error with context"""
        error_ctx = ErrorContext(error_text, command or self.last_command)

        # Get recent file changes
        error_ctx.recent_changes = self.get_recent_file_changes(minutes=5)

        # Get git branch
        error_ctx.git_branch = self.get_current_git_branch()

        # Store error
        self.recent_errors.append(error_ctx)

        logger.warning(f"🚨 Captured error: {error_ctx.error_type}")

        return error_ctx

    def get_recent_file_changes(self, minutes: int = 5) -> List[Dict]:
        """Get files modified in the last N minutes"""
        changes = []
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        try:
            cwd = Path.cwd()

            # Get git status for changed files
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=2
            )

            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.strip():
                        # Parse git status line: "XY filename"
                        status = line[:2]
                        filename = line[3:].strip()

                        # Check file modification time
                        file_path = cwd / filename
                        if file_path.exists():
                            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if mtime > cutoff_time:
                                changes.append({
                                    "file": filename,
                                    "status": status.strip(),
                                    "modified": mtime.isoformat()
                                })

        except Exception as e:
            logger.debug(f"Could not get recent changes: {e}")

        return changes[:10]  # Limit to 10 most recent

    def get_current_git_branch(self) -> Optional[str]:
        """Get current git branch"""
        try:
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return None

    def format_for_debugging(self, error_context: ErrorContext) -> str:
        """
        Format error for web AI tools (ChatGPT, Claude):
        - Clear error description
        - Relevant code snippets
        - What was being attempted
        - Recent changes that might have caused it
        """
        output = []

        # Header
        output.append(f"## 🐛 {error_context.error_type}\n")

        # When it happened
        time_ago = datetime.now() - error_context.timestamp
        if time_ago.seconds < 60:
            time_str = "just now"
        elif time_ago.seconds < 3600:
            time_str = f"{time_ago.seconds // 60} minutes ago"
        else:
            time_str = f"{time_ago.seconds // 3600} hours ago"

        output.append(f"**Occurred:** {time_str}")

        # Command that caused it
        if error_context.command:
            output.append(f"**Command:** `{error_context.command}`")

        # Directory
        output.append(f"**Directory:** `{error_context.directory}`")

        # Git branch
        if error_context.git_branch:
            output.append(f"**Branch:** `{error_context.git_branch}`\n")

        # Error details
        output.append("### Error Details\n")
        output.append("```")
        # Limit error text to 50 lines
        error_lines = error_context.error_text.split('\n')
        output.append('\n'.join(error_lines[-50:]))
        output.append("```\n")

        # Affected files
        if error_context.affected_files:
            output.append("### Affected Files\n")
            for file in error_context.affected_files[:5]:
                output.append(f"- `{file}`")
            output.append("")

        # Recent changes
        if error_context.recent_changes:
            output.append("### Recent Changes (Last 5 min)\n")
            for change in error_context.recent_changes[:5]:
                status = change.get('status', '??')
                file = change.get('file', 'unknown')
                output.append(f"- {status} `{file}`")
            output.append("")

        # Helpful context
        output.append("### What I was doing\n")
        if error_context.error_type == 'Import Error':
            output.append("- Trying to import a module that may not be installed")
            output.append("- Check if package is in requirements.txt")
        elif error_context.error_type == 'Test Failure':
            output.append("- Running tests that failed")
            output.append("- Check recent code changes for breaking changes")
        elif error_context.error_type == 'Syntax Error':
            output.append("- Code has syntax errors that prevent execution")
        else:
            output.append(f"- Executing command: {error_context.command or 'unknown'}")

        return '\n'.join(output)

    def get_recent_errors(self, limit: int = 5) -> List[ErrorContext]:
        """Get the most recent errors"""
        return list(self.recent_errors)[:limit]

    def get_last_error(self) -> Optional[ErrorContext]:
        """Get the most recent error"""
        return self.recent_errors[0] if self.recent_errors else None

    def clear_errors(self):
        """Clear all captured errors"""
        self.recent_errors.clear()
        logger.info("🧹 Cleared all error history")

    def set_last_command(self, command: str):
        """Set the last executed command"""
        self.last_command = command
