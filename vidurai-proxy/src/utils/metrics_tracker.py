"""
Metrics Tracker
Tracks token savings, cost savings, and performance metrics
Provides real-time statistics for terminal UI display
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

@dataclass
class SessionMetrics:
    """
    Metrics for a single session

    Tracks:
    - Request count
    - Token usage (before/after compression)
    - Cost savings
    - Performance timing
    """
    session_id: str
    requests: int = 0
    original_tokens: int = 0
    compressed_tokens: int = 0
    tokens_saved: int = 0
    cost_saved: float = 0.0
    total_time_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    last_request: Optional[datetime] = None

    def update(
        self,
        original: int,
        compressed: int,
        elapsed_ms: float,
        input_cost_per_m: float
    ):
        """
        Update metrics with new request data

        Args:
            original: Original token count
            compressed: Compressed token count
            elapsed_ms: Request duration in milliseconds
            input_cost_per_m: Cost per million input tokens
        """
        self.requests += 1
        self.original_tokens += original
        self.compressed_tokens += compressed
        self.tokens_saved = self.original_tokens - self.compressed_tokens
        self.total_time_ms += elapsed_ms
        self.last_request = datetime.now()

        # Calculate cost saved (input tokens only)
        self.cost_saved = (self.tokens_saved / 1_000_000) * input_cost_per_m

    @property
    def reduction_percentage(self) -> float:
        """Calculate token reduction percentage"""
        if self.original_tokens == 0:
            return 0.0
        return (self.tokens_saved / self.original_tokens) * 100

    @property
    def avg_time_ms(self) -> float:
        """Calculate average request time"""
        if self.requests == 0:
            return 0.0
        return self.total_time_ms / self.requests


class MetricsTracker:
    """
    Track metrics across all sessions

    Features:
    - Per-session metrics
    - Global aggregate metrics
    - Real-time cost calculations
    - Performance tracking
    """

    def __init__(self, config):
        """
        Initialize metrics tracker

        Args:
            config: Config object from config_loader
        """
        self.config = config
        self.sessions: Dict[str, SessionMetrics] = {}

        logger.info("MetricsTracker initialized")

    def record_request(
        self,
        session_id: str,
        original_tokens: int,
        compressed_tokens: int,
        elapsed_ms: float
    ) -> SessionMetrics:
        """
        Record metrics for a request

        Args:
            session_id: Session identifier
            original_tokens: Token count before compression
            compressed_tokens: Token count after compression
            elapsed_ms: Request duration in milliseconds

        Returns:
            Updated SessionMetrics for this session
        """

        # Get or create session metrics
        if session_id not in self.sessions:
            self.sessions[session_id] = SessionMetrics(session_id=session_id)

        metrics = self.sessions[session_id]

        # Update metrics
        metrics.update(
            original=original_tokens,
            compressed=compressed_tokens,
            elapsed_ms=elapsed_ms,
            input_cost_per_m=self.config.metrics.input_cost_per_million
        )

        logger.debug(
            f"Session {session_id[:8]}... metrics updated: "
            f"{metrics.tokens_saved:,} tokens saved "
            f"({metrics.reduction_percentage:.1f}% reduction)"
        )

        return metrics

    def get_session_metrics(self, session_id: str) -> SessionMetrics:
        """
        Get metrics for a specific session

        Args:
            session_id: Session identifier

        Returns:
            SessionMetrics for this session (empty if not found)
        """
        return self.sessions.get(
            session_id,
            SessionMetrics(session_id=session_id)
        )

    def get_global_metrics(self) -> dict:
        """
        Get aggregate metrics across all sessions

        Returns:
            Dictionary with global statistics
        """
        total_sessions = len(self.sessions)
        total_requests = sum(m.requests for m in self.sessions.values())
        total_original = sum(m.original_tokens for m in self.sessions.values())
        total_compressed = sum(m.compressed_tokens for m in self.sessions.values())
        total_saved = sum(m.tokens_saved for m in self.sessions.values())
        total_cost_saved = sum(m.cost_saved for m in self.sessions.values())
        total_time = sum(m.total_time_ms for m in self.sessions.values())

        # Calculate averages
        reduction_pct = (total_saved / total_original * 100) if total_original > 0 else 0
        avg_time = (total_time / total_requests) if total_requests > 0 else 0

        return {
            'sessions': total_sessions,
            'requests': total_requests,
            'original_tokens': total_original,
            'compressed_tokens': total_compressed,
            'tokens_saved': total_saved,
            'reduction_percentage': reduction_pct,
            'cost_saved': total_cost_saved,
            'avg_time_ms': avg_time
        }

    def get_top_sessions(self, limit: int = 5) -> list:
        """
        Get sessions with most token savings

        Args:
            limit: Number of sessions to return

        Returns:
            List of SessionMetrics sorted by tokens_saved
        """
        sorted_sessions = sorted(
            self.sessions.values(),
            key=lambda m: m.tokens_saved,
            reverse=True
        )
        return sorted_sessions[:limit]

    def calculate_cost_saved(
        self,
        tokens_saved: int,
        is_input: bool = True
    ) -> float:
        """
        Calculate cost saved for given token count

        Args:
            tokens_saved: Number of tokens saved
            is_input: If True, use input cost; else output cost

        Returns:
            Cost saved in dollars
        """
        cost_per_m = (
            self.config.metrics.input_cost_per_million if is_input
            else self.config.metrics.output_cost_per_million
        )

        return (tokens_saved / 1_000_000) * cost_per_m

    def reset_session(self, session_id: str):
        """
        Reset metrics for a session

        Args:
            session_id: Session to reset
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Reset metrics for session: {session_id[:8]}...")

    def reset_all(self):
        """Reset all metrics"""
        self.sessions.clear()
        logger.info("Reset all metrics")

    def get_summary_report(self) -> str:
        """
        Generate text summary report

        Returns:
            Formatted summary string
        """
        global_metrics = self.get_global_metrics()

        report = f"""
METRICS SUMMARY
{'='*60}

Sessions:          {global_metrics['sessions']}
Total Requests:    {global_metrics['requests']}

TOKEN ANALYSIS:
  Original:        {global_metrics['original_tokens']:,}
  Compressed:      {global_metrics['compressed_tokens']:,}
  Saved:           {global_metrics['tokens_saved']:,}
  Reduction:       {global_metrics['reduction_percentage']:.1f}%

COST SAVINGS:
  Total Saved:     ${global_metrics['cost_saved']:.4f}

PERFORMANCE:
  Avg Time:        {global_metrics['avg_time_ms']:.0f}ms
"""

        return report
