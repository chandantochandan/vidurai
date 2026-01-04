"""
The Human-AI Whisperer
Makes AI conversations feel like talking to a senior dev who knows everything

Philosophy: Not data dumps - but conversation enhancement
Goal: Make users say "WOW, how did it know that?"
"""

import re
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from collections import defaultdict, deque
import logging

logger = logging.getLogger("vidurai.whisperer")


class HumanAIWhisperer:
    """
    Not just context - but CONVERSATION ENHANCEMENT
    Makes every AI interaction feel magical
    """

    def __init__(self):
        self.conversation_memory = deque(maxlen=50)
        self.user_patterns = defaultdict(list)
        self.project_understanding = {}
        self.wow_moments = []
        self.frustration_level = "neutral"

        logger.info("🎭 Human-AI Whisperer initialized")

    def create_wow_context(self, user_input: str, recent_activity: Dict) -> str:
        """
        Create context that makes users say "WOW, that's smart!"

        Instead of:
        [FILES: auth.py, server.py]

        We create:
        💡 Hey! I notice you're debugging that OAuth issue from 2 hours ago.
        The error started after you changed port 8080→3000 in server.py but
        forgot docker-compose.yml. Want me to focus on that?

        Returns human-friendly, conversational context
        """
        logger.info(f"🎯 Creating wow context for: '{user_input[:50]}...'")

        # Step 1: Understand the REAL question behind the question
        real_need = self.decode_human_frustration(user_input)
        logger.info(f"🧠 Decoded need: {real_need['real_need']} (emotion: {real_need['emotion']})")

        # Step 2: Connect the dots they didn't mention
        hidden_connections = self.find_brilliant_connections(real_need, recent_activity)
        logger.info(f"🔍 Found {len(hidden_connections)} brilliant connections")

        # Step 3: Format as friendly conversation starter
        context = self.format_as_friendly_whisper(real_need, hidden_connections, recent_activity)

        logger.info(f"✨ Wow context created: {len(context)} chars")
        return context

    def decode_human_frustration(self, user_input: str) -> Dict[str, Any]:
        """
        Humans say "it's broken" but mean specific things

        Decode what they REALLY need:
        - "not working" = needs diagnosis
        - "why" = needs explanation
        - "how to" = needs guidance
        - "continue" = needs memory recall
        """
        user_lower = user_input.lower()

        # Panic patterns (high emotion)
        if any(word in user_lower for word in ['broken', 'wtf', 'fuck', 'damn', 'nothing works', '!!!', 'help!!!']):
            return {
                "real_need": "error_diagnosis",
                "emotion": "panicked",
                "response_style": "calm_rescuer",
                "urgency": "high"
            }

        # Frustration patterns
        if any(word in user_lower for word in ['not working', 'failed', 'error', 'broken', 'doesn\'t work']):
            return {
                "real_need": "error_diagnosis",
                "emotion": "frustrated",
                "response_style": "calm_helpful",
                "urgency": "medium"
            }

        # Confusion patterns
        if any(word in user_lower for word in ['why', 'how come', 'doesn\'t make sense', 'confused', 'understand']):
            return {
                "real_need": "explanation",
                "emotion": "confused",
                "response_style": "patient_teacher",
                "urgency": "low"
            }

        # Learning patterns
        if any(word in user_lower for word in ['how do i', 'how to', 'implement', 'create', 'build', 'make']):
            return {
                "real_need": "guidance",
                "emotion": "curious",
                "response_style": "encouraging_mentor",
                "urgency": "low"
            }

        # Continuation patterns
        if any(word in user_lower for word in ['continue', 'where was i', 'what was i', 'yesterday', 'last time', 'before']):
            return {
                "real_need": "memory_recall",
                "emotion": "returning",
                "response_style": "helpful_assistant",
                "urgency": "medium"
            }

        # Review patterns
        if any(word in user_lower for word in ['check', 'review', 'look at', 'is this right', 'correct', 'validate']):
            return {
                "real_need": "validation",
                "emotion": "uncertain",
                "response_style": "supportive_reviewer",
                "urgency": "low"
            }

        # Default
        return {
            "real_need": "general_help",
            "emotion": "neutral",
            "response_style": "friendly_helper",
            "urgency": "low"
        }

    def find_brilliant_connections(self, real_need: Dict, activity: Dict) -> List[Dict[str, Any]]:
        """
        Find connections that will make the user think "WOW, how did it know?"

        Examples:
        - "This error started 23 minutes ago when you changed that import"
        - "Similar issue last week - here's what worked"
        - "You were at line 47 in auth.py when you stopped"
        - "You have a TODO comment about this exact thing"
        """
        connections = []

        if real_need["real_need"] == "error_diagnosis":
            # The "Breaking Point" connection
            breaking_point = self.find_when_it_broke(activity)
            if breaking_point:
                connections.append({
                    "type": "breaking_point",
                    "insight": breaking_point,
                    "wow_factor": "I know EXACTLY when it broke"
                })

            # The "Déjà Vu" connection
            similar_error = self.find_similar_past_errors(activity)
            if similar_error:
                connections.append({
                    "type": "pattern_match",
                    "insight": similar_error,
                    "wow_factor": "This happened before, here's what worked"
                })

            # The "Missing Piece" connection
            missing_config = self.find_missing_config(activity)
            if missing_config:
                connections.append({
                    "type": "missing_config",
                    "insight": missing_config,
                    "wow_factor": "You changed code but forgot config"
                })

        elif real_need["real_need"] == "memory_recall":
            # The "You Were Here" connection
            last_progress = self.find_last_progress_point(activity)
            if last_progress:
                connections.append({
                    "type": "last_progress",
                    "insight": last_progress,
                    "wow_factor": "You were HERE when you stopped"
                })

            # The "Your Own Notes" connection
            todos = self.find_todo_comments(activity)
            if todos:
                connections.append({
                    "type": "todos",
                    "insight": todos,
                    "wow_factor": "You left yourself these notes"
                })

        elif real_need["real_need"] == "guidance":
            # The "You've Done This Before" connection
            own_examples = self.find_similar_implementations(activity)
            if own_examples:
                connections.append({
                    "type": "own_examples",
                    "insight": own_examples,
                    "wow_factor": "You did something similar here"
                })

        return connections

    def find_when_it_broke(self, activity: Dict) -> Optional[Dict]:
        """
        Find the EXACT moment things broke

        Example:
        "The error started 23 minutes ago when you changed the import statement in auth.py"
        """
        recent_errors = activity.get('recent_errors', [])
        recent_changes = activity.get('recent_files_changed', [])

        if not recent_errors:
            return None

        # Get first error
        first_error = recent_errors[0]
        error_time = first_error.get('time', time.time())

        # Find the change right before the error
        for change in recent_changes:
            change_time = change.get('time', 0)
            if change_time < error_time and (error_time - change_time) < 300:  # Within 5 minutes
                time_ago = self.humanize_time(error_time - change_time)
                return {
                    "time_ago": time_ago,
                    "change_description": f"you modified {change.get('file', 'a file')}",
                    "file": change.get('file', ''),
                    "error_type": self.extract_error_type(first_error.get('output', ''))
                }

        # Fallback
        time_ago = self.humanize_time(time.time() - error_time)
        return {
            "time_ago": time_ago,
            "change_description": "something changed",
            "error_type": self.extract_error_type(first_error.get('output', ''))
        }

    def find_similar_past_errors(self, activity: Dict) -> Optional[Dict]:
        """
        Find if this error happened before

        Example:
        "Similar ImportError on Nov 15 - you fixed it by adding the package to requirements.txt"
        """
        # This would need persistent storage
        # For now, return None (TODO: implement with database)
        return None

    def find_missing_config(self, activity: Dict) -> Optional[Dict]:
        """
        Detect when user changed code but forgot config

        Example:
        "You changed the port in server.py but docker-compose.yml still has 8080"
        """
        recent_changes = activity.get('recent_files_changed', [])

        # Look for code + config file patterns
        code_files = [f for f in recent_changes if f.get('file', '').endswith(('.py', '.js', '.ts'))]
        config_files = [f for f in recent_changes if 'config' in f.get('file', '').lower() or
                       f.get('file', '') in ['docker-compose.yml', '.env', 'package.json']]

        if code_files and not config_files:
            # Code changed but no config change
            return {
                "changed_code": code_files[0].get('file', ''),
                "missing_config": "configuration file",
                "hint": "Did you update the config to match?"
            }

        return None

    def find_last_progress_point(self, activity: Dict) -> Optional[Dict]:
        """
        Find where user stopped working

        Example:
        "You were working on line 47 in auth.py, implementing the token refresh logic"
        """
        recent_changes = activity.get('recent_files_changed', [])

        if recent_changes:
            last_file = recent_changes[-1]
            return {
                "file": last_file.get('file', ''),
                "time_ago": self.humanize_time(time.time() - last_file.get('time', time.time())),
                "context": "working on it"
            }

        return None

    def find_todo_comments(self, activity: Dict) -> Optional[Dict]:
        """
        Find TODO comments from recent files

        Example:
        "Your TODO: 'Add error handling for token expiry'"
        """
        # This would need file content scanning
        # For now, return placeholder
        return {
            "todos": ["Add error handling", "Update tests", "Fix edge cases"],
            "found_in": ["auth.py", "server.py"]
        }

    def find_similar_implementations(self, activity: Dict) -> Optional[Dict]:
        """
        Find similar code patterns from user's own codebase

        Example:
        "You have a similar OAuth implementation in old_project/auth.py"
        """
        # This would need code similarity analysis
        # For now, return None
        return None

    def format_as_friendly_whisper(self, real_need: Dict, connections: List, activity: Dict) -> str:
        """
        Format context as a friendly, conversational whisper

        NOT: [FILES: auth.py] [ERROR: ImportError] [TIME: 10:23]
        BUT: 💡 About that ImportError from 5 minutes ago - you changed auth.py but might have missed updating imports
        """
        # Choose emotional tone
        emotion_prefixes = {
            "panicked": "🚨 Don't worry! ",
            "frustrated": "💡 Quick heads up - ",
            "confused": "🤔 Let me clarify - ",
            "curious": "📚 Building on what you know - ",
            "returning": "👋 Welcome back! ",
            "uncertain": "✅ For context - ",
            "neutral": "ℹ️  FYI - "
        }

        prefix = emotion_prefixes.get(real_need["emotion"], "ℹ️  ")

        # NEW: Add SQL hints if available
        sql_hints = activity.get('sql_hints', [])
        if sql_hints:
            sql_hint_text = self._format_sql_hints(sql_hints)
            context_parts = [sql_hint_text]
        else:
            context_parts = []

        # Build natural language from connections
        for connection in connections:
            if connection["type"] == "breaking_point":
                insight = connection["insight"]
                context_parts.append(
                    f"The {insight.get('error_type', 'issue')} started {insight['time_ago']} "
                    f"when {insight['change_description']}."
                )

            elif connection["type"] == "pattern_match":
                insight = connection["insight"]
                context_parts.append(
                    f"Similar issue on {insight['date']}: {insight['solution']}."
                )

            elif connection["type"] == "missing_config":
                insight = connection["insight"]
                context_parts.append(
                    f"You changed {insight['changed_code']} but "
                    f"the {insight['missing_config']} might need updating too."
                )

            elif connection["type"] == "last_progress":
                insight = connection["insight"]
                context_parts.append(
                    f"You were working on {insight['file']} {insight['time_ago']}."
                )

            elif connection["type"] == "todos":
                insight = connection["insight"]
                if insight.get("todos"):
                    todos_str = ", ".join(f'"{t}"' for t in insight["todos"][:2])
                    context_parts.append(f"Your TODOs: {todos_str}")

            elif connection["type"] == "own_examples":
                insight = connection["insight"]
                context_parts.append(
                    f"You have similar code in {insight['file']}"
                )

        # Combine into natural paragraph
        if context_parts:
            context = prefix + " ".join(context_parts)
        else:
            # Minimal but helpful fallback
            project_name = self.get_project_name(activity)
            context = f"{prefix}Working on {project_name}."

        # Add invisible metadata for AI
        context += self.add_invisible_metadata(real_need, connections, activity)

        return context

    def _format_sql_hints(self, hints: List[Dict]) -> str:
        """
        Format SQL memory hints as natural language

        Args:
            hints: List of memory dicts from SQL database

        Returns:
            Formatted string like "From past experience: Fixed auth bug (3d ago); Similar error in login.py (7d ago)"
        """
        if not hints:
            return ""

        from datetime import datetime

        formatted_hints = []
        for hint in hints[:3]:  # Max 3
            gist = hint.get('gist', 'Unknown')

            # Calculate age
            try:
                created_at = datetime.fromisoformat(hint['created_at'])
                age = datetime.now() - created_at

                if age.days > 0:
                    age_text = f"{age.days}d ago"
                elif age.seconds >= 3600:
                    hours = age.seconds // 3600
                    age_text = f"{hours}h ago"
                else:
                    mins = age.seconds // 60
                    age_text = f"{mins}m ago"

                formatted_hints.append(f"{gist} ({age_text})")
            except:
                formatted_hints.append(gist)

        if formatted_hints:
            return "📜 From past experience: " + "; ".join(formatted_hints)
        return ""

    def add_invisible_metadata(self, real_need: Dict, connections: List, activity: Dict) -> str:
        """
        Add metadata that AI needs but human doesn't see clutter

        Format as HTML comment (invisible in most AI interfaces)
        """
        metadata = {
            "user_state": real_need["emotion"],
            "response_style": real_need["response_style"],
            "urgency": real_need["urgency"],
            "connection_count": len(connections),
            "working_directory": activity.get('current_project', 'unknown')
        }

        # Format as invisible hint
        return f"\n<!-- Vidurai: {json.dumps(metadata)} -->"

    def humanize_time(self, seconds: float) -> str:
        """
        Convert seconds to human-friendly time

        60 → "1 minute"
        3600 → "1 hour"
        7200 → "2 hours"
        """
        if seconds < 60:
            return f"{int(seconds)} seconds"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        elif seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours > 1 else ''}"
        else:
            days = int(seconds / 86400)
            return f"{days} day{'s' if days > 1 else ''}"

    def extract_error_type(self, error_output: str) -> str:
        """
        Extract friendly error type from stack trace

        "ImportError: No module named 'foo'" → "ImportError"
        "TypeError: cannot concat str and int" → "TypeError"
        """
        # Common Python errors
        error_patterns = [
            'ImportError', 'ModuleNotFoundError', 'TypeError', 'ValueError',
            'AttributeError', 'KeyError', 'IndexError', 'FileNotFoundError',
            'PermissionError', 'RuntimeError', 'SyntaxError'
        ]

        for error_type in error_patterns:
            if error_type in error_output:
                return error_type

        # Fallback
        return "error"

    def get_project_name(self, activity: Dict) -> str:
        """Get friendly project name"""
        current_project = activity.get('current_project', '')
        if current_project:
            return Path(current_project).name
        return "your project"

    def track_wow_moment(self, user_reaction: str):
        """
        Track when users are impressed
        Learn what creates 'wow' moments
        """
        wow_indicators = [
            "wow", "amazing", "how did you know", "that's exactly right",
            "perfect", "yes that's it", "brilliant", "genius", "awesome"
        ]

        user_lower = user_reaction.lower()
        for indicator in wow_indicators:
            if indicator in user_lower:
                self.wow_moments.append({
                    "time": datetime.now(),
                    "trigger": indicator,
                    "reaction": user_reaction[:100]
                })
                logger.info(f"🌟 WOW MOMENT DETECTED: {indicator}")
                break

    def get_wow_statistics(self) -> Dict[str, Any]:
        """Get wow moment statistics"""
        return {
            "total_wow_moments": len(self.wow_moments),
            "recent_wows": len([w for w in self.wow_moments
                               if (datetime.now() - w["time"]).total_seconds() < 86400]),
            "top_triggers": self.get_top_wow_triggers()
        }

    def get_top_wow_triggers(self) -> List[str]:
        """Get most common wow triggers"""
        if not self.wow_moments:
            return []

        trigger_counts = defaultdict(int)
        for wow in self.wow_moments:
            trigger_counts[wow["trigger"]] += 1

        return sorted(trigger_counts.items(), key=lambda x: x[1], reverse=True)[:5]
