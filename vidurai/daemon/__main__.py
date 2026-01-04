"""
Vidurai Daemon Entry Point

Allows running the daemon as a Python module:
    python -m vidurai.daemon

@version 2.2.0-Guardian
"""

from .server import main

if __name__ == "__main__":
    main()
