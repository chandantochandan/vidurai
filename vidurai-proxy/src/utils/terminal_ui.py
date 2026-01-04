"""
Terminal UI
Beautiful terminal output showing transparent proxy operations
Inspired by Claude Code's transparent progress display
"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box
from datetime import datetime
from typing import Optional

console = Console()

class TerminalUI:
    """
    Terminal UI for displaying proxy operations with transparency

    Features:
    - Startup banner with configuration
    - Real-time request processing display
    - Vidurai compression statistics
    - Token savings metrics
    - Error reporting
    """

    def __init__(self, config):
        """
        Initialize terminal UI

        Args:
            config: Config object from config_loader
        """
        self.config = config
        self.console = Console()

    def show_startup_banner(self):
        """Display startup banner with configuration"""

        banner_text = f"""[bold cyan]VIDURAI PROXY SERVER[/bold cyan]
[dim]Universal AI Memory Management Proxy[/dim]

[yellow]विस्मृति भी विद्या है[/yellow]
[dim](Forgetting too is knowledge)[/dim]

[green]Configuration:[/green]
  • Host: [cyan]{self.config.server.host}:{self.config.server.port}[/cyan]
  • Vidurai Profile: [cyan]{self.config.vidurai.reward_profile}[/cyan]
  • Compression: [cyan]{'Enabled' if self.config.vidurai.compression_enabled else 'Disabled'}[/cyan]
  • Threshold: [cyan]{self.config.vidurai.compression_threshold} messages[/cyan]
  • Decay: [cyan]{'Enabled' if self.config.vidurai.enable_decay else 'Disabled'}[/cyan]
  • Min Importance: [cyan]{self.config.vidurai.min_importance}[/cyan]

[bold green]Ready to accept requests![/bold green]

[yellow]जय विदुराई! 🕉️[/yellow]
        """

        panel = Panel(
            banner_text,
            title="[bold white]Vidurai Proxy v1.0.0[/bold white]",
            border_style="cyan",
            box=box.DOUBLE,
            padding=(1, 2)
        )

        self.console.print()
        self.console.print(panel)
        self.console.print()

    def show_request_received(self, method: str, path: str, provider: str):
        """
        Show incoming request

        Args:
            method: HTTP method (POST, GET, etc.)
            path: Request path
            provider: Detected provider name
        """
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.console.print(
            f"[dim]{timestamp}[/dim] "
            f"[yellow]→[/yellow] "
            f"[bold white]{method}[/bold white] "
            f"[cyan]{path}[/cyan] "
            f"[dim]({provider})[/dim]"
        )

    def show_processing(self, message_count: int, token_estimate: int):
        """
        Show Vidurai processing step

        Args:
            message_count: Number of messages being processed
            token_estimate: Estimated token count
        """
        self.console.print(
            f"   [cyan]🧠 Processing {message_count} messages "
            f"(~{token_estimate:,} tokens)[/cyan]"
        )

    def show_vidurai_layers(self):
        """Show Vidurai's three-kosha processing"""
        self.console.print(
            f"   [dim]├─ Annamaya Kosha:[/dim] [cyan]Working memory cache[/cyan]"
        )
        self.console.print(
            f"   [dim]├─ Manomaya Kosha:[/dim] [cyan]Episodic archival[/cyan]"
        )
        self.console.print(
            f"   [dim]├─ Vismriti Engine:[/dim] [cyan]Strategic compression[/cyan]"
        )
        self.console.print(
            f"   [dim]└─ Viveka Layer:[/dim] [cyan]Importance filtering[/cyan]"
        )

    def show_compression(
        self,
        before: int,
        after: int,
        session_total_saved: int = 0
    ):
        """
        Show compression results

        Args:
            before: Token count before compression
            after: Token count after compression
            session_total_saved: Total tokens saved in session
        """
        saved = before - after
        pct = (saved / before * 100) if before > 0 else 0

        self.console.print(
            f"   [green]✓[/green] Compressed: "
            f"[white]{before:,}[/white] → [white]{after:,}[/white] tokens "
            f"[dim]({pct:.1f}% reduction)[/dim]"
        )

        if session_total_saved > 0:
            self.console.print(
                f"   [dim]Session total: {session_total_saved:,} tokens saved[/dim]"
            )

    def show_forwarding(self, provider: str, target_url: str):
        """
        Show forwarding to provider API

        Args:
            provider: Provider name
            target_url: Target URL (optional, for debugging)
        """
        self.console.print(
            f"   [blue]→[/blue] Forwarding to [cyan]{provider}[/cyan] API"
        )

    def show_response(
        self,
        status: int,
        elapsed_ms: float,
        cost_saved: Optional[float] = None
    ):
        """
        Show response received

        Args:
            status: HTTP status code
            elapsed_ms: Request duration in milliseconds
            cost_saved: Cost saved in dollars (optional)
        """
        status_color = "green" if status == 200 else "red"
        status_icon = "✓" if status == 200 else "✗"

        response_text = (
            f"   [green]{status_icon}[/green] Response: "
            f"[{status_color}]{status}[/{status_color}] "
            f"[dim]({elapsed_ms:.0f}ms)[/dim]"
        )

        if cost_saved and cost_saved > 0:
            response_text += f" [yellow]💰 ${cost_saved:.6f} saved[/yellow]"

        self.console.print(response_text)
        self.console.print()  # Blank line between requests

    def show_error(self, error: str, details: Optional[str] = None):
        """
        Show error message

        Args:
            error: Error message
            details: Optional error details
        """
        self.console.print(f"   [red]✗ Error:[/red] [white]{error}[/white]")

        if details:
            self.console.print(f"   [dim]{details}[/dim]")

        self.console.print()

    def show_session_stats(
        self,
        requests: int,
        tokens_saved: int,
        cost_saved: float,
        reduction_pct: float
    ):
        """
        Show session statistics summary

        Args:
            requests: Number of requests processed
            tokens_saved: Total tokens saved
            cost_saved: Total cost saved
            reduction_pct: Average reduction percentage
        """
        stats_text = f"""[bold]Session Statistics[/bold]

[cyan]Requests:[/cyan] {requests}
[cyan]Tokens Saved:[/cyan] {tokens_saved:,} ({reduction_pct:.1f}% avg reduction)
[cyan]Cost Saved:[/cyan] ${cost_saved:.4f}
        """

        panel = Panel(
            stats_text,
            title="[bold]💾 Savings Summary[/bold]",
            border_style="green",
            box=box.ROUNDED
        )

        self.console.print(panel)
        self.console.print()

    def show_shutdown(self, total_savings: dict):
        """
        Show shutdown message with total savings

        Args:
            total_savings: Dictionary with total statistics
        """
        shutdown_text = f"""[bold yellow]Vidurai Proxy Server shutting down[/bold yellow]

[dim]Session Summary:[/dim]
  • Requests: [cyan]{total_savings.get('requests', 0)}[/cyan]
  • Tokens Saved: [cyan]{total_savings.get('tokens_saved', 0):,}[/cyan]
  • Cost Saved: [cyan]${total_savings.get('cost_saved', 0):.4f}[/cyan]

[yellow]जय विदुराई! 🕉️[/yellow]
        """

        self.console.print()
        self.console.print(Panel(
            shutdown_text,
            border_style="yellow",
            box=box.DOUBLE
        ))
        self.console.print()


def create_ui(config) -> TerminalUI:
    """
    Factory function to create TerminalUI instance

    Args:
        config: Config object

    Returns:
        TerminalUI instance
    """
    return TerminalUI(config)
