"""
Vidurai Integration for Claude Code
Wraps Claude Code's conversation management with Vidurai memory
"""

from vidurai import ViduraiMemory
import json
import os
from datetime import datetime

class ClaudeCodeViduriWrapper:
    """
    Wrapper that integrates Vidurai with Claude Code conversations
    """

    def __init__(self, session_id: str = None):
        """Initialize Vidurai for Claude Code session"""

        self.session_id = session_id or f"claude-code-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        # Initialize Vidurai with optimal settings for coding sessions
        # Note: Using version 0.2.1 API (installed version)
        self.vidurai = ViduraiMemory()

        self.message_count = 0
        self.total_tokens_before = 0
        self.total_tokens_after = 0

        print(f"🕉️ Vidurai initialized for session: {self.session_id}")

    def add_message(self, role: str, content: str, metadata: dict = None):
        """
        Add a message to Vidurai memory

        Args:
            role: 'user' or 'assistant'
            content: Message content
            metadata: Optional metadata (file context, code snippets, etc.)
        """

        self.message_count += 1

        # Track tokens before
        tokens_before = len(content.split())  # Rough estimate
        self.total_tokens_before += tokens_before

        # Remember in Vidurai
        self.vidurai.remember(
            content=content,
            metadata={
                "role": role,
                "session_id": self.session_id,
                "message_number": self.message_count,
                **(metadata or {})
            }
        )

        print(f"📝 Message {self.message_count} added ({tokens_before} tokens)")

    def get_context_for_claude(self, query: str = None, max_messages: int = 20):
        """
        Get optimized context for Claude Code's next request

        Args:
            query: Optional current query to find relevant context
            max_messages: Maximum number of messages to include

        Returns:
            List of relevant messages optimized by Vidurai
        """

        # Get relevant memories from Vidurai (v0.2.1 API)
        all_memories = self.vidurai.recall(query=query)

        # Take top N by importance
        relevant_memories = all_memories[:max_messages]

        # Format for Claude Code
        context_messages = []
        total_tokens = 0

        for mem in relevant_memories:
            context_messages.append({
                "role": mem.metadata.get("role", "user"),
                "content": mem.content,
                "importance": mem.importance
            })
            total_tokens += len(mem.content.split())

        self.total_tokens_after += total_tokens

        print(f"🧠 Retrieved {len(context_messages)} relevant messages ({total_tokens} tokens)")

        return context_messages

    def get_savings_report(self):
        """Get token savings report"""

        savings = self.total_tokens_before - self.total_tokens_after
        savings_pct = (savings / self.total_tokens_before * 100) if self.total_tokens_before > 0 else 0

        report = f"""
╔══════════════════════════════════════════════════════════╗
║           VIDURAI SAVINGS REPORT - CLAUDE CODE          ║
╚══════════════════════════════════════════════════════════╝

Session ID: {self.session_id}
Messages Processed: {self.message_count}

📊 TOKEN ANALYSIS:
  Original Tokens:    {self.total_tokens_before:,}
  After Compression:  {self.total_tokens_after:,}
  Tokens Saved:       {savings:,}
  Reduction:          {savings_pct:.1f}%

💰 COST SAVINGS (Claude Sonnet 4.5):
  Input cost: $3/M tokens
  Saved: ${(savings / 1_000_000 * 3):.4f}

🕉️ विस्मृति भी विद्या है (Forgetting too is knowledge)

जय विदुराई!
        """

        return report
