"""
Vidurai Clients - Live Mode for External Tools
===============================================

This module provides lightweight clients that connect to the Vidurai Daemon
instead of loading a separate VismritiMemory instance (avoiding Split Brain).

Usage:
    from vidurai.clients import ViduraiLive

    client = ViduraiLive()
    context = client.get_context()
    print(context)

Jupyter Magics:
    # In notebook, load the extension:
    %load_ext vidurai.clients.magics

    # Use the remember magic:
    %%remember
    def my_analysis():
        pass
"""

from .jupyter_client import ViduraiLive, ViduraiLiveError, DaemonNotFoundError

__all__ = ['ViduraiLive', 'ViduraiLiveError', 'DaemonNotFoundError']
