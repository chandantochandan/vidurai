"""
Vidurai Context Mediator
The intelligence that understands what both human and AI need
Philosophy: विस्मृति भी विद्या है (Forgetting too is knowledge)

This is the philosophical core of Vidurai:
- Understands what the user is doing (state detection)
- Predicts what they forgot to mention (context awareness)
- Knows what will confuse the AI (noise filtering)
- Formats optimally for each AI platform (adaptation)
- Compresses intelligently when needed (RL compression)
"""

import os
import re
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import logging

from .human_ai_whisperer import HumanAIWhisperer

logger = logging.getLogger("vidurai.mediator")


class ContextMediator:
    """
    Mediates between human memory needs and AI comprehension limits

    The bridge between:
    - Human: Who forgets important details but over-explains
    - AI: Who needs precise context but gets confused by noise
    """

    def __init__(self, audience: Optional[str] = None):
        """
        Initialize ContextMediator

        Args:
            audience: Optional audience perspective for multi-audience gists (Phase 5)
                     Options: 'developer', 'ai', 'manager', 'personal'
        """
        self.context_window = deque(maxlen=100)  # Rolling window of events
        self.user_state = 'unknown'
        self.last_state_detection = 0
        self.state_detection_interval = 5.0  # Re-detect every 5 seconds

        self.ai_platform = None
        self.max_context_size = 2000  # tokens/chars

        # User activity tracking
        self.recent_errors = []
        self.recent_files_changed = []
        self.recent_commands = []

        # Noise patterns (what to exclude)
        self.noise_patterns = self.build_noise_patterns()

        # NEW: Human-AI Whisperer for WOW moments
        self.whisperer = HumanAIWhisperer()

        # NEW: Memory bridge for SQL hints (fail-safe)
        # Phase 5: Support audience parameter
        self.memory_bridge = None
        self.audience = audience  # Phase 5: Store audience preference
        self._init_memory_bridge(audience=audience)

        audience_label = f" with {audience} perspective" if audience else ""
        logger.info(f"🧠 Context Mediator initialized{audience_label} with Human-AI Whisperer")

    def _init_memory_bridge(self, audience: Optional[str] = None):
        """
        Initialize memory bridge for SQL hints (fail-safe)

        If SQL database is unavailable, daemon still works normally

        Args:
            audience: Optional audience perspective for multi-audience gists (Phase 5)
        """
        try:
            # Try to import and initialize
            from .memory_bridge import MemoryBridge
            from vidurai.storage.database import MemoryDatabase

            # Initialize database
            db = MemoryDatabase()

            # Initialize bridge with conservative limits
            # Phase 5: Support audience parameter
            self.memory_bridge = MemoryBridge(
                db=db,
                max_memories=3,  # Max 3 hints
                min_salience="HIGH",  # Only HIGH/CRITICAL
                audience=audience  # Phase 5: Multi-Audience
            )

            audience_label = f" ({audience} perspective)" if audience else ""
            logger.info(f"✨ Memory bridge initialized{audience_label} (SQL hints enabled)")

        except ImportError as e:
            logger.warning(f"Memory bridge unavailable (import error): {e}")
            self.memory_bridge = None
        except Exception as e:
            logger.warning(f"Memory bridge initialization failed: {e}")
            self.memory_bridge = None
            # Daemon continues without SQL hints

    def build_noise_patterns(self) -> List[re.Pattern]:
        """
        Build patterns for identifying noise
        These are things that confuse AI without adding value
        """
        patterns = [
            # npm/yarn install spam
            re.compile(r'npm (WARN|info|notice|verb)'),
            re.compile(r'yarn install v\d+\.\d+'),
            re.compile(r'added \d+ packages?'),

            # Successful test outputs (keep only failures)
            re.compile(r'✓ \d+ tests? passed'),
            re.compile(r'All tests passed'),
            re.compile(r'PASS .*\.test\.(js|ts|py)'),

            # Build success messages
            re.compile(r'Build succeeded'),
            re.compile(r'Compiled successfully'),
            re.compile(r'webpack \d+\.\d+\.\d+ compiled'),

            # Git routine messages
            re.compile(r'Already up to date'),
            re.compile(r'On branch \w+'),
            re.compile(r'Your branch is up to date'),

            # Boilerplate warnings
            re.compile(r'DeprecationWarning:'),
            re.compile(r'FutureWarning:'),

            # Empty or meaningless changes
            re.compile(r'^\s*$'),  # Empty lines
            re.compile(r'^#\s*$'),  # Comment lines only
        ]

        return patterns

    def add_event(self, event: Dict[str, Any]):
        """Add event to context window"""
        self.context_window.append({
            'timestamp': time.time(),
            'event': event
        })

        # Extract relevant info for state detection
        event_type = event.get('event', '')

        if event_type == 'file_changed':
            self.recent_files_changed.append({
                'file': event.get('filename', ''),
                'time': time.time(),
                'importance': event.get('context', {}).get('importance', 'medium')
            })

        elif event_type == 'terminal_output':
            output = event.get('output', '')

            # Detect errors
            if any(keyword in output.lower() for keyword in ['error', 'exception', 'failed', 'traceback']):
                self.recent_errors.append({
                    'output': output,
                    'time': time.time()
                })

        elif event_type == 'terminal_command':
            self.recent_commands.append({
                'command': event.get('command', ''),
                'time': time.time()
            })

    def detect_user_state(self) -> str:
        """
        Analyze recent activity to understand what user is doing

        States:
        - 'debugging': Error occurred, searching for solution
        - 'building': Creating new features
        - 'learning': Reading docs, trying examples
        - 'refactoring': Modifying existing code
        - 'confused': Rapid context switches, multiple errors
        - 'idle': No recent activity

        Returns current state
        """
        now = time.time()

        # Check if we need to re-detect
        if now - self.last_state_detection < self.state_detection_interval:
            return self.user_state

        self.last_state_detection = now

        # Clean old events (older than 5 minutes)
        cutoff_time = now - 300
        self.recent_errors = [e for e in self.recent_errors if e['time'] > cutoff_time]
        self.recent_files_changed = [f for f in self.recent_files_changed if f['time'] > cutoff_time]
        self.recent_commands = [c for c in self.recent_commands if c['time'] > cutoff_time]

        # No recent activity
        if not self.recent_files_changed and not self.recent_commands and not self.recent_errors:
            self.user_state = 'idle'
            return self.user_state

        # Recent errors → debugging
        if len(self.recent_errors) > 0:
            # Multiple errors in short time → confused
            if len(self.recent_errors) > 3:
                self.user_state = 'confused'
                logger.info("🤔 User state: CONFUSED (multiple errors)")
                return self.user_state
            else:
                self.user_state = 'debugging'
                logger.info("🐛 User state: DEBUGGING")
                return self.user_state

        # Analyze recent commands
        command_patterns = {
            'learning': ['cat', 'less', 'grep', 'man', 'help', '--help', 'docs'],
            'building': ['mkdir', 'touch', 'create', 'init', 'new'],
            'refactoring': ['mv', 'rename', 'refactor'],
            'debugging': ['pytest', 'test', 'debug', 'gdb', 'pdb'],
        }

        command_scores = defaultdict(int)
        for cmd_entry in self.recent_commands[-10:]:  # Last 10 commands
            cmd = cmd_entry['command'].lower()
            for state, patterns in command_patterns.items():
                if any(pattern in cmd for pattern in patterns):
                    command_scores[state] += 1

        if command_scores:
            detected_state = max(command_scores, key=command_scores.get)
            self.user_state = detected_state
            logger.info(f"📊 User state: {detected_state.upper()} (from commands)")
            return self.user_state

        # Analyze file changes
        if len(self.recent_files_changed) > 10:
            # Lots of changes → building
            self.user_state = 'building'
            logger.info("🏗️  User state: BUILDING (many files changed)")
            return self.user_state
        elif len(self.recent_files_changed) > 0:
            # Few targeted changes → refactoring
            self.user_state = 'refactoring'
            logger.info("♻️  User state: REFACTORING")
            return self.user_state

        # Default
        self.user_state = 'building'
        return self.user_state

    def analyze_prompt_intent(self, prompt: str) -> str:
        """
        Understand what the user is really asking for

        Intents:
        - 'fix_error': User has a bug
        - 'how_to': User wants to learn
        - 'explain': User needs understanding
        - 'continue': User wants to continue previous work
        - 'review': User wants code review
        - 'implement': User wants to build something
        """
        prompt_lower = prompt.lower()

        # Intent patterns
        intent_patterns = {
            'fix_error': [
                'error', 'bug', 'fix', 'broken', 'not working', 'fails',
                'exception', 'traceback', 'crash', 'issue', 'problem'
            ],
            'how_to': [
                'how to', 'how do i', 'how can i', 'tutorial', 'guide',
                'example', 'show me', 'teach me'
            ],
            'explain': [
                'what is', 'what does', 'why', 'explain', 'understand',
                'clarify', 'what\'s', 'meaning', 'purpose'
            ],
            'continue': [
                'continue', 'keep going', 'next', 'finish', 'complete',
                'as we discussed', 'from before', 'previous'
            ],
            'review': [
                'review', 'check', 'look at', 'feedback', 'opinion',
                'thoughts on', 'critique', 'improve'
            ],
            'implement': [
                'create', 'build', 'make', 'implement', 'add', 'write',
                'develop', 'code', 'generate'
            ]
        }

        # Score each intent
        intent_scores = defaultdict(int)
        for intent, patterns in intent_patterns.items():
            for pattern in patterns:
                if pattern in prompt_lower:
                    intent_scores[intent] += 1

        # Return highest scoring intent
        if intent_scores:
            detected_intent = max(intent_scores, key=intent_scores.get)
            logger.info(f"🎯 Prompt intent: {detected_intent.upper()}")
            return detected_intent

        return 'implement'  # Default

    def get_immediate_context(self, intent: str) -> Dict[str, Any]:
        """
        Get the most immediately relevant context based on intent

        For 'fix_error': Last error, related code
        For 'how_to': Current files, similar examples
        For 'continue': Last work session
        For 'implement': Current project structure
        """
        context = {
            'intent': intent,
            'user_state': self.user_state,
            'immediate_info': []
        }

        if intent == 'fix_error':
            # Include recent errors
            if self.recent_errors:
                context['immediate_info'].append({
                    'type': 'error',
                    'content': self.recent_errors[-1]['output'][:500]  # Last error, truncated
                })

            # Include recently changed files (might be related to error)
            recent_high_importance = [
                f for f in self.recent_files_changed[-5:]
                if f['importance'] == 'high'
            ]
            if recent_high_importance:
                context['immediate_info'].append({
                    'type': 'recent_changes',
                    'files': [f['file'] for f in recent_high_importance]
                })

        elif intent == 'continue':
            # Include last N file changes
            context['immediate_info'].append({
                'type': 'recent_work',
                'files': [f['file'] for f in self.recent_files_changed[-10:]]
            })

        elif intent == 'implement':
            # Include current project structure hints
            files_by_type = defaultdict(list)
            for f in self.recent_files_changed[-20:]:
                ext = Path(f['file']).suffix
                files_by_type[ext].append(f['file'])

            context['immediate_info'].append({
                'type': 'project_structure',
                'file_types': dict(files_by_type)
            })

        return context

    def get_relevant_history(self, intent: str) -> List[Dict[str, Any]]:
        """
        Get relevant historical context based on intent
        Not everything, just what matters
        """
        relevant_events = []

        # Look back through context window
        for entry in list(self.context_window)[-50:]:  # Last 50 events
            event = entry['event']
            event_type = event.get('event', '')

            # For fix_error intent, include errors and related files
            if intent == 'fix_error':
                if event_type == 'terminal_output' and 'error' in event.get('output', '').lower():
                    relevant_events.append(event)
                elif event_type == 'file_changed':
                    relevant_events.append(event)

            # For implement intent, include recent structural changes
            elif intent == 'implement':
                if event_type == 'file_changed' and event.get('context', {}).get('importance') == 'high':
                    relevant_events.append(event)

            # For continue intent, include recent activity
            elif intent == 'continue':
                relevant_events.append(event)

        return relevant_events[-20:]  # Max 20 events

    def get_environment_context(self) -> Dict[str, Any]:
        """
        Get current environment context
        What environment is the user working in?
        """
        return {
            'current_state': self.user_state,
            'active_files_count': len(self.recent_files_changed),
            'recent_errors_count': len(self.recent_errors),
        }

    def identify_noise(self) -> List[str]:
        """
        Identify what NOT to send to AI
        This is the 'forgetting' part of विस्मृति

        Noise includes:
        - Repetitive npm install outputs
        - Unrelated file changes
        - Old errors that were fixed
        - Boilerplate code
        - Successful test outputs
        """
        noise_items = []

        # Check recent events for noise patterns
        for entry in list(self.context_window)[-50:]:
            event = entry['event']

            if event.get('event') == 'terminal_output':
                output = event.get('output', '')

                # Check against noise patterns
                for pattern in self.noise_patterns:
                    if pattern.search(output):
                        noise_items.append(f"Filtered: {output[:50]}...")
                        break

        return noise_items

    def format_for_platform(self, context: Dict, platform: str) -> str:
        """
        Format context optimally for each AI platform

        ChatGPT: Likes structured markdown with clear sections
        Claude: Handles long context well, prefers XML-like tags
        Gemini: Prefers concise bullets
        Perplexity: Likes question-answer format
        """
        if platform in ['ChatGPT', 'Unknown']:
            return self.format_chatgpt(context)
        elif platform == 'Claude':
            return self.format_claude(context)
        elif platform == 'Gemini':
            return self.format_gemini(context)
        elif platform == 'Perplexity':
            return self.format_perplexity(context)
        else:
            return self.format_default(context)

    def format_chatgpt(self, context: Dict) -> str:
        """Format for ChatGPT - structured markdown"""
        parts = ["[VIDURAI CONTEXT]", ""]

        # User state
        state_emoji = {
            'debugging': '🐛',
            'building': '🏗️',
            'learning': '📚',
            'refactoring': '♻️',
            'confused': '🤔',
            'idle': '💤'
        }
        emoji = state_emoji.get(context.get('user_state', 'unknown'), '🔧')
        parts.append(f"**Current Activity:** {emoji} {context.get('user_state', 'unknown').title()}")
        parts.append("")

        # Immediate context
        immediate = context.get('immediate', {})
        if immediate.get('immediate_info'):
            parts.append("**Immediate Context:**")
            for info in immediate['immediate_info']:
                info_type = info.get('type', '').replace('_', ' ').title()
                parts.append(f"- {info_type}")
            parts.append("")

        # Environment
        env = context.get('environment', {})
        parts.append(f"**Files Monitored:** {env.get('active_files_count', 0)}")

        if env.get('recent_errors_count', 0) > 0:
            parts.append(f"**Recent Errors:** {env['recent_errors_count']}")

        parts.append("")
        parts.append("[END CONTEXT]")

        return '\n'.join(parts)

    def format_claude(self, context: Dict) -> str:
        """Format for Claude - XML-like tags"""
        parts = ["<vidurai_context>"]

        state = context.get('user_state', 'unknown')
        parts.append(f'  <activity state="{state}" />')

        env = context.get('environment', {})
        parts.append(f'  <environment files="{env.get("active_files_count", 0)}" errors="{env.get("recent_errors_count", 0)}" />')

        immediate = context.get('immediate', {})
        if immediate.get('immediate_info'):
            parts.append('  <immediate>')
            for info in immediate['immediate_info']:
                info_type = info.get('type', 'info')
                parts.append(f'    <{info_type} />')
            parts.append('  </immediate>')

        parts.append("</vidurai_context>")

        return '\n'.join(parts)

    def format_gemini(self, context: Dict) -> str:
        """Format for Gemini - concise bullets"""
        parts = ["# Vidurai Context"]

        state = context.get('user_state', 'unknown')
        parts.append(f"• Activity: {state.title()}")

        env = context.get('environment', {})
        parts.append(f"• Files: {env.get('active_files_count', 0)} active")

        if env.get('recent_errors_count', 0) > 0:
            parts.append(f"• Errors: {env['recent_errors_count']} recent")

        return '\n'.join(parts)

    def format_perplexity(self, context: Dict) -> str:
        """Format for Perplexity - question-answer style"""
        parts = ["[Context]"]

        state = context.get('user_state', 'unknown')
        parts.append(f"Current task: {state.replace('_', ' ')}")

        env = context.get('environment', {})
        parts.append(f"Workspace: {env.get('active_files_count', 0)} files")

        return ' | '.join(parts)

    def format_default(self, context: Dict) -> str:
        """Default format - simple and universal"""
        state = context.get('user_state', 'unknown')
        env = context.get('environment', {})

        return f"[VIDURAI] {state.upper()} | {env.get('active_files_count', 0)} files"

    def needs_compression(self, formatted: str) -> bool:
        """Check if context needs compression"""
        return len(formatted) > self.max_context_size

    def apply_rl_compression(self, formatted: str) -> str:
        """
        Use RL agent to compress context
        Maintains meaning while reducing tokens

        TODO: Integrate with vidurai's Q-learning agent
        """
        # For now, simple truncation with ellipsis
        if len(formatted) > self.max_context_size:
            return formatted[:self.max_context_size-20] + "\n...(truncated)"
        return formatted

    def prepare_context_for_ai(self, user_prompt: str, ai_platform: str) -> str:
        """
        Prepare optimal context for AI based on:
        1. What the user is asking
        2. What the user forgot to mention
        3. What the AI needs to know
        4. What would confuse the AI (exclude this)

        NOW with WOW moments via Human-AI Whisperer!
        PLUS SQL long-term memory hints!

        Returns formatted context string ready for injection
        """
        # Update user state
        self.detect_user_state()

        # NEW: Get SQL hints (if available)
        sql_hints = []
        if self.memory_bridge:
            try:
                current_error = None
                if self.recent_errors:
                    current_error = self.recent_errors[-1].get('output')

                current_file = None
                if self.recent_files_changed:
                    current_file = self.recent_files_changed[-1].get('file')

                sql_hints = self.memory_bridge.get_relevant_hints(
                    current_project=self.get_current_project(),
                    current_error=current_error,
                    current_file=current_file,
                    user_state=self.user_state
                )

                if sql_hints:
                    logger.debug(f"Retrieved {len(sql_hints)} SQL hints")

            except Exception as e:
                logger.warning(f"Failed to get SQL hints: {e}")
                sql_hints = []
                # Fail-safe: continue without SQL hints

        # Prepare activity dict for whisperer
        activity = {
            'current_project': self.get_current_project(),
            'recent_errors': self.recent_errors,
            'recent_files_changed': self.recent_files_changed,
            'recent_commands': self.recent_commands,
            'user_state': self.user_state,
            'sql_hints': sql_hints  # NEW: Include SQL hints
        }

        # NEW: Use Human-AI Whisperer to create WOW context
        wow_context = self.whisperer.create_wow_context(user_prompt, activity)

        # Compress if needed
        if self.needs_compression(wow_context):
            logger.info("🗜️  Compressing context...")
            wow_context = self.apply_rl_compression(wow_context)

        logger.info(f"✨ WOW context prepared: {len(wow_context)} chars for {ai_platform}")

        return wow_context

    def get_recent_events(self, limit: int = 10) -> list:
        """
        Return the last N events from the context window.
        Required by dashboard RPC handlers.

        Args:
            limit: Maximum number of events to return (default: 10)

        Returns:
            List of recent event dictionaries

        Note: Rule II (None-Safe) - Uses .get() for safe access
        """
        # Safe extraction with .get() in case entry structure is malformed
        return [
            entry.get('event', {})
            for entry in list(self.context_window)[-limit:]
            if isinstance(entry, dict)
        ]

    def get_current_project(self) -> str:
        """Get current project path from recent activity"""
        if self.recent_files_changed:
            # Get most recent file's project
            recent_file = self.recent_files_changed[-1].get('project', '')
            if recent_file:
                return recent_file
        return '/home/user/vidurai'  # fallback
