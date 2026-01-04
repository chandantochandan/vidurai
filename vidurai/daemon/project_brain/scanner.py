#!/usr/bin/env python3
"""
PHASE 1: PROJECT AUTO-DETECTION
Automatically discovers all projects without configuration
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime
import subprocess

logger = logging.getLogger("vidurai.project_brain.scanner")


class ProjectInfo:
    """Information about a detected project"""

    def __init__(self, path: str):
        self.path = Path(path)
        self.name = self.path.name
        self.type = None
        self.version = None
        self.language = None
        self.git_branch = None
        self.git_commits = []
        self.problems = []
        self.last_scanned = datetime.now()

    def to_dict(self) -> dict:
        return {
            "path": str(self.path),
            "name": self.name,
            "type": self.type,
            "version": self.version,
            "language": self.language,
            "git_branch": self.git_branch,
            "git_commits": self.git_commits,
            "problems": self.problems,
            "last_scanned": self.last_scanned.isoformat()
        }


class ProjectScanner:
    """Automatically detect and analyze projects"""

    def __init__(self, memory_store=None):
        self.projects: Dict[str, ProjectInfo] = {}
        self.current_project: Optional[ProjectInfo] = None
        self.memory_store = memory_store

        # Common project directories
        self.search_paths = [
            Path.home() / "projects",
            Path.home() / "Projects",
            Path.home() / "dev",
            Path.home() / "code",
            Path.home() / "Code",
            Path.home() / "work",
            Path.home() / "workspace",
            Path.home() / "Development",
            Path.home(),
        ]

    def scan_all_projects(
        self,
        max_projects: int = 20,
        max_depth: int = 3,
        quick_mode: bool = True,
        lazy: bool = False
    ) -> List[ProjectInfo]:
        """
        Find all projects without any configuration
        Discovers 90% of developer's projects automatically

        v2.2: quick_mode=True (default) skips heavy operations for fast startup
        v2.5: lazy=True returns immediately (no file system walk) for <0.1s startup

        Args:
            max_projects: Maximum number of projects to scan
            max_depth: Maximum directory depth to search
            quick_mode: If True, skip heavy operations (version, language detection)
            lazy: If True, return immediately without scanning (for instant startup)

        Returns:
            List of ProjectInfo objects (empty if lazy=True)
        """
        # IRONCLAD RULE I: Non-Blocking Startup
        # If lazy=True, return immediately - daemon becomes "Ready" instantly
        if lazy:
            logger.info("⚡ Lazy mode: Skipping initial scan (will scan on first file event)")
            return []

        logger.info("🔍 Starting automatic project scan...")
        found_paths: Set[str] = set()

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            logger.debug(f"   Scanning: {search_path}")

            # Find git repos in this path
            repos = self._find_git_repos(search_path, max_depth)
            found_paths.update(repos)

            if len(found_paths) >= max_projects:
                break

        # Analyze each found project
        logger.info(f"📊 Found {len(found_paths)} projects, analyzing...")

        for path_str in list(found_paths)[:max_projects]:
            try:
                project = ProjectInfo(path_str)

                # v2.2: Quick mode - only detect type, skip heavy operations
                project.type = self.detect_project_type(project.path)

                if not quick_mode:
                    # Full analysis (deferred until file event arrives)
                    project.version = self.extract_version(project.path)
                    project.language = self.detect_language(project.path)
                    git_info = self.get_git_info(project.path)
                    project.git_branch = git_info.get("branch")
                    project.git_commits = git_info.get("commits", [])
                    project.problems = self.detect_problems(project)

                # Store project
                self.projects[path_str] = project
                logger.info(f"   ✓ {project.name} ({project.type or 'unknown'})")

            except Exception as e:
                logger.error(f"   ✗ Failed to analyze {path_str}: {e}")

        # Save to memory
        if self.memory_store:
            self.memory_store.save_projects(self.projects)

        logger.info(f"✅ Scanned {len(self.projects)} projects")
        return list(self.projects.values())

    def _find_git_repos(self, search_path: Path, max_depth: int) -> Set[str]:
        """Find all git repositories in a path"""
        repos = set()

        try:
            for root, dirs, _ in os.walk(search_path):
                # Calculate depth
                depth = len(Path(root).relative_to(search_path).parts)
                if depth > max_depth:
                    dirs.clear()
                    continue

                # Check for .git directory
                if '.git' in dirs:
                    repos.add(root)
                    # Don't recurse into found repos
                    dirs.clear()

                # Skip common ignore directories
                dirs[:] = [d for d in dirs if d not in {
                    'node_modules', '__pycache__', '.venv', 'venv',
                    'dist', 'build', '.next', 'target', '.pytest_cache',
                    '.git'
                }]

        except PermissionError:
            pass

        return repos

    def detect_project_type(self, path: Path) -> Optional[str]:
        """
        Identify project type from files present:
        - package.json → node
        - setup.py/pyproject.toml → python
        - Cargo.toml → rust
        - go.mod → go
        - pom.xml → java
        - Gemfile → ruby
        """
        type_indicators = {
            "node": ["package.json"],
            "python": ["setup.py", "pyproject.toml", "requirements.txt"],
            "rust": ["Cargo.toml"],
            "go": ["go.mod"],
            "java": ["pom.xml", "build.gradle"],
            "ruby": ["Gemfile"],
            "php": ["composer.json"],
            "dotnet": ["*.csproj", "*.sln"],
        }

        for proj_type, indicators in type_indicators.items():
            for indicator in indicators:
                if list(path.glob(indicator)):
                    return proj_type

        return None

    def extract_version(self, path: Path) -> Optional[str]:
        """
        Find version from standard locations:
        - package.json → version field
        - setup.py → version= parameter
        - __version__.py → __version__ variable
        - VERSION file → direct content
        - pyproject.toml → tool.poetry.version
        """
        # Try package.json
        package_json = path / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text())
                return data.get("version")
            except:
                pass

        # Try pyproject.toml
        pyproject = path / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text()
                for line in content.split('\n'):
                    if 'version' in line and '=' in line:
                        return line.split('=')[1].strip().strip('"\'')
            except:
                pass

        # Try setup.py
        setup_py = path / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text()
                for line in content.split('\n'):
                    if 'version=' in line or 'version =' in line:
                        # Extract version from line like: version="1.2.3",
                        parts = line.split('=', 1)
                        if len(parts) == 2:
                            version = parts[1].strip().strip('",\'')
                            return version
            except:
                pass

        # Try __version__.py
        version_file = path / "__version__.py"
        if version_file.exists():
            try:
                content = version_file.read_text()
                for line in content.split('\n'):
                    if '__version__' in line:
                        return line.split('=')[1].strip().strip('"\'')
            except:
                pass

        # Try VERSION file
        version_file = path / "VERSION"
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except:
                pass

        # Try Cargo.toml
        cargo = path / "Cargo.toml"
        if cargo.exists():
            try:
                content = cargo.read_text()
                for line in content.split('\n'):
                    if 'version' in line and '=' in line:
                        return line.split('=')[1].strip().strip('"\'')
            except:
                pass

        return None

    def detect_language(self, path: Path) -> Optional[str]:
        """Detect primary language from file extensions"""
        extension_count = {}

        # Count file extensions
        try:
            for file in path.rglob('*'):
                if file.is_file() and not self._should_ignore_path(file):
                    ext = file.suffix.lower()
                    if ext in {'.py', '.js', '.ts', '.tsx', '.jsx', '.rs', '.go', '.java', '.rb', '.php', '.cs'}:
                        extension_count[ext] = extension_count.get(ext, 0) + 1
        except:
            pass

        # Return most common
        if extension_count:
            most_common = max(extension_count.items(), key=lambda x: x[1])
            ext_to_lang = {
                '.py': 'Python',
                '.js': 'JavaScript',
                '.ts': 'TypeScript',
                '.tsx': 'TypeScript',
                '.jsx': 'JavaScript',
                '.rs': 'Rust',
                '.go': 'Go',
                '.java': 'Java',
                '.rb': 'Ruby',
                '.php': 'PHP',
                '.cs': 'C#'
            }
            return ext_to_lang.get(most_common[0])

        return None

    def _should_ignore_path(self, path: Path) -> bool:
        """Check if path should be ignored"""
        ignore_parts = {
            '.git', 'node_modules', '__pycache__', '.venv', 'venv',
            'dist', 'build', '.next', 'target', '.pytest_cache'
        }
        return any(part in path.parts for part in ignore_parts)

    def get_git_info(self, path: Path) -> dict:
        """Get git branch and recent commits"""
        info = {"branch": None, "commits": []}

        try:
            # Get current branch
            result = subprocess.run(
                ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                info["branch"] = result.stdout.strip()

            # Get last 5 commits
            result = subprocess.run(
                ['git', 'log', '--pretty=format:%h|%s|%ar', '-5'],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                commits = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split('|', 2)
                        if len(parts) == 3:
                            commits.append({
                                "hash": parts[0],
                                "message": parts[1],
                                "when": parts[2]
                            })
                info["commits"] = commits
        except:
            pass

        return info

    def detect_problems(self, project: ProjectInfo) -> List[str]:
        """
        Detect common problems:
        - Version mismatches
        - Outdated documentation
        - Missing dependencies
        - Too many uncommitted changes
        """
        problems = []

        # Check for missing dependencies
        if project.type == "node":
            if (project.path / "package.json").exists() and not (project.path / "node_modules").exists():
                problems.append("Missing node_modules (run npm install)")

        elif project.type == "python":
            if (project.path / "requirements.txt").exists():
                venv_paths = [project.path / ".venv", project.path / "venv"]
                if not any(p.exists() for p in venv_paths):
                    problems.append("No virtual environment found")

        # Check for uncommitted changes
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=project.path,
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0:
                changes = [line for line in result.stdout.split('\n') if line.strip()]
                if len(changes) > 20:
                    problems.append(f"{len(changes)} uncommitted changes")
        except:
            pass

        # Check if README is outdated (older than recent commits)
        readme = project.path / "README.md"
        if readme.exists() and project.git_commits:
            try:
                readme_time = readme.stat().st_mtime
                # Get time of most recent commit
                result = subprocess.run(
                    ['git', 'log', '-1', '--format=%ct'],
                    cwd=project.path,
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                if result.returncode == 0:
                    last_commit_time = int(result.stdout.strip())
                    # If README is older than last commit by more than a day
                    if readme_time < last_commit_time - 86400:
                        problems.append("README may be outdated")
            except:
                pass

        return problems

    def auto_switch_context(self) -> Optional[ProjectInfo]:
        """
        Detect current working directory change
        Automatically switch to that project's context
        """
        cwd = Path.cwd()

        # Check if we're in a known project
        for path_str, project in self.projects.items():
            try:
                cwd.relative_to(project.path)
                # We're inside this project
                if self.current_project != project:
                    logger.info(f"📂 Switched context to: {project.name}")
                    self.current_project = project
                return project
            except ValueError:
                continue

        # Not in a known project, check if cwd is a git repo
        if (cwd / ".git").exists():
            # Add this project
            if str(cwd) not in self.projects:
                logger.info(f"🆕 Detected new project: {cwd.name}")
                project = ProjectInfo(str(cwd))
                project.type = self.detect_project_type(cwd)
                project.version = self.extract_version(cwd)
                project.language = self.detect_language(cwd)
                git_info = self.get_git_info(cwd)
                project.git_branch = git_info.get("branch")
                project.git_commits = git_info.get("commits", [])
                project.problems = self.detect_problems(project)

                self.projects[str(cwd)] = project
                self.current_project = project

                if self.memory_store:
                    self.memory_store.save_projects(self.projects)

                return project

        return self.current_project

    def get_project_summary(self, project: ProjectInfo) -> str:
        """Get a concise summary of a project"""
        summary_parts = [f"**{project.name}**"]

        if project.version:
            summary_parts.append(f"v{project.version}")

        if project.type:
            summary_parts.append(f"({project.type})")

        if project.language:
            summary_parts.append(f"- {project.language}")

        if project.git_branch:
            summary_parts.append(f"- Branch: {project.git_branch}")

        summary = " ".join(summary_parts)

        if project.problems:
            summary += f"\n⚠️ Issues: {', '.join(project.problems[:3])}"

        if project.git_commits:
            summary += f"\n📝 Last commit: {project.git_commits[0]['message']}"

        return summary
