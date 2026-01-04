#!/usr/bin/env python3
"""
PHASE 3: SMART CONTEXT BUILDER
Builds different contexts based on user's current activity
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("vidurai.project_brain.context_builder")


class ContextBuilder:
    """Build intelligent context based on current activity"""

    def __init__(self, scanner, error_watcher):
        self.scanner = scanner
        self.error_watcher = error_watcher
        self.max_tokens = 2000  # Keep context concise

    def build_context(self, trigger_type: str = "manual", user_prompt: str = "") -> Dict:
        """
        Build context based on what user is doing:
        - If recent error: Focus on debugging
        - If documentation files open: Focus on documentation
        - If test files mentioned: Focus on testing
        - Otherwise: General project context
        """
        # Auto-switch to current project
        current_project = self.scanner.auto_switch_context()

        # Get recent error
        recent_error = self.error_watcher.get_last_error()

        # Detect user intent from prompt
        intent = self.detect_user_intent(user_prompt, recent_error)

        context = {
            "intent": intent,
            "timestamp": datetime.now().isoformat(),
            "trigger": trigger_type
        }

        # Add project info
        if current_project:
            context["project"] = {
                "name": current_project.name,
                "version": current_project.version,
                "type": current_project.type,
                "language": current_project.language,
                "branch": current_project.git_branch,
                "problems": current_project.problems
            }

            # Add recent commits
            if current_project.git_commits:
                context["recent_activity"] = {
                    "last_commit": current_project.git_commits[0],
                    "recent_commits": current_project.git_commits[:3]
                }

        # Add error context if debugging
        if intent == "debugging" and recent_error:
            context["debugging"] = {
                "error_type": recent_error.error_type,
                "occurred": recent_error.timestamp.isoformat(),
                "command": recent_error.command,
                "affected_files": recent_error.affected_files[:5],
                "recent_changes": recent_error.recent_changes[:3],
                "possible_cause": self.analyze_error_cause(recent_error)
            }

        # Add structure for documentation
        elif intent == "documentation" and current_project:
            context["documentation"] = {
                "readme_exists": (current_project.path / "README.md").exists(),
                "docs_dir_exists": (current_project.path / "docs").exists(),
                "needs_update": "README may be outdated" in current_project.problems
            }

        # Add testing info
        elif intent == "testing" and current_project:
            context["testing"] = self._get_testing_info(current_project)

        return context

    def detect_user_intent(self, user_prompt: str, recent_error=None) -> str:
        """
        Based on recent activity, guess what user needs:
        - Recent error → Debugging help
        - "test" in prompt → Testing
        - "doc" in prompt → Documentation
        - "add", "create", "new" → Feature development
        - "refactor", "clean" → Refactoring
        """
        prompt_lower = user_prompt.lower()

        # Check for recent error
        if recent_error:
            time_since_error = (datetime.now() - recent_error.timestamp).seconds
            if time_since_error < 300:  # Within 5 minutes
                return "debugging"

        # Check prompt keywords
        if any(word in prompt_lower for word in ['error', 'bug', 'fix', 'broken', 'fail', 'debug']):
            return "debugging"

        if any(word in prompt_lower for word in ['test', 'testing', 'pytest', 'jest', 'unittest']):
            return "testing"

        if any(word in prompt_lower for word in ['doc', 'documentation', 'readme', 'guide']):
            return "documentation"

        if any(word in prompt_lower for word in ['add', 'create', 'new', 'feature', 'implement']):
            return "feature_development"

        if any(word in prompt_lower for word in ['refactor', 'clean', 'improve', 'optimize']):
            return "refactoring"

        return "general"

    def analyze_error_cause(self, error_ctx) -> str:
        """Analyze possible cause of error"""
        if error_ctx.error_type == "Import Error":
            return "Missing package - likely not installed in virtual environment"

        elif error_ctx.error_type == "Module Not Found":
            return "Missing npm package - may need to run npm install"

        elif error_ctx.error_type == "Syntax Error":
            return "Code syntax issue in one of the affected files"

        elif error_ctx.error_type == "Test Failure":
            if error_ctx.recent_changes:
                files = ', '.join(c['file'] for c in error_ctx.recent_changes[:2])
                return f"Recent changes may have broken tests: {files}"
            return "Test expectations may be outdated"

        elif error_ctx.error_type == "Python Runtime Error":
            return "Runtime issue - check variable types and None values"

        else:
            return "Check error details and recent changes"

    def _get_testing_info(self, project) -> Dict:
        """Get information about testing setup"""
        info = {}

        # Check for test directories
        test_dirs = [
            project.path / "tests",
            project.path / "test",
            project.path / "__tests__",
        ]
        info["test_dir"] = any(d.exists() for d in test_dirs)

        # Check for test configuration
        if project.type == "python":
            info["framework"] = "pytest" if (project.path / "pytest.ini").exists() else "unittest"
        elif project.type == "node":
            info["framework"] = "jest" if (project.path / "jest.config.js").exists() else "unknown"

        return info

    def format_context(self, context: Dict, platform: str = "chatgpt_web") -> str:
        """
        Format context for specific platform:
        - 'claude_code': Technical, detailed
        - 'chatgpt_web': Concise, error-focused
        - 'terminal': Brief summary
        """
        if platform == "terminal":
            return self._format_terminal(context)
        elif platform == "claude_code":
            return self._format_claude(context)
        else:
            return self._format_web(context)

    def _format_terminal(self, context: Dict) -> str:
        """Brief terminal output"""
        lines = []

        if "project" in context:
            proj = context["project"]
            parts = [proj["name"]]
            if proj.get("version"):
                parts.append(f"v{proj['version']}")
            if proj.get("type"):
                parts.append(f"({proj['type']})")

            lines.append(" ".join(parts))

            if proj.get("branch"):
                lines.append(f"Branch: {proj['branch']}")

        if context.get("intent") == "debugging" and "debugging" in context:
            debug = context["debugging"]
            lines.append(f"\n🐛 {debug['error_type']}")
            if debug.get("command"):
                lines.append(f"Command: {debug['command']}")

        return "\n".join(lines)

    def _format_claude(self, context: Dict) -> str:
        """Detailed technical context for Claude Code"""
        lines = []

        # Header
        lines.append("# Project Context\n")

        # Project info
        if "project" in context:
            proj = context["project"]
            lines.append(f"**Project:** {proj['name']}")
            if proj.get("version"):
                lines.append(f"**Version:** {proj['version']}")
            if proj.get("type"):
                lines.append(f"**Type:** {proj['type']}")
            if proj.get("language"):
                lines.append(f"**Language:** {proj['language']}")
            if proj.get("branch"):
                lines.append(f"**Branch:** {proj['branch']}")

            if proj.get("problems"):
                lines.append(f"\n**Issues:**")
                for problem in proj["problems"]:
                    lines.append(f"- {problem}")

            lines.append("")

        # Intent-specific context
        intent = context.get("intent", "general")
        lines.append(f"## Current Task: {intent.replace('_', ' ').title()}\n")

        # Debugging context
        if intent == "debugging" and "debugging" in context:
            debug = context["debugging"]
            lines.append(f"### Error: {debug['error_type']}\n")
            lines.append(f"**Command:** `{debug.get('command', 'unknown')}`")

            if debug.get("affected_files"):
                lines.append(f"\n**Affected Files:**")
                for file in debug["affected_files"]:
                    lines.append(f"- `{file}`")

            if debug.get("recent_changes"):
                lines.append(f"\n**Recent Changes:**")
                for change in debug["recent_changes"]:
                    lines.append(f"- {change['status']} `{change['file']}`")

            if debug.get("possible_cause"):
                lines.append(f"\n**Likely Cause:** {debug['possible_cause']}")

            lines.append("")

        # Recent activity
        if "recent_activity" in context:
            activity = context["recent_activity"]
            lines.append("### Recent Activity\n")
            last = activity["last_commit"]
            lines.append(f"**Last Commit:** {last['message']} ({last['when']})")
            lines.append("")

        return "\n".join(lines)

    def _format_web(self, context: Dict) -> str:
        """Concise format for web AI tools"""
        lines = []

        # Project header
        if "project" in context:
            proj = context["project"]
            header_parts = [f"**PROJECT:** {proj['name']}"]
            if proj.get("version"):
                header_parts.append(f"v{proj['version']}")
            if proj.get("type"):
                header_parts.append(f"({proj['type']})")

            lines.append(" ".join(header_parts))

            if proj.get("branch"):
                lines.append(f"**BRANCH:** {proj['branch']}")

            lines.append("")

        # Intent
        intent = context.get("intent", "general")

        if intent == "debugging" and "debugging" in context:
            # Use error watcher's detailed formatting
            recent_error = self.error_watcher.get_last_error()
            if recent_error:
                return self.error_watcher.format_for_debugging(recent_error)

        elif intent == "documentation" and "documentation" in context:
            lines.append("**TASK:** Documentation Update")
            doc = context["documentation"]
            if doc.get("needs_update"):
                lines.append("⚠️ README may be outdated")

        elif intent == "testing":
            lines.append("**TASK:** Testing")
            if "testing" in context:
                test = context["testing"]
                if test.get("framework"):
                    lines.append(f"**Framework:** {test['framework']}")

        else:
            lines.append(f"**TASK:** {intent.replace('_', ' ').title()}")

        # Recent commits
        if "recent_activity" in context:
            activity = context["recent_activity"]
            lines.append(f"\n**RECENT:** {activity['last_commit']['message']}")

        # Problems
        if "project" in context and context["project"].get("problems"):
            lines.append(f"\n**ISSUES:**")
            for problem in context["project"]["problems"][:3]:
                lines.append(f"- {problem}")

        return "\n".join(lines)

    def build_quick_context(self) -> str:
        """Build a quick one-liner context"""
        current_project = self.scanner.current_project
        recent_error = self.error_watcher.get_last_error()

        if recent_error:
            time_since = (datetime.now() - recent_error.timestamp).seconds
            if time_since < 60:
                return f"🐛 {recent_error.error_type} just occurred in {current_project.name if current_project else 'current project'}"

        if current_project:
            return f"📂 Working on {current_project.name} ({current_project.type or 'unknown type'})"

        return "📂 No project context available"

    def estimate_token_count(self, text: str) -> int:
        """Rough estimate of token count (1 token ≈ 4 chars)"""
        return len(text) // 4
