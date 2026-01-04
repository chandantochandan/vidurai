"""
Smart File Watcher with Intelligent Filtering
Prevents spam from log files and irrelevant changes
Philosophy: विस्मृति भी विद्या है - Know what to forget
"""

import os
import time
import hashlib
from pathlib import Path
from watchdog.events import FileSystemEventHandler
from collections import defaultdict
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger("vidurai.smart_watcher")


class SmartFileWatcher(FileSystemEventHandler):
    """Intelligent file watcher that filters noise and spam"""

    def __init__(self, project_path: str, event_queue):
        super().__init__()
        self.project_path = project_path
        self.event_queue = event_queue

        # Ignore patterns - comprehensive list
        self.ignore_extensions = {
            # Logs and temporary
            '.log', '.tmp', '.temp', '.swp', '.swo', '.swn',
            # Python
            '.pyc', '.pyo', '.pyd', '.so',
            # JavaScript/Node
            '.lock',
            # OS files
            '.DS_Store', 'Thumbs.db', 'desktop.ini',
            # IDE files
            '.idea', '.vscode', '.vs',
            # Build artifacts
            '.o', '.obj', '.exe', '.dll', '.dylib',
        }

        self.ignore_directories = {
            '.git', '.svn', '.hg',
            'node_modules', 'bower_components',
            '__pycache__', '.pytest_cache', '.mypy_cache',
            '.venv', 'venv', 'env', 'ENV',
            'dist', 'build', 'target', 'out',
            '.next', '.nuxt', '.cache',
            'coverage', '.coverage', 'htmlcov',
            'logs', 'temp', 'tmp',
        }

        self.ignore_files = {
            'package-lock.json',
            'yarn.lock',
            'poetry.lock',
            'Pipfile.lock',
            'composer.lock',
            'Gemfile.lock',
            '.gitignore',
            '.dockerignore',
        }

        # Tracking for intelligent filtering
        self.file_hashes: Dict[str, str] = {}
        self.change_buffer: Dict[str, float] = defaultdict(float)
        self.debounce_time = 0.5  # 500ms debounce

        # Statistics
        self.stats = {
            'total_events': 0,
            'ignored_events': 0,
            'debounced_events': 0,
            'no_content_change': 0,
            'broadcast_events': 0,
        }

    def should_ignore(self, filepath: str) -> bool:
        """
        Determine if file should be ignored
        Returns True if file should NOT trigger updates
        """
        path = Path(filepath)

        # Check if directory in ignore list
        for part in path.parts:
            if part in self.ignore_directories:
                return True

        # Check file extension
        if path.suffix.lower() in self.ignore_extensions:
            return True

        # Check specific filenames
        if path.name in self.ignore_files:
            return True

        # Check if file contains 'log' in name
        if 'log' in path.name.lower() and path.suffix in {'.txt', '.out'}:
            return True

        # Ignore very large files (>10MB) to avoid memory issues
        try:
            if path.exists() and path.stat().st_size > 10 * 1024 * 1024:
                logger.debug(f"Ignoring large file: {path.name} ({path.stat().st_size} bytes)")
                return True
        except (OSError, IOError):
            return True

        # Ignore binary files (heuristic check)
        if self.is_binary_file(filepath):
            return True

        return False

    def is_binary_file(self, filepath: str, check_bytes: int = 8192) -> bool:
        """
        Check if file is binary (heuristic)
        Returns True if file appears to be binary
        """
        try:
            with open(filepath, 'rb') as f:
                chunk = f.read(check_bytes)
                # If null bytes present, likely binary
                if b'\x00' in chunk:
                    return True
                # Check for high percentage of non-text bytes
                text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)))
                non_text = sum(1 for byte in chunk if byte not in text_chars)
                if len(chunk) > 0 and non_text / len(chunk) > 0.3:
                    return True
        except (IOError, OSError):
            return True

        return False

    def calculate_file_hash(self, filepath: str) -> Optional[str]:
        """
        Calculate MD5 hash of file content
        Returns None if file cannot be read
        """
        try:
            hasher = hashlib.md5()
            with open(filepath, 'rb') as f:
                # Read in chunks to handle large files
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (IOError, OSError) as e:
            logger.debug(f"Could not hash file {filepath}: {e}")
            return None

    def has_content_changed(self, filepath: str) -> bool:
        """
        Check if file content actually changed (not just metadata/timestamps)
        Returns True only if content is different
        """
        current_hash = self.calculate_file_hash(filepath)

        if current_hash is None:
            return False  # Could not read file, don't broadcast

        previous_hash = self.file_hashes.get(filepath)

        # Update stored hash
        self.file_hashes[filepath] = current_hash

        # If first time seeing file, consider it changed
        if previous_hash is None:
            return True

        # Check if hash differs
        return current_hash != previous_hash

    def extract_file_context(self, filepath: str) -> Dict[str, Any]:
        """
        Extract relevant context from file
        Returns structured context, not entire file content
        """
        path = Path(filepath)

        context = {
            'filename': path.name,
            'extension': path.suffix,
            'relative_path': str(path.relative_to(self.project_path)) if self.project_path in str(path) else str(path),
            'size': 0,
            'importance': 'medium',
        }

        try:
            stat = path.stat()
            context['size'] = stat.st_size

            # Determine importance based on file type and location
            context['importance'] = self.assess_importance(path)

            # Extract preview for text files
            if path.suffix in {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.c', '.cpp', '.h'}:
                context['preview'] = self.extract_code_preview(filepath)

        except (OSError, IOError) as e:
            logger.debug(f"Could not extract context from {filepath}: {e}")

        return context

    def assess_importance(self, path: Path) -> str:
        """
        Assess importance of file change
        Returns: 'high', 'medium', or 'low'
        """
        # High importance files
        if path.suffix in {'.py', '.js', '.ts', '.java', '.go', '.rs'}:
            return 'high'

        # Configuration files
        if path.name in {'package.json', 'requirements.txt', 'Cargo.toml', 'go.mod'}:
            return 'high'

        # Documentation
        if path.suffix in {'.md', '.rst', '.txt'} and 'readme' in path.name.lower():
            return 'medium'

        # Tests
        if 'test' in path.name.lower() or 'spec' in path.name.lower():
            return 'medium'

        # Everything else
        return 'low'

    def extract_code_preview(self, filepath: str, max_lines: int = 10) -> str:
        """
        Extract preview of code file (first few lines or recent changes)
        """
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                lines = []
                for i, line in enumerate(f):
                    if i >= max_lines:
                        break
                    lines.append(line.rstrip())
                return '\n'.join(lines)
        except (IOError, OSError):
            return ""

    def on_modified(self, event):
        """
        Handle file modification with intelligence
        """
        if event.is_directory:
            return

        self.stats['total_events'] += 1
        filepath = event.src_path

        # 1. Ignore irrelevant files
        if self.should_ignore(filepath):
            self.stats['ignored_events'] += 1
            logger.debug(f"Ignored: {Path(filepath).name}")
            return

        # 2. Check if content actually changed
        if not self.has_content_changed(filepath):
            self.stats['no_content_change'] += 1
            logger.debug(f"No content change: {Path(filepath).name}")
            return

        # 3. Debounce rapid changes
        current_time = time.time()
        last_change = self.change_buffer[filepath]

        if current_time - last_change < self.debounce_time:
            self.stats['debounced_events'] += 1
            logger.debug(f"Debounced: {Path(filepath).name}")
            return

        self.change_buffer[filepath] = current_time

        # 4. Extract relevant context
        context = self.extract_file_context(filepath)

        # 5. Broadcast intelligent update
        self.broadcast_smart_update(filepath, context)

    def broadcast_smart_update(self, filepath: str, context: Dict[str, Any]):
        """
        Send intelligent update to event queue
        """
        path = Path(filepath)

        event_data = {
            'event': 'file_changed',
            'path': str(path),
            'project': self.project_path,
            'filename': path.name,
            'timestamp': time.time(),
            'context': context,
        }

        # Add to queue for async broadcast
        self.event_queue.put(event_data)

        self.stats['broadcast_events'] += 1
        logger.info(f"📝 {context['importance'].upper()}: {path.name} changed")

    def get_statistics(self) -> Dict[str, Any]:
        """Get watcher statistics"""
        total = self.stats['total_events']
        broadcast = self.stats['broadcast_events']

        return {
            **self.stats,
            'efficiency': f"{broadcast}/{total} events broadcast" if total > 0 else "0/0",
            'filter_rate': f"{((total - broadcast) / total * 100):.1f}%" if total > 0 else "0%"
        }
