#!/usr/bin/env python3
"""
PERSISTENT STORAGE
Stores project data and errors as JSON files for easy debugging
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger("vidurai.project_brain.memory_store")


class MemoryStore:
    """JSON-based persistent storage for project brain"""

    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            self.storage_dir = Path.home() / ".vidurai" / "project_brain"
        else:
            self.storage_dir = storage_dir

        # Create storage directories
        self.projects_dir = self.storage_dir / "projects"
        self.errors_dir = self.storage_dir / "errors"

        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.errors_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"💾 Memory store initialized at: {self.storage_dir}")

    def save_projects(self, projects: Dict):
        """Save all projects to JSON files"""
        try:
            # Save individual project files
            for path_str, project in projects.items():
                # Create safe filename from path
                safe_name = self._path_to_filename(path_str)
                file_path = self.projects_dir / f"{safe_name}.json"

                # Save project data
                data = project.to_dict()
                file_path.write_text(json.dumps(data, indent=2))

            # Save index file
            index = {
                "last_updated": datetime.now().isoformat(),
                "project_count": len(projects),
                "projects": [
                    {
                        "name": p.name,
                        "path": str(p.path),
                        "type": p.type,
                        "version": p.version
                    }
                    for p in projects.values()
                ]
            }

            index_file = self.storage_dir / "index.json"
            index_file.write_text(json.dumps(index, indent=2))

            logger.debug(f"💾 Saved {len(projects)} projects")

        except Exception as e:
            logger.error(f"Failed to save projects: {e}")

    def load_projects(self) -> Dict:
        """Load all projects from JSON files"""
        projects = {}

        try:
            # Load from individual project files
            for file_path in self.projects_dir.glob("*.json"):
                try:
                    data = json.loads(file_path.read_text())

                    # Import here to avoid circular dependency
                    from .scanner import ProjectInfo

                    # Reconstruct ProjectInfo object
                    project = ProjectInfo(data["path"])
                    project.name = data.get("name", project.name)
                    project.type = data.get("type")
                    project.version = data.get("version")
                    project.language = data.get("language")
                    project.git_branch = data.get("git_branch")
                    project.git_commits = data.get("git_commits", [])
                    project.problems = data.get("problems", [])

                    if data.get("last_scanned"):
                        project.last_scanned = datetime.fromisoformat(data["last_scanned"])

                    projects[data["path"]] = project

                except Exception as e:
                    logger.error(f"Failed to load project from {file_path}: {e}")

            logger.info(f"💾 Loaded {len(projects)} projects from storage")

        except Exception as e:
            logger.error(f"Failed to load projects: {e}")

        return projects

    def save_error(self, error_context):
        """Save an error to storage"""
        try:
            # Create filename with timestamp
            timestamp = error_context.timestamp.strftime("%Y%m%d_%H%M%S")
            error_type = error_context.error_type.replace(" ", "_").lower()
            filename = f"{timestamp}_{error_type}.json"

            file_path = self.errors_dir / filename

            # Save error data
            data = error_context.to_dict()
            file_path.write_text(json.dumps(data, indent=2))

            logger.debug(f"💾 Saved error: {filename}")

            # Keep only last 50 errors (cleanup old ones)
            self._cleanup_old_errors(max_errors=50)

        except Exception as e:
            logger.error(f"Failed to save error: {e}")

    def load_errors(self, limit: int = 10) -> List:
        """Load recent errors from storage"""
        errors = []

        try:
            # Get all error files sorted by modification time (newest first)
            error_files = sorted(
                self.errors_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Load the most recent ones
            for file_path in error_files[:limit]:
                try:
                    data = json.loads(file_path.read_text())

                    # Import here to avoid circular dependency
                    from .error_watcher import ErrorContext

                    # Reconstruct ErrorContext object
                    error_ctx = ErrorContext(
                        data.get("error_text", ""),
                        data.get("command")
                    )
                    error_ctx.error_type = data.get("error_type", "Unknown Error")
                    error_ctx.directory = data.get("directory", "")
                    error_ctx.timestamp = datetime.fromisoformat(data["timestamp"])
                    error_ctx.recent_changes = data.get("recent_changes", [])
                    error_ctx.git_branch = data.get("git_branch")
                    error_ctx.affected_files = data.get("affected_files", [])

                    errors.append(error_ctx)

                except Exception as e:
                    logger.error(f"Failed to load error from {file_path}: {e}")

            logger.debug(f"💾 Loaded {len(errors)} errors from storage")

        except Exception as e:
            logger.error(f"Failed to load errors: {e}")

        return errors

    def _cleanup_old_errors(self, max_errors: int = 50):
        """Remove old error files to save space"""
        try:
            error_files = sorted(
                self.errors_dir.glob("*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )

            # Remove files beyond max_errors
            for file_path in error_files[max_errors:]:
                file_path.unlink()
                logger.debug(f"🧹 Removed old error: {file_path.name}")

        except Exception as e:
            logger.error(f"Failed to cleanup old errors: {e}")

    def get_project_by_path(self, path: str) -> Optional[dict]:
        """Get a specific project by path"""
        safe_name = self._path_to_filename(path)
        file_path = self.projects_dir / f"{safe_name}.json"

        if file_path.exists():
            try:
                return json.loads(file_path.read_text())
            except Exception as e:
                logger.error(f"Failed to load project {path}: {e}")

        return None

    def _path_to_filename(self, path: str) -> str:
        """Convert file path to safe filename"""
        # Replace path separators with underscores
        safe = path.replace("/", "_").replace("\\", "_")
        # Remove leading underscores (from absolute paths)
        safe = safe.lstrip("_")
        # Limit length
        if len(safe) > 200:
            safe = safe[:200]
        return safe

    def get_storage_stats(self) -> dict:
        """Get statistics about stored data"""
        try:
            project_count = len(list(self.projects_dir.glob("*.json")))
            error_count = len(list(self.errors_dir.glob("*.json")))

            # Calculate total size
            total_size = sum(
                f.stat().st_size
                for f in self.storage_dir.rglob("*.json")
            )

            return {
                "storage_dir": str(self.storage_dir),
                "projects": project_count,
                "errors": error_count,
                "total_size_bytes": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2)
            }

        except Exception as e:
            logger.error(f"Failed to get storage stats: {e}")
            return {}

    def clear_all(self):
        """Clear all stored data (use with caution!)"""
        try:
            # Remove all project files
            for file_path in self.projects_dir.glob("*.json"):
                file_path.unlink()

            # Remove all error files
            for file_path in self.errors_dir.glob("*.json"):
                file_path.unlink()

            # Remove index
            index_file = self.storage_dir / "index.json"
            if index_file.exists():
                index_file.unlink()

            logger.warning("🧹 Cleared all stored data")

        except Exception as e:
            logger.error(f"Failed to clear storage: {e}")

    def export_to_json(self, output_file: Path):
        """Export all data to a single JSON file"""
        try:
            # Load index
            index_file = self.storage_dir / "index.json"
            index = {}
            if index_file.exists():
                index = json.loads(index_file.read_text())

            # Load all projects
            projects = []
            for file_path in self.projects_dir.glob("*.json"):
                try:
                    projects.append(json.loads(file_path.read_text()))
                except:
                    pass

            # Load recent errors
            errors = []
            for file_path in list(self.errors_dir.glob("*.json"))[:20]:
                try:
                    errors.append(json.loads(file_path.read_text()))
                except:
                    pass

            # Combine into export
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "index": index,
                "projects": projects,
                "recent_errors": errors
            }

            output_file.write_text(json.dumps(export_data, indent=2))
            logger.info(f"📦 Exported data to: {output_file}")

        except Exception as e:
            logger.error(f"Failed to export data: {e}")
