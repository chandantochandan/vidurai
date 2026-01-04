"""
Vidurai MCP Installer
Installs Vidurai as an MCP server for Claude Desktop and other AI clients.
Sprint 1 - The Connector

Architecture:
- Detects OS and finds correct config path
- Preserves existing config entries
- Creates backup before modification
- Uses sys.executable for correct Python path
"""

import json
import os
import platform
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from loguru import logger


def get_claude_config_path() -> Path:
    """
    Get Claude Desktop config path based on OS.

    Returns:
        Path to claude_desktop_config.json
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        config_path = Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    elif system == "Windows":
        # Use APPDATA on Windows
        appdata = os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")
        config_path = Path(appdata) / "Claude" / "claude_desktop_config.json"
    else:  # Linux and others
        # XDG config or fallback
        xdg_config = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
        config_path = Path(xdg_config) / "Claude" / "claude_desktop_config.json"

    return config_path


def install_mcp_server(config_path: Optional[Path] = None, dry_run: bool = False) -> Tuple[bool, str]:
    """
    Install Vidurai as an MCP server for Claude Desktop.

    Args:
        config_path: Optional custom config path (for testing)
        dry_run: If True, only show what would be done without modifying files

    Returns:
        Tuple of (success: bool, message: str)
    """
    if config_path is None:
        config_path = get_claude_config_path()

    config_path = Path(config_path)

    # Log to stderr (stdout reserved for JSON output in CLI)
    print(f"[Vidurai MCP Installer]", file=sys.stderr)
    print(f"  Config path: {config_path}", file=sys.stderr)
    print(f"  Python executable: {sys.executable}", file=sys.stderr)

    # Build the MCP server entry
    mcp_entry = {
        "command": sys.executable,
        "args": ["-m", "vidurai.mcp_server"]
    }

    if dry_run:
        print(f"\n[DRY RUN] Would add entry:", file=sys.stderr)
        print(f"  \"vidurai\": {json.dumps(mcp_entry, indent=2)}", file=sys.stderr)
        return True, "Dry run completed"

    # Ensure parent directory exists
    os.makedirs(config_path.parent, exist_ok=True)

    # Load existing config or create new
    config = {}
    if config_path.exists():
        # Create backup before modification
        backup_path = config_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        try:
            shutil.copy2(config_path, backup_path)
            print(f"  Backup created: {backup_path}", file=sys.stderr)
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
            print(f"  Warning: Could not create backup: {e}", file=sys.stderr)

        # Read existing config
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            print(f"  Loaded existing config with {len(config)} top-level keys", file=sys.stderr)
        except json.JSONDecodeError as e:
            print(f"  Warning: Existing config is invalid JSON: {e}", file=sys.stderr)
            print(f"  Creating fresh config...", file=sys.stderr)
            config = {}
    else:
        print(f"  No existing config found, creating new...", file=sys.stderr)

    # Ensure mcpServers dict exists
    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Check if already installed
    existing = config["mcpServers"].get("vidurai")
    if existing:
        print(f"  Existing vidurai entry found, updating...", file=sys.stderr)
    else:
        print(f"  Adding new vidurai entry...", file=sys.stderr)

    # Add/update vidurai entry
    config["mcpServers"]["vidurai"] = mcp_entry

    # Write config with indentation
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"\n[SUCCESS] Vidurai MCP server installed!", file=sys.stderr)
        print(f"  Restart Claude Desktop to activate.", file=sys.stderr)
        return True, f"MCP server installed to {config_path}"
    except Exception as e:
        error_msg = f"Failed to write config: {e}"
        print(f"\n[ERROR] {error_msg}", file=sys.stderr)
        return False, error_msg


def uninstall_mcp_server(config_path: Optional[Path] = None) -> Tuple[bool, str]:
    """
    Remove Vidurai from Claude Desktop MCP servers.

    Args:
        config_path: Optional custom config path (for testing)

    Returns:
        Tuple of (success: bool, message: str)
    """
    if config_path is None:
        config_path = get_claude_config_path()

    config_path = Path(config_path)

    print(f"[Vidurai MCP Uninstaller]", file=sys.stderr)
    print(f"  Config path: {config_path}", file=sys.stderr)

    if not config_path.exists():
        return False, "Config file does not exist"

    # Create backup
    backup_path = config_path.with_suffix(f".bak.{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    try:
        shutil.copy2(config_path, backup_path)
        print(f"  Backup created: {backup_path}", file=sys.stderr)
    except Exception as e:
        print(f"  Warning: Could not create backup: {e}", file=sys.stderr)

    # Load config
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
    except Exception as e:
        return False, f"Failed to read config: {e}"

    # Check if vidurai exists
    if "mcpServers" not in config or "vidurai" not in config.get("mcpServers", {}):
        return False, "Vidurai MCP server not found in config"

    # Remove vidurai entry
    del config["mcpServers"]["vidurai"]
    print(f"  Removed vidurai entry", file=sys.stderr)

    # Write config
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"\n[SUCCESS] Vidurai MCP server uninstalled!", file=sys.stderr)
        return True, "MCP server uninstalled"
    except Exception as e:
        return False, f"Failed to write config: {e}"


def check_mcp_status(config_path: Optional[Path] = None) -> dict:
    """
    Check current MCP installation status.

    Returns:
        Dict with status information
    """
    if config_path is None:
        config_path = get_claude_config_path()

    config_path = Path(config_path)

    status = {
        "config_path": str(config_path),
        "config_exists": config_path.exists(),
        "vidurai_installed": False,
        "vidurai_config": None,
        "other_servers": []
    }

    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            mcp_servers = config.get("mcpServers", {})

            if "vidurai" in mcp_servers:
                status["vidurai_installed"] = True
                status["vidurai_config"] = mcp_servers["vidurai"]

            status["other_servers"] = [k for k in mcp_servers.keys() if k != "vidurai"]

        except Exception as e:
            status["error"] = str(e)

    return status
