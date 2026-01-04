#!/usr/bin/env python3
"""
Auto-detection of development projects and tools
Finds Git repos, VS Code workspaces, and active editors
"""

import os
from pathlib import Path
from typing import List, Dict, Set
import logging
import json

logger = logging.getLogger("vidurai.detector")

class AutoDetector:
    """Automatically detect projects worth watching"""

    def __init__(self):
        self.home = Path.home()

    def find_git_repos(self, max_depth: int = 3, max_repos: int = 10) -> List[Path]:
        """Find all Git repositories in common dev directories"""
        repos = []

        # Common development directories
        search_paths = [
            self.home / "Projects",
            self.home / "Code",
            self.home / "Development",
            self.home / "workspace",
            self.home / "dev",
            self.home / "Documents" / "Projects",
            self.home,  # Home directory itself
        ]

        logger.info("🔍 Searching for Git repositories...")

        for search_path in search_paths:
            if not search_path.exists():
                continue

            logger.info(f"   Scanning: {search_path}")

            try:
                # Walk directory tree
                for root, dirs, _ in os.walk(search_path):
                    # Limit depth
                    depth = len(Path(root).relative_to(search_path).parts)
                    if depth > max_depth:
                        dirs.clear()
                        continue

                    # Check if this is a Git repo
                    if '.git' in dirs:
                        repo_path = Path(root)
                        repos.append(repo_path)
                        logger.info(f"   ✓ Found: {repo_path.name}")
                        dirs.remove('.git')  # Don't recurse into .git

                        # Stop if we've found enough
                        if len(repos) >= max_repos:
                            return repos

                    # Skip large directories
                    dirs[:] = [d for d in dirs if d not in {
                        'node_modules', '.venv', 'venv', '__pycache__',
                        '.git', 'build', 'dist', '.next', 'target',
                        'Library', 'Applications', '.Trash'
                    }]

            except (PermissionError, OSError) as e:
                logger.debug(f"   Skipping {search_path}: {e}")
                continue

        logger.info(f"🎯 Found {len(repos)} Git repositories")
        return repos

    def detect_vscode_workspaces(self) -> List[Path]:
        """Detect VS Code workspace files"""
        workspaces = []

        # Check VS Code storage
        vscode_storage = self.home / '.config' / 'Code' / 'User' / 'workspaceStorage'

        if vscode_storage.exists():
            try:
                for workspace_dir in vscode_storage.iterdir():
                    workspace_json = workspace_dir / 'workspace.json'
                    if workspace_json.exists():
                        try:
                            data = json.loads(workspace_json.read_text())
                            if 'folder' in data:
                                folder_uri = data['folder']
                                # Parse file:// URI
                                if folder_uri.startswith('file://'):
                                    folder_path = Path(folder_uri[7:])
                                    if folder_path.exists():
                                        workspaces.append(folder_path)
                                        logger.info(f"   ✓ VS Code workspace: {folder_path.name}")
                        except:
                            continue
            except:
                pass

        return workspaces

    def detect_active_editors(self) -> Dict[str, bool]:
        """Detect which code editors are installed/running"""
        editors = {}

        # Check for VS Code
        vscode_config = self.home / '.config' / 'Code'
        if vscode_config.exists():
            editors['vscode'] = True
            logger.info("   ✓ VS Code detected")

        # Check for Cursor
        cursor_config = self.home / '.config' / 'Cursor'
        if cursor_config.exists():
            editors['cursor'] = True
            logger.info("   ✓ Cursor detected")

        # Check for running processes (optional, requires psutil)
        try:
            import psutil
            for proc in psutil.process_iter(['name']):
                name = proc.info['name'].lower()
                if 'code' in name and 'vscode' not in editors:
                    editors['vscode_running'] = True
                elif 'cursor' in name:
                    editors['cursor_running'] = True
                elif 'zed' in name:
                    editors['zed'] = True
        except ImportError:
            logger.debug("   psutil not installed, skipping process detection")

        return editors

    def get_project_priority(self, path: Path) -> int:
        """Calculate priority score for a project"""
        score = 0

        # Recent activity (check .git modification time)
        git_dir = path / '.git'
        if git_dir.exists():
            try:
                mtime = git_dir.stat().st_mtime
                import time
                age_days = (time.time() - mtime) / 86400

                if age_days < 7:
                    score += 100  # Very recent
                elif age_days < 30:
                    score += 50   # Recent
                elif age_days < 90:
                    score += 10   # Somewhat recent
            except:
                pass

        # Check for common project indicators
        indicators = {
            'package.json': 20,      # Node.js project
            'requirements.txt': 20,  # Python project
            'Cargo.toml': 20,        # Rust project
            'go.mod': 20,            # Go project
            'pom.xml': 20,           # Java project
            'Gemfile': 20,           # Ruby project
            'README.md': 10,         # Documented
            '.env': 5,               # Has configuration
        }

        for file, points in indicators.items():
            if (path / file).exists():
                score += points

        return score

    def auto_discover_projects(self, max_projects: int = 5) -> List[Path]:
        """Auto-discover and prioritize projects to watch"""
        logger.info("🚀 Auto-discovering projects...")

        # Get all repos
        repos = self.find_git_repos(max_repos=20)

        # Get VS Code workspaces
        workspaces = self.detect_vscode_workspaces()

        # Combine and deduplicate
        all_projects = list(set(repos + workspaces))

        # Score and sort
        scored_projects = [
            (path, self.get_project_priority(path))
            for path in all_projects
        ]
        scored_projects.sort(key=lambda x: x[1], reverse=True)

        # Take top N
        top_projects = [path for path, score in scored_projects[:max_projects]]

        logger.info(f"📊 Prioritized {len(top_projects)} projects to watch")
        for i, path in enumerate(top_projects, 1):
            logger.info(f"   {i}. {path.name} ({path})")

        return top_projects
