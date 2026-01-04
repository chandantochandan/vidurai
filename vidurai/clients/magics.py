"""
Vidurai Jupyter Magics
======================

IPython cell magics for Vidurai integration.

Usage:
    # In Jupyter notebook, first load the extension:
    %load_ext vidurai.clients.magics

    # Then use the %%remember magic:
    %%remember
    def analyze_data(df):
        '''Analyzes user retention data'''
        return df.groupby('cohort').mean()

    # Or with metadata:
    %%remember --salience high --tags retention,analysis
    # Analysis: User retention improved by 15% in Q4

The cell content is sent to the Vidurai daemon and becomes part of
your project's shared memory (visible in VS Code, etc.)
"""

import argparse
import shlex
from typing import Optional

try:
    from IPython.core.magic import Magics, magics_class, cell_magic, line_magic
    from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
    from IPython import get_ipython
    HAS_IPYTHON = True
except ImportError:
    HAS_IPYTHON = False
    # Stub classes for when IPython is not available
    class Magics:
        pass
    def magics_class(cls):
        return cls
    def cell_magic(name):
        def decorator(func):
            return func
        return decorator
    def line_magic(name):
        def decorator(func):
            return func
        return decorator
    def magic_arguments():
        def decorator(func):
            return func
        return decorator
    def argument(*args, **kwargs):
        def decorator(func):
            return func
        return decorator
    def parse_argstring(func, line):
        return argparse.Namespace()
    def get_ipython():
        return None

from .jupyter_client import ViduraiLive, ViduraiLiveError


# Global client instance (lazy-initialized)
_vidurai_client: Optional[ViduraiLive] = None


def get_client() -> ViduraiLive:
    """Get or create the global ViduraiLive client."""
    global _vidurai_client
    if _vidurai_client is None:
        _vidurai_client = ViduraiLive()
    return _vidurai_client


@magics_class
class ViduraiMagics(Magics):
    """
    Vidurai IPython magics for memory integration.

    Provides:
    - %%remember: Store cell content in project memory
    - %vidurai_status: Check daemon connection status
    - %vidurai_context: Get current project context
    """

    def __init__(self, shell=None):
        super().__init__(shell)
        self.client = get_client()

    @magic_arguments()
    @argument(
        '--salience', '-s',
        type=str,
        default='medium',
        choices=['critical', 'high', 'medium', 'low'],
        help='Memory importance level'
    )
    @argument(
        '--tags', '-t',
        type=str,
        default='',
        help='Comma-separated tags for the memory'
    )
    @argument(
        '--notebook', '-n',
        type=str,
        default='',
        help='Notebook name (auto-detected if not provided)'
    )
    @argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress output messages'
    )
    @cell_magic('remember')
    def remember(self, line: str, cell: str):
        """
        Store cell content in Vidurai project memory.

        Usage:
            %%remember
            # Your code or analysis here...

            %%remember --salience high
            # Important insight or code

            %%remember --tags feature,auth --salience critical
            def authenticate_user(credentials):
                '''Critical auth function'''
                pass

        The cell content is sent to the Vidurai daemon and becomes
        part of your project's shared context.
        """
        args = parse_argstring(self.remember, line)

        # Build metadata
        metadata = {
            'language': 'python',
            'source': 'jupyter_magic'
        }

        if args.tags:
            metadata['tags'] = [t.strip() for t in args.tags.split(',')]

        if args.notebook:
            metadata['file_path'] = args.notebook
        else:
            # Try to get notebook name from IPython
            try:
                if self.shell and hasattr(self.shell, 'user_ns'):
                    # Check for notebook name in various places
                    for key in ['__session__', '__file__']:
                        if key in self.shell.user_ns:
                            metadata['file_path'] = str(self.shell.user_ns[key])
                            break
            except Exception:
                pass

        try:
            success = self.client.remember(
                content=cell,
                salience=args.salience,
                metadata=metadata
            )

            if not args.quiet:
                if success:
                    print(f"✅ Remembered ({args.salience}): {cell[:50]}...")
                else:
                    print("⚠️ Failed to remember content")

        except ViduraiLiveError as e:
            if not args.quiet:
                print(f"❌ Error: {e}")
                print("   Is the Vidurai daemon running?")

    @line_magic('vidurai_status')
    def status(self, line: str):
        """
        Check Vidurai daemon connection status.

        Usage:
            %vidurai_status
        """
        try:
            if self.client.is_connected():
                health = self.client.get_health()
                print(f"✅ Connected to Vidurai Daemon v{health.get('version', '?')}")
                print(f"   Uptime: {health.get('uptime_human', '?')}")
                print(f"   Projects: {health.get('watched_projects', 0)}")
            else:
                print("❌ Not connected to Vidurai daemon")
                print("   Start daemon with: vidurai-daemon")
        except Exception as e:
            print(f"❌ Error checking status: {e}")

    @magic_arguments()
    @argument(
        '--audience', '-a',
        type=str,
        default='ai',
        choices=['developer', 'ai', 'manager'],
        help='Target audience for context'
    )
    @argument(
        '--limit', '-l',
        type=int,
        default=200,
        help='Max characters to display'
    )
    @line_magic('vidurai_context')
    def context(self, line: str):
        """
        Get current project context from daemon.

        Usage:
            %vidurai_context
            %vidurai_context --audience developer
            %vidurai_context --limit 500
        """
        args = parse_argstring(self.context, line)

        try:
            ctx = self.client.get_context(audience=args.audience)
            if ctx:
                display_text = ctx[:args.limit]
                if len(ctx) > args.limit:
                    display_text += f"\n... [{len(ctx) - args.limit} more chars]"
                print(display_text)
            else:
                print("📭 No context available")
        except ViduraiLiveError as e:
            print(f"❌ Error getting context: {e}")

    @magic_arguments()
    @argument(
        '--profile', '-p',
        type=str,
        choices=['cost_focused', 'balanced', 'quality_focused'],
        help='Memory profile to set'
    )
    @line_magic('vidurai_profile')
    def profile(self, line: str):
        """
        Get or set memory profile.

        Usage:
            %vidurai_profile
            %vidurai_profile --profile cost_focused
            %vidurai_profile -p quality_focused
        """
        args = parse_argstring(self.profile, line)

        if args.profile:
            try:
                success = self.client.set_profile(args.profile)
                if success:
                    print(f"✅ Profile set to: {args.profile}")
                else:
                    print(f"❌ Failed to set profile")
            except ViduraiLiveError as e:
                print(f"❌ Error: {e}")
        else:
            # Just show stats
            try:
                stats = self.client.get_stats()
                print(f"📊 Brain Stats:")
                print(f"   Projects: {stats.get('projects_tracked', '?')}")
                print(f"   Current: {stats.get('current_project', 'None')}")
            except ViduraiLiveError as e:
                print(f"❌ Error: {e}")


def load_ipython_extension(ipython):
    """
    Load the Vidurai magics extension.

    Called when user runs: %load_ext vidurai.clients.magics
    """
    if ipython is None:
        print("❌ Cannot load Vidurai magics: IPython not available")
        return

    ipython.register_magics(ViduraiMagics)
    print("✅ Vidurai magics loaded!")
    print("   Available:")
    print("   - %%remember      : Store cell in project memory")
    print("   - %vidurai_status : Check daemon connection")
    print("   - %vidurai_context: Get project context")
    print("   - %vidurai_profile: Get/set memory profile")


def unload_ipython_extension(ipython):
    """Unload the extension."""
    global _vidurai_client
    _vidurai_client = None


# Auto-register when imported in IPython environment
if HAS_IPYTHON:
    ip = get_ipython()
    if ip is not None:
        # Only auto-load if we're in an interactive IPython session
        # and not being imported as a module
        pass  # Don't auto-load, let user decide with %load_ext
