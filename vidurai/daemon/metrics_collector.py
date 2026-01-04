#!/usr/bin/env python3
"""
Metrics collection for website stats and monitoring
Tracks tokens saved, contexts served, money saved, etc.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import logging

logger = logging.getLogger("vidurai.metrics")

class MetricsCollector:
    """Collect and calculate metrics for dashboard and website"""

    def __init__(self):
        self.start_time = datetime.now()
        self.tokens_saved_total = 0
        self.tokens_saved_today = 0
        self.contexts_served = 0
        self.files_analyzed = 0
        self.projects_watched = 0
        self.last_reset = datetime.now()

    def record_context_served(self, tokens_before: int, tokens_after: int):
        """Record when context is served to an AI tool"""
        tokens_saved = tokens_before - tokens_after

        self.tokens_saved_total += tokens_saved
        self.tokens_saved_today += tokens_saved
        self.contexts_served += 1

        logger.debug(f"💰 Tokens saved: {tokens_saved} (Total: {self.tokens_saved_total})")

    def calculate_money_saved(self) -> float:
        """Calculate money saved based on GPT-4 pricing"""
        # GPT-4 pricing: ~$0.03 per 1K tokens (average of input/output)
        return (self.tokens_saved_total / 1000) * 0.03

    def calculate_token_reduction_percentage(self, original: int, compressed: int) -> float:
        """Calculate percentage reduction"""
        if original == 0:
            return 0.0
        return ((original - compressed) / original) * 100

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary"""
        uptime = datetime.now() - self.start_time

        return {
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": self._format_uptime(uptime),
            "tokens_saved_total": self.tokens_saved_total,
            "tokens_saved_today": self.tokens_saved_today,
            "contexts_served": self.contexts_served,
            "money_saved_usd": round(self.calculate_money_saved(), 2),
            "files_analyzed": self.files_analyzed,
            "projects_watched": self.projects_watched,
            "average_tokens_per_context": (
                self.tokens_saved_total // self.contexts_served
                if self.contexts_served > 0 else 0
            )
        }

    def _format_uptime(self, delta: timedelta) -> str:
        """Format uptime as human-readable string"""
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60

        if hours > 24:
            days = hours // 24
            hours = hours % 24
            return f"{days}d {hours}h {minutes}m"
        elif hours > 0:
            return f"{hours}h {minutes}m {seconds}s"
        elif minutes > 0:
            return f"{minutes}m {seconds}s"
        else:
            return f"{seconds}s"

    def reset_daily_stats(self):
        """Reset daily statistics (should be called at midnight)"""
        self.tokens_saved_today = 0
        self.last_reset = datetime.now()
        logger.info("📊 Daily metrics reset")

    def should_reset_daily(self) -> bool:
        """Check if it's time to reset daily stats"""
        now = datetime.now()
        return now.date() > self.last_reset.date()
